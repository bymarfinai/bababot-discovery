#!/usr/bin/env python3
"""V10-E — BTC London dynamic direction classifier (research only).

Goal: infer BUY / SELL / NO TRADE dynamically 15 minutes after London cash open,
using only information available at that decision time.

Frozen design:
- Pair BTCUSDT, 5m source data.
- London open 08:00 Europe/London, DST-aware.
- Decision point = +15m after open.
- Target = sign of return from decision close to close 60m later.
- Train = previous 120d; validation = latest 120d.
- Interpretable DecisionTreeClassifier(max_depth=3, min_samples_leaf=15, random_state=42).
- A leaf trades only if training leaf purity >= 60%; otherwise NO TRADE.
- No hyperparameter sweep, no TP/SL, no fee/slippage, no live changes.
"""

import json, math
from datetime import datetime, timedelta, timezone
from statistics import mean
from zoneinfo import ZoneInfo

from research.v7_f_fib_120d_archive_audit import load_series

PAIR="BTCUSDT"
PREV_START=datetime.fromisoformat("2025-12-07T15:11:15.831175+00:00")
LATEST_START=datetime.fromisoformat("2026-04-06T15:11:15.831175+00:00")
LATEST_END=datetime.fromisoformat("2026-08-04T15:11:15.831175+00:00")
DATA_START=(PREV_START-timedelta(days=3)).replace(hour=0,minute=0,second=0,microsecond=0)
DATA_END=(LATEST_END+timedelta(days=2)).replace(hour=0,minute=0,second=0,microsecond=0)
LON=ZoneInfo("Europe/London")

FEATURES=[
    "pre_ret_1h","pre_ret_4h","pre_ret_24h",
    "day_pos","day_range_pct","dist_hod_pct","dist_lod_pct",
    "dist_pdh_pct","dist_pdl_pct",
    "rv_1h","rv_4h",
    "open15_ret","open15_range_pct","open15_close_pos",
]

def tdt(r): return datetime.fromtimestamp(int(r[2])/1000,tz=timezone.utc)
def o(r): return float(r[3])
def h(r): return float(r[4])
def l(r): return float(r[5])
def c(r): return float(r[6])
def ret(a,b): return 100.0*(b-a)/a if a else 0.0

def block(t):
    if PREV_START <= t < LATEST_START: return "train"
    if LATEST_START <= t < LATEST_END: return "validation"
    return None

def london_open_for_utc_date(d):
    # Generate local date candidates and select open whose UTC date matches d.
    day0=datetime(d.year,d.month,d.day,tzinfo=timezone.utc)
    cand=[]
    for k in (-1,0,1):
        local_date=(day0+timedelta(days=k)).astimezone(LON).date()
        local=datetime(local_date.year,local_date.month,local_date.day,8,0,tzinfo=LON)
        u=local.astimezone(timezone.utc)
        if u.date()==d: cand.append(u)
    return sorted(cand)[0] if cand else None

def close_before(rows, t):
    xs=[r for r in rows if tdt(r)<t]
    return c(xs[-1]) if xs else None

def close_at(rows,t):
    xs=[r for r in rows if tdt(r)>=t]
    return c(xs[0]) if xs else None

def window(rows,a,b): return [r for r in rows if a <= tdt(r) < b]

def absret_rv(rs):
    if len(rs)<2: return 0.0
    vals=[]
    prev=c(rs[0])
    for r in rs[1:]:
        cc=c(r); vals.append(abs(ret(prev,cc))); prev=cc
    return mean(vals) if vals else 0.0

def feature_row(rows, open_t, pdh, pdl):
    decision_t=open_t+timedelta(minutes=15)
    entry=close_at(rows, decision_t-timedelta(minutes=5))
    # close_at grabs 5m bar starting at 10m; its close field is effectively decision close in archive layout.
    # Safer: explicit first 3 bars from open and use third close.
    op15=window(rows,open_t,decision_t)
    if len(op15)<3: return None
    entry=c(op15[-1])
    future=window(rows,decision_t,decision_t+timedelta(minutes=65))
    if len(future)<12: return None
    exit60=c(future[11])

    pre1=window(rows,decision_t-timedelta(hours=1),decision_t)
    pre4=window(rows,decision_t-timedelta(hours=4),decision_t)
    pre24=window(rows,decision_t-timedelta(hours=24),decision_t)
    if len(pre24)<250: return None
    p1=c(pre1[0]); p4=c(pre4[0]); p24=c(pre24[0])

    day_start=datetime(open_t.year,open_t.month,open_t.day,tzinfo=timezone.utc)
    daypre=window(rows,day_start,decision_t)
    if not daypre: return None
    hod=max(h(r) for r in daypre); lod=min(l(r) for r in daypre)
    dr=hod-lod
    day_pos=(entry-lod)/dr if dr>0 else 0.5
    day_range_pct=100*dr/entry if entry else 0
    dist_hod=100*(hod-entry)/entry
    dist_lod=100*(entry-lod)/entry
    dist_pdh=100*(pdh-entry)/entry if pdh is not None else 0
    dist_pdl=100*(entry-pdl)/entry if pdl is not None else 0

    op15_open=o(op15[0]); op15_high=max(h(r) for r in op15); op15_low=min(l(r) for r in op15)
    op_range=op15_high-op15_low
    op_close_pos=(entry-op15_low)/op_range if op_range>0 else 0.5

    x={
      "pre_ret_1h":ret(p1,entry),"pre_ret_4h":ret(p4,entry),"pre_ret_24h":ret(p24,entry),
      "day_pos":day_pos,"day_range_pct":day_range_pct,"dist_hod_pct":dist_hod,"dist_lod_pct":dist_lod,
      "dist_pdh_pct":dist_pdh,"dist_pdl_pct":dist_pdl,
      "rv_1h":absret_rv(pre1),"rv_4h":absret_rv(pre4),
      "open15_ret":ret(op15_open,entry),"open15_range_pct":100*op_range/entry if entry else 0,
      "open15_close_pos":op_close_pos,
    }
    y=1 if exit60>entry else 0 if exit60<entry else None
    if y is None: return None
    return {"time":decision_t.isoformat(),"x":x,"y":y,"ret60":ret(entry,exit60)}

def metrics(rows, actions=None):
    # y: 1 UP, 0 DOWN. actions optional 1 BUY / 0 SELL / -1 NO TRADE.
    if actions is None:
        return {}
    traded=[(r,a) for r,a in zip(rows,actions) if a in (0,1)]
    wins=sum(1 for r,a in traded if r["y"]==a)
    losses=len(traded)-wins
    return {"n_days":len(rows),"trades":len(traded),"wins":wins,"losses":losses,
            "coverage_pct":round(100*len(traded)/len(rows),2) if rows else None,
            "wr_pct":round(100*wins/len(traded),2) if traded else None,
            "mean_signed_ret_pct":round(mean([(r["ret60"] if a==1 else -r["ret60"]) for r,a in traded]),5) if traded else None}

def main():
    from sklearn.tree import DecisionTreeClassifier, export_text
    rows=load_series(PAIR,"5m",DATA_START,DATA_END)
    days=sorted(set(tdt(r).date() for r in rows))
    samples=[]
    for d in days:
        open_t=london_open_for_utc_date(d)
        if not open_t or not block(open_t): continue
        prevd=d-timedelta(days=1)
        prevrows=[r for r in rows if tdt(r).date()==prevd]
        if not prevrows: continue
        pdh=max(h(r) for r in prevrows); pdl=min(l(r) for r in prevrows)
        fr=feature_row(rows,open_t,pdh,pdl)
        if fr:
            fr["block"]=block(open_t); samples.append(fr)
    train=[s for s in samples if s["block"]=="train"]
    val=[s for s in samples if s["block"]=="validation"]
    Xtr=[[s["x"][f] for f in FEATURES] for s in train]; ytr=[s["y"] for s in train]
    Xv=[[s["x"][f] for f in FEATURES] for s in val]
    clf=DecisionTreeClassifier(max_depth=3,min_samples_leaf=15,random_state=42)
    clf.fit(Xtr,ytr)

    # Leaf policy: majority side only if train purity >=60%, else no trade.
    tr_leaf=clf.apply(Xtr); v_leaf=clf.apply(Xv)
    leaf_info={}
    for leaf in sorted(set(tr_leaf)):
        idx=[i for i,z in enumerate(tr_leaf) if z==leaf]
        buys=sum(ytr[i]==1 for i in idx); sells=len(idx)-buys
        maj=1 if buys>=sells else 0
        purity=max(buys,sells)/len(idx)
        leaf_info[int(leaf)]={"n":len(idx),"buy_n":buys,"sell_n":sells,"majority":"BUY" if maj==1 else "SELL","purity_pct":round(100*purity,2),"trade":purity>=0.60}
    atr=[]
    for z in tr_leaf:
        inf=leaf_info[int(z)]; atr.append(1 if inf["trade"] and inf["majority"]=="BUY" else 0 if inf["trade"] else -1)
    av=[]
    for z in v_leaf:
        inf=leaf_info.get(int(z)); av.append(1 if inf and inf["trade"] and inf["majority"]=="BUY" else 0 if inf and inf["trade"] else -1)

    # Feature importances for interpretation.
    imp=sorted([{"feature":f,"importance":round(float(v),5)} for f,v in zip(FEATURES,clf.feature_importances_) if v>0],key=lambda z:z["importance"],reverse=True)

    result={"phase":"V10-E","status":"BTC_LONDON_DYNAMIC_DIRECTION_TREE",
      "definition":{"pair":PAIR,"tf":"5m","session":"London 08:00 local DST-aware","decision":"15m after open","target":"direction over next60m","train":"previous120d","validation":"latest120d","model":"DecisionTree max_depth=3 min_samples_leaf=15","leaf_trade_gate":"training purity >=60%, else NO TRADE","threshold_sweep":False,"tp_sl":None,"fees_slippage":"not applied","live_changes":False},
      "coverage":{"train_days":len(train),"validation_days":len(val)},
      "tree_rules":export_text(clf,feature_names=FEATURES),"feature_importance":imp,"leaf_policy":leaf_info,
      "train":metrics(train,atr),"validation":metrics(val,av)}
    print("V10_E_RESULT",json.dumps(result,separators=(",",":")))

if __name__=="__main__": main()
