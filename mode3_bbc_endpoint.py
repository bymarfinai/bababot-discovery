"""Mode3 BBC Backtest Endpoint — v2.6 with exit_on_state_change support."""
import os
from dataclasses import asdict
from fastapi import APIRouter, Query
import sqlite3, numpy as np
from datetime import datetime
from mode3_bbc import Mode3BBCConfig, Switcher, compute_ema_series, compute_va_at_bar
from mode3_bbc.config import preset_a, preset_b, preset_c, preset_d
from mode3_bbc.switcher import Trade

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc"])
DB_PATH = os.environ.get("DB_PATH", "market_data.db")

def load_candles_from_db(symbol, timeframe, start_ts, end_ts):
    conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
    cur.execute("SELECT open_time, open, high, low, close, volume FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<? ORDER BY open_time ASC", (symbol, timeframe, start_ts, end_ts))
    rows = cur.fetchall(); conn.close(); return rows
def compute_mtf_bull_entry(rows_1h, rows_15m):
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
    o15=np.array([r[1] for r in rows_15m],dtype=float); l15=np.array([r[3] for r in rows_15m],dtype=float); c15=np.array([r[4] for r in rows_15m],dtype=float)
    ema15=compute_ema_series(c15,20); idx={r[0]:i for i,r in enumerate(rows_15m)}; M=15*60*1000; ec,el=[],[]
    for r in rows_1h:
        t=r[0]; fc,fl=None,None
        for k in range(4):
            j=idx.get(t+k*M)
            if j is not None and l15[j]<=ema15[j] and c15[j]>ema15[j] and c15[j]>o15[j]: fc=float(c15[j]); fl=float(l15[j]); break
        ec.append(fc); el.append(fl)
    return ec,el
def compute_mtf_bear_entry(rows_1h, rows_15m):
    if not rows_15m: return [None]*len(rows_1h), [None]*len(rows_1h)
    o15=np.array([r[1] for r in rows_15m],dtype=float); h15=np.array([r[2] for r in rows_15m],dtype=float); c15=np.array([r[4] for r in rows_15m],dtype=float)
    ema15=compute_ema_series(c15,20); idx={r[0]:i for i,r in enumerate(rows_15m)}; M=15*60*1000; ec,eh=[],[]
    for r in rows_1h:
        t=r[0]; fc,fh=None,None
        for k in range(4):
            j=idx.get(t+k*M)
            if j is not None and h15[j]>=ema15[j] and c15[j]<ema15[j] and c15[j]<o15[j]: fc=float(c15[j]); fh=float(h15[j]); break
        ec.append(fc); eh.append(fh)
    return ec,eh
def compute_mtf_sideways_entry(rows_1h, rows_15m, vahs, vals):
    n=len(rows_1h)
    if not rows_15m: return [None]*n,[None]*n,[None]*n,[None]*n
    h15=np.array([r[2] for r in rows_15m],dtype=float); l15=np.array([r[3] for r in rows_15m],dtype=float); c15=np.array([r[4] for r in rows_15m],dtype=float)
    idx={r[0]:i for i,r in enumerate(rows_15m)}; M=15*60*1000; sc,sh,lc,ll=[],[],[],[]
    for i,r in enumerate(rows_1h):
        t=r[0]; vah=vahs[i]; val=vals[i]; s_c,s_h,l_c,l_l=None,None,None,None
        if vah is None or val is None: sc.append(None);sh.append(None);lc.append(None);ll.append(None); continue
        for k in range(4):
            j=idx.get(t+k*M)
            if j is None: continue
            if s_c is None and h15[j]>=vah and c15[j]<=vah: s_c=float(c15[j]); s_h=float(h15[j])
            if l_c is None and l15[j]<=val and c15[j]>=val: l_c=float(c15[j]); l_l=float(l15[j])
            if s_c is not None and l_c is not None: break
        sc.append(s_c);sh.append(s_h);lc.append(l_c);ll.append(l_l)
    return sc,sh,lc,ll

@router.get("/presets")
def get_presets():
    return {
        "A": {"name": "Max PnL WR>=70%", "desc": "BULL TP1.3/SL2.0, BEAR TP1.5/SL2.0", "params": preset_a()},
        "B": {"name": "Symmetric R:R 1:1", "desc": "BULL/BEAR TP1.3/SL1.3 (DEFAULT)", "params": preset_b()},
        "C": {"name": "Max Edge", "desc": "BULL TP1.0/SL0.8, BEAR TP0.8/SL0.8", "params": preset_c()},
        "D": {"name": "Max PnL (low WR)", "desc": "BULL/BEAR TP4.0/SL1.3", "params": preset_d()},
    }

@router.get("/backtest")
def backtest_mode3_bbc(
    symbol:str=Query("BTCUSDT"), timeframe:str=Query("1h"),
    days:int=Query(30,ge=1,le=1500), end_days_ago:int=Query(0,ge=0,le=1500),
    va_window:int=Query(50,ge=20,le=200), ema_period:int=Query(20,ge=5,le=100),
    tp_pct:float=Query(0.013,ge=0.001,le=0.10), sideways_tp_pct:float=Query(0.015,ge=0.0,le=0.10),
    bear_tp_pct:float=Query(0.0,ge=0.0,le=0.10),
    sl_pct:float=Query(0.013,ge=0.0,le=0.10), sideways_sl_pct:float=Query(0.0,ge=0.0,le=0.10),
    bear_sl_pct:float=Query(0.0,ge=0.0,le=0.10),
    trail_to_be_trigger_pct:float=Query(0.0,ge=0.0,le=0.10),
    sideways_trail_to_be_trigger_pct:float=Query(0.0,ge=0.0,le=0.10),
    sideways_ema_filter_enabled:bool=Query(False),
    sideways_min_sl_dist_pct:float=Query(0.0,ge=0.0,le=0.10),
    sideways_dual_mode_enabled:bool=Query(False),
    sideways_detector_size_ratio:float=Query(0.1,ge=0.0,le=1.0),
    sideways_poc_breakout_enabled:bool=Query(False),
    sideways_poc_body_ratio_min:float=Query(0.5,ge=0.0,le=1.0),
    direct_transition_enabled:bool=Query(True),
    trailing_ema_enabled:bool=Query(False),
    trailing_ema_period:int=Query(7,ge=3,le=50),
    trailing_ema_min_bars:int=Query(1,ge=0,le=20),
    trailing_ema_max_tp_pct:float=Query(0.0,ge=0.0,le=0.20),
    use_wick_exit:bool=Query(True),
    entry_usd:float=Query(10.0), leverage:float=Query(50.0),
    fee_pct:float=Query(0.001), slippage_pct:float=Query(0.0005),
    bull_mtf_15m_enabled:bool=Query(True), bull_body_ratio_min:float=Query(0.5,ge=0.0,le=1.0),
    bull_poc_entry_enabled:bool=Query(False), bull_poc_max_distance_pct:float=Query(0.02),
    bull_wait_retest_enabled:bool=Query(False), bull_retest_swing_lookback:int=Query(20),
    bull_retest_tolerance_pct:float=Query(0.003), bull_retest_max_bars:int=Query(5),
    bull_use_swing_break:bool=Query(False), bull_swing_lookback:int=Query(20),
    bull_use_26_support:bool=Query(False), bull_26_lookback:int=Query(50),
    bull_26_ratio:float=Query(2.6), bull_26_tolerance_pct:float=Query(0.003),
    bear_mtf_15m_enabled:bool=Query(True), bear_body_ratio_min:float=Query(0.6,ge=0.0,le=1.0),
    sideways_mtf_15m_enabled:bool=Query(True), sideways_body_ratio_min:float=Query(0.6,ge=0.0,le=1.0),
    # ── NEW: exit on state change ──
    exit_on_state_change:bool=Query(False),
):
    config = Mode3BBCConfig(
        va_window=va_window, ema_period=ema_period,
        tp_pct=tp_pct, sideways_tp_pct=sideways_tp_pct, bear_tp_pct=bear_tp_pct,
        sl_pct=sl_pct, sideways_sl_pct=sideways_sl_pct, bear_sl_pct=bear_sl_pct,
        trail_to_be_trigger_pct=trail_to_be_trigger_pct,
        sideways_trail_to_be_trigger_pct=sideways_trail_to_be_trigger_pct,
        sideways_ema_filter_enabled=sideways_ema_filter_enabled,
        sideways_min_sl_dist_pct=sideways_min_sl_dist_pct,
        sideways_dual_mode_enabled=sideways_dual_mode_enabled,
        sideways_detector_size_ratio=sideways_detector_size_ratio,
        sideways_poc_breakout_enabled=sideways_poc_breakout_enabled,
        sideways_poc_body_ratio_min=sideways_poc_body_ratio_min,
        direct_transition_enabled=direct_transition_enabled,
        trailing_ema_enabled=trailing_ema_enabled, trailing_ema_period=trailing_ema_period,
        trailing_ema_min_bars=trailing_ema_min_bars, trailing_ema_max_tp_pct=trailing_ema_max_tp_pct,
        use_wick_exit=use_wick_exit, entry_usd=entry_usd, leverage=leverage,
        fee_pct_roundtrip=fee_pct, slippage_pct=slippage_pct,
        bull_poc_entry_enabled=bull_poc_entry_enabled, bull_poc_max_distance_pct=bull_poc_max_distance_pct,
        bull_mtf_15m_enabled=bull_mtf_15m_enabled, bull_body_ratio_min=bull_body_ratio_min,
        bull_wait_retest_enabled=bull_wait_retest_enabled, bull_retest_swing_lookback=bull_retest_swing_lookback,
        bull_retest_tolerance_pct=bull_retest_tolerance_pct, bull_retest_max_bars=bull_retest_max_bars,
        bull_use_swing_break=bull_use_swing_break, bull_swing_lookback=bull_swing_lookback,
        bull_use_26_support=bull_use_26_support, bull_26_lookback=bull_26_lookback,
        bull_26_ratio=bull_26_ratio, bull_26_tolerance_pct=bull_26_tolerance_pct,
        bear_mtf_15m_enabled=bear_mtf_15m_enabled, bear_body_ratio_min=bear_body_ratio_min,
        sideways_mtf_15m_enabled=sideways_mtf_15m_enabled, sideways_body_ratio_min=sideways_body_ratio_min,
    )
    now_ms=int(datetime.utcnow().timestamp()*1000); end_ts=now_ms-(end_days_ago*86400*1000); start_ts=end_ts-(days*86400*1000)
    rows=load_candles_from_db(symbol, timeframe, start_ts, end_ts)
    if len(rows)<config.startup_warmup_candles: return {"error":f"Not enough candles: {len(rows)}","trades":[]}
    opens=np.array([r[1] for r in rows],dtype=float); highs=np.array([r[2] for r in rows],dtype=float)
    lows=np.array([r[3] for r in rows],dtype=float); closes=np.array([r[4] for r in rows],dtype=float)
    volumes=np.array([r[5] for r in rows],dtype=float); ema20=compute_ema_series(closes,config.ema_period)
    vahs,vals,pocs=[],[],[]
    for i in range(len(rows)):
        vah,val,poc=compute_va_at_bar(highs,lows,closes,volumes,i,config.va_window,config.va_percentile_high,config.va_percentile_low)
        vahs.append(vah);vals.append(val);pocs.append(poc)
    switcher=Switcher(config)
    if config.trailing_ema_enabled:
        switcher.trailing_ema_series = compute_ema_series(closes, config.trailing_ema_period)
    if bull_mtf_15m_enabled or bear_mtf_15m_enabled or sideways_mtf_15m_enabled:
        rows_15m=load_candles_from_db(symbol,'15m',start_ts,end_ts)
        if rows_15m:
            if bull_mtf_15m_enabled: ec,el=compute_mtf_bull_entry(rows,rows_15m); switcher.mtf_bull_entry_close=ec; switcher.mtf_bull_entry_low=el
            if bear_mtf_15m_enabled: ec,eh=compute_mtf_bear_entry(rows,rows_15m); switcher.mtf_bear_entry_close=ec; switcher.mtf_bear_entry_high=eh
            if sideways_mtf_15m_enabled:
                sc,sh,lc,ll=compute_mtf_sideways_entry(rows,rows_15m,vahs,vals)
                switcher.mtf_sideways_short_entry_close=sc; switcher.mtf_sideways_short_entry_high=sh
                switcher.mtf_sideways_long_entry_close=lc; switcher.mtf_sideways_long_entry_low=ll

    # ── Main backtest loop with optional exit_on_state_change ──
    state_change_exits = 0
    for i in range(len(rows)):
        prev_state = switcher.state
        had_pos = switcher.position is not None
        old_pos_ref = switcher.position  # reference before process

        switcher.process_candle(bar_idx=i, o=opens[i], h=highs[i], l=lows[i], c=closes[i],
                                ema20=ema20[i], vah=vahs[i], val=vals[i], poc=pocs[i])

        # Exit on state change: if state changed AND we still have the same position open
        if exit_on_state_change and switcher.position is not None and had_pos:
            new_state = switcher.state
            if new_state != prev_state:
                # State changed while in position → close at candle close price
                pos = switcher.position
                exit_price = float(closes[i])
                if pos.side == 'LONG':
                    pnl_pct = (exit_price - pos.entry_price) / pos.entry_price
                else:
                    pnl_pct = (pos.entry_price - exit_price) / pos.entry_price
                pnl_pct_net = pnl_pct - config.total_cost_pct()
                pnl_usd = pnl_pct_net * config.notional() * pos.size_ratio

                switcher.trades.append(Trade(
                    tool=pos.tool, side=pos.side, entry_price=pos.entry_price,
                    exit_price=exit_price, entry_bar=pos.entry_bar, exit_bar=i,
                    exit_type='STATE_CHG', pnl_pct=pnl_pct_net, pnl_usd=pnl_usd,
                    peak_high=pos.peak_high, trough_low=pos.trough_low,
                    sl_level=pos.sl_level, tp_level=pos.tp_level,
                    ema_at_entry=pos.ema_at_entry, ema_at_exit=float(ema20[i]),
                    entry_trigger=pos.entry_trigger,
                ))
                switcher.position = None
                state_change_exits += 1

    trades=switcher.trades; n=len(trades)
    wins=[t for t in trades if t.pnl_usd>0]; losses=[t for t in trades if t.pnl_usd<=0]
    total_pnl_usd=sum(t.pnl_usd for t in trades); wr=100.0*len(wins)/n if n>0 else 0
    tool_stats={}
    for tool in ['SIDEWAYS','BULL','BEAR']:
        tt=[t for t in trades if t.tool==tool]
        if tt:
            tw=[t for t in tt if t.pnl_usd>0]
            tool_stats[tool]={"count":len(tt),"wr_pct":round(100.0*len(tw)/len(tt),2),"pnl_usd":round(sum(t.pnl_usd for t in tt),2)}
    exit_type_breakdown={}
    for t in trades: exit_type_breakdown[t.exit_type]=exit_type_breakdown.get(t.exit_type,0)+1
    equity=0; peak_eq=0; max_dd=0
    for t in trades:
        equity += t.pnl_usd
        if equity > peak_eq: peak_eq = equity
        dd = peak_eq - equity
        if dd > max_dd: max_dd = dd
    max_streak=0; cur_streak=0
    for t in trades:
        if t.pnl_usd <= 0: cur_streak += 1; max_streak = max(max_streak, cur_streak)
        else: cur_streak = 0
    trade_list=[{"tool":t.tool,"side":t.side,"entry_price":round(t.entry_price,2),"exit_price":round(t.exit_price,2),
        "entry_bar":t.entry_bar,"exit_bar":t.exit_bar,"exit_type":t.exit_type,"pnl_pct":round(t.pnl_pct*100,3),
        "pnl_usd":round(t.pnl_usd,2),"sl_level":round(t.sl_level,2),"tp_level":round(t.tp_level,2),
        "sl_distance_pct":round(abs(t.entry_price-t.sl_level)/t.entry_price*100,3),
        "ema_at_entry":round(t.ema_at_entry,2),"ema_at_exit":round(t.ema_at_exit,2),
        "peak_high":round(t.peak_high,2),"trough_low":round(t.trough_low,2),"entry_trigger":t.entry_trigger} for t in trades]
    return {"symbol":symbol,"timeframe":timeframe,"days":days,"end_days_ago":end_days_ago,
        "candles_processed":len(rows),"config":asdict(config),
        "exit_on_state_change":exit_on_state_change, "state_change_exits":state_change_exits,
        "summary":{"total_trades":n,"win_rate_pct":round(wr,2),"wins":len(wins),"losses":len(losses),
            "total_pnl_usd":round(total_pnl_usd,2),"capital_start":config.capital_usd,
            "capital_end":round(config.capital_usd+total_pnl_usd,2),
            "max_drawdown_usd":round(max_dd,2),"max_loss_streak":max_streak,
            "trailing_ema_exits":switcher._trailing_ema_exits,
            "exit_type_breakdown":exit_type_breakdown},
        "per_tool":tool_stats,"trades":trade_list,"final_state":switcher.state}

@router.get("/health")
def mode3_bbc_health():
    return {"status":"ok","module":"mode3_bbc","version":"2.6-state-change","db_path":DB_PATH}
