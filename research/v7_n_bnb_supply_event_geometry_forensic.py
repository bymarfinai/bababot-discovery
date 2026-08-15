#!/usr/bin/env python3
"""V7-N — BNB SUPPLY <38.2 event-geometry forensic.

Research only; no live/order integration and no trading-rule optimization.

Frozen target inherited from V7-J/L/M:
  pair=BNBUSDT, side=SUPPLY, fib_band=<38.2, RR=1, confirm_bars=3.

Question:
Can the recent B6-B8 ON era (~72% WR) be explained by event-local geometry
already observable at confirmation time, rather than broad market regime?

Feature inventory is deliberately limited to fields already produced by the
frozen V4-A1/V4-B/V4-B1 pipeline plus deterministic geometry derived from those
same frozen objects:
- 1H zone/BOS geometry: zone width, base->BOS, BOS distance/displacement,
  BOS body/close location, volume expansion;
- causal impulse geometry: impulse leg / ATR and zone position vs anchor/extreme;
- first-touch timing: zone age at touch (hours);
- 5m absorption/reclaim geometry from pre-existing V4-B1 _enrich;
- exact fib retracement from pre-existing V4-B2.

No feature threshold is used to filter trades in this run. Prior-touch count is
not a feature because V4-B is first-touch-only by construction (always zero
before the evaluated touch).
"""

import json
import math
import os
import sqlite3
import statistics
from datetime import datetime, timezone, timedelta

import numpy as np

from research import v7_f_fib_120d_archive_audit as archive

PAIR = "BNBUSDT"
DAYS = 971
BLOCK_DAYS = 120
WINDOW_END = datetime.fromisoformat("2026-08-15T15:11:15.831175+00:00")
WINDOW_START = WINDOW_END - timedelta(days=DAYS)
DB = "/tmp/v7_n_bnb_geometry.db"

# All were defined before this run by V4-A1 / V4-B1 / V4-B2, except the last
# four deterministic timing/impulse ratios which require no tunable threshold.
FEATURES = [
    "zone_width_atr", "base_to_bos_bars", "bos_distance_atr", "displacement_atr",
    "bos_body_ratio", "bos_close_location", "volume_expansion",
    "zone_width_pct", "bars_to_confirm", "abs_delta_pct",
    "penetration_zone_x", "close_penetration_zone_x", "reclaim_extension_zone_x",
    "confirm_body_ratio", "confirm_close_location", "quote_volume_expansion",
    "adverse_progress_per_delta", "fib_retracement", "distance_to_nearest_fib",
    "retest_age_hours", "impulse_leg_atr", "zone_to_anchor_atr",
    "zone_to_extreme_atr", "confirm_directional_body_ratio", "confirm_rejection_wick_ratio",
]


def stat(rows):
    n = len(rows); w = sum(int(r["win"]) for r in rows)
    return {"n": n, "wins": w, "losses": n-w,
            "wr_pct": round(100.0*w/n, 2) if n else None}


def finite(vals):
    out=[]
    for v in vals:
        try:
            x=float(v)
            if math.isfinite(x): out.append(x)
        except Exception:
            pass
    return out


def med(vals):
    x=finite(vals)
    return float(statistics.median(x)) if x else None


def mean(vals):
    x=finite(vals)
    return float(statistics.mean(x)) if x else None


def std(vals):
    x=finite(vals)
    return float(statistics.pstdev(x)) if len(x)>=2 else None


def effect_size(a, b):
    """Absolute standardized mean difference; descriptive only."""
    xa=finite(a); xb=finite(b)
    if len(xa)<2 or len(xb)<2:return None
    va=np.var(np.asarray(xa,dtype=float),ddof=1); vb=np.var(np.asarray(xb,dtype=float),ddof=1)
    denom=math.sqrt(((len(xa)-1)*va+(len(xb)-1)*vb)/max(1,len(xa)+len(xb)-2))
    if denom<=0:return 0.0
    return float((np.mean(xb)-np.mean(xa))/denom)


def quartiles(rows, feature):
    z=[]
    for r in rows:
        try:
            x=float(r.get(feature))
            if math.isfinite(x):z.append((x,r))
        except Exception:
            pass
    z.sort(key=lambda t:t[0])
    if len(z)<12:return []
    groups=np.array_split(np.arange(len(z)),4)
    ans=[]
    for qi,ids in enumerate(groups,1):
        rr=[z[int(i)][1] for i in ids]
        vv=[z[int(i)][0] for i in ids]
        ans.append({"q":qi,**stat(rr),"value_median":round(float(np.median(vv)),6)})
    return ans


def monotonic_direction(qs):
    if len(qs)!=4 or any(q["wr_pct"] is None for q in qs):return None
    w=[q["wr_pct"] for q in qs]
    up=all(w[i]<=w[i+1] for i in range(3))
    down=all(w[i]>=w[i+1] for i in range(3))
    return "UP" if up else "DOWN" if down else None


def build_db():
    if os.path.exists(DB):os.unlink(DB)
    conn=sqlite3.connect(DB)
    conn.execute("""CREATE TABLE klines(
        symbol TEXT,timeframe TEXT,open_time INTEGER,
        open REAL,high REAL,low REAL,close REAL,volume REAL,
        close_time INTEGER,quote_volume REAL,trades INTEGER,
        taker_buy_volume REAL,taker_buy_quote_volume REAL,
        PRIMARY KEY(symbol,timeframe,open_time))""")
    coverage={}
    for tf in ("1h","5m"):
        rows=archive.load_series(PAIR,tf,WINDOW_START,WINDOW_END)
        conn.executemany("INSERT OR REPLACE INTO klines VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",rows)
        conn.commit()
        coverage[tf]={"rows":len(rows),
                      "first":datetime.fromtimestamp(rows[0][2]/1000,tz=timezone.utc).isoformat() if rows else None,
                      "last":datetime.fromtimestamp(rows[-1][2]/1000,tz=timezone.utc).isoformat() if rows else None}
    conn.close();return coverage


def fixed_load(symbol,timeframe,days):
    conn=sqlite3.connect(DB)
    try:
        return conn.execute("""SELECT open_time,open,high,low,close,volume
            FROM klines WHERE symbol=? AND timeframe=? AND open_time>=? AND open_time<?
            ORDER BY open_time ASC""",
            (symbol,timeframe,int(WINDOW_START.timestamp()*1000),int(WINDOW_END.timestamp()*1000))).fetchall()
    finally:conn.close()


def child_extra(child, conf):
    b=int(conf["confirm_k"]); cr=child[b]
    o,h,l,c=map(float,cr[1:5]); rng=max(h-l,0.0)
    directional=(o-c)/rng if rng>0 else 0.0  # SUPPLY: positive = bearish body
    rejection=(h-max(o,c))/rng if rng>0 else 0.0  # SUPPLY upper wick
    return {
        "confirm_directional_body_ratio":round(float(directional),6),
        "confirm_rejection_wick_ratio":round(float(rejection),6),
    }


def main():
    coverage=build_db();os.environ["DB_PATH"]=DB

    import v4_context_fib_forensic_endpoint as fib
    import v4_absorption_forensic_endpoint as af
    from v4_first_retest_endpoint import _build_a1_zones, HOUR_MS, _coverage
    from v4_reaction_absorption_endpoint import _load_child_full, _find_confirmation, _resolve_after_confirmation

    fib._load=fixed_load
    rows=fixed_load(PAIR,"1h",DAYS)
    T,O,H,L,C,ATR,zones=_build_a1_zones(rows,10,0.5,3,8,1.0,0.0)
    child=_load_child_full(PAIR,"5m",T[0],T[-1]+HOUR_MS)
    cov=_coverage(child,T[0],T[-1]+HOUR_MS,"5m")
    if cov["coverage_pct"]<95:raise RuntimeError(f"5m coverage {cov['coverage_pct']}")
    child_times=[int(r[0]) for r in child]
    anchors=fib._fib_anchor_map(T,H,L,ATR,zones)

    events=[]
    for z in zones:
        if z["side"]!="SUPPLY":continue
        conf=_find_confirmation(z,T,child,child_times,3,720)
        if conf.get("signal_status")!="CONFIRMED":continue
        out=_resolve_after_confirmation(z,conf,child,1.0,72)
        if out.get("outcome") not in {"BOUNCE","BREAK"}:continue
        ff=fib._fib_features(z,conf,child,anchors.get(z["zone_id"]))
        if fib._fib_band(ff.get("fib_retracement"))!="<38.2":continue

        dt=datetime.fromisoformat(conf["confirm_time"])
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        dt=dt.astimezone(timezone.utc)
        block=int(((dt-WINDOW_START).total_seconds())//(BLOCK_DAYS*86400))+1

        item={"pair":PAIR,"side":"SUPPLY","band":"<38.2","block":block,"t":dt,
              "win":1 if out["outcome"]=="BOUNCE" else 0,"outcome":out["outcome"],
              "zone_id":z["zone_id"]}
        for k in ["zone_width_atr","base_to_bos_bars","bos_distance_atr","displacement_atr",
                  "bos_body_ratio","bos_close_location","volume_expansion"]:
            item[k]=z.get(k)
        item.update(af._enrich(z,conf,child))
        item.update(ff)
        item.update(child_extra(child,conf))

        bos_close=int(T[int(z["bos_bar"])])+HOUR_MS
        touch_t=int(child[int(conf["touch_k"])][0])
        item["retest_age_hours"]=round((touch_t-bos_close)/HOUR_MS,6)

        ai=anchors.get(z["zone_id"])
        a=float(z.get("atr") or 0.0)
        if ai and a>0:
            anchor=float(ai["anchor"]); extreme=float(ai["extreme"])
            item["impulse_leg_atr"]=round((anchor-extreme)/a,6)
            item["zone_to_anchor_atr"]=round((anchor-float(z["zone_high"]))/a,6)
            item["zone_to_extreme_atr"]=round((float(z["zone_low"])-extreme)/a,6)
        else:
            item["impulse_leg_atr"]=item["zone_to_anchor_atr"]=item["zone_to_extreme_atr"]=None
        events.append(item)

    events.sort(key=lambda r:r["t"])
    in8=[r for r in events if 1<=r["block"]<=8]
    hold=[r for r in in8 if 1<=r["block"]<=5]
    recent=[r for r in in8 if 6<=r["block"]<=8]
    block5=[r for r in in8 if r["block"]==5]

    parity={
        "all8":stat(in8),"holdout_b1_b5":stat(hold),"recent_b6_b8":stat(recent),"block5":stat(block5),
        "expected":{"all8":{"n":39,"wins":21,"losses":18},"holdout_b1_b5":{"n":21,"wins":8,"losses":13},"recent_b6_b8":{"n":18,"wins":13,"losses":5}},
    }
    parity["pass"]=(parity["all8"]["n"]==39 and parity["all8"]["wins"]==21 and
                    parity["holdout_b1_b5"]["n"]==21 and parity["holdout_b1_b5"]["wins"]==8 and
                    parity["recent_b6_b8"]["n"]==18 and parity["recent_b6_b8"]["wins"]==13)

    block_stats=[]
    for b in range(1,9):
        xs=[r for r in in8 if r["block"]==b]
        block_stats.append({"block":b,**stat(xs),"feature_medians":{f:round(med([r.get(f) for r in xs]),6) if med([r.get(f) for r in xs]) is not None else None for f in FEATURES}})

    reports=[]
    for f in FEATURES:
        hm=med([r.get(f) for r in hold]); rm=med([r.get(f) for r in recent]); b5m=med([r.get(f) for r in block5])
        qs=quartiles(in8,f); mono=monotonic_direction(qs)
        all_w=med([r.get(f) for r in in8 if r["win"]]); all_l=med([r.get(f) for r in in8 if not r["win"]])
        rec_w=med([r.get(f) for r in recent if r["win"]]); rec_l=med([r.get(f) for r in recent if not r["win"]])
        hold_w=med([r.get(f) for r in hold if r["win"]]); hold_l=med([r.get(f) for r in hold if not r["win"]])
        spread=None
        if len(qs)==4 and qs[0]["wr_pct"] is not None and qs[-1]["wr_pct"] is not None:
            spread=round(qs[-1]["wr_pct"]-qs[0]["wr_pct"],2)
        reports.append({
            "feature":f,
            "holdout_median":round(hm,6) if hm is not None else None,
            "recent_median":round(rm,6) if rm is not None else None,
            "block5_median":round(b5m,6) if b5m is not None else None,
            "recent_minus_holdout_effect_d":round(effect_size([r.get(f) for r in hold],[r.get(f) for r in recent]),4) if effect_size([r.get(f) for r in hold],[r.get(f) for r in recent]) is not None else None,
            "all_winner_median":round(all_w,6) if all_w is not None else None,
            "all_loser_median":round(all_l,6) if all_l is not None else None,
            "holdout_winner_median":round(hold_w,6) if hold_w is not None else None,
            "holdout_loser_median":round(hold_l,6) if hold_l is not None else None,
            "recent_winner_median":round(rec_w,6) if rec_w is not None else None,
            "recent_loser_median":round(rec_l,6) if rec_l is not None else None,
            "quartile_wr":qs,"q4_minus_q1_wr_pp":spread,"strict_monotonic_wr":mono,
        })

    # Rank only for inspection. This is NOT a gate-selection rule.
    def score(x):
        d=abs(x["recent_minus_holdout_effect_d"] or 0.0)
        sp=abs(x["q4_minus_q1_wr_pp"] or 0.0)
        mono=1.0 if x["strict_monotonic_wr"] else 0.0
        return (mono,d,sp)
    ranked=sorted(reports,key=score,reverse=True)

    result={
        "phase":"V7-N","status":"BNB_SUPPLY_EVENT_GEOMETRY_FORENSIC",
        "definition":{"pair":PAIR,"side":"SUPPLY","fib_band":"<38.2","rr":1.0,"confirm_bars":3,
                      "holdout_blocks":[1,2,3,4,5],"recent_on_blocks":[6,7,8],
                      "feature_threshold_search":False,"trade_filtering":False,"tp_sl_sweep":False,"live_changes":False,
                      "prior_touch_count":"invariant zero before evaluated touch because V4-B is first-touch-only"},
        "coverage":{"archive":coverage,"child":cov},"parity":parity,
        "blocks":block_stats,"feature_reports":reports,"ranked_descriptive":ranked,
        "interpretation_lock":"This run is forensic only. No threshold may be promoted from this output without a separate frozen validation run.",
    }
    print("V7_N_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__":main()
