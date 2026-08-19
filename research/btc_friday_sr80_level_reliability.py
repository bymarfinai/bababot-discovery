#!/usr/bin/env python3
"""SR80: BTC Friday-WIB causal support/resistance level reliability study.

Research-only. No live trading code. The target is level HOLD vs BREAK on first
touch, not trade PnL. Protocol is frozen in BTC_Friday_SR80_Level_Reliability_Preregistration.md.
"""
from __future__ import annotations

import json, math
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier

import f517_regime_attribution as f517

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / "BTC_Friday_SR80_Level_Reliability_Result.md"
OUT_JSON = ROOT / "BTC_Friday_SR80_Level_Reliability_Result.json"
OUT_ROWS = ROOT / "BTC_Friday_SR80_Level_Reliability_Rows.csv"
OUT_LEAVES = ROOT / "BTC_Friday_SR80_Level_Reliability_Discovery_Leaves.csv"

START = pd.Timestamp("2023-12-02T00:00:00Z")
END = pd.Timestamp("2026-07-30T00:00:00Z")
PIVOT = 3
CLUSTER_ATR = 0.10
REACTION_ATR = 0.50
HORIZON = pd.Timedelta(hours=6)

FEATURES = [
    "is_support",
    "has_pday",
    "has_w7",
    "has_swing",
    "confluence_count",
    "distance_open_atr",
    "prior_near_count",
    "age_hours",
    "approach_ret30_toward",
    "approach_ret60_toward",
    "approach_range30_atr",
    "approach_toward_fraction6",
    "volume30_rel24",
    "ema20_slope3h_aligned",
    "atr_pct",
]


def build_h1(k: pd.DataFrame) -> pd.DataFrame:
    x = k[["open", "high", "low", "close", "quote_volume"]].copy()
    count = x["close"].resample("1h", label="left", closed="left").count()
    h = x.resample("1h", label="left", closed="left").agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), quote_volume=("quote_volume", "sum")
    )
    h = h[count == 12].dropna().copy()
    prev = h.close.shift(1)
    tr = pd.concat([
        h.high - h.low,
        (h.high - prev).abs(),
        (h.low - prev).abs(),
    ], axis=1).max(axis=1)
    h["atr14"] = tr.ewm(alpha=1/14, adjust=False, min_periods=14).mean()
    h["ema20"] = h.close.ewm(span=20, adjust=False).mean()
    return h


def source_family(src: str) -> str:
    if src in {"PDH", "PDL"}: return "PDAY"
    if src in {"W7H", "W7L"}: return "W7"
    return "SWING"


def confirmed_swings(h: pd.DataFrame, freeze: pd.Timestamp) -> List[Dict]:
    # Need a little left context; pivots themselves must be in prior seven days.
    z = h[(h.index >= freeze - pd.Timedelta(days=8)) & (h.index < freeze)].copy()
    rows = []
    if len(z) < 2*PIVOT + 1:
        return rows
    hi = z.high.to_numpy(float); lo = z.low.to_numpy(float); idx = list(z.index)
    for i in range(PIVOT, len(z)-PIVOT):
        t = idx[i]
        if t < freeze - pd.Timedelta(days=7):
            continue
        hs = hi[i-PIVOT:i+PIVOT+1]
        ls = lo[i-PIVOT:i+PIVOT+1]
        if hi[i] == np.max(hs) and int(np.sum(hs == hi[i])) == 1:
            rows.append({"price": float(hi[i]), "source": "SWING_H", "origin": t})
        if lo[i] == np.min(ls) and int(np.sum(ls == lo[i])) == 1:
            rows.append({"price": float(lo[i]), "source": "SWING_L", "origin": t})
    highs = sorted([r for r in rows if r["source"] == "SWING_H"], key=lambda r:r["origin"], reverse=True)[:3]
    lows = sorted([r for r in rows if r["source"] == "SWING_L"], key=lambda r:r["origin"], reverse=True)[:3]
    return highs + lows


def raw_levels(k: pd.DataFrame, h: pd.DataFrame, freeze: pd.Timestamp) -> List[Dict]:
    pday = k[(k.index >= freeze-pd.Timedelta(days=1)) & (k.index < freeze)]
    w7 = k[(k.index >= freeze-pd.Timedelta(days=7)) & (k.index < freeze)]
    if len(pday) != 288 or len(w7) < 7*288-2:
        return []
    out = []
    for src, frame, col, fn in [
        ("PDH", pday, "high", "max"), ("PDL", pday, "low", "min"),
        ("W7H", w7, "high", "max"), ("W7L", w7, "low", "min"),
    ]:
        if fn == "max":
            t = frame[col].idxmax(); px = float(frame[col].max())
        else:
            t = frame[col].idxmin(); px = float(frame[col].min())
        out.append({"price": px, "source": src, "origin": t})
    out.extend(confirmed_swings(h, freeze))
    return out


def cluster_levels(levels: List[Dict], atr: float) -> List[Dict]:
    if not levels or not np.isfinite(atr) or atr <= 0:
        return []
    tol = CLUSTER_ATR * atr
    xs = sorted(levels, key=lambda r:r["price"])
    groups = []
    cur = [xs[0]]
    for r in xs[1:]:
        prices = [q["price"] for q in cur] + [r["price"]]
        if max(prices) - min(prices) <= tol:
            cur.append(r)
        else:
            groups.append(cur); cur = [r]
    groups.append(cur)
    out = []
    for g in groups:
        prices = [r["price"] for r in g]
        sources = sorted(set(r["source"] for r in g))
        out.append({
            "level": float(np.median(prices)),
            "sources": sources,
            "families": sorted(set(source_family(s) for s in sources)),
            "origins": [r["origin"] for r in g],
            "confluence_count": len(g),
        })
    return out


def completed_h1_before(h: pd.DataFrame, t: pd.Timestamp) -> pd.DataFrame:
    # 1H bar opened at u is complete only at u+1h <= t.
    return h[h.index <= t - pd.Timedelta(hours=1)]


def volume_rel24(k: pd.DataFrame, touch: pd.Timestamp) -> float:
    hist = k[(k.index >= touch-pd.Timedelta(hours=24)) & (k.index < touch)]
    if len(hist) < 12:
        return np.nan
    pre6 = hist.tail(6)
    q30 = float(pre6.quote_volume.sum())
    vals = hist.quote_volume.to_numpy(float)
    sums = []
    # Non-overlapping 30m blocks ending before touch, aligned backwards.
    n = len(vals)//6
    vals = vals[-n*6:]
    for i in range(n): sums.append(float(vals[i*6:(i+1)*6].sum()))
    med = float(np.median(sums)) if sums else np.nan
    return q30/med if np.isfinite(med) and med > 0 else np.nan


def approach_features(k: pd.DataFrame, h: pd.DataFrame, touch: pd.Timestamp,
                      side: str, atr: float) -> Dict:
    pre12 = k[k.index < touch].tail(12)
    pre6 = pre12.tail(6)
    if len(pre12) < 12 or len(pre6) < 6:
        return {f:np.nan for f in ["approach_ret30_toward","approach_ret60_toward",
                                   "approach_range30_atr","approach_toward_fraction6",
                                   "volume30_rel24","ema20_slope3h_aligned"]}
    sign = -1.0 if side == "SUPPORT" else 1.0
    r30 = float(pre6.iloc[-1].close/pre6.iloc[0].open - 1.0)
    r60 = float(pre12.iloc[-1].close/pre12.iloc[0].open - 1.0)
    rng30 = float(pre6.high.max()-pre6.low.min())/atr if atr > 0 else np.nan
    barret = pre6.close.to_numpy(float)/pre6.open.to_numpy(float)-1.0
    toward = float(np.mean(sign*barret > 0))
    hc = completed_h1_before(h, touch)
    if len(hc) >= 4:
        slope = float(hc.iloc[-1].ema20/hc.iloc[-4].ema20 - 1.0)
        aligned = slope if side == "SUPPORT" else -slope
    else:
        aligned = np.nan
    return {
        "approach_ret30_toward": sign*r30,
        "approach_ret60_toward": sign*r60,
        "approach_range30_atr": rng30,
        "approach_toward_fraction6": toward,
        "volume30_rel24": volume_rel24(k,touch),
        "ema20_slope3h_aligned": aligned,
    }


def resolve(k: pd.DataFrame, touch: pd.Timestamp, level: float, side: str, atr: float) -> Dict:
    if touch not in k.index:
        return {"outcome":"INTEGRITY_ERROR"}
    up = level + REACTION_ATR*atr
    dn = level - REACTION_ATR*atr
    b0 = k.loc[touch]
    # Touch candle path is unknowable once either outcome boundary is reached.
    if float(b0.high) >= up or float(b0.low) <= dn:
        return {"outcome":"AMBIGUOUS_TOUCH_BAR"}
    bars = k[(k.index > touch) & (k.index < touch+HORIZON)]
    for t,b in bars.iterrows():
        hu = float(b.high) >= up
        ld = float(b.low) <= dn
        if hu and ld:
            return {"outcome":"AMBIGUOUS_LATER_BAR", "resolution_time":str(t)}
        if side == "SUPPORT":
            if hu: return {"outcome":"HOLD", "resolution_time":str(t)}
            if ld: return {"outcome":"BREAK", "resolution_time":str(t)}
        else:
            if ld: return {"outcome":"HOLD", "resolution_time":str(t)}
            if hu: return {"outcome":"BREAK", "resolution_time":str(t)}
    return {"outcome":"UNRESOLVED"}


def friday_dates() -> List[pd.Timestamp]:
    # Date label is WIB calendar Friday; convert local midnight to UTC.
    ds = pd.date_range("2023-12-08", "2026-07-24", freq="W-FRI")
    return [pd.Timestamp(d.date()).tz_localize("Asia/Jakarta").tz_convert("UTC") for d in ds]


def build_events(k: pd.DataFrame, h: pd.DataFrame) -> tuple[pd.DataFrame,int]:
    rows=[]; violations=0
    for fs in friday_dates():
        fe=fs+pd.Timedelta(days=1)
        if fs not in k.index: continue
        hc=completed_h1_before(h,fs)
        if hc.empty or not np.isfinite(hc.iloc[-1].atr14): continue
        atr=float(hc.iloc[-1].atr14); f_open=float(k.loc[fs].open)
        levels=cluster_levels(raw_levels(k,h,fs),atr)
        friday=k[(k.index>=fs)&(k.index<fe)]
        prior7h=h[(h.index>=fs-pd.Timedelta(days=7))&(h.index<fs)]
        for ci,c in enumerate(levels):
            level=float(c["level"])
            if level == f_open: continue
            side="SUPPORT" if level < f_open else "RESISTANCE"
            touched=friday[(friday.low.astype(float)<=level)&(friday.high.astype(float)>=level)]
            if touched.empty: continue
            touch=touched.index[0]
            # Causality checks.
            if any(pd.Timestamp(o)>=fs for o in c["origins"]): violations+=1
            tol=CLUSTER_ATR*atr
            near=int(((prior7h.low.astype(float)<=level+tol)&(prior7h.high.astype(float)>=level-tol)).sum())
            youngest=max(c["origins"])
            age=(fs-pd.Timestamp(youngest)).total_seconds()/3600.0
            af=approach_features(k,h,touch,side,atr)
            res=resolve(k,touch,level,side,atr)
            rows.append({
                "friday_wib":str((fs+pd.Timedelta(hours=7)).date()),
                "freeze_utc":str(fs),"touch_utc":str(touch),"cluster_id":f"{(fs+pd.Timedelta(hours=7)).date()}-{ci}",
                "level":level,"side":side,"sources":"|".join(c["sources"]),"families":"|".join(c["families"]),
                "is_support":int(side=="SUPPORT"),
                "has_pday":int("PDAY" in c["families"]),"has_w7":int("W7" in c["families"]),"has_swing":int("SWING" in c["families"]),
                "confluence_count":int(c["confluence_count"]),
                "distance_open_atr":abs(level-f_open)/atr,
                "prior_near_count":near,"age_hours":age,"atr":atr,"atr_pct":atr/f_open,
                **af,**res,
            })
    return pd.DataFrame(rows),violations


def rate_stats(z: pd.DataFrame) -> Dict:
    if len(z)==0: return {"n":0,"hold":0,"break":0,"rate":None,"wilson95":[None,None]}
    n=len(z); w=int((z.outcome=="HOLD").sum()); br=int((z.outcome=="BREAK").sum())
    p=w/n
    zc=1.959963984540054
    den=1+zc*zc/n
    center=(p+zc*zc/(2*n))/den
    half=zc*math.sqrt((p*(1-p)+zc*zc/(4*n))/n)/den
    return {"n":n,"hold":w,"break":br,"rate":p,"wilson95":[max(0.,center-half),min(1.,center+half)]}


def path_to_leaf(clf: DecisionTreeClassifier, leaf:int) -> List:
    tr=clf.tree_; out=[]
    def rec(node,conds):
        if node==leaf:
            out.extend(conds); return True
        if tr.children_left[node]==tr.children_right[node]: return False
        f=FEATURES[tr.feature[node]]; thr=float(tr.threshold[node])
        if rec(tr.children_left[node],conds+[[f,"<=",thr]]): return True
        if rec(tr.children_right[node],conds+[[f,">",thr]]): return True
        return False
    rec(0,[]); return out


def rule_text(path:List) -> str:
    return " AND ".join(f"{f} {op} {v:.8g}" for f,op,v in path)


def blocks(df:pd.DataFrame, leaf:int) -> Dict:
    dates=sorted(df.friday_wib.unique()); out={}
    for i,ch in enumerate(np.array_split(np.array(dates,dtype=object),4)):
        q=df[df.friday_wib.isin(set(ch)) & (df.leaf==leaf)]
        out[f"B{i+1}"]=rate_stats(q)
    return out


def main():
    k=f517.load_klines().copy()
    # Keep warmup before START but no Friday event after END.
    k=k[k.index < END+pd.Timedelta(days=1)].copy()
    h=build_h1(k)
    events,violations=build_events(k,h)
    if events.empty: raise RuntimeError("no SR80 events")
    events.to_csv(OUT_ROWS,index=False)
    resolved=events[events.outcome.isin(["HOLD","BREAK"])].copy()
    if len(resolved)<80: raise RuntimeError(f"too few resolved levels {len(resolved)}")
    dates=sorted(set(x for x in events.friday_wib.tolist()))
    cut=int(math.floor(.70*len(dates))); dd=set(dates[:cut]); vd=set(dates[cut:])
    resolved["period"]=np.where(resolved.friday_wib.isin(dd),"discovery","validation")
    disc=resolved[resolved.period=="discovery"].copy(); val=resolved[resolved.period=="validation"].copy()
    if len(disc)<50 or len(val)<20: raise RuntimeError(f"insufficient split {len(disc)}/{len(val)}")

    med={f:float(pd.to_numeric(disc[f],errors="coerce").replace([np.inf,-np.inf],np.nan).median()) for f in FEATURES}
    X=resolved[FEATURES].copy()
    for f in FEATURES:
        X[f]=pd.to_numeric(X[f],errors="coerce").replace([np.inf,-np.inf],np.nan).fillna(med[f])
    y=(resolved.outcome=="HOLD").astype(int)
    Xd=X.loc[disc.index]; yd=y.loc[disc.index]
    clf=DecisionTreeClassifier(criterion="gini",max_depth=3,min_samples_leaf=20,random_state=20260819)
    clf.fit(Xd,yd)
    resolved["leaf"]=clf.apply(X)
    disc=resolved[resolved.period=="discovery"].copy(); val=resolved[resolved.period=="validation"].copy()

    leaves=[]
    for leaf in sorted(set(disc.leaf.tolist())):
        q=disc[disc.leaf==leaf]; s=rate_stats(q); path=path_to_leaf(clf,int(leaf))
        # sklearn class at leaf
        node=int(leaf); cls=int(clf.classes_[int(np.argmax(clf.tree_.value[node][0]))])
        leaves.append({"leaf":int(leaf),"predicted_class":cls,"rule":rule_text(path),"path":path,**s})
    pd.DataFrame([{k:v for k,v in r.items() if k!="path"} for r in leaves]).to_csv(OUT_LEAVES,index=False)
    eligible=[r for r in leaves if r["predicted_class"]==1 and r["n"]>=30 and r["rate"] is not None and r["rate"]>=.80]
    eligible.sort(key=lambda r:(-r["rate"],-r["n"],r["leaf"]))

    baseline={"discovery":rate_stats(disc),"validation":rate_stats(val),"full":rate_stats(resolved)}
    counts=events.outcome.value_counts().to_dict()
    out={
        "protocol":"SR80","status":"COMPLETE","friday_dates_with_touches":len(dates),
        "touch_events":len(events),"resolved_events":len(resolved),"outcome_counts":{str(k):int(v) for k,v in counts.items()},
        "discovery_dates":len(dd),"validation_dates":len(vd),"discovery_resolved":len(disc),"validation_resolved":len(val),
        "integrity_violations":int(violations),"features":FEATURES,"discovery_medians":med,
        "tree":{"criterion":"gini","max_depth":3,"min_samples_leaf":20,"random_state":20260819},
        "baseline":baseline,"discovery_leaves":leaves,"eligible_discovery_80":len(eligible),
    }
    if not eligible:
        out.update({"selected":None,"verdict":"REJECT_SR80_LEVEL_IDENTIFIER","reason":"No discovery HOLD leaf achieved N>=30 and rate>=80%."})
    else:
        r=eligible[0]; leaf=r["leaf"]
        sd=rate_stats(disc[disc.leaf==leaf]); sv=rate_stats(val[val.leaf==leaf]); sf=rate_stats(resolved[resolved.leaf==leaf]); bl=blocks(resolved,leaf)
        selected=resolved[resolved.leaf==leaf]
        families=set()
        for txt in selected.families.astype(str): families.update(x for x in txt.split("|") if x)
        positive=sum(s["n"]>=5 and s["rate"] is not None and s["rate"]>.50 for s in bl.values())
        gate=bool(sd["n"]>=30 and sd["rate"]>=.80 and sv["n"]>=12 and sv["rate"] is not None and sv["rate"]>=.80 and
                  sf["n"]>=50 and sf["rate"] is not None and sf["rate"]>=.80 and baseline["validation"]["rate"] is not None and
                  sv["rate"]>baseline["validation"]["rate"] and len(families)>=2 and positive>=3 and violations==0)
        out["selected"]={"leaf":leaf,"rule":r["rule"],"path":r["path"],"discovery":sd,"validation":sv,"full":sf,
                         "blocks":bl,"positive_blocks":positive,"source_families":sorted(families),
                         "support_n":int((selected.side=="SUPPORT").sum()),"resistance_n":int((selected.side=="RESISTANCE").sum())}
        out["verdict"]="BTC_FRIDAY_SR80_CANDIDATE" if gate else "REJECT_SR80_LEVEL_IDENTIFIER"
        out["guardrail"]="Exact discovery-selected leaf only. No support-only/resistance-only rescue or threshold retune."

    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+"\n")
    def pct(x): return "-" if x is None else f"{100*x:.2f}%"
    def ci(x):
        a,b=x; return "-" if a is None else f"{100*a:.1f}%–{100*b:.1f}%"
    md=["# BTC Friday SR80 — Support/Resistance Level Reliability Result","",
        f"**Verdict: {out['verdict']}**","",
        f"Friday dates with touched frozen levels: **{out['friday_dates_with_touches']}**",
        f"First-touch events: **{out['touch_events']}**; resolved HOLD/BREAK: **{out['resolved_events']}**",
        f"Outcome counts: `{out['outcome_counts']}`",
        f"Integrity violations: **{violations}**","",
        "## Unconditional level reliability","",
        "| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |",
        "|---|---:|---:|---:|---:|---:|"]
    for name,s in [("Discovery",baseline["discovery"]),("Validation",baseline["validation"]),("Full",baseline["full"])]:
        md.append(f"| {name} | {s['n']} | {s['hold']} | {s['break']} | {pct(s['rate'])} | {ci(s['wilson95'])} |")
    md += ["","## Discovery tree leaves","","| Leaf | Pred HOLD? | N | HOLD | Rate | Rule |","|---:|---:|---:|---:|---:|---|"]
    for r in leaves:
        md.append(f"| {r['leaf']} | {r['predicted_class']} | {r['n']} | {r['hold']} | {pct(r['rate'])} | `{r['rule']}` |")
    if out.get("selected") is None:
        md += ["","## 80% identification verdict","",f"**{out['verdict']}**","",out["reason"]]
    else:
        s=out["selected"]
        md += ["","## Discovery-selected high-confidence level rule","",f"`{s['rule']}`","",
               "| Cohort | N | HOLD | BREAK | HOLD rate | Wilson 95% |","|---|---:|---:|---:|---:|---:|"]
        for name,q in [("Discovery",s["discovery"]),("Validation",s["validation"]),("Full",s["full"])]:
            md.append(f"| {name} | {q['n']} | {q['hold']} | {q['break']} | {pct(q['rate'])} | {ci(q['wilson95'])} |")
        md += ["","### Chronological blocks","","| Block | N | HOLD | Rate |","|---|---:|---:|---:|"]
        for b,q in s["blocks"].items(): md.append(f"| {b} | {q['n']} | {q['hold']} | {pct(q['rate'])} |")
        md += ["",f"Selected source families: **{', '.join(s['source_families'])}**; support/resistance observations **{s['support_n']} / {s['resistance_n']}**.","",
               "## 80% identification verdict","",f"**{out['verdict']}**"]
    md += ["","This study measures historical first-touch level behavior, not guaranteed future support/resistance and not trade profitability."]
    OUT_MD.write_text("\n".join(md)+"\n")
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__ == "__main__":
    main()
