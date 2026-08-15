"""V7-D causal trigger forensic for the legacy BBC family.

Read-only research endpoint. No live/order integration.

Frozen causal repair:
- The completed 1H candle updates the legacy BBC signal/state machine first.
- A captured BULL/BEAR setup may only confirm on the four completed 15m candles
  of the *following* hour. Unconfirmed setup expires after that one hour.
- Entry is the close of the first qualifying 15m confirmation candle.
- Entry candle cannot also hit TP/SL; exit tracking begins on later 15m bars.
- Legacy EMA7, body gates, TP/SL=1.3%, $10 x50 and 0.15% total cost preserved.
- SIDEWAYS entries disabled.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher
from causal_bbc_endpoint import (
    _load_rows, _ema_series, _value_area, _capture_signal, _confirm_signal,
    _make_position, _close_trade, _sync_state_after_exit,
)

router = APIRouter(prefix="/v7", tags=["v7_research"])
PAIRS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
CANONICAL_END_MS = 1785852000000  # 2026-08-04 14:00 UTC exclusive
HOUR_MS = 60 * 60 * 1000


def _cfg():
    return Mode3BBCConfig(
        va_window=50, ema_period=7,
        tp_pct=0.013, sl_pct=0.013,
        bear_tp_pct=0.0, bear_sl_pct=0.0,
        sideways_tp_pct=0.015,
        bull_body_ratio_min=0.5,
        bear_body_ratio_min=0.6,
        sideways_body_ratio_min=0.6,
        enable_sideways_trades=False,
        direct_transition_enabled=True,
        entry_usd=10.0, leverage=50.0,
        fee_pct_roundtrip=0.001, slippage_pct=0.0005,
        bull_mtf_15m_enabled=False,
        bear_mtf_15m_enabled=False,
        sideways_mtf_15m_enabled=False,
        trailing_ema_enabled=False,
        bull_poc_entry_enabled=False,
        bull_wait_retest_enabled=False,
        bull_use_swing_break=False,
        bull_use_26_support=False,
        sideways_poc_breakout_enabled=False,
    )


def _label(pre_state, tool):
    if tool == "BULL":
        return {
            "BULL":"BULL_STAY_EMA_RECLAIM",
            "SIDEWAYS":"DIRECT_SIDEWAYS_TO_BULL",
            "WAIT_SEE_BEARISH":"DIRECT_WAIT_BEARISH_TO_BULL",
            "BEAR":"DIRECT_BEAR_TO_BULL",
            "STARTUP":"STARTUP_TO_BULL",
        }.get(pre_state, f"BULL_FROM_{pre_state}")
    if tool == "BEAR":
        return {
            "BEAR":"BEAR_STAY_EMA_REJECTION",
            "SIDEWAYS":"DIRECT_SIDEWAYS_TO_BEAR",
            "WAIT_SEE_BULLISH":"DIRECT_WAIT_BULLISH_TO_BEAR",
            "BULL":"DIRECT_BULL_TO_BEAR",
            "STARTUP":"STARTUP_TO_BEAR",
        }.get(pre_state, f"BEAR_FROM_{pre_state}")
    return f"{tool}_FROM_{pre_state}"


def _stat(rows):
    n=len(rows); w=sum(r["win"] for r in rows); pnl=sum(r["pnl_usd"] for r in rows)
    return {"trades":n,"wins":w,"losses":n-w,
            "wr_pct":round(100*w/n,2) if n else None,
            "pnl_usd":round(pnl,2),
            "expectancy_usd":round(pnl/n,4) if n else None}


def _run_pair(symbol, start_ms, end_ms):
    cfg=_cfg()
    rows=_load_rows(symbol,"1h",start_ms,end_ms)
    rows15=_load_rows(symbol,"15m",start_ms,end_ms)
    if len(rows)<cfg.startup_warmup_candles or not rows15:
        raise RuntimeError(f"{symbol}: insufficient data 1h={len(rows)} 15m={len(rows15)}")

    closes=[float(r[4]) for r in rows]; ema=_ema_series(closes,7)
    vah,val,poc=_value_area(rows,50)
    closes15=[float(r[4]) for r in rows15]; ema15=_ema_series(closes15,20)
    idx15={int(r[0]):i for i,r in enumerate(rows15)}
    by_hour={}
    for r in rows15: by_hour.setdefault(int(r[0])//HOUR_MS,[]).append(r)

    sw=Switcher(cfg)
    warmup=cfg.startup_warmup_candles
    for i in range(min(warmup,len(rows))):
        sw.process_candle(i,float(rows[i][1]),float(rows[i][2]),float(rows[i][3]),float(rows[i][4]),ema[i],vah[i],val[i],poc[i])
        sw.position=None

    # pending = {signal fields + trigger + arm_hour}; valid for exactly next hour.
    pending=None; active=None; active_meta=None; trades=[]
    expired=0; confirmations=0; armed=0
    processed_start=max(warmup,51)

    for i in range(processed_start,len(rows)):
        hour_time=int(rows[i][0]); hour_key=hour_time//HOUR_MS
        candles15=sorted(by_hour.get(hour_key,[]),key=lambda r:int(r[0]))

        # Only setup armed by immediately preceding hour is eligible here.
        eligible = pending if (pending is not None and pending["confirm_hour"] == hour_key) else None
        if pending is not None and pending["confirm_hour"] < hour_key:
            expired += 1; pending=None

        for c15 in candles15:
            c15_time=int(c15[0]); j15=idx15.get(c15_time)
            if j15 is None: continue
            if active is not None:
                active.peak_high=max(active.peak_high,float(c15[2])); active.trough_low=min(active.trough_low,float(c15[3]))
                hit=None; price=None
                if active.side=="LONG":
                    if float(c15[3]) < active.sl: hit="SL"; price=active.sl
                    elif float(c15[2]) >= active.tp: hit="TP"; price=active.tp
                else:
                    if float(c15[2]) > active.sl: hit="SL"; price=active.sl
                    elif float(c15[3]) <= active.tp: hit="TP"; price=active.tp
                if hit:
                    t=_close_trade(active,price,c15_time,hit,cfg)
                    trades.append({"symbol":symbol,"trigger":active_meta["trigger"],"entry_time":active.entry_time,
                                   "pnl_usd":float(t.pnl_usd),"win":bool(t.pnl_usd>0),"tool":active.tool,"side":active.side})
                    _sync_state_after_exit(sw,active,hit); active=None; active_meta=None
                continue

            if eligible is not None and pending is not None and _confirm_signal(
                eligible,c15,ema15[j15],vah[i-1] if i>0 else None,val[i-1] if i>0 else None,0.6
            ):
                active=_make_position(eligible,c15,j15,i,cfg,vah[i-1] if i>0 else None,val[i-1] if i>0 else None)
                active_meta={"trigger":eligible["trigger"]}
                confirmations += 1; pending=None; eligible=None
                # frozen: no exit evaluation on the entry/confirmation candle.

        if eligible is not None and pending is not None:
            expired += 1; pending=None

        # Only after all 15m children of this hour are processed is the 1H bar complete.
        pre_state=sw.state
        sw.process_candle(i,float(rows[i][1]),float(rows[i][2]),float(rows[i][3]),float(rows[i][4]),ema[i],vah[i],val[i],poc[i])
        sig=_capture_signal(sw,i)
        if sig is not None:
            sig["trigger"]=_label(pre_state,sig["tool"])

        # Opposite completed-1H signal closes an active causal position at 1H close.
        if active is not None and sig is not None and sig["side"] != active.side:
            t=_close_trade(active,float(rows[i][4]),hour_time,"REVERSE",cfg)
            trades.append({"symbol":symbol,"trigger":active_meta["trigger"],"entry_time":active.entry_time,
                           "pnl_usd":float(t.pnl_usd),"win":bool(t.pnl_usd>0),"tool":active.tool,"side":active.side})
            _sync_state_after_exit(sw,active,"REVERSE"); active=None; active_meta=None

        if active is None and sig is not None:
            sig["confirm_hour"]=hour_key+1
            pending=sig; armed += 1

    if active is not None:
        last=rows[-1]
        t=_close_trade(active,float(last[4]),int(last[0]),"END",cfg)
        trades.append({"symbol":symbol,"trigger":active_meta["trigger"],"entry_time":active.entry_time,
                       "pnl_usd":float(t.pnl_usd),"win":bool(t.pnl_usd>0),"tool":active.tool,"side":active.side})

    return trades,{"bars_1h":len(rows),"bars_15m":len(rows15),"armed":armed,"confirmed":confirmations,"expired":expired}


@router.get("/causal-trigger-forensic")
def causal_trigger_forensic(days:int=Query(971,ge=30,le=1500),end_ts_ms:int=Query(CANONICAL_END_MS,ge=1)):
    start_ms=end_ts_ms-days*86400000
    all_rows=[]; coverage={}; errors={}
    for p in PAIRS:
        try:
            rr,cov=_run_pair(p,start_ms,end_ts_ms); all_rows.extend(rr); coverage[p]=cov
        except Exception as e: errors[p]=str(e)

    triggers=sorted(set(r["trigger"] for r in all_rows))
    overall=_stat(all_rows)
    by_pair={p:_stat([r for r in all_rows if r["symbol"]==p]) for p in PAIRS}
    by_trigger={g:_stat([r for r in all_rows if r["trigger"]==g]) for g in triggers}
    by_trigger_pair={g:{p:_stat([r for r in all_rows if r["trigger"]==g and r["symbol"]==p]) for p in PAIRS} for g in triggers}

    start_dt=datetime.fromtimestamp(start_ms/1000,tz=timezone.utc); end_dt=datetime.fromtimestamp(end_ts_ms/1000,tz=timezone.utc)
    span=end_dt-start_dt; cuts=[start_dt+span*k/4 for k in range(5)]; names=["Q1_early","Q2","Q3","Q4_recent"]
    by_trigger_block={g:{} for g in triggers}; by_block={}
    for i,name in enumerate(names):
        lo=int(cuts[i].timestamp()*1000); hi=int(cuts[i+1].timestamp()*1000)
        xs=[r for r in all_rows if lo<=r["entry_time"]<hi]; by_block[name]=_stat(xs)
        for g in triggers: by_trigger_block[g][name]=_stat([r for r in xs if r["trigger"]==g])

    robustness={}
    for g in triggers:
        pair_pos=sum(1 for p in PAIRS if by_trigger_pair[g][p]["trades"]>=20 and (by_trigger_pair[g][p]["expectancy_usd"] or 0)>0)
        block_pos=sum(1 for b in names if by_trigger_block[g][b]["trades"]>=20 and (by_trigger_block[g][b]["expectancy_usd"] or 0)>0)
        robustness[g]={"positive_pairs":pair_pos,"positive_blocks":block_pos,
                       "all_4_pairs_positive":pair_pos==4,"all_4_blocks_positive":block_pos==4}

    return {"phase":"V7-D","status":"FROZEN_CAUSAL_NEXT_HOUR_15M_TRIGGER_FORENSIC",
            "window":{"start":start_dt.isoformat(),"end_exclusive":end_dt.isoformat(),"days":days},
            "frozen_definition":{"1h_signal":"completed candle only","confirmation":"first qualifying completed 15m in immediately following hour only","expiry":"after one hour","entry":"15m confirmation close","entry_bar_exit":False,"tp_pct":0.013,"sl_pct":0.013,"total_cost_pct":0.0015,"sideways_trades":False,"threshold_sweep":False},
            "coverage":coverage,"errors":errors,"overall":overall,"by_pair":by_pair,
            "by_trigger":by_trigger,"by_trigger_pair":by_trigger_pair,"by_block":by_block,
            "by_trigger_block":by_trigger_block,"trigger_robustness":robustness}
