#!/usr/bin/env python3
"""V8-A — frozen EMA9/20 1H continuation-pullback baseline.

Research only. No EMA/threshold/TP-SL sweep.

Frozen signal sequence (completed 1H candles only):
BULL
  1) pretrend candle close > EMA9
  2) pullback candle: EMA9 > EMA20; both EMAs rising; candle range overlaps
     the EMA9..EMA20 zone; pullback closes >= EMA20
  3) next confirmation candle remains EMA9 > EMA20, is bullish, and closes > EMA9
BEAR is the exact mirror.

Entry = confirmation 1H close.
SL = pullback candle extreme (low for BULL, high for BEAR).
TP = symmetric 1R target.
Outcome path = completed 5m candles strictly after the 1H confirmation close.
If one 5m candle touches both TP and SL, outcome is AMBIGUOUS and excluded.
One pair / one open position: signals while a prior position is unresolved are skipped.
Censored trades are excluded and counted.

Comparison windows are the same adjacent V7-J blocks:
  previous: 2025-12-07T15:11:15.831175Z .. 2026-04-06T15:11:15.831175Z
  latest:   2026-04-06T15:11:15.831175Z .. 2026-08-04T15:11:15.831175Z
A warmup and forward-resolution buffer are downloaded from official Binance USD-M archives.
"""

import bisect
import json
from datetime import datetime, timedelta, timezone

from research.v7_f_fib_120d_archive_audit import load_series

PAIRS=["BTCUSDT","ETHUSDT","SOLUSDT","BNBUSDT"]
PREV_START=datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START=datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END=datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
WARMUP_DAYS=35
FORWARD_DAYS=11
DATA_START=PREV_START-timedelta(days=WARMUP_DAYS)
DATA_END=LATEST_END+timedelta(days=FORWARD_DAYS)


def ema(values, period):
    if not values:return []
    a=2.0/(period+1.0)
    out=[float(values[0])]
    for v in values[1:]:out.append(a*float(v)+(1.0-a)*out[-1])
    return out


def stat(rows):
    resolved=[r for r in rows if r["outcome"] in ("WIN","LOSS")]
    w=sum(r["outcome"]=="WIN" for r in resolved)
    l=len(resolved)-w
    return {
        "signals":len(rows),"resolved":len(resolved),"wins":w,"losses":l,
        "wr_pct":round(100.0*w/len(resolved),2) if resolved else None,
        "ambiguous":sum(r["outcome"]=="AMBIGUOUS" for r in rows),
        "censored":sum(r["outcome"]=="CENSORED" for r in rows),
    }


def scan_outcome(side, entry, sl, tp, entry_close_ms, bars5, times5, start_idx=0):
    j=max(start_idx,bisect.bisect_left(times5,entry_close_ms))
    for k in range(j,len(bars5)):
        t,o,h,l,c=bars5[k]
        if side=="BULL":
            hit_tp=h>=tp; hit_sl=l<=sl
        else:
            hit_tp=l<=tp; hit_sl=h>=sl
        if hit_tp and hit_sl:return "AMBIGUOUS",t,k
        if hit_tp:return "WIN",t,k
        if hit_sl:return "LOSS",t,k
    return "CENSORED",None,len(bars5)-1


def block_of(dt):
    if PREV_START<=dt<LATEST_START:return "previous_120d"
    if LATEST_START<=dt<LATEST_END:return "latest_120d"
    return None


def main():
    all_trades=[]; coverage={}; skipped_open={}
    for pair in PAIRS:
        r1=load_series(pair,"1h",DATA_START,DATA_END)
        r5=load_series(pair,"5m",DATA_START,DATA_END)
        coverage[pair]={
            "1h":{"rows":len(r1),"first":datetime.fromtimestamp(r1[0][2]/1000,tz=timezone.utc).isoformat() if r1 else None,"last":datetime.fromtimestamp(r1[-1][2]/1000,tz=timezone.utc).isoformat() if r1 else None},
            "5m":{"rows":len(r5),"first":datetime.fromtimestamp(r5[0][2]/1000,tz=timezone.utc).isoformat() if r5 else None,"last":datetime.fromtimestamp(r5[-1][2]/1000,tz=timezone.utc).isoformat() if r5 else None},
        }
        # tuple: open_time, open, high, low, close
        bars1=[(int(x[2]),float(x[3]),float(x[4]),float(x[5]),float(x[6])) for x in r1]
        bars5=[(int(x[2]),float(x[3]),float(x[4]),float(x[5]),float(x[6])) for x in r5]
        times5=[x[0] for x in bars5]
        closes=[x[4] for x in bars1]
        e9=ema(closes,9); e20=ema(closes,20)
        open_until_ms=-1; scan_hint=0; skipped=0
        for i in range(22,len(bars1)):
            # sequence: i-2 pretrend, i-1 pullback, i confirmation
            t0,o0,h0,l0,c0=bars1[i-2]
            tpull,op,hp,lp,cp=bars1[i-1]
            tc,oc,hc,lc,cc=bars1[i]
            confirm_dt=datetime.fromtimestamp(tc/1000,tz=timezone.utc)
            b=block_of(confirm_dt)
            if not b:continue
            entry_close_ms=tc+3_600_000
            if entry_close_ms<=open_until_ms:
                skipped+=1; continue

            bull=(
                c0>e9[i-2]
                and e9[i-1]>e20[i-1]
                and e9[i-1]>e9[i-2] and e20[i-1]>e20[i-2]
                and lp<=e9[i-1] and hp>=e20[i-1]
                and cp>=e20[i-1]
                and e9[i]>e20[i]
                and cc>oc and cc>e9[i]
            )
            bear=(
                c0<e9[i-2]
                and e9[i-1]<e20[i-1]
                and e9[i-1]<e9[i-2] and e20[i-1]<e20[i-2]
                and hp>=e9[i-1] and lp<=e20[i-1]
                and cp<=e20[i-1]
                and e9[i]<e20[i]
                and cc<oc and cc<e9[i]
            )
            if not (bull or bear):continue
            side="BULL" if bull else "BEAR"
            entry=cc
            sl=lp if bull else hp
            risk=(entry-sl) if bull else (sl-entry)
            if risk<=0:continue
            target=entry+risk if bull else entry-risk
            outcome,exit_ms,exit_idx=scan_outcome(side,entry,sl,target,entry_close_ms,bars5,times5,scan_hint)
            if outcome in ("WIN","LOSS","AMBIGUOUS") and exit_ms is not None:
                open_until_ms=exit_ms+300_000
                scan_hint=max(scan_hint,exit_idx)
            else:
                open_until_ms=int(DATA_END.timestamp()*1000)
            all_trades.append({
                "pair":pair,"block":b,"side":side,"confirm_time":confirm_dt.isoformat(),
                "entry":entry,"sl":sl,"tp":target,"risk_pct":round(100.0*risk/entry,4),
                "outcome":outcome,"exit_time":datetime.fromtimestamp(exit_ms/1000,tz=timezone.utc).isoformat() if exit_ms else None,
            })
        skipped_open[pair]=skipped

    result={
        "phase":"V8-A","status":"FROZEN_EMA9_20_PULLBACK_120D_VS_120D",
        "definition":{
            "structure_tf":"1h","execution_path_tf":"5m","ema_fast":9,"ema_slow":20,
            "entry":"confirmation 1h close","stop":"pullback candle extreme","rr":1.0,
            "bull":"pretrend close>EMA9; pullback overlaps EMA9-EMA20; EMA9>EMA20 and both rising; pullback close>=EMA20; next candle bullish close>EMA9",
            "bear":"exact mirror","one_pair_one_position":True,"same_5m_tp_sl":"AMBIGUOUS excluded",
            "threshold_sweep":False,"ema_sweep":False,"tp_sl_sweep":False,"fees_slippage":"not applied; raw structural geometry",
        },
        "windows":{
            "previous_120d":{"start":PREV_START.isoformat(),"end_exclusive":LATEST_START.isoformat()},
            "latest_120d":{"start":LATEST_START.isoformat(),"end_exclusive":LATEST_END.isoformat()},
        },
        "coverage":coverage,"skipped_signals_while_position_open":skipped_open,
        "overall":stat(all_trades),
        "by_block":{b:stat([r for r in all_trades if r["block"]==b]) for b in ("previous_120d","latest_120d")},
        "by_side":{s:stat([r for r in all_trades if r["side"]==s]) for s in ("BULL","BEAR")},
        "by_block_side":{b:{s:stat([r for r in all_trades if r["block"]==b and r["side"]==s]) for s in ("BULL","BEAR")} for b in ("previous_120d","latest_120d")},
        "by_pair":{p:stat([r for r in all_trades if r["pair"]==p]) for p in PAIRS},
        "by_block_pair":{b:{p:stat([r for r in all_trades if r["block"]==b and r["pair"]==p]) for p in PAIRS} for b in ("previous_120d","latest_120d")},
        "by_pair_side":{p:{s:stat([r for r in all_trades if r["pair"]==p and r["side"]==s]) for s in ("BULL","BEAR")} for p in PAIRS},
        "risk_geometry":{
            "resolved_risk_pct_median":None,
            "resolved_risk_pct_min":None,"resolved_risk_pct_max":None,
        },
    }
    resolved=[r for r in all_trades if r["outcome"] in ("WIN","LOSS")]
    if resolved:
        rs=sorted(r["risk_pct"] for r in resolved)
        result["risk_geometry"]={"resolved_risk_pct_median":round(rs[len(rs)//2],4),"resolved_risk_pct_min":rs[0],"resolved_risk_pct_max":rs[-1]}
    print("V8_A_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
