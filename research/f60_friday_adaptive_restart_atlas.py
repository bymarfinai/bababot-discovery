#!/usr/bin/env python3
"""F6.0 — Friday15 Adaptive Restart Atlas.

Research only; live BBC untouched.

Purpose
-------
Restart Friday15 BUY research using the adaptive methodology learned from the
Tuesday/Saturday work, without inheriting F5 management thresholds.

Frozen parent:
- Friday 15:00 WIB / 08:00 UTC BUY
- TP +2.0%, SL -0.7%, max hold 6h
- $500 fixed notional, $0.75 round-trip fee
- same 138 Friday sample and 82/56 discovery-validation split as F5.0

This milestone is FORENSIC ONLY. No trade action is attached.
Natural geometry is expressed in Friday risk units R=0.7%:
- +0.35% = 0.5R favorable proof
- +0.70% = 1.0R favorable proof
- +1.40% = 2.0R favorable proof
Snapshots: +30m, +60m, +120m.

Questions:
1) Which favorable-proof states separate eventual winners/losses and transfer D/V?
2) Does early failure mean trend continuation lower, or can it recover?
3) Which pre-entry / EMA / taker / volatility contexts interact with path state?
4) Is the main Friday problem entry-state, early thesis failure, or late giveback?

No threshold sweep, no management rule, no classifier, no live changes.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

import f517_regime_attribution as f517

OUT = Path(os.getenv("F60_OUT", "f60_out"))
OUT.mkdir(parents=True, exist_ok=True)
SPLIT = f517.SPLIT_N
R = f517.SL
LEVELS = [("H05R", 0.5 * R), ("H10R", 1.0 * R), ("H20R", 2.0 * R)]
SNAPS = [30, 60, 120]


def auc(y, score):
    y = np.asarray(y, dtype=int); score = np.asarray(score, dtype=float)
    m = np.isfinite(score); y = y[m]; score = score[m]
    n1 = int(y.sum()); n0 = len(y)-n1
    if n1 == 0 or n0 == 0: return np.nan
    ranks = pd.Series(score).rank(method="average").to_numpy()
    return float((ranks[y==1].sum() - n1*(n1+1)/2)/(n1*n0))


def path_features(k: pd.DataFrame, t: pd.Timestamp, tr: f517.Trade) -> dict:
    entry = tr.entry
    ex = tr.exit_t
    bars = k[(k.index >= t) & (k.index < ex)]
    out = {}

    # First causal proof times: completed 5m bar whose high first reaches level.
    hits = {}
    for name, lev in LEVELS:
        ht = None
        for b in bars.itertuples(index=False):
            if float(b.high)/entry - 1.0 >= lev:
                ht = b.ts + pd.Timedelta(minutes=5)
                break
        hits[name] = ht
        out[f"{name}_reached"] = ht is not None
        out[f"{name}_min"] = ((ht-t).total_seconds()/60) if ht is not None else np.nan

    # How much adversity occurred before first 0.5R proof?
    h = hits["H05R"]
    end = h if h is not None else ex
    pre = k[(k.index >= t) & (k.index < end)]
    if len(pre):
        out["mae_before_h05r"] = max(0.0, 1.0 - float(pre.low.min())/entry)
    else:
        out["mae_before_h05r"] = 0.0

    # Post 0.5R path: graduate to 1R vs give back to <=0 before 1R.
    if h is None:
        out["post_h05r_state"] = "NO_05R"
        out["giveback0_min"] = np.nan
    else:
        aft = k[(k.index >= h) & (k.index < ex)]
        gb = None; g1 = hits["H10R"]
        for b in aft.itertuples(index=False):
            if float(b.close)/entry - 1.0 <= 0.0:
                gb = b.ts + pd.Timedelta(minutes=5); break
        if g1 is not None and (gb is None or g1 <= gb): state = "GRADUATE_1R_FIRST"
        elif gb is not None: state = "GIVEBACK_ZERO_FIRST"
        else: state = "HOLD_POSITIVE"
        out["post_h05r_state"] = state
        out["giveback0_min"] = ((gb-h).total_seconds()/60) if gb is not None else np.nan

    # Snapshot state uses only completed bars before decision open.
    for mins in SNAPS:
        d = t + pd.Timedelta(minutes=mins)
        alive = tr.exit_t > d and d in k.index
        out[f"alive{mins}"] = bool(alive)
        if not alive:
            for x in ["progress","mfe","mae","taker","ema7_dist","ema20_dist","ema_spread"]:
                out[f"{x}{mins}"] = np.nan
            continue
        w = k[(k.index >= t) & (k.index < d)]
        if len(w) != mins//5: raise RuntimeError(f"bad snapshot {t} {mins}: {len(w)}")
        px = float(k.loc[d, "open"])
        out[f"progress{mins}"] = px/entry - 1.0
        out[f"mfe{mins}"] = float(w.high.max())/entry - 1.0
        out[f"mae{mins}"] = 1.0 - float(w.low.min())/entry
        out[f"taker{mins}"] = float(np.nanmean(w.taker_imb.to_numpy(float)))
        last = w.iloc[-1]
        out[f"ema7_dist{mins}"] = float(last.close)/float(last.ema7)-1.0
        out[f"ema20_dist{mins}"] = float(last.close)/float(last.ema20)-1.0
        out[f"ema_spread{mins}"] = float(last.ema7)/float(last.ema20)-1.0
    return out


def basic_pre(k, t):
    feat = f517.preentry_features(k, None, t)
    # Additional causal location geometry using completed pre-entry bars only.
    done = t - pd.Timedelta(minutes=5)
    c = float(k.loc[done, "close"])
    for mins, nm in [(60,"1h"),(240,"4h"),(1440,"24h")]:
        w = k[(k.index >= t-pd.Timedelta(minutes=mins)) & (k.index < t)]
        if len(w) == mins//5:
            hi=float(w.high.max()); lo=float(w.low.min())
            feat[f"dist_{nm}_high"] = c/hi-1.0
            feat[f"dist_{nm}_low"] = c/lo-1.0
            feat[f"loc_{nm}"] = (c-lo)/(hi-lo) if hi>lo else .5
    return feat


def met(g, pnl_col="parent_pnl"):
    if len(g)==0: return {"n":0,"wins":0,"wr":np.nan,"pnl":0.0}
    p=g[pnl_col].to_numpy(float); w=int((p>0).sum())
    return {"n":int(len(g)),"wins":w,"wr":w/len(g),"pnl":float(p.sum())}


def cohort(df, col):
    rows=[]
    for val,g in df.groupby(col,dropna=False):
        r={"state":str(val),**met(g)}
        d=met(g[g.i<SPLIT]); v=met(g[g.i>=SPLIT])
        r.update({f"d_{k}":x for k,x in d.items()}); r.update({f"v_{k}":x for k,x in v.items()})
        rows.append(r)
    return sorted(rows,key=lambda z:(-z["n"],z["state"]))


def main():
    print("F6.0 loading Friday frozen data...", flush=True)
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive="left",freq="D") if d.weekday()==4]
    trs=[]; rec=[]
    for i,d in enumerate(days):
        t=pd.Timestamp(d.date(),tz="UTC")+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); trs.append(tr)
        r={"i":i,"period":"discovery" if i<SPLIT else "validation","date":tr.date,
           "entry_t":str(t),"parent_pnl":tr.pnl,"parent_win":tr.pnl>0,"reason":tr.reason,
           "parent_mfe":tr.mfe,"parent_mae":tr.mae}
        r.update(basic_pre(k,t)); r.update(path_features(k,t,tr)); rec.append(r)
    f517.assert_parent(trs)
    df=pd.DataFrame(rec); df.to_csv(OUT/"f60_rows.csv",index=False)

    tables={}
    for c in ["H05R_reached","H10R_reached","H20R_reached","post_h05r_state"]:
        tables[c]=cohort(df,c)

    # Snapshot continuous winner-separation AUCs (winner high unless named adverse).
    auc_rows=[]
    for mins in SNAPS:
        alive=df[df[f"alive{mins}"]]
        feats=[f"progress{mins}",f"mfe{mins}",f"mae{mins}",f"taker{mins}",f"ema7_dist{mins}",f"ema20_dist{mins}",f"ema_spread{mins}"]
        for feat in feats:
            for period,g in [("full",alive),("discovery",alive[alive.i<SPLIT]),("validation",alive[alive.i>=SPLIT])]:
                a=auc(g.parent_win.astype(int),g[feat])
                auc_rows.append({"snapshot":mins,"feature":feat,"period":period,"n":len(g),"auc_win_high":a})
    aucdf=pd.DataFrame(auc_rows); aucdf.to_csv(OUT/"f60_snapshot_auc.csv",index=False)

    # Pre-entry features: descriptive only, no cutoff selection.
    pre_feats=["ret60","taker_imb60","volume_ratio60","range_ratio60","entry_ema_spread","entry_ema_spread_chg15",
               "dist_1h_high","dist_4h_high","loc_1h","loc_4h"]
    pre_rows=[]
    for feat in pre_feats:
        if feat not in df.columns: continue
        for period,g in [("full",df),("discovery",df[df.i<SPLIT]),("validation",df[df.i>=SPLIT])]:
            pre_rows.append({"feature":feat,"period":period,"n":len(g),"auc_win_high":auc(g.parent_win.astype(int),g[feat]),
                             "win_median":float(g[g.parent_win][feat].median()),"loss_median":float(g[~g.parent_win][feat].median())})
    predf=pd.DataFrame(pre_rows); predf.to_csv(OUT/"f60_preentry_auc.csv",index=False)

    parent=met(df); disc=met(df[df.i<SPLIT]); val=met(df[df.i>=SPLIT])
    summary={"parent":parent,"discovery":disc,"validation":val,"tables":tables,
             "snapshot_auc":aucdf.to_dict("records"),"preentry_auc":predf.to_dict("records")}
    (OUT/"f60_summary.json").write_text(json.dumps(summary,indent=2,default=float))

    def pct(x): return "NA" if not np.isfinite(x) else f"{100*x:.2f}%"
    def money(x): return f"${x:+.3f}"
    md=["# Friday15 F6.0 — Adaptive Restart Atlas","",
        "**Status:** COMPLETE — FORENSIC ONLY; NO MANAGEMENT/DIRECTION RULE", "**Research only:** live BBC untouched","",
        "## Frozen parent parity",
        f"- Full: **{parent['wins']}W/{parent['n']-parent['wins']}L = {pct(parent['wr'])}, {money(parent['pnl'])}**",
        f"- Discovery: **{pct(disc['wr'])}, {money(disc['pnl'])}**",
        f"- Validation: **{pct(val['wr'])}, {money(val['pnl'])}**","",
        "## Natural Friday risk-unit proof states",
        "R = frozen SL 0.70%; proof levels are +0.35% (0.5R), +0.70% (1R), +1.40% (2R).","" ]
    for c in ["H05R_reached","H10R_reached","H20R_reached","post_h05r_state"]:
        md.append(f"### {c}")
        md.append("| State | N | WR | PnL | Discovery N/WR/PnL | Validation N/WR/PnL |")
        md.append("|---|---:|---:|---:|---:|---:|")
        for r in tables[c]:
            md.append(f"| {r['state']} | {r['n']} | {pct(r['wr'])} | {money(r['pnl'])} | {r['d_n']} / {pct(r['d_wr'])} / {money(r['d_pnl'])} | {r['v_n']} / {pct(r['v_wr'])} / {money(r['v_pnl'])} |")
        md.append("")
    md += ["## Snapshot AUCs","Winner-separation only; no cutoff was fitted. AUC >0.5 means higher feature tends to winners.",""]
    for mins in SNAPS:
        md.append(f"### +{mins}m")
        x=aucdf[aucdf.snapshot==mins]
        for feat in sorted(x.feature.unique()):
            z=x[x.feature==feat].set_index("period")
            md.append(f"- `{feat}`: full **{z.loc['full','auc_win_high']:.3f}**, D **{z.loc['discovery','auc_win_high']:.3f}**, V **{z.loc['validation','auc_win_high']:.3f}**")
        md.append("")
    md += ["## Pre-entry AUCs","Descriptive causal context only; no threshold selected.",""]
    for feat in predf.feature.unique():
        z=predf[predf.feature==feat].set_index("period")
        md.append(f"- `{feat}`: full **{z.loc['full','auc_win_high']:.3f}**, D **{z.loc['discovery','auc_win_high']:.3f}**, V **{z.loc['validation','auc_win_high']:.3f}**")
    md += ["","## Interpretation guardrail","This restart intentionally does not reuse F5.12/F5.16 warning thresholds as actions. The next milestone, if any, must be chosen from chronology-stable path/state structure observed here and predeclared before management testing."]
    (OUT/"F6.0_CHECKPOINT.md").write_text("\n".join(md)+"\n")
    print(json.dumps(summary,indent=2,default=float),flush=True)

if __name__ == "__main__":
    main()
