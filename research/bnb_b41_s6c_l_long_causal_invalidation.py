#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION"
S6B_SIG="35ab7d201fe45d398b3c959483aa7eef5d68a9d901336d57a25489f9b2f54190"
S6B2_SIG="34311bc2e4d9d005c37ee461817463757dcf7532b8aa4f78ac454135430afc86"
BASE=["entry_drawdown","mae_so_far","down_slope_3"]
CANDS=[
    ("R1_30_SCORE_Q85",30,"SCORE"),
    ("R2_60_DRAW_Q85",60,"DRAW"),
    ("R3_60_SCORE_Q85",60,"SCORE"),
    ("R4_60_2OF3_Q85",60,"CONFLUENCE"),
]

def verify():
    a=(ROOT/"results/bnb_b41_s6b_l/BNB_B41_S6B_L_LONG_FAILURE_ANATOMY_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6b_l2/BNB_B41_S6B_L2_LONG_TECHNICAL_AUGMENTATION_Freeze.txt").read_text()
    if f"S6B_L_SIGNATURE_SHA256={S6B_SIG}" not in a: raise RuntimeError("S6B-L mismatch")
    if f"S6B_L2_SIGNATURE_SHA256={S6B2_SIG}" not in b: raise RuntimeError("S6B-L2 mismatch")

def fit_scale(s):
    x=pd.Series(s).astype(float).dropna()
    med=float(x.median()); q1=float(x.quantile(.25)); q3=float(x.quantile(.75)); den=q3-q1
    if not np.isfinite(den) or den<=1e-12: den=float(x.std(ddof=0))
    if not np.isfinite(den) or den<=1e-12: den=1.0
    return med,den

def rz(s,p):
    med,den=p
    return (pd.Series(s,dtype=float)-med)/den

def stats(z):
    z=z[z.valid180].copy()
    bw=z[z.baseline_winner]
    bl=z[~z.baseline_winner]
    fs=bw[bw.stop]
    lc=bl[bl.stop].copy()
    if len(lc): lc["improvement"]=lc.rule_outcome-lc.baseline_aligned180
    return {
        "n180":len(z),
        "baseline_wins":len(bw),"baseline_losers":len(bl),
        "baseline_mean":float(z.baseline_aligned180.mean()) if len(z) else np.nan,
        "baseline_median":float(z.baseline_aligned180.median()) if len(z) else np.nan,
        "baseline_q10":float(z.baseline_aligned180.quantile(.10)) if len(z) else np.nan,
        "stop_n":int(z.stop.sum()),
        "stop_rate":float(z.stop.mean()) if len(z) else np.nan,
        "false_stop_winners":len(fs),
        "false_stop_rate":len(fs)/len(bw) if len(bw) else np.nan,
        "loser_caught":len(lc),
        "loser_catch_rate":len(lc)/len(bl) if len(bl) else np.nan,
        "median_loser_improvement":float(lc.improvement.median()) if len(lc) else np.nan,
        "mean_outcome":float(z.rule_outcome.mean()) if len(z) else np.nan,
        "median_outcome":float(z.rule_outcome.median()) if len(z) else np.nan,
        "q10_outcome":float(z.rule_outcome.quantile(.10)) if len(z) else np.nan,
        "positive_rate":float((z.rule_outcome>0).mean()) if len(z) else np.nan,
        "median_stop_outcome":float(z.loc[z.stop,"rule_outcome"].median()) if z.stop.any() else np.nan,
    }

def main():
    verify()
    F=pd.read_csv(ROOT/"results/bnb_b41_s6b_l/BNB_B41_S6B_L_LONG_FAILURE_ANATOMY_SnapshotLedger.csv.gz",
                  compression="gzip",parse_dates=["session_day"])
    F=F[F.horizon_min.isin([30,60])].copy()

    s5=pd.read_csv(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
                   compression="gzip",parse_dates=["detector_ts","endpoint_ts"])
    s5=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")&
          (s5.valid180)].copy()
    if len(s5)!=118: raise RuntimeError(f"LONG base parity {len(s5)} !=118")

    # Wide snapshot features.
    keep=["signal_key","period","year","label","horizon_min","entry","wall_distance",
          "entry_drawdown","mae_so_far","down_slope_3"]
    W=F[keep].copy()
    wide=W.pivot(index=["signal_key","period","year","label","entry","wall_distance"],
                 columns="horizon_min",values=BASE).reset_index()
    wide.columns=[("_".join(map(str,c)).strip("_") if isinstance(c,tuple) else c) for c in wide.columns]

    base=s5[["signal_key","detector_ts","endpoint_ts","aligned180","detector_close"]].rename(
        columns={"aligned180":"baseline_aligned180","detector_close":"entry_s5"})
    D=wide.merge(base,on="signal_key",how="left",validate="one_to_one")
    if D.baseline_aligned180.isna().any(): raise RuntimeError("missing baseline")
    D["baseline_winner"]=D.baseline_aligned180>0
    D["valid180"]=True

    # Reconstruct raw close at 30m / 60m after detector.
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["close"]].astype(float).sort_index()
    for h in [30,60]:
        vals=[]
        for r in D.itertuples(index=False):
            ts=pd.Timestamp(r.detector_ts)+pd.Timedelta(minutes=h)
            if ts not in k.index: raise RuntimeError(f"missing close {ts}")
            vals.append(float(k.loc[ts,"close"]))
        D[f"close_{h}"]=vals

    # DEV-only robust scales and risk scores.
    dev=D[D.period=="DEV"].copy()
    params={}
    for h in [30,60]:
        for f in BASE:
            col=f"{f}_{h}"
            params[(h,f)]=fit_scale(dev[col])
        for frame in [D]:
            frame[f"risk_score_{h}"]=sum(
                rz(frame[f"{f}_{h}"],params[(h,f)]).to_numpy() for f in BASE
            )/len(BASE)

    # Winner-derived frozen thresholds from DEV only.
    dw=D[(D.period=="DEV")&D.baseline_winner]
    th={
        "score30_q85":float(dw.risk_score_30.quantile(.85)),
        "score60_q85":float(dw.risk_score_60.quantile(.85)),
        "draw60_q85":float(dw.entry_drawdown_60.quantile(.85)),
        "mae60_q85":float(dw.mae_so_far_60.quantile(.85)),
        "slope60_q85":float(dw.down_slope_3_60.quantile(.85)),
    }

    ledgers=[]
    for name,h,kind in CANDS:
        z=D.copy()
        if kind=="SCORE":
            trig=z[f"risk_score_{h}"] >= th[f"score{h}_q85"]
        elif kind=="DRAW":
            trig=z.entry_drawdown_60 >= th["draw60_q85"]
        elif kind=="CONFLUENCE":
            votes=(z.entry_drawdown_60>=th["draw60_q85"]).astype(int)
            votes+=(z.mae_so_far_60>=th["mae60_q85"]).astype(int)
            votes+=(z.down_slope_3_60>=th["slope60_q85"]).astype(int)
            z["risk_votes"]=votes
            trig=votes>=2
        else: raise RuntimeError(kind)
        z["candidate"]=name
        z["checkpoint_min"]=h
        z["stop"]=trig.astype(bool)
        z["exit_price"]=np.where(z.stop,z[f"close_{h}"],np.nan)
        z["rule_outcome"]=np.where(
            z.stop,
            (z[f"close_{h}"]-z.entry)/z.wall_distance,
            z.baseline_aligned180
        )
        ledgers.append(z)
    L=pd.concat(ledgers,ignore_index=True)

    summaries=[]
    for per in ["DEV","REF","ALL"]:
        p=L if per=="ALL" else L[L.period==per]
        for name,_,_ in CANDS:
            q=p[p.candidate==name]
            summaries.append({"period":per,"candidate":name,**stats(q)})
    A=pd.DataFrame(summaries)

    def eligible(row):
        return bool(
            row.n180>=30 and row.false_stop_rate<=.15 and row.loser_catch_rate>=.25 and
            np.isfinite(row.median_loser_improvement) and row.median_loser_improvement>0 and
            row.mean_outcome>=row.baseline_mean and row.q10_outcome>row.baseline_q10
        )

    devrows=A[A.period=="DEV"].copy()
    devrows["eligible"]=devrows.apply(eligible,axis=1)

    # Earliest checkpoint first; fixed simplicity order inside same checkpoint.
    priority={name:i for i,(name,_,_) in enumerate(CANDS)}
    checks={name:h for name,h,_ in CANDS}
    es=devrows[devrows.eligible].copy()
    if len(es):
        es["checkpoint"]=es.candidate.map(checks)
        es["priority"]=es.candidate.map(priority)
        es=es.sort_values(["checkpoint","priority"])
        nominee=str(es.iloc[0].candidate)
        rr=A[(A.period=="REF")&(A.candidate==nominee)].iloc[0]
        ref_ok=bool(
            rr.n180>=20 and rr.false_stop_rate<=.15 and rr.loser_catch_rate>=.25 and
            np.isfinite(rr.median_loser_improvement) and rr.median_loser_improvement>0 and
            rr.mean_outcome>=rr.baseline_mean and rr.q10_outcome>rr.baseline_q10
        )
    else:
        nominee="NO_NOMINATION"; ref_ok=False

    status="BNB_B41_S6C_L_LONG_INVALIDATION_READY" if ref_ok else "BNB_B41_S6C_L_LONG_INVALIDATION_NOT_READY"

    # Annual anatomy for nominee if one exists.
    yr=[]
    if nominee!="NO_NOMINATION":
        for y in [2022,2023,2024,2025,2026]:
            q=L[(L.candidate==nominee)&(L.year==y)]
            if len(q):
                yr.append({"year":y,**stats(q)})
    Y=pd.DataFrame(yr)

    sig=hashlib.sha256(json.dumps({
        "parents":[S6B_SIG,S6B2_SIG],"setup":"LOWER_C2_LONG_TF60_MARKET",
        "base_features":BASE,"scaling":"DEV_MEDIAN_IQR",
        "threshold_source":"DEV_WINNER_Q85",
        "candidates":[x[0] for x in CANDS],
        "dev_gate":{"false_stop_max":.15,"loser_catch_min":.25,"loser_improvement":">0","mean":">=baseline","q10":">baseline"},
        "selection":"EARLIEST_CHECKPOINT_THEN_FIXED_SIMPLICITY_ORDER",
        "ref_gate":"SAME_WITH_N180_MIN20",
        "no_ema_fib":True,"no_tp":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    devrows.to_csv(ROOT/f"{PFX}_DEV_Eligibility.csv",index=False)
    pd.DataFrame([{"threshold":k,"value":v} for k,v in th.items()]).to_csv(ROOT/f"{PFX}_Thresholds.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_NomineeByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S6B_L_SIGNATURE_SHA256={S6B_SIG}\nPARENT_S6B_L2_SIGNATURE_SHA256={S6B2_SIG}\n"
        f"S6C_L_SIGNATURE_SHA256={sig}\nNOMINEE={nominee}\nREF_VALIDATED={'TRUE' if ref_ok else 'FALSE'}\n"
        "THRESHOLD_SOURCE=DEV_WINNER_Q85\nNO_EMA_FIB=TRUE\nNO_TP=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"
    lines=[
        "# BNB B41-S6C-L — LONG Causal Invalidation Rule Construction","",
        f"**Status: {status}**","",f"S6C-L signature: `{sig}`","",
        "Thresholds are frozen from DEV winners only. EMA/Fibonacci are excluded. No TP is used.","",
        "## Frozen DEV-winner thresholds","",
        "| Threshold | Value |","|---|---:|"
    ]
    for k,v in th.items(): lines.append(f"| {k} | {v:.6f} |")

    lines += ["","## Rule audit","",
        "| Period | Candidate | Stops | False-stop winners | Loser catch | Med loser improve | Mean Δ | q10 Δ | Positive | Med stop outcome |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.candidate} | {pct(r.stop_rate)} | "
            f"{r.false_stop_winners}/{r.baseline_wins} ({pct(r.false_stop_rate)}) | "
            f"{r.loser_caught}/{r.baseline_losers} ({pct(r.loser_catch_rate)}) | "
            f"{num(r.median_loser_improvement)} | {num(r.mean_outcome-r.baseline_mean)} | "
            f"{num(r.q10_outcome-r.baseline_q10)} | {pct(r.positive_rate)} | {num(r.median_stop_outcome)} |"
        )

    lines += ["","## DEV gate","",
        "| Candidate | Eligible |","|---|---|"]
    for r in devrows.itertuples(index=False):
        lines.append(f"| {r.candidate} | {'YES' if r.eligible else 'NO'} |")

    lines += ["","## Nomination",
        f"- DEV nominee: **{nominee}**.",
        f"- REF validated: **{'YES' if ref_ok else 'NO'}**.",
        f"- LONG invalidation gate: **{'READY' if ref_ok else 'NOT READY'}**.",
        "",
        "No TP, trade WR, PF, expectancy, leverage, or PnL was optimized."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
