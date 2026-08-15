"""V4-B1 — forensic separation of confirmed 5m absorption winners vs losers.

This is descriptive only. It reuses the frozen V4-B event/entry/outcome logic and
asks which already-observable features differ between BOUNCE and BREAK.
No feature is used to filter trades in this endpoint.
"""

import bisect
import math
import statistics
from fastapi import APIRouter, Query

from v4_structural_zone_endpoint import _load, _ts
from v4_first_retest_endpoint import HOUR_MS, _build_a1_zones, _coverage
from v4_reaction_absorption_endpoint import (
    _load_child_full,
    _find_confirmation,
    _resolve_after_confirmation,
)

router = APIRouter(prefix="/v4/absorption-forensic", tags=["v4_absorption_forensic"])


def _median(xs):
    xs=[float(x) for x in xs if x is not None and math.isfinite(float(x))]
    return round(float(statistics.median(xs)), 6) if xs else None


def _pct(a,b):
    return 100.0*a/b if b else 0.0


def _prior_quote_median(rows, k, lb=20):
    vals=[float(rows[i][5] or 0.0) for i in range(max(0,k-lb),k) if float(rows[i][5] or 0.0)>0]
    return float(statistics.median(vals)) if vals else None


def _enrich(zone, conf, child_rows):
    if conf.get("signal_status") != "CONFIRMED":
        return {}
    a=int(conf["touch_k"]); b=int(conf["confirm_k"])
    win=child_rows[a:b+1]
    zlo=float(zone["zone_low"]); zhi=float(zone["zone_high"]); zw=zhi-zlo
    if zw<=0:return {}

    lows=[float(r[3]) for r in win]; highs=[float(r[2]) for r in win]
    closes=[float(r[4]) for r in win]
    qsum=sum(float(r[5] or 0.0) for r in win)
    prior_q=_prior_quote_median(child_rows,a,20)
    q_per_bar=qsum/max(1,len(win))
    qexp=q_per_bar/prior_q if prior_q and prior_q>0 else None

    cr=child_rows[b]
    o,h,l,c=map(float,cr[1:5]); rng=max(h-l,0.0)
    body=abs(c-o)/rng if rng>0 else 0.0

    if zone["side"]=="DEMAND":
        penetration=max(0.0,zhi-min(lows))/zw
        close_pen=max(0.0,zhi-min(closes))/zw
        reclaim=max(0.0,c-zhi)/zw
        close_loc=(c-l)/rng if rng>0 else 0.5
    else:
        penetration=max(0.0,max(highs)-zlo)/zw
        close_pen=max(0.0,max(closes)-zlo)/zw
        reclaim=max(0.0,zlo-c)/zw
        close_loc=(h-c)/rng if rng>0 else 0.5

    abs_delta_pct=abs(float(conf.get("cumulative_delta_pct",0.0)))
    # Lower value = less adverse closing progress for a given amount of aggressive pressure.
    adverse_progress_per_delta=close_pen/max(abs_delta_pct,0.01)

    return {
        "bars_to_confirm": int(conf.get("bars_to_confirm",0)),
        "abs_delta_pct": round(abs_delta_pct,6),
        "penetration_zone_x": round(penetration,6),
        "close_penetration_zone_x": round(close_pen,6),
        "reclaim_extension_zone_x": round(reclaim,6),
        "confirm_body_ratio": round(body,6),
        "confirm_close_location": round(close_loc,6),
        "quote_volume_expansion": round(qexp,6) if qexp is not None else None,
        "adverse_progress_per_delta": round(adverse_progress_per_delta,8),
        "zone_width_pct": round(100.0*zw/float(conf["entry"]),6),
    }


def _compare(rows, features):
    wins=[r for r in rows if r.get("outcome")=="BOUNCE"]
    losses=[r for r in rows if r.get("outcome")=="BREAK"]
    out={}
    for f in features:
        wm=_median([r.get(f) for r in wins]); lm=_median([r.get(f) for r in losses])
        out[f]={
            "winner_median":wm,
            "loser_median":lm,
            "median_diff": round(wm-lm,6) if wm is not None and lm is not None else None,
        }
    return out


def _quartiles(rows, feature):
    xs=[float(r[feature]) for r in rows if r.get(feature) is not None and math.isfinite(float(r[feature]))]
    if len(xs)<8:return []
    s=sorted(xs)
    def q(p):
        return s[min(len(s)-1,max(0,int(round((len(s)-1)*p))))]
    cuts=[q(.25),q(.5),q(.75)]
    buckets=[[],[],[],[]]
    for r in rows:
        v=r.get(feature)
        if v is None:continue
        v=float(v)
        idx=0 if v<=cuts[0] else 1 if v<=cuts[1] else 2 if v<=cuts[2] else 3
        buckets[idx].append(r)
    ans=[]
    for i,b in enumerate(buckets):
        w=sum(r.get("outcome")=="BOUNCE" for r in b); n=len(b)
        ans.append({"bucket":i+1,"n":n,"wr_pct":round(_pct(w,n),2) if n else None})
    return ans


def _pair_direction(rows, feature):
    """Compare winner-vs-loser median direction by pair; descriptive consistency only."""
    out={}
    for p in sorted(set(r["symbol"] for r in rows)):
        xs=[r for r in rows if r["symbol"]==p]
        w=[r[feature] for r in xs if r.get("outcome")=="BOUNCE" and r.get(feature) is not None]
        l=[r[feature] for r in xs if r.get("outcome")=="BREAK" and r.get(feature) is not None]
        wm=_median(w); lm=_median(l)
        out[p]={"winner_median":wm,"loser_median":lm,"direction": None if wm is None or lm is None else ("HIGHER_IN_WINNERS" if wm>lm else "LOWER_IN_WINNERS" if wm<lm else "EQUAL")}
    return out


@router.get("")
def absorption_forensic(
    symbols: str = Query("BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT"),
    days: int = Query(120, ge=30, le=1500),
    rr: float = Query(1.0, ge=1.0, le=3.0),
    confirm_bars: int = Query(3, ge=1, le=12),
    sample_limit: int = Query(200, ge=0, le=500),
):
    syms=[s.strip().upper() for s in symbols.split(',') if s.strip()]
    all_rows=[]; pair_stats={}; errors={}

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
        times=[int(r[0]) for r in child]
        pr=[]
        for z in zones:
            conf=_find_confirmation(z,T,child,times,confirm_bars,720)
            if conf.get("signal_status")!="CONFIRMED":continue
            out=_resolve_after_confirmation(z,conf,child,rr,72)
            if out.get("outcome") not in {"BOUNCE","BREAK"}:continue
            item={"symbol":symbol,"side":z["side"],"zone_id":z["zone_id"],"confirm_time":conf.get("confirm_time"),"outcome":out["outcome"]}
            item.update(_enrich(z,conf,child)); pr.append(item); all_rows.append(item)
        w=sum(r["outcome"]=="BOUNCE" for r in pr); n=len(pr)
        pair_stats[symbol]={"resolved":n,"wins":w,"losses":n-w,"wr_pct":round(_pct(w,n),2) if n else None}

    features=[
        "bars_to_confirm","abs_delta_pct","penetration_zone_x","close_penetration_zone_x",
        "reclaim_extension_zone_x","confirm_body_ratio","confirm_close_location",
        "quote_volume_expansion","adverse_progress_per_delta","zone_width_pct",
    ]
    w=sum(r["outcome"]=="BOUNCE" for r in all_rows); n=len(all_rows)
    return {
        "phase":"V4-B1",
        "status":"ABSORPTION_WINNER_LOSER_FORENSIC",
        "definition":"Frozen V4-B signals only; no filtering or tuning applied.",
        "symbols":syms,"days":days,"rr":rr,"confirm_bars":confirm_bars,
        "overall":{"resolved":n,"wins":w,"losses":n-w,"wr_pct":round(_pct(w,n),2) if n else None},
        "by_pair":pair_stats,"errors":errors,
        "winner_vs_loser":_compare(all_rows,features),
        "quartile_wr":{f:_quartiles(all_rows,f) for f in features},
        "pair_direction_consistency":{f:_pair_direction(all_rows,f) for f in features},
        "notes":{
            "penetration_zone_x":"1.0 means wick reached the distal edge; >1.0 means wick pierced it before reclaim.",
            "close_penetration_zone_x":"adverse closing progress into/through zone, normalized by zone width.",
            "adverse_progress_per_delta":"adverse closing progress divided by abs cumulative taker-delta percentage; lower means more pressure absorbed with less price progress.",
            "reclaim_extension_zone_x":"confirmation close distance beyond proximal edge / zone width.",
        },
        "sample":all_rows[-sample_limit:] if sample_limit else [],
    }
