"""V4-B2 — context forensic for frozen V4-B absorption signals.

Two independent descriptive hypotheses only:
1) Regime alignment: does a demand reaction work better when the latest fully
   completed 1H V2 regime is BULL (supply in BEAR)?
2) Fibonacci location: do successful reactions cluster at a particular causal
   retracement of the impulse that produced the BOS?

No filtering/tuning is applied here. The frozen V4-B entry/outcome logic is
reused unchanged.
"""

import bisect
import math
import statistics
import numpy as np
from fastapi import APIRouter, Query

from v4_structural_zone_endpoint import _load, CausalSwingTracker
from v4_first_retest_endpoint import HOUR_MS, MINUTE_MS, _build_a1_zones, _coverage
from v4_reaction_absorption_endpoint import (
    _load_child_full,
    _find_confirmation,
    _resolve_after_confirmation,
)
from continuation_detector_endpoint import ContinuationDetectorV2, _ema as _v2_ema, _atr as _v2_atr

router = APIRouter(prefix="/v4/context-fib-forensic", tags=["v4_context_fib_forensic"])

FIB_LEVELS = [0.382, 0.5, 0.618, 0.705, 0.786]
FIVE_MIN_MS = 5 * MINUTE_MS


def _stat(rows):
    n=len(rows); w=sum(r.get("outcome")=="BOUNCE" for r in rows)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":round(100.0*w/n,2) if n else None}


def _median(xs):
    vals=[float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return round(float(statistics.median(vals)),6) if vals else None


def _regime_series(O,H,L,C):
    ef=_v2_ema(C,7); es=_v2_ema(C,20); atr=_v2_atr(H,L,C,14)
    det=ContinuationDetectorV2(7,20,10,0.5,3,min_pb_bars=1)
    out=[]
    for i in range(len(C)):
        det.process(i,O,H,L,C,ef,es,atr)
        out.append(det.regime)
    return out


def _fib_anchor_map(T,H,L,ATR,zones):
    """Map each zone_id to causal opposite-swing anchor + BOS extreme.

    Demand: latest confirmed swing low -> BOS candle high.
    Supply: latest confirmed swing high -> BOS candle low.
    Both endpoints are known by BOS candle close.
    """
    by_bos={}
    for z in zones:
        by_bos.setdefault(int(z["bos_bar"]),[]).append(z)
    tracker=CausalSwingTracker(10,0.5)
    out={}
    for i in range(len(T)):
        tracker.update(i,H,L,ATR)
        if i not in by_bos:
            continue
        for z in by_bos[i]:
            if z["side"]=="DEMAND":
                sw=tracker.last_low
                if sw and sw["confirmed_at"]<=i and float(H[i])>float(sw["price"]):
                    out[z["zone_id"]]={"anchor":float(sw["price"]),"extreme":float(H[i])}
            else:
                sw=tracker.last_high
                if sw and sw["confirmed_at"]<=i and float(sw["price"])>float(L[i]):
                    out[z["zone_id"]]={"anchor":float(sw["price"]),"extreme":float(L[i])}
    return out


def _fib_features(z,conf,child,anchor_info):
    if not anchor_info:return {}
    a=int(conf["touch_k"]); b=int(conf["confirm_k"])
    win=child[a:b+1]
    anchor=float(anchor_info["anchor"]); extreme=float(anchor_info["extreme"])
    if z["side"]=="DEMAND":
        leg=extreme-anchor
        reaction=min(float(r[3]) for r in win)
        retr=(extreme-reaction)/leg if leg>0 else None
    else:
        leg=anchor-extreme
        reaction=max(float(r[2]) for r in win)
        retr=(reaction-extreme)/leg if leg>0 else None
    if retr is None or not math.isfinite(retr):return {}
    nearest=min(FIB_LEVELS,key=lambda x:abs(retr-x))
    dist=abs(retr-nearest)
    return {
        "fib_retracement":round(float(retr),6),
        "nearest_fib":str(nearest),
        "distance_to_nearest_fib":round(float(dist),6),
        "near_fib_3pct":bool(dist<=0.03),
    }


def _fib_band(x):
    if x is None:return "NO_ANCHOR"
    x=float(x)
    if x < .382:return "<38.2"
    if x < .5:return "38.2-50"
    if x < .618:return "50-61.8"
    if x < .705:return "61.8-70.5"
    if x < .786:return "70.5-78.6"
    return ">=78.6"


@router.get("")
def context_fib_forensic(
    symbols:str=Query("BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"),
    days:int=Query(120,ge=30,le=1500),
    rr:float=Query(1.0,ge=1.0,le=3.0),
    confirm_bars:int=Query(3,ge=1,le=12),
    sample_limit:int=Query(100,ge=0,le=500),
):
    syms=[s.strip().upper() for s in symbols.split(',') if s.strip()]
    all_rows=[]; errors={}

    for symbol in syms:
        rows=_load(symbol,"1h",days)
        if len(rows)<100:
            errors[symbol]=f"not enough 1h data: {len(rows)}"; continue
        T,O,H,L,C,ATR,zones=_build_a1_zones(rows,10,0.5,3,8,1.0,0.0)
        child_start=T[0]; child_end=T[-1]+HOUR_MS
        child=_load_child_full(symbol,"5m",child_start,child_end)
        if not child:
            errors[symbol]="no 5m data"; continue
        cov=_coverage(child,child_start,child_end,"5m")
        if cov["coverage_pct"]<95:
            errors[symbol]=f"5m coverage {cov['coverage_pct']}%"; continue

        regimes=_regime_series(O,H,L,C)
        anchors=_fib_anchor_map(T,H,L,ATR,zones)
        child_times=[int(r[0]) for r in child]

        for z in zones:
            conf=_find_confirmation(z,T,child,child_times,confirm_bars,720)
            if conf.get("signal_status")!="CONFIRMED":continue
            out=_resolve_after_confirmation(z,conf,child,rr,72)
            if out.get("outcome") not in {"BOUNCE","BREAK"}:continue

            ck=int(conf["confirm_k"])
            confirm_close_ms=int(child[ck][0])+FIVE_MIN_MS
            # Latest 1H candle whose close is <= confirmation close.
            ri=bisect.bisect_right(T,confirm_close_ms-HOUR_MS)-1
            regime=regimes[ri] if 0<=ri<len(regimes) else "STARTUP"
            if z["side"]=="DEMAND":
                regime_relation="ALIGNED" if regime=="BULL" else "OPPOSED" if regime=="BEAR" else "SIDEWAYS"
            else:
                regime_relation="ALIGNED" if regime=="BEAR" else "OPPOSED" if regime=="BULL" else "SIDEWAYS"

            item={
                "symbol":symbol,"side":z["side"],"zone_id":z["zone_id"],
                "outcome":out["outcome"],"confirm_time":conf.get("confirm_time"),
                "regime":regime,"regime_relation":regime_relation,
            }
            item.update(_fib_features(z,conf,child,anchors.get(z["zone_id"])))
            item["fib_band"]=_fib_band(item.get("fib_retracement"))
            all_rows.append(item)

    regime_stats={k:_stat([r for r in all_rows if r.get("regime_relation")==k]) for k in ["ALIGNED","SIDEWAYS","OPPOSED"]}
    fib_bands=["<38.2","38.2-50","50-61.8","61.8-70.5","70.5-78.6",">=78.6","NO_ANCHOR"]
    fib_stats={k:_stat([r for r in all_rows if r.get("fib_band")==k]) for k in fib_bands}
    nearest_stats={str(f):_stat([r for r in all_rows if r.get("nearest_fib")==str(f)]) for f in FIB_LEVELS}
    near=[r for r in all_rows if r.get("near_fib_3pct") is True]
    far=[r for r in all_rows if r.get("near_fib_3pct") is False]

    wins=[r for r in all_rows if r["outcome"]=="BOUNCE"]
    losses=[r for r in all_rows if r["outcome"]=="BREAK"]

    by_pair={}
    for p in syms:
        xs=[r for r in all_rows if r["symbol"]==p]
        by_pair[p]={
            "overall":_stat(xs),
            "aligned":_stat([r for r in xs if r["regime_relation"]=="ALIGNED"]),
            "non_aligned":_stat([r for r in xs if r["regime_relation"]!="ALIGNED"]),
            "near_fib_3pct":_stat([r for r in xs if r.get("near_fib_3pct") is True]),
        }

    return {
        "phase":"V4-B2",
        "status":"REGIME_AND_FIBONACCI_FORENSIC",
        "definition":{
            "baseline":"Frozen V4-B signals/outcomes unchanged",
            "regime":"Latest fully completed causal V2 1H regime at 5m confirmation close",
            "fib_impulse_demand":"latest causally confirmed swing low at BOS close -> BOS candle high",
            "fib_impulse_supply":"latest causally confirmed swing high at BOS close -> BOS candle low",
            "fib_reaction_point":"deepest 5m wick from first touch through confirmation",
            "fib_levels":FIB_LEVELS,
            "near_fib_diagnostic":"absolute retracement distance <= 0.03; descriptive only",
        },
        "overall":_stat(all_rows),
        "regime_relation":regime_stats,
        "fib_bands":fib_stats,
        "nearest_fib":nearest_stats,
        "near_fib_3pct":{"near":_stat(near),"far":_stat(far)},
        "winner_vs_loser":{
            "winner_median_retracement":_median([r.get("fib_retracement") for r in wins]),
            "loser_median_retracement":_median([r.get("fib_retracement") for r in losses]),
            "winner_median_distance_to_nearest_fib":_median([r.get("distance_to_nearest_fib") for r in wins]),
            "loser_median_distance_to_nearest_fib":_median([r.get("distance_to_nearest_fib") for r in losses]),
        },
        "by_pair":by_pair,
        "errors":errors,
        "sample":all_rows[-sample_limit:] if sample_limit else [],
    }
