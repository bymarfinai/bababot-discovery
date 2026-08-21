#!/usr/bin/env python3
"""Performance-only runner for preregistered B11.

No research rule is changed. It monkey-patches only the development ranking implementation
so the candidate table is scanned once instead of once per rule.
"""
from pathlib import Path
import numpy as np
import pandas as pd
import btc_weekly_mtf_level_atlas_b11 as b11

ROOT = Path(__file__).resolve().parent.parent
b11.OUT_MD = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Result.md"
b11.OUT_JSON = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Result.json"
b11.OUT_SEL = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Selected.csv"
b11.OUT_RULES = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Rules.csv"
b11.OUT_ATLAS = ROOT / "BTC_WEEKLY_MTF_LEVEL_ATLAS_B11_FAST_Atlas.csv"


def scan_mask(s):
    ts=pd.to_datetime(s,utc=True)
    wd=ts.dt.weekday.to_numpy(int)
    hr=ts.dt.hour.to_numpy(int)
    return (wd<5)|((wd==5)&(hr<=b11.SCAN_CUTOFF_HOUR))


def fast_rank(cand,dev_weeks):
    ws=b11.week_set(dev_weeks)
    m=scan_mask(cand.signal_ts)
    q=cand.loc[m & cand.week.isin(ws)].sort_values(["rule","signal_ts"])
    routed=q.groupby(["rule","week"],as_index=False,sort=False).head(1)
    by={k:v for k,v in routed.groupby("rule",sort=False)}
    rows=[]
    for rule in sorted(cand.rule.unique()):
        x=by.get(rule,cand.iloc[0:0])
        s=b11.stat(x,dev_weeks)
        parts=rule.split("|")
        rows.append({"rule":rule,"source_tf":parts[0],"family":parts[1],"side_type":parts[2],"mode":parts[3],**s})
    r=pd.DataFrame(rows)
    r["fullcov"]=(r.coverage>=1.0-1e-12).astype(int)
    r["wr_sort"]=r.wr.fillna(-1.0); r["pf_sort"]=r.pf.fillna(-1.0)
    r=r.sort_values(["fullcov","wr_sort","wilson","pf_sort","n","rule"],ascending=[False,False,False,False,False,True]).reset_index(drop=True)
    r["rank"]=np.arange(1,len(r)+1)
    return r


def fast_route_rule(cand,rule,weeks):
    ws=b11.week_set(weeks); m=scan_mask(cand.signal_ts)
    q=cand.loc[m & (cand.rule==rule) & cand.week.isin(ws)].sort_values("signal_ts")
    if q.empty:return q
    q=q.groupby("week",as_index=False,sort=False).head(1).copy(); q["route"]="PRIMARY_RULE"
    return q.sort_values("signal_ts").reset_index(drop=True)


def fast_route_top4(cand,rules,weeks):
    ws=b11.week_set(weeks); rank={r:i for i,r in enumerate(rules)}; m=scan_mask(cand.signal_ts)
    q=cand.loc[m & cand.rule.isin(rules) & cand.week.isin(ws)].copy()
    if q.empty:return q
    q["router_rank"]=q.rule.map(rank).astype(int)
    q=q.sort_values(["signal_ts","router_rank","rule"]).groupby("week",as_index=False,sort=False).head(1).copy()
    q["route"]="TOP4_ROUTER"
    return q.sort_values("signal_ts").reset_index(drop=True)

b11.rank_development_rules=fast_rank
b11.route_rule=fast_route_rule
b11.route_top4=fast_route_top4

if __name__=="__main__":
    b11.main()
    # Explicitly mark this as a performance-only implementation revision.
    p=b11.OUT_MD
    if p.exists():
        txt=p.read_text(encoding="utf-8")
        txt=txt.replace("# BTC Weekly MTF Level Atlas B11 — Result","# BTC Weekly MTF Level Atlas B11 — Result\n\nImplementation revision **B11_FAST1** (performance-only; preregistered logic unchanged).",1)
        p.write_text(txt,encoding="utf-8")
