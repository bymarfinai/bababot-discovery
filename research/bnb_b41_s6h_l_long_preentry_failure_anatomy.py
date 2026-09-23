#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6H_L_LONG_PREENTRY_FAILURE_ANATOMY"
S4B_SIG="acab9ae7928bdcbebc3608a1f5818a6b5eaa6a4a782f446a2cc418e8e50adcbc"
S5_SIG="5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241"
S6G_SIG="778ed211d039860e0429bf54799e26e3ca9dba0b5672bffe9857fd7d760e1abe"
FEATURES=[
 "penetration_depth","outside_close_fraction","failed_reclaim_count","wall_cross_count",
 "low_recency","detector_range","weak_final_margin","weak_recovery_from_low",
 "short_final_inside_streak","down_slope_3_preentry","down_slope_6_preentry",
 "weak_reclaim_strength","weak_final_clv","recent_last_outside"
]
COMPOSITE_FEATURES=[
 "penetration_depth","outside_close_fraction","failed_reclaim_count",
 "weak_final_margin","short_final_inside_streak","down_slope_3_preentry"
]

def verify():
    checks=[
      (ROOT/"results/bnb_b41_s4b/BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY_Freeze.txt",
       f"S4B_SIGNATURE_SHA256={S4B_SIG}"),
      (ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Freeze.txt",
       f"S5_SIGNATURE_SHA256={S5_SIG}"),
      (ROOT/"results/bnb_b41_s6g_l/BNB_B41_S6G_L_LONG_PARTIAL_DERISK_Freeze.txt",
       f"S6G_L_SIGNATURE_SHA256={S6G_SIG}"),
    ]
    for p,s in checks:
        if s not in p.read_text(): raise RuntimeError(f"parent mismatch {p.name}")

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
    med=float(x.median()); q1=float(x.quantile(.25)); q3=float(x.quantile(.75))
    den=q3-q1
    if not np.isfinite(den) or den<=1e-12: den=float(x.std(ddof=0))
    if not np.isfinite(den) or den<=1e-12: den=1.0
    return med,den

def z(s,p):
    med,den=p
    return (pd.Series(s,dtype=float)-med)/den

def count_failed_reclaims(states):
    # states True = below wall. Count inside -> outside relapses after first outside.
    seen=False; cnt=0
    prev=None
    for st in states:
        st=bool(st)
        if st: seen=True
        if seen and prev is False and st is True: cnt+=1
        prev=st
    return cnt

def final_inside_streak(states):
    n=0
    for st in states[::-1]:
        if bool(st): break
        n+=1
    return n

def main():
    verify()

    E=pd.read_csv(
      ROOT/"results/bnb_b41_s4b/BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY_Ledger.csv.gz",
      compression="gzip",parse_dates=["session_day","first_touch_ts","detector_ts"]
    )
    E=E[
      (E.eligible_tf==True)&
      (E.side=="LOWER")&
      (E.character=="C2_RECLAIM_AFTER_CLOSE")&
      (E.direction=="LONG")&
      (E.tf=="TF60")
    ].copy()

    S5=pd.read_csv(
      ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
      compression="gzip",parse_dates=["session_day","detector_ts"]
    )
    S5=S5[
      (S5.candidate=="E0_MARKET")&
      (S5.side=="LOWER")&
      (S5.character=="C2_RECLAIM_AFTER_CLOSE")&
      (S5.direction=="LONG")&
      (S5.tf=="TF60")&
      (S5.valid180)
    ].copy()

    # S5 has exactly the valid +180 labels we need.
    if len(S5)!=118: raise RuntimeError(f"S5 LONG parity {len(S5)} !=118")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    for r in S5.itertuples(index=False):
        day=pd.Timestamp(r.session_day)
        det=pd.Timestamp(r.detector_ts)
        # Find matching frozen S4B event to recover first_touch.
        m=E[(E.session_day==day)&(E.detector_ts==det)]
        if len(m)!=1: raise RuntimeError(f"S4B event match {day} {det} -> {len(m)}")
        ev=m.iloc[0]
        touch=pd.Timestamp(ev.first_touch_ts)
        bars=grouped[day]
        if touch not in bars.index or det not in bars.index: raise RuntimeError("missing detector bars")
        i=bars.index.get_loc(touch); j=bars.index.get_loc(det)
        if not isinstance(i,(int,np.integer)) or not isinstance(j,(int,np.integer)): raise RuntimeError("nonunique index")
        obs=bars.iloc[i:j+1].copy()
        if len(obs)!=12: raise RuntimeError(f"TF60 obs len {len(obs)}")

        wall=float(r.wall); wd=abs(wall-float(r.session_open))
        if wd<=0: raise RuntimeError("nonpositive wall distance")
        closes=obs.close.to_numpy(float); lows=obs.low.to_numpy(float)
        states=closes<wall
        if not states.any() or states[-1]: raise RuntimeError("not C2 reclaim morphology")

        minlow=float(obs.low.min()); maxhigh=float(obs.high.max())
        penetration=max(0.0,wall-minlow)/wd
        cross=int(np.sum(states[1:]!=states[:-1]))
        low_idx=int(np.argmin(lows))
        inside_streak=final_inside_streak(states)
        last_out=np.where(states)[0][-1]
        bars_since_last=(len(states)-1)-int(last_out)
        final=obs.iloc[-1]
        frange=float(final.high-final.low)
        clv=.5 if frange<=1e-12 else float((final.close-final.low)/frange)
        denom=max(wall-minlow,.05*wd)

        f={
          "penetration_depth":penetration,
          "outside_close_fraction":float(states.mean()),
          "failed_reclaim_count":float(count_failed_reclaims(states)),
          "wall_cross_count":float(cross),
          "low_recency":float(low_idx/11.0),
          "detector_range":float((maxhigh-minlow)/wd),
          "weak_final_margin":float(-(float(final.close)-wall)/wd),
          "weak_recovery_from_low":float(-(float(final.close)-minlow)/wd),
          "short_final_inside_streak":float(-inside_streak),
          "down_slope_3_preentry":float(-(closes[-1]-closes[-4])/wd),
          "down_slope_6_preentry":float(-(closes[-1]-closes[-7])/wd),
          "weak_reclaim_strength":float(-(float(final.close)-wall)/denom),
          "weak_final_clv":float(-clv),
          "recent_last_outside":float(-bars_since_last),
        }
        rows.append({
          "signal_key":r.signal_key,"session_day":day,"year":int(r.year),"period":str(r.period),
          "first_touch_ts":touch,"detector_ts":det,"wall":wall,"wall_distance":wd,
          "entry":float(r.detector_close),"aligned180":float(r.aligned180),
          "label":"LOSER" if float(r.aligned180)<=0 else "WINNER",
          **f
        })
    L=pd.DataFrame(rows)
    L["is_loser"]=L.label.eq("LOSER")

    # Parity checks.
    for per,w,l in [("DEV",49,27),("REF",24,18)]:
        q=L[L.period==per]
        if int((~q.is_loser).sum())!=w or int(q.is_loser.sum())!=l:
            raise RuntimeError(f"{per} label parity drift")

    # DEV-fitted frozen composite.
    dev=L[L.period=="DEV"]
    scales={f:fit_scale(dev[f]) for f in COMPOSITE_FEATURES}
    for frame in [L]:
        frame["RECLAIM_RISK_COMPOSITE"]=sum(
          z(frame[f],scales[f]).to_numpy() for f in COMPOSITE_FEATURES
        )/len(COMPOSITE_FEATURES)

    audit=[]
    allfeatures=FEATURES+["RECLAIM_RISK_COMPOSITE"]
    for f in allfeatures:
        for per in ["DEV","REF","ALL"]:
            q=L if per=="ALL" else L[L.period==per]
            w=q[~q.is_loser][f]; lo=q[q.is_loser][f]
            audit.append({
              "feature":f,"period":per,
              "winner_n":len(w),"loser_n":len(lo),
              "winner_median":float(w.median()),"loser_median":float(lo.median()),
              "failure_auc":auc_failure(q.is_loser,q[f])
            })
    A=pd.DataFrame(audit)

    noms=[]
    for f in allfeatures:
        d=A[(A.feature==f)&(A.period=="DEV")].iloc[0]
        r=A[(A.feature==f)&(A.period=="REF")].iloc[0]
        devnom=bool(d.winner_n>=30 and d.loser_n>=20 and d.failure_auc>=.60)
        refval=bool(devnom and r.winner_n>=20 and r.loser_n>=15 and r.failure_auc>=.55)
        noms.append({
          "feature":f,"dev_nominated":devnom,"ref_validated":refval,
          "dev_auc":d.failure_auc,"ref_auc":r.failure_auc,
          "dev_winner_median":d.winner_median,"dev_loser_median":d.loser_median,
          "ref_winner_median":r.winner_median,"ref_loser_median":r.loser_median
        })
    N=pd.DataFrame(noms)
    V=N[N.ref_validated].copy()

    yearly=[]
    for y in [2022,2023,2024,2025,2026]:
        q=L[L.year==y]
        for f in allfeatures:
            yearly.append({
              "year":y,"feature":f,"winner_n":int((~q.is_loser).sum()),"loser_n":int(q.is_loser.sum()),
              "failure_auc":auc_failure(q.is_loser,q[f]) if q.is_loser.any() and (~q.is_loser).any() else np.nan
            })
    Y=pd.DataFrame(yearly)

    status=("BNB_B41_S6H_L_PREENTRY_FAILURE_PRECURSOR_FOUND" if len(V)
            else "BNB_B41_S6H_L_NO_STABLE_PREENTRY_FAILURE_PRECURSOR")

    sig=hashlib.sha256(json.dumps({
      "parents":[S4B_SIG,S5_SIG,S6G_SIG],
      "setup":"LOWER_Q80_C2_TF60_MARKET_LONG",
      "observation":"FROZEN_12X5M_DETECTOR_WINDOW_ONLY",
      "features":FEATURES,
      "composite":COMPOSITE_FEATURES,
      "scaling":"DEV_MEDIAN_IQR",
      "dev_gate":{"winner_n":30,"loser_n":20,"auc":.60},
      "ref_gate":{"winner_n":20,"loser_n":15,"auc":.55},
      "no_filter_threshold":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_FeatureAudit.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    V.to_csv(ROOT/f"{PFX}_Validated.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
      f"PARENT_S4B_SIGNATURE_SHA256={S4B_SIG}\nPARENT_S5_SIGNATURE_SHA256={S5_SIG}\n"
      f"PARENT_S6G_L_SIGNATURE_SHA256={S6G_SIG}\nS6H_L_SIGNATURE_SHA256={sig}\n"
      "SETUP=LOWER_Q80_C2_TF60_MARKET_LONG\nOBSERVATION=PREENTRY_12X5M_ONLY\n"
      "NO_FILTER_THRESHOLD=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}"
    lines=[
      "# BNB B41-S6H-L — LONG Pre-Entry Failure Anatomy","",
      f"**Status: {status}**","",f"S6H-L signature: `{sig}`","",
      "Only information known at the frozen TF60 detector close is used. No entry filter threshold is constructed.","",
      "## DEV nominations -> REF holdout","",
      "| Feature | DEV AUC | REF AUC | DEV winner med | DEV loser med | REF winner med | REF loser med | DEV nom | REF valid |",
      "|---|---:|---:|---:|---:|---:|---:|---|---|"
    ]
    for r in N.itertuples(index=False):
        lines.append(
          f"| {r.feature} | {num(r.dev_auc)} | {num(r.ref_auc)} | {num(r.dev_winner_median)} | "
          f"{num(r.dev_loser_median)} | {num(r.ref_winner_median)} | {num(r.ref_loser_median)} | "
          f"{'YES' if r.dev_nominated else 'NO'} | {'YES' if r.ref_validated else 'NO'} |"
        )
    lines += ["","## Stable pre-entry precursors",""]
    if len(V):
        for r in V.sort_values(["dev_auc","ref_auc"],ascending=False).itertuples(index=False):
            lines.append(f"- **{r.feature}** — DEV AUC {r.dev_auc:.3f}, REF AUC {r.ref_auc:.3f}.")
    else:
        lines.append("- None.")
    lines += ["","## Gate",
      f"- DEV nominees: **{int(N.dev_nominated.sum())}**.",
      f"- REF-validated precursors: **{len(V)}**.",
      f"- Next: **{'separately preregister entry-filter construction' if len(V) else 'do not filter LONG entry from this morphology family'}**.",
      "",
      "No entry filter threshold, TP, SL, WR optimization, PF, expectancy, leverage, fees/slippage, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
