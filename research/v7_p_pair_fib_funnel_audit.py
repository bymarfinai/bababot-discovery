#!/usr/bin/env python3
"""V7-P — pair-level FIB funnel + anchor audit.

Research only. No live/order changes. No threshold optimization.

Question:
Why are some pair x FIB cells sparse? Distinguish:
1) structural scarcity (few 1H zones),
2) anchor scarcity/invalidity,
3) first-retest / V4-B confirmation scarcity,
4) outcome resolution scarcity,
5) genuine pair-specific retracement distribution.

Uses the exact frozen V7-J 971d window and unchanged V4-A1/V4-B/V4-B2 logic.
The 23.6% level is reported only because V7-O already froze it; no new band is
selected here.
"""
import json, math, os, statistics
from collections import Counter, defaultdict

from research import v7_j_fib_pair_120d_vs_120d as j

PAIRS=j.PAIRS
SIDES=("DEMAND","SUPPLY")


def pct(a,b): return round(100.0*a/b,2) if b else None

def q(vals,p):
    xs=sorted(float(x) for x in vals if x is not None and math.isfinite(float(x)))
    if not xs:return None
    pos=(len(xs)-1)*p; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    if lo==hi:return round(xs[lo],6)
    v=xs[lo]*(hi-pos)+xs[hi]*(pos-lo)
    return round(v,6)

def dist(vals):
    xs=[float(x) for x in vals if x is not None and math.isfinite(float(x))]
    return {"n":len(xs),"p10":q(xs,.10),"p25":q(xs,.25),"median":q(xs,.50),"p75":q(xs,.75),"p90":q(xs,.90),
            "min":round(min(xs),6) if xs else None,"max":round(max(xs),6) if xs else None}

def outcome_stat(rows):
    n=len(rows); w=sum(r.get("outcome")=="BOUNCE" for r in rows)
    return {"n":n,"wins":w,"losses":n-w,"wr_pct":pct(w,n)}

def stage_report(zones, rows, anchor_map):
    zone_ids={z["zone_id"] for z in zones}
    zs=[z for z in zones if z["zone_id"] in zone_ids]
    rs=[r for r in rows if r["zone_id"] in zone_ids]
    status=Counter(r["signal_status"] for r in rs)
    confirmed=[r for r in rs if r["signal_status"]=="CONFIRMED"]
    resolved=[r for r in confirmed if r.get("outcome") in ("BOUNCE","BREAK")]
    anchored_z=[z for z in zs if z["zone_id"] in anchor_map]
    anchored_conf=[r for r in confirmed if r["zone_id"] in anchor_map]
    anchored_res=[r for r in resolved if r["zone_id"] in anchor_map and r.get("fib_retracement") is not None]
    retr=[r["fib_retracement"] for r in anchored_res]
    canonical=[r for r in anchored_res if .236 <= float(r["fib_retracement"]) < .382]
    shallow=[r for r in anchored_res if float(r["fib_retracement"]) < .236]
    b382_50=[r for r in anchored_res if .382 <= float(r["fib_retracement"]) < .5]
    return {
        "zones":len(zs),
        "zones_with_causal_anchor":len(anchored_z),
        "anchor_rate_pct":pct(len(anchored_z),len(zs)),
        "signal_status_counts":dict(status),
        "touched_or_decided":sum(v for k,v in status.items() if k!="NO_RETEST"),
        "confirmed":len(confirmed),
        "confirmation_rate_per_zone_pct":pct(len(confirmed),len(zs)),
        "confirmation_rate_given_not_no_retest_pct":pct(len(confirmed),sum(v for k,v in status.items() if k!="NO_RETEST")),
        "confirmed_with_anchor":len(anchored_conf),
        "resolved":len(resolved),
        "resolved_with_anchor":len(anchored_res),
        "resolved_outcome":outcome_stat(resolved),
        "retracement_distribution":dist(retr),
        "retracement_sanity":{"negative":sum(float(x)<0 for x in retr),"gt_100pct":sum(float(x)>1 for x in retr),"within_0_100pct":sum(0<=float(x)<=1 for x in retr)},
        "fib_23.6_38.2":outcome_stat(canonical),
        "fib_lt23.6":outcome_stat(shallow),
        "fib_38.2_50":outcome_stat(b382_50),
        "share_23.6_38.2_of_resolved_anchor_pct":pct(len(canonical),len(anchored_res)),
        "share_lt23.6_of_resolved_anchor_pct":pct(len(shallow),len(anchored_res)),
    }

def main():
    coverage=j.build_db(); os.environ["DB_PATH"]=j.DB
    from v4_first_retest_endpoint import _build_a1_zones, _coverage, HOUR_MS
    import v4_reaction_absorption_endpoint as react
    import v4_context_fib_forensic_endpoint as fib

    fib._load=j.fixed_load
    reports={}; all_retr_by_side=defaultdict(list)
    for p in PAIRS:
        rows=j.fixed_load(p,"1h",j.DAYS)
        T,O,H,L,C,ATR,zones=_build_a1_zones(rows,10,0.5,3,8,1.0,0.0)
        child=react._load_child_full(p,"5m",T[0],T[-1]+HOUR_MS)
        cov=_coverage(child,T[0],T[-1]+HOUR_MS,"5m")
        if cov["coverage_pct"]<99.0: raise RuntimeError(f"{p} child coverage {cov}")
        times=[int(r[0]) for r in child]
        anchors=fib._fib_anchor_map(T,H,L,ATR,zones)
        event_rows=[]
        for z in zones:
            conf=react._find_confirmation(z,T,child,times,3,720)
            item={"zone_id":z["zone_id"],"side":z["side"],"signal_status":conf.get("signal_status")}
            item.update(conf)
            if conf.get("signal_status")=="CONFIRMED":
                out=react._resolve_after_confirmation(z,conf,child,1.0,72); item.update(out)
                if out.get("outcome") in ("BOUNCE","BREAK") and z["zone_id"] in anchors:
                    ff=fib._fib_features(z,conf,child,anchors[z["zone_id"]]); item.update(ff)
                    item["fib_band_original"]=fib._fib_band(item.get("fib_retracement"))
                    if item.get("fib_retracement") is not None: all_retr_by_side[z["side"]].append(float(item["fib_retracement"]))
            event_rows.append(item)

        pair={"data":{"bars_1h":len(rows),"bars_5m":len(child),"coverage_5m_pct":cov["coverage_pct"]},
              "all":stage_report(zones,event_rows,anchors),"by_side":{}}
        for side in SIDES:
            zside=[z for z in zones if z["side"]==side]
            pair["by_side"][side]=stage_report(zside,event_rows,anchors)
        # Distribution of original V4-B2 bands on resolved anchored events.
        for side in SIDES:
            counts=Counter()
            for r in event_rows:
                if r.get("side")==side and r.get("outcome") in ("BOUNCE","BREAK") and r.get("fib_retracement") is not None:
                    counts[fib._fib_band(r["fib_retracement"])]+=1
            pair["by_side"][side]["original_fib_band_counts"]=dict(counts)
        reports[p]=pair

    # Cross-pair comparison: if anchor/confirm rates are similar but retracement
    # distributions differ, sparsity is a genuine pair-distribution effect rather
    # than missing-data or formula-scale issue.
    supply_summary=[]
    for p in PAIRS:
        s=reports[p]["by_side"]["SUPPLY"]
        supply_summary.append({"pair":p,"zones":s["zones"],"anchor_rate_pct":s["anchor_rate_pct"],
                               "confirmed":s["confirmed"],"confirmation_rate_per_zone_pct":s["confirmation_rate_per_zone_pct"],
                               "resolved_with_anchor":s["resolved_with_anchor"],
                               "retracement_median":s["retracement_distribution"]["median"],
                               "n_23.6_38.2":s["fib_23.6_38.2"]["n"],"wr_23.6_38.2":s["fib_23.6_38.2"]["wr_pct"],
                               "share_23.6_38.2_pct":s["share_23.6_38.2_of_resolved_anchor_pct"],
                               "n_lt23.6":s["fib_lt23.6"]["n"],"share_lt23.6_pct":s["share_lt23.6_of_resolved_anchor_pct"]})

    result={"phase":"V7-P","status":"PAIR_FIB_FUNNEL_AND_ANCHOR_AUDIT",
            "definition":{"window_start":j.WINDOW_START.isoformat(),"window_end":j.WINDOW_END.isoformat(),"days":j.DAYS,
                          "zone_logic":"frozen V4-A1","confirmation":"frozen V4-B, first touch, <=3x5m, taker-flow absorption/reclaim",
                          "fib_anchor":"frozen V4-B2 causal opposite swing -> BOS extreme","rr":1.0,
                          "reported_existing_level":"23.6% boundary inherited from V7-O","threshold_sweep":False,"live_changes":False},
            "coverage":coverage,"pairs":reports,"supply_cross_pair_summary":supply_summary,
            "formula_sanity_note":"Retracement is dimensionless: SUPPLY=(reaction_high-BOS_low)/(causal_swing_high-BOS_low); DEMAND is symmetric. Pair price scale cannot by itself change the ratio.",
            "interpretation_lock":"This run diagnoses sparsity only. It must not select a new pair-specific threshold or FIB band."}
    print("V7_P_RESULT",json.dumps(result,separators=(",",":"),default=str))

if __name__=="__main__": main()
