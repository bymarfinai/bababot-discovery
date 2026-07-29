"""Tick Discovery endpoints: /tick/start, /tick/stop, /tick/status, /tick/log,
/tick/analyze, /tick/extract, /tick/candle-range, /tick/sweep*, /tick/custom-backtest,
/tick/cluster, /tick/profile, /tick/test-close-position, /tick/backtest-close-position, /tick/first-move.

NOTE: test-close-position, backtest-close-position, first-move are large analysis endpoints.
They were originally pasted at the bottom of app.py — now properly housed here.
"""
import sqlite3
from collections import defaultdict
from datetime import datetime, timezone
from fastapi import APIRouter, Body

from shared import DB_PATH
from tick_discovery import (
    start_tick_discovery, stop_tick_discovery, get_discovery_status, get_discovery_log,
    extract_tick_events, analyze_tick_stats,
    start_sweep_engine, stop_sweep_engine, get_sweep_status,
    pause_sweep_engine, resume_sweep_engine,
    profile_winning_combo, cluster_levels, combo_sweep, custom_backtest,
    _load_data as td_load_data, DB_PATH as TD_DB_PATH,
)

router = APIRouter()


@router.get("/tick/start")
def tick_start(pairs: str = None, timeframes: str = None, window: int = 10,
    buffer_pct: float = 0.8, buffer2_pct: float = 1.0, tp_pct: float = 1.0,
    sl_pct: float = 0.5, days: int = 1825):
    return start_tick_discovery(pairs=pairs.split(",") if pairs else None,
        timeframes=timeframes.split(",") if timeframes else None,
        window=window, buffer_pct=buffer_pct, buffer2_pct=buffer2_pct,
        tp_pct=tp_pct, sl_pct=sl_pct, days=days)

@router.get("/tick/stop")
def tick_stop(): return stop_tick_discovery()

@router.get("/tick/status")
def tick_status(): return get_discovery_status()

@router.get("/tick/log")
def tick_log(limit: int = 200): return {"ok": True, "log": get_discovery_log(limit)}

@router.get("/tick/analyze")
def tick_analyze(symbol: str = "BTCUSDT", timeframe: str = "4h", window: int = 10,
    buffer_pct: float = 0.8, tp_pct: float = 1.0, sl_pct: float = 0.5,
    group_by: str = "hour_utc", days: int = 1825):
    return analyze_tick_stats(symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct, group_by=group_by, days=days)

@router.get("/tick/extract")
def tick_extract(symbol: str = "BTCUSDT", timeframe: str = "4h", window: int = 10,
    buffer_pct: float = 0.8, tp_pct: float = 1.0, sl_pct: float = 0.5,
    days: int = 1825, save: bool = True):
    return extract_tick_events(symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct, days=days, save_to_d1=save)

@router.get("/tick/sweep")
def tick_sweep(pairs: str = None, timeframes: str = None, window: int = 10,
    days: int = 1825, modes: str = "both", position_usd: float = 100, leverage: int = 50):
    return start_sweep_engine(pairs=pairs.split(",") if pairs else None,
        timeframes=timeframes.split(",") if timeframes else None,
        window=window, days=days, modes=modes, position_usd=position_usd, leverage=leverage)

@router.get("/tick/sweep-stop")
def tick_sweep_stop(): return stop_sweep_engine()

@router.get("/tick/sweep-pause")
def tick_sweep_pause(): return pause_sweep_engine()

@router.get("/tick/sweep-resume")
def tick_sweep_resume(): return resume_sweep_engine()

@router.get("/tick/sweep-status")
def tick_sweep_status(): return get_sweep_status()

@router.post("/tick/custom-backtest")
def tick_custom_backtest(body: dict = Body(...)):
    symbol = body.get("symbol", "BTCUSDT")
    timeframe = body.get("timeframe", "15m")
    config = body.get("config", {})
    for key in ["regime_mode", "regime_window"]:
        if key in body and key not in config: config[key] = body[key]
    return custom_backtest(symbol, timeframe, config)

@router.get("/tick/cluster")
def tick_cluster(symbol: str = "DOGEUSDT", timeframe: str = "4h", window: int = 10, days: int = 1825):
    rows, sub_lookup = td_load_data(TD_DB_PATH, symbol, timeframe, "1m")
    if len(rows) < window + 20: return {"error": "insufficient data", "rows": len(rows)}
    if days > 0:
        ms_limit = days * 86400 * 1000; last_time = rows[-1][5]
        rows = [r for r in rows if r[5] >= last_time - ms_limit]
    return cluster_levels(rows, sub_lookup, symbol, timeframe, window=window, days=days, save_to_d1=True)

@router.get("/tick/profile")
def tick_profile(symbol: str = "DOGEUSDT", timeframe: str = "4h", window: int = 10,
    buffer_pct: float = 2.0, tp_pct: float = 1.0, sl_pct: float = 2.0,
    buffer2_pct: float = 1.5, close_filter_pct: float = 0, days: int = 1825):
    return profile_winning_combo(symbol=symbol, timeframe=timeframe, window=window,
        buffer_pct=buffer_pct, tp_pct=tp_pct, sl_pct=sl_pct, buffer2_pct=buffer2_pct,
        close_filter_pct=close_filter_pct, days=days)


# ══════════════════════════════════════════════
# CANDLE RANGE ANALYSIS
# ══════════════════════════════════════════════

@router.get("/tick/candle-range")
def candle_range(symbol: str = "SOLUSDT", timeframe: str = "4h", days: int = 1825):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("SELECT open, high, low, close, open_time FROM klines WHERE symbol=? AND timeframe=? ORDER BY open_time ASC", (symbol, timeframe)).fetchall()
    sub_rows = conn.execute("SELECT open, high, low, close, open_time FROM klines WHERE symbol=? AND timeframe='1m' ORDER BY open_time ASC", (symbol,)).fetchall()
    conn.close()
    if not rows or not sub_rows: return {"error": "no data"}
    if days > 0:
        ms_limit = days * 86400 * 1000; last_time = rows[-1][4]
        rows = [r for r in rows if r[4] >= last_time - ms_limit]
    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}
    parent_ms = tf_ms.get(timeframe, 14400000)
    sub_groups = defaultdict(list)
    for sr in sub_rows: sub_groups[(sr[4] // parent_ms) * parent_ms].append(sr)
    thresholds = [0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0, 2.5, 3.0]
    results = []; total = len(rows)
    for t in thresholds:
        lm, sm = [], []
        for r in rows:
            lt, st = r[0]*(1+t/100), r[0]*(1-t/100)
            subs = sub_groups.get((r[4]//parent_ms)*parent_ms, [])
            lf = sf = False
            for idx, sc in enumerate(subs):
                if not lf and sc[1] >= lt: lm.append(idx); lf = True
                if not sf and sc[2] <= st: sm.append(idx); sf = True
                if lf and sf: break
        def cs(m):
            if not m: return None
            s = sorted(m); n = len(s); avg = sum(s)/n
            std = (sum((x-avg)**2 for x in s)/n)**0.5
            return {"avg_min": round(avg,1), "median_min": s[n//2], "p25_min": s[int(n*0.25)], "p75_min": s[int(n*0.75)]}
        results.append({"tp_pct": t, "long_hit_pct": round(len(lm)/total*100,1), "short_hit_pct": round(len(sm)/total*100,1),
            "long_timing": cs(lm), "short_timing": cs(sm)})
    return {"symbol": symbol, "timeframe": timeframe, "total_candles": total, "results": results}


# ══════════════════════════════════════════════
# TEST CLOSE POSITION (hipotesis analysis)
# ══════════════════════════════════════════════

@router.get("/tick/test-close-position")
def test_close_position(symbol: str = "DOGEUSDT", timeframe: str = "4h", window: int = 10, days: int = 1825):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("SELECT open, high, low, close, volume, open_time FROM klines WHERE symbol=? AND timeframe=? ORDER BY open_time ASC", (symbol, timeframe)).fetchall()
    sub_rows = conn.execute("SELECT open, high, low, close, open_time FROM klines WHERE symbol=? AND timeframe='1m' ORDER BY open_time ASC", (symbol,)).fetchall()
    conn.close()
    if not rows or not sub_rows: return {"error": "no data"}
    tf_ms = {"15m": 900000, "1h": 3600000, "4h": 14400000}; parent_ms = tf_ms.get(timeframe, 14400000)
    sub_groups = defaultdict(list)
    for sr in sub_rows: sub_groups[(sr[4]//parent_ms)*parent_ms].append({"h": sr[1], "l": sr[2]})
    n = len(rows)
    highs = [r[1] for r in rows]; lows = [r[2] for r in rows]; closes = [r[3] for r in rows]; times = [r[5] for r in rows]
    cr = [closes[i]/closes[i-1] if closes[i-1]!=0 else 1.0 for i in range(1,n)]
    hr = [highs[i]/highs[i-1] if highs[i-1]!=0 else 1.0 for i in range(1,n)]
    lr = [lows[i]/lows[i-1] if lows[i-1]!=0 else 1.0 for i in range(1,n)]
    start_idx = max(window, next((idx for idx,r in enumerate(rows) if r[5] >= rows[-1][5]-days*86400*1000), window)) if days > 0 else window
    buckets = {"very_low_0_15":(0,0.15),"low_15_30":(0.15,0.30),"mid_low_30_45":(0.30,0.45),
        "mid_45_55":(0.45,0.55),"mid_high_55_70":(0.55,0.70),"high_70_85":(0.70,0.85),"very_high_85_100":(0.85,1.01)}
    results = {b: {"total":0,"high_first":0,"low_first":0,"none":0} for b in buckets}
    for i in range(start_idx, len(cr)):
        if i+1 >= n: break
        ph = highs[i]*sum(hr[i-window:i])/window; pl = lows[i]*sum(lr[i-window:i])/window
        pc = closes[i]*sum(cr[i-window:i])/window; pr = ph-pl
        if pr <= 0: continue
        cp = (pc-pl)/pr
        subs = sub_groups.get((times[i+1]//parent_ms)*parent_ms, [])
        if not subs: continue
        mph = mpl = None
        for si,sc in enumerate(subs):
            if mph is None and sc["h"]>=ph: mph=si
            if mpl is None and sc["l"]<=pl: mpl=si
            if mph is not None and mpl is not None: break
        fe = "HIGH" if mph is not None and (mpl is None or mph<mpl) else "LOW" if mpl is not None else "NONE"
        for bn,(lo,hi) in buckets.items():
            if lo<=cp<hi:
                results[bn]["total"]+=1
                results[bn]["high_first" if fe=="HIGH" else "low_first" if fe=="LOW" else "none"]+=1
                break
    table = []
    for bn,(lo,hi) in buckets.items():
        d = results[bn]
        if d["total"]==0: continue
        hp = round(d["high_first"]/d["total"]*100,1); lp = round(d["low_first"]/d["total"]*100,1)
        table.append({"bucket":bn,"total":d["total"],"high_first_pct":hp,"low_first_pct":lp,
            "predicted_direction":"SHORT" if hp>lp else "LONG" if lp>hp else "SKIP", "confidence": max(hp,lp)})
    tc = sum(d["total"] for d in results.values()); correct=0; testable=0
    for bn,d in results.items():
        if "very_low" in bn or "low_15" in bn: correct+=d["high_first"]; testable+=d["total"]
        elif "very_high" in bn or "high_70" in bn: correct+=d["low_first"]; testable+=d["total"]
    return {"symbol":symbol,"timeframe":timeframe,"total_candles":tc,"table":table,
        "hipotesis_test":{"testable_candles":testable,"correct":correct,"accuracy":round(correct/testable*100,1) if testable>0 else 0}}


# ══════════════════════════════════════════════
# BACKTEST CLOSE POSITION (direction signal)
# ══════════════════════════════════════════════

@router.get("/tick/backtest-close-position")
def backtest_close_position(symbol: str="DOGEUSDT", timeframe: str="4h", window: int=10,
    days: int=1825, tp_pct: float=0.5, sl_pct: float=0.5, long_threshold: float=0.70,
    short_threshold: float=0.30, position_usd: float=100, leverage: int=50):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("SELECT open,high,low,close,volume,open_time FROM klines WHERE symbol=? AND timeframe=? ORDER BY open_time ASC",(symbol,timeframe)).fetchall()
    sub_rows = conn.execute("SELECT open,high,low,close,open_time FROM klines WHERE symbol=? AND timeframe='1m' ORDER BY open_time ASC",(symbol,)).fetchall()
    conn.close()
    if not rows or not sub_rows: return {"error":"no data"}
    tf_ms={"15m":900000,"1h":3600000,"4h":14400000}; pm=tf_ms.get(timeframe,14400000)
    sg=defaultdict(list)
    for sr in sub_rows: sg[(sr[4]//pm)*pm].append({"o":sr[0],"h":sr[1],"l":sr[2],"c":sr[3]})
    n=len(rows); o=[r[0] for r in rows]; h=[r[1] for r in rows]; l=[r[2] for r in rows]; c=[r[3] for r in rows]; t=[r[5] for r in rows]
    cr=[c[i]/c[i-1] if c[i-1]!=0 else 1.0 for i in range(1,n)]
    hr=[h[i]/h[i-1] if h[i-1]!=0 else 1.0 for i in range(1,n)]
    lr=[l[i]/l[i-1] if l[i-1]!=0 else 1.0 for i in range(1,n)]
    notional=position_usd*leverage; fee=notional*0.07/100; trades=[]
    for i in range(window,len(cr)):
        if i+1>=n: break
        ph=h[i]*sum(hr[i-window:i])/window; pl=l[i]*sum(lr[i-window:i])/window; pc=c[i]*sum(cr[i-window:i])/window
        pr=ph-pl
        if pr<=0: continue
        cp=(pc-pl)/pr
        if cp>=long_threshold: d="LONG"
        elif cp<=short_threshold: d="SHORT"
        else: continue
        ct=t[i+1]; co=o[i+1]; subs=sg.get((ct//pm)*pm,[])
        if not subs: continue
        if d=="LONG": tp=co*(1+tp_pct/100); sl=co*(1-sl_pct/100)
        else: tp=co*(1-tp_pct/100); sl=co*(1+sl_pct/100)
        ep=er=None; em=0
        for si,sc in enumerate(subs):
            if d=="LONG":
                if sc["h"]>=tp: ep=tp;er="TP";em=si;break
                if sc["l"]<=sl: ep=sl;er="SL";em=si;break
            else:
                if sc["l"]<=tp: ep=tp;er="TP";em=si;break
                if sc["h"]>=sl: ep=sl;er="SL";em=si;break
        if er is None: ep=c[i+1];er="CLOSE";em=len(subs)
        pp=((ep-co)/co*100) if d=="LONG" else ((co-ep)/co*100)
        pd=notional*pp/100-fee
        dt=datetime.fromtimestamp(ct/1000,tz=timezone.utc)
        trades.append({"win":pd>0,"pnl":round(pd,2),"side":d,"exit_reason":er,"exit_minute":em,"close_position":round(cp,3),"hour_utc":dt.hour})
    if not trades: return {"error":"no trades"}
    tot=len(trades); wins=sum(1 for x in trades if x["win"]); wr=round(wins/tot*100,1)
    total_pnl=round(sum(x["pnl"] for x in trades),2)
    pd_days=max((t[-1]-t[window+1])/86400000,1)
    longs=[x for x in trades if x["side"]=="LONG"]; shorts=[x for x in trades if x["side"]=="SHORT"]
    eq=0;pk=0;mdd=0
    for x in trades:
        eq+=x["pnl"]
        if eq>pk: pk=eq
        if pk-eq>mdd: mdd=pk-eq
    return {"symbol":symbol,"timeframe":timeframe,"config":{"tp_pct":tp_pct,"sl_pct":sl_pct,"window":window},
        "results":{"total_trades":tot,"wins":wins,"win_rate":wr,"total_pnl":total_pnl,"profit_per_day":round(total_pnl/pd_days,2),"max_drawdown":round(mdd,2)},
        "direction_breakdown":{
            "long":{"trades":len(longs),"wr":round(sum(1 for x in longs if x["win"])/len(longs)*100,1) if longs else 0,"pnl":round(sum(x["pnl"] for x in longs),2)},
            "short":{"trades":len(shorts),"wr":round(sum(1 for x in shorts if x["win"])/len(shorts)*100,1) if shorts else 0,"pnl":round(sum(x["pnl"] for x in shorts),2)}}}


# ══════════════════════════════════════════════
# FIRST MOVE ANALYSIS
# ══════════════════════════════════════════════

@router.get("/tick/first-move")
def first_move(symbol: str="DOGEUSDT", timeframe: str="4h", window: int=10, move_pct: float=0.5):
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    rows = conn.execute("SELECT open,high,low,close,volume,open_time FROM klines WHERE symbol=? AND timeframe=? ORDER BY open_time ASC",(symbol,timeframe)).fetchall()
    sub_rows = conn.execute("SELECT open,high,low,close,open_time FROM klines WHERE symbol=? AND timeframe='1m' ORDER BY open_time ASC",(symbol,)).fetchall()
    conn.close()
    tf_ms={"15m":900000,"1h":3600000,"4h":14400000}; pm=tf_ms.get(timeframe,14400000)
    sg=defaultdict(list)
    for sr in sub_rows: sg[(sr[4]//pm)*pm].append({"h":sr[1],"l":sr[2]})
    n=len(rows); o=[r[0] for r in rows]; h=[r[1] for r in rows]; l=[r[2] for r in rows]; c=[r[3] for r in rows]; ts=[r[5] for r in rows]
    cr=[c[i]/c[i-1] if c[i-1]!=0 else 1.0 for i in range(1,n)]
    hr=[h[i]/h[i-1] if h[i-1]!=0 else 1.0 for i in range(1,n)]
    lr=[l[i]/l[i-1] if l[i-1]!=0 else 1.0 for i in range(1,n)]
    records=[]
    for i in range(window,len(cr)):
        if i+1>=n: break
        ct=ts[i+1]; co=o[i+1]; subs=sg.get((ct//pm)*pm,[])
        if not subs: continue
        ut=co*(1+move_pct/100); dt_t=co*(1-move_pct/100)
        fm=None; fmin=None
        for si,sc in enumerate(subs):
            uh=sc["h"]>=ut; dh=sc["l"]<=dt_t
            if uh and dh: fm="BOTH";fmin=si;break
            elif uh: fm="UP";fmin=si;break
            elif dh: fm="DOWN";fmin=si;break
        if fm is None: fm="NEITHER";fmin=len(subs)
        pd="bullish" if c[i]>o[i] else "bearish" if c[i]<o[i] else "doji"
        pcr=h[i]-l[i]; pcp=(c[i]-l[i])/pcr if pcr>0 else 0.5
        records.append({"first_move":fm,"first_minute":fmin,"prev_dir":pd,"prev_close_position":round(pcp,3),
            "hour":datetime.fromtimestamp(ct/1000,tz=timezone.utc).hour})
    total=len(records)
    uc=sum(1 for r in records if r["first_move"]=="UP"); dc=sum(1 for r in records if r["first_move"]=="DOWN")
    def up_pct(subset):
        u=sum(1 for r in subset if r["first_move"]=="UP"); d=sum(1 for r in subset if r["first_move"]=="DOWN"); t=u+d
        return (round(u/t*100,1) if t>0 else 0, t)
    by_pd={}
    for p in ["bullish","bearish","doji"]:
        s=[r for r in records if r["prev_dir"]==p]; pct,cnt=up_pct(s)
        by_pd[p]={"up_first_pct":pct,"down_first_pct":round(100-pct,1),"trades":cnt}
    by_pcp={}
    for label,lo,hi in [("bottom_0_20",0,0.2),("low_20_40",0.2,0.4),("mid_40_60",0.4,0.6),("high_60_80",0.6,0.8),("top_80_100",0.8,1.01)]:
        s=[r for r in records if lo<=r["prev_close_position"]<hi]; pct,cnt=up_pct(s)
        by_pcp[label]={"up_first_pct":pct,"down_first_pct":round(100-pct,1),"trades":cnt}
    return {"symbol":symbol,"timeframe":timeframe,"move_pct":move_pct,"total_candles":total,
        "overall":{"up_first":uc,"down_first":dc,"up_first_pct":round(uc/(uc+dc)*100,1) if uc+dc>0 else 0},
        "by_prev_direction":by_pd,"by_prev_close_position":by_pcp}
