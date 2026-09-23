#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6B_L_LONG_FAILURE_ANATOMY"
S5_SIG="5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241"
S6_SIG="cd192358bb7b294fb3f581aa1e887aa7f4de97a4995dae7866b1a440fe3561fc"
HORIZONS=[15,30,45,60]
CONT=[
 "entry_drawdown","below_wall_depth","mae_so_far","lack_mfe","below_wall_fraction",
 "max_consecutive_below_wall","final_consecutive_below_wall","failed_reclaim_count",
 "lower_low_pressure","down_slope_3"
]
BINARY=["final_below_wall","detector_extreme_touched","detector_extreme_close_breached"]

def verify():
    a=(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6/BNB_B41_S6_STRUCTURAL_INVALIDATION_DISCOVERY_Freeze.txt").read_text()
    if f"S5_SIGNATURE_SHA256={S5_SIG}" not in a: raise RuntimeError("S5 mismatch")
    if f"S6_SIGNATURE_SHA256={S6_SIG}" not in b: raise RuntimeError("S6 mismatch")

def max_consec(x):
    cur=mx=0
    for v in x:
        if v: cur+=1; mx=max(mx,cur)
        else: cur=0
    return mx

def final_consec(x):
    n=0
    for v in x[::-1]:
        if v:n+=1
        else:break
    return n

def auc_failure(w,l):
    w=pd.Series(w).dropna().astype(float)
    l=pd.Series(l).dropna().astype(float)
    if len(w)==0 or len(l)==0:return np.nan
    x=pd.concat([w,l],ignore_index=True)
    ranks=x.rank(method="average")
    rl=float(ranks.iloc[len(w):].sum())
    nl=len(l); nw=len(w)
    return float((rl-nl*(nl+1)/2)/(nl*nw))

def snapshot(bars, det, horizon, entry, wall, extreme, wd):
    end=det+pd.Timedelta(minutes=horizon)
    z=bars[(bars.index>det)&(bars.index<=end)].copy()
    if end not in bars.index or not len(z): return None
    closes=z.close.to_numpy(float)
    below=closes<wall
    cur=float(z.close.iloc[-1])
    mae=max(0.0,entry-float(z.low.min()))/wd
    mfe=max(0.0,float(z.high.max())-entry)/wd

    transitions=0
    seen_reclaim=False
    prev_below=None
    for b in below:
        if prev_below is True and b is False:
            seen_reclaim=True
        elif prev_below is False and b is True and seen_reclaim:
            transitions+=1
        prev_below=bool(b)

    half=max(1,len(z)//2)
    low1=float(z.low.iloc[:half].min())
    low2=float(z.low.iloc[half:].min()) if half<len(z) else low1
    ll=max(0.0,low1-low2)/wd

    if len(closes)>=4:
        slope=(closes[-1]-closes[-4])/wd
    elif len(closes)>=2:
        slope=(closes[-1]-closes[0])/wd
    else:
        slope=0.0

    return {
      "entry_drawdown":(entry-cur)/wd,
      "below_wall_depth":max(0.0,wall-cur)/wd,
      "mae_so_far":mae,
      "lack_mfe":-mfe,
      "below_wall_fraction":float(below.mean()),
      "max_consecutive_below_wall":float(max_consec(list(below))),
      "final_consecutive_below_wall":float(final_consec(list(below))),
      "failed_reclaim_count":float(transitions),
      "lower_low_pressure":ll,
      "down_slope_3":-slope,
      "final_below_wall":bool(cur<wall),
      "detector_extreme_touched":bool(float(z.low.min())<=extreme),
      "detector_extreme_close_breached":bool((z.close<extreme).any()),
    }

def main():
    verify()
    s5=pd.read_csv(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
                   compression="gzip",parse_dates=["session_day","detector_ts","endpoint_ts"])
    q=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")].copy()
    q=q[q.valid180].copy()
    if len(q)!=118: raise RuntimeError(f"LONG parity {len(q)} !=118")
    q["outcome_label"]=np.where(q.aligned180>0,"WINNER","LOSER")

    s6=pd.read_csv(ROOT/"results/bnb_b41_s6/BNB_B41_S6_STRUCTURAL_INVALIDATION_DISCOVERY_Ledger.csv.gz",
                   compression="gzip",parse_dates=["session_day","detector_ts","stop_ts"])
    bx=s6[(s6.side=="LOWER")&(s6.direction=="LONG")&(s6.tf=="TF60")&
          (s6.candidate=="S5_DETECTOR_EXTREME_CLOSE5")].copy()
    bx=bx[["signal_key","stop","stop_ts"]].rename(columns={"stop":"extreme_close_breach","stop_ts":"extreme_close_breach_ts"})
    q=q.merge(bx,on="signal_key",how="left",validate="one_to_one")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    breach_rows=[]
    for r in q.itertuples(index=False):
        day=pd.Timestamp(r.session_day); det=pd.Timestamp(r.detector_ts)
        bars=grouped[day]
        entry=float(r.detector_close); wall=float(r.wall); wd=abs(wall-float(r.session_open))
        i=bars.index.get_loc(det)
        obs=bars.iloc[i-11:i+1]
        extreme=float(obs.low.min())

        for h in HORIZONS:
            f=snapshot(bars,det,h,entry,wall,extreme,wd)
            if f is None: continue
            rows.append({
              "signal_key":r.signal_key,"session_day":day,"year":int(r.year),"period":r.period,
              "label":r.outcome_label,"aligned180":float(r.aligned180),"horizon_min":h,
              "entry":entry,"wall":wall,"detector_extreme":extreme,"wall_distance":wd,**f
            })

        if bool(r.extreme_close_breach) and pd.notna(r.extreme_close_breach_ts):
            bt=pd.Timestamp(r.extreme_close_breach_ts)
            pre=bars[(bars.index>det)&(bars.index<bt)]
            if len(pre):
                closes=pre.close.to_numpy(float); below=closes<wall
                mfe=max(0.0,float(pre.high.max())-entry)/wd
                mae=max(0.0,entry-float(pre.low.min()))/wd
                reclaims=int(np.sum((below[:-1]==True)&(below[1:]==False))) if len(below)>1 else 0
                fails=int(np.sum((below[:-1]==False)&(below[1:]==True))) if len(below)>1 else 0
                prior=float(pre.close.iloc[-1])
                breach_rows.append({
                    "signal_key":r.signal_key,"period":r.period,"year":int(r.year),
                    "breach_type":"FALSE_BREACH_WINNER" if r.outcome_label=="WINNER" else "TRUE_FAILURE_LOSER",
                    "minutes_to_breach":float((bt-det)/pd.Timedelta(minutes=1)),
                    "prior_close_vs_wall":(prior-wall)/wd,
                    "pre_breach_mae":mae,"pre_breach_mfe":mfe,
                    "pre_breach_below_fraction":float(below.mean()),
                    "pre_breach_reclaims":reclaims,"pre_breach_failed_reclaims":fails
                })
    F=pd.DataFrame(rows)
    B=pd.DataFrame(breach_rows)

    effects=[]
    for h in HORIZONS:
      for feat in CONT:
        for per in ["DEV","REF"]:
            z=F[(F.horizon_min==h)&(F.period==per)]
            w=z[z.label=="WINNER"][feat]; l=z[z.label=="LOSER"][feat]
            effects.append({"horizon_min":h,"feature":feat,"kind":"CONT","period":per,
                            "winner_n":w.notna().sum(),"loser_n":l.notna().sum(),
                            "winner_median":float(w.median()),"loser_median":float(l.median()),
                            "failure_auc":auc_failure(w,l),
                            "rate_delta":np.nan})
      for feat in BINARY:
        for per in ["DEV","REF"]:
            z=F[(F.horizon_min==h)&(F.period==per)]
            w=z[z.label=="WINNER"][feat].astype(float); l=z[z.label=="LOSER"][feat].astype(float)
            effects.append({"horizon_min":h,"feature":feat,"kind":"BINARY","period":per,
                            "winner_n":len(w),"loser_n":len(l),
                            "winner_median":float(w.mean()),"loser_median":float(l.mean()),
                            "failure_auc":np.nan,
                            "rate_delta":float(l.mean()-w.mean())})
    E=pd.DataFrame(effects)

    noms=[]
    for h in HORIZONS:
      for feat in CONT+BINARY:
        d=E[(E.horizon_min==h)&(E.feature==feat)&(E.period=="DEV")].iloc[0]
        r=E[(E.horizon_min==h)&(E.feature==feat)&(E.period=="REF")].iloc[0]
        if d.kind=="CONT":
            dev=bool(d.winner_n>=30 and d.loser_n>=20 and d.failure_auc>=.60)
            ref=bool(dev and r.winner_n>=20 and r.loser_n>=15 and r.failure_auc>=.55)
            strength_dev=d.failure_auc; strength_ref=r.failure_auc
        else:
            dev=bool(d.winner_n>=30 and d.loser_n>=20 and d.rate_delta>=.15)
            ref=bool(dev and r.winner_n>=20 and r.loser_n>=15 and r.rate_delta>=.10)
            strength_dev=d.rate_delta; strength_ref=r.rate_delta
        noms.append({"horizon_min":h,"feature":feat,"kind":d.kind,
                     "dev_nominated":dev,"ref_validated":ref,
                     "dev_strength":strength_dev,"ref_strength":strength_ref})
    N=pd.DataFrame(noms)
    V=N[N.ref_validated].copy()
    earliest=int(V.horizon_min.min()) if len(V) else np.nan
    status="BNB_B41_S6B_L_LONG_FAILURE_PRECURSOR_FOUND" if len(V) else "BNB_B41_S6B_L_NO_STABLE_LONG_FAILURE_PRECURSOR"

    bsum=[]
    if len(B):
      for per in ["DEV","REF","ALL"]:
        p=B if per=="ALL" else B[B.period==per]
        for typ in ["FALSE_BREACH_WINNER","TRUE_FAILURE_LOSER"]:
          z=p[p.breach_type==typ]
          bsum.append({
            "period":per,"breach_type":typ,"n":len(z),
            "median_minutes_to_breach":float(z.minutes_to_breach.median()) if len(z) else np.nan,
            "median_prior_close_vs_wall":float(z.prior_close_vs_wall.median()) if len(z) else np.nan,
            "median_pre_mae":float(z.pre_breach_mae.median()) if len(z) else np.nan,
            "median_pre_mfe":float(z.pre_breach_mfe.median()) if len(z) else np.nan,
            "median_below_fraction":float(z.pre_breach_below_fraction.median()) if len(z) else np.nan,
            "median_reclaims":float(z.pre_breach_reclaims.median()) if len(z) else np.nan,
            "median_failed_reclaims":float(z.pre_breach_failed_reclaims.median()) if len(z) else np.nan,
          })
    BS=pd.DataFrame(bsum)

    sig=hashlib.sha256(json.dumps({
      "parents":[S5_SIG,S6_SIG],"setup":"LOWER_C2_LONG_TF60_MARKET",
      "horizons":HORIZONS,"continuous":CONT,"binary":BINARY,
      "dev":{"auc":.60,"binary_delta":.15,"winner_n":30,"loser_n":20},
      "ref":{"auc":.55,"binary_delta":.10,"winner_n":20,"loser_n":15},
      "breach_anatomy":"DESCRIPTIVE_ONLY","no_stop_rule":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    F.to_csv(ROOT/f"{PFX}_SnapshotLedger.csv.gz",index=False,compression="gzip")
    E.to_csv(ROOT/f"{PFX}_Effects.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    B.to_csv(ROOT/f"{PFX}_BreachLedger.csv.gz",index=False,compression="gzip")
    BS.to_csv(ROOT/f"{PFX}_BreachSummary.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
      f"PARENT_S5_SIGNATURE_SHA256={S5_SIG}\nPARENT_S6_SIGNATURE_SHA256={S6_SIG}\n"
      f"S6B_L_SIGNATURE_SHA256={sig}\nHORIZONS=15,30,45,60\nNO_STOP_RULE=TRUE\n",
      encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}"
    lines=[
      "# BNB B41-S6B-L — LONG Failure Anatomy","",
      f"**Status: {status}**","",f"S6B-L signature: `{sig}`","",
      "Setup is frozen: Lower Q80 reclaim, TF60 maturation, market LONG. S6B-L discovers precursors only; it does not create an SL.","",
      "## DEV-nominated precursor validation","",
      "| Horizon | Feature | Kind | DEV strength | REF strength | DEV nominated | REF validated |",
      "|---:|---|---|---:|---:|---|---|"
    ]
    for r in N[N.dev_nominated].sort_values(["horizon_min","feature"]).itertuples(index=False):
      ds=pct(r.dev_strength) if r.kind=="BINARY" else num(r.dev_strength)
      rs=pct(r.ref_strength) if r.kind=="BINARY" else num(r.ref_strength)
      lines.append(f"| {r.horizon_min}m | {r.feature} | {r.kind} | {ds} | {rs} | YES | {'YES' if r.ref_validated else 'NO'} |")
    if not N.dev_nominated.any():
      lines.append("| — | No DEV precursor met preregistered separation | — | — | — | NO | NO |")

    lines += ["","## REF-validated stable precursors","",
      "| Horizon | Feature | Kind | DEV | REF |",
      "|---:|---|---|---:|---:|"
    ]
    for r in V.sort_values(["horizon_min","feature"]).itertuples(index=False):
      ds=pct(r.dev_strength) if r.kind=="BINARY" else num(r.dev_strength)
      rs=pct(r.ref_strength) if r.kind=="BINARY" else num(r.ref_strength)
      lines.append(f"| {r.horizon_min}m | {r.feature} | {r.kind} | {ds} | {rs} |")
    if not len(V): lines.append("| — | None | — | — | — |")

    lines += ["","## Detector-extreme CLOSE5 breach anatomy (descriptive only)","",
      "| Period | Breach cohort | N | Time to breach | Prior close vs wall | Pre MAE | Pre MFE | Below-wall frac | Reclaims | Failed reclaims |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in BS.itertuples(index=False):
      lines.append(f"| {r.period} | {r.breach_type} | {r.n} | {num(r.median_minutes_to_breach)}m | "
                   f"{num(r.median_prior_close_vs_wall)}x | {num(r.median_pre_mae)}x | {num(r.median_pre_mfe)}x | "
                   f"{pct(r.median_below_fraction)} | {num(r.median_reclaims)} | {num(r.median_failed_reclaims)} |")

    lines += ["","## Gate",
      f"- Stable REF-validated precursor count: **{len(V)}**.",
      f"- Earliest stable precursor horizon: **{int(earliest) if np.isfinite(earliest) else 'NONE'}{'m' if np.isfinite(earliest) else ''}**.",
      f"- Next step: **{'S6C-L causal invalidation rule construction' if len(V) else 'do not construct a LONG stop rule yet'}**.",
      "",
      "No SL threshold, TP, trade WR, PF, expectancy, leverage, or PnL was optimized."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
