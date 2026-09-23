#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6B_L2_LONG_TECHNICAL_AUGMENTATION"
PARENT_SIG="35ab7d201fe45d398b3c959483aa7eef5d68a9d901336d57a25489f9b2f54190"
HORIZONS=[30,60]
BASE=["entry_drawdown","mae_so_far","down_slope_3"]

EMA_CONT=["close_below_ema7","close_below_ema20","ema7_below_ema20","ema7_down15","ema20_down30"]
EMA_BIN=["close_under_ema7","close_under_ema20","ema7_under_ema20","close_under_both_ema"]
FIB_CONT=["reclaim_fib_giveback"]
FIB_BIN=["fib_382_breached","fib_500_breached","fib_618_breached","fib_786_breached"]
FEATURES=EMA_CONT+EMA_BIN+FIB_CONT+FIB_BIN

def verify():
    txt=(ROOT/"results/bnb_b41_s6b_l/BNB_B41_S6B_L_LONG_FAILURE_ANATOMY_Freeze.txt").read_text()
    if f"S6B_L_SIGNATURE_SHA256={PARENT_SIG}" not in txt:
        raise RuntimeError("S6B-L signature mismatch")

def auc_failure(y,score):
    y=np.asarray(y,dtype=bool); s=np.asarray(score,dtype=float)
    ok=np.isfinite(s); y=y[ok]; s=s[ok]
    p=s[y]; n=s[~y]
    if len(p)==0 or len(n)==0:return np.nan
    wins=0.0
    for x in p:
        wins += np.sum(x>n)+0.5*np.sum(x==n)
    return float(wins/(len(p)*len(n)))

def fit_scale(s):
    x=pd.Series(s).astype(float).dropna()
    med=float(x.median())
    q1=float(x.quantile(.25)); q3=float(x.quantile(.75)); den=q3-q1
    if not np.isfinite(den) or den<=1e-12:
        den=float(x.std(ddof=0))
    if not np.isfinite(den) or den<=1e-12:
        den=1.0
    return med,den

def z(s,params):
    med,den=params
    return (pd.Series(s,dtype=float)-med)/den

def main():
    verify()
    F=pd.read_csv(ROOT/"results/bnb_b41_s6b_l/BNB_B41_S6B_L_LONG_FAILURE_ANATOMY_SnapshotLedger.csv.gz",
                  compression="gzip",parse_dates=["session_day"])
    F=F[F.horizon_min.isin(HORIZONS)].copy()
    if len(F)!=236: raise RuntimeError(f"snapshot parity {len(F)} !=236")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["open","high","low","close"]].astype(float).sort_index().copy()
    k["ema7"]=k.close.ewm(span=7,adjust=False).mean()
    k["ema20"]=k.close.ewm(span=20,adjust=False).mean()

    rows=[]
    for r in F.itertuples(index=False):
        # Snapshot timestamp is detector + horizon; reconstruct from session date by matching entry row:
        # detector timestamp is available from S5 ledger keyed by signal.
        rows.append(r._asdict())
    T=pd.DataFrame(rows)

    s5=pd.read_csv(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
                   compression="gzip",parse_dates=["detector_ts"])
    s5=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")&
          (s5.valid180)].copy()
    T=T.merge(s5[["signal_key","detector_ts"]],on="signal_key",how="left",validate="many_to_one")
    if T.detector_ts.isna().any(): raise RuntimeError("missing detector timestamp")

    tech=[]
    for r in T.itertuples(index=False):
        ts=pd.Timestamp(r.detector_ts)+pd.Timedelta(minutes=int(r.horizon_min))
        if ts not in k.index: raise RuntimeError(f"missing snapshot kline {ts}")
        i=k.index.get_loc(ts)
        if not isinstance(i,(int,np.integer)): raise RuntimeError("nonunique ts")
        b=k.iloc[i]
        entry=float(r.entry); extreme=float(r.detector_extreme); wd=float(r.wall_distance)
        leg=entry-extreme
        if leg<=0: raise RuntimeError("nonpositive reclaim leg")
        close=float(b.close); e7=float(b.ema7); e20=float(b.ema20)
        i15=max(0,i-3); i30=max(0,i-6)
        e7p=float(k.iloc[i15].ema7); e20p=float(k.iloc[i30].ema20)

        giveback=(entry-close)/leg
        tech.append({
            "signal_key":r.signal_key,"horizon_min":int(r.horizon_min),
            "snapshot_ts":ts,"snapshot_close":close,
            "ema7":e7,"ema20":e20,
            "close_below_ema7":(e7-close)/wd,
            "close_below_ema20":(e20-close)/wd,
            "ema7_below_ema20":(e20-e7)/wd,
            "ema7_down15":(e7p-e7)/wd,
            "ema20_down30":(e20p-e20)/wd,
            "close_under_ema7":float(close<e7),
            "close_under_ema20":float(close<e20),
            "ema7_under_ema20":float(e7<e20),
            "close_under_both_ema":float((close<e7) and (close<e20)),
            "reclaim_fib_giveback":giveback,
            "fib_382_breached":float(close<=entry-0.382*leg),
            "fib_500_breached":float(close<=entry-0.500*leg),
            "fib_618_breached":float(close<=entry-0.618*leg),
            "fib_786_breached":float(close<=entry-0.786*leg),
        })
    X=pd.DataFrame(tech)
    T=T.merge(X,on=["signal_key","horizon_min"],how="left",validate="one_to_one")
    T["is_loser"]=T.label.eq("LOSER")

    out=[]
    base_rows=[]
    scales={}
    for h in HORIZONS:
        d=T[(T.horizon_min==h)&(T.period=="DEV")].copy()
        r=T[(T.horizon_min==h)&(T.period=="REF")].copy()

        for feat in BASE+FEATURES:
            scales[(h,feat)]=fit_scale(d[feat])

        for g in [d,r]:
            score=sum(z(g[f],scales[(h,f)]).to_numpy() for f in BASE)/len(BASE)
            g.loc[:,"base_score"]=score

        bdev=auc_failure(d.is_loser,d.base_score); bref=auc_failure(r.is_loser,r.base_score)
        base_rows.append({"horizon_min":h,"dev_auc":bdev,"ref_auc":bref,
                          "dev_winners":int((~d.is_loser).sum()),"dev_losers":int(d.is_loser.sum()),
                          "ref_winners":int((~r.is_loser).sum()),"ref_losers":int(r.is_loser.sum())})

        for feat in FEATURES:
            fam="EMA" if feat in EMA_CONT+EMA_BIN else "FIB"
            kind="BINARY" if feat in EMA_BIN+FIB_BIN else "CONT"
            ud=auc_failure(d.is_loser,d[feat]); ur=auc_failure(r.is_loser,r[feat])

            dz=z(d[feat],scales[(h,feat)]).to_numpy()
            rz=z(r[feat],scales[(h,feat)]).to_numpy()
            d_aug=(d.base_score.to_numpy()*len(BASE)+dz)/(len(BASE)+1)
            r_aug=(r.base_score.to_numpy()*len(BASE)+rz)/(len(BASE)+1)
            ad=auc_failure(d.is_loser,d_aug); ar=auc_failure(r.is_loser,r_aug)

            dev_nom=bool((~d.is_loser).sum()>=30 and d.is_loser.sum()>=20 and
                         np.isfinite(ud) and ud>=.58 and np.isfinite(ad) and ad>=bdev+.015)
            ref_val=bool(dev_nom and (~r.is_loser).sum()>=20 and r.is_loser.sum()>=15 and
                         np.isfinite(ur) and ur>=.55 and np.isfinite(ar) and ar>=bref+.010)
            out.append({
                "horizon_min":h,"family":fam,"feature":feat,"kind":kind,
                "dev_univ_auc":ud,"ref_univ_auc":ur,
                "dev_base_auc":bdev,"ref_base_auc":bref,
                "dev_aug_auc":ad,"ref_aug_auc":ar,
                "dev_aug_delta":ad-bdev,"ref_aug_delta":ar-bref,
                "dev_nominated":dev_nom,"ref_validated":ref_val,
            })

    A=pd.DataFrame(out); B=pd.DataFrame(base_rows)
    V=A[A.ref_validated].copy()
    ema_ok=bool(((V.family=="EMA")).any()); fib_ok=bool(((V.family=="FIB")).any())
    if ema_ok and fib_ok: status="BNB_B41_S6B_L2_EMA_AND_FIB_ADD_STABLE_INFORMATION"
    elif ema_ok: status="BNB_B41_S6B_L2_EMA_ADDS_STABLE_INFORMATION"
    elif fib_ok: status="BNB_B41_S6B_L2_FIB_ADDS_STABLE_INFORMATION"
    else: status="BNB_B41_S6B_L2_TECHNICAL_AUGMENTATION_NOT_SUPPORTED"

    sig=hashlib.sha256(json.dumps({
        "parent":PARENT_SIG,"horizons":HORIZONS,"baseline":BASE,
        "ema_cont":EMA_CONT,"ema_bin":EMA_BIN,"fib_cont":FIB_CONT,"fib_bin":FIB_BIN,
        "ema":{"spans":[7,20],"adjust":False},
        "fib":{"anchor":"DETECTOR_EXTREME_TO_ENTRY","levels":[.382,.5,.618,.786]},
        "dev_gate":{"univ_auc":.58,"aug_delta":.015,"winner_n":30,"loser_n":20},
        "ref_gate":{"univ_auc":.55,"aug_delta":.010,"winner_n":20,"loser_n":15},
        "no_exit_rule":True,
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    T.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    B.to_csv(ROOT/f"{PFX}_Baseline.csv",index=False)
    A.to_csv(ROOT/f"{PFX}_FeatureAudit.csv",index=False)
    V.to_csv(ROOT/f"{PFX}_Validated.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S6B_L_SIGNATURE_SHA256={PARENT_SIG}\nS6B_L2_SIGNATURE_SHA256={sig}\n"
        "HORIZONS=30,60\nEMA=EMA7,EMA20\nFIB_ANCHOR=DETECTOR_EXTREME_TO_ENTRY\n"
        "FIB_LEVELS=0.382,0.500,0.618,0.786\nNO_EXIT_RULE=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}"
    lines=[
        "# BNB B41-S6B-L2 — LONG EMA / Fibonacci Augmentation","",
        f"**Status: {status}**","",f"S6B-L2 signature: `{sig}`","",
        "Technical features are tested only as additions to the frozen price-path precursor baseline. No exit threshold is constructed.","",
        "## Frozen price-path baseline","",
        "| Horizon | DEV AUC | REF AUC | DEV W/L | REF W/L |",
        "|---:|---:|---:|---:|---:|"
    ]
    for x in B.itertuples(index=False):
        lines.append(f"| {x.horizon_min}m | {num(x.dev_auc)} | {num(x.ref_auc)} | {x.dev_winners}/{x.dev_losers} | {x.ref_winners}/{x.ref_losers} |")

    lines += ["","## DEV-nominated technical augmentations","",
              "| Horizon | Family | Feature | DEV univ | REF univ | DEV aug | ΔDEV | REF aug | ΔREF | REF validated |",
              "|---:|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for x in A[A.dev_nominated].sort_values(["horizon_min","family","feature"]).itertuples(index=False):
        lines.append(f"| {x.horizon_min}m | {x.family} | {x.feature} | {num(x.dev_univ_auc)} | {num(x.ref_univ_auc)} | "
                     f"{num(x.dev_aug_auc)} | {num(x.dev_aug_delta)} | {num(x.ref_aug_auc)} | {num(x.ref_aug_delta)} | "
                     f"{'YES' if x.ref_validated else 'NO'} |")
    if not A.dev_nominated.any():
        lines.append("| — | — | No technical feature improved the DEV baseline enough | — | — | — | — | — | — | NO |")

    lines += ["","## REF-validated additions","",
              "| Horizon | Family | Feature | DEV Δ | REF Δ |",
              "|---:|---|---|---:|---:|"]
    for x in V.sort_values(["horizon_min","family","feature"]).itertuples(index=False):
        lines.append(f"| {x.horizon_min}m | {x.family} | {x.feature} | {num(x.dev_aug_delta)} | {num(x.ref_aug_delta)} |")
    if not len(V): lines.append("| — | — | None | — | — |")

    lines += ["","## Gate",
              f"- EMA adds stable incremental information: **{'YES' if ema_ok else 'NO'}**.",
              f"- Fibonacci adds stable incremental information: **{'YES' if fib_ok else 'NO'}**.",
              f"- Validated technical additions: **{len(V)}**.",
              "",
              "No SL threshold, TP, trade WR, PF, expectancy, leverage, or PnL was optimized."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
