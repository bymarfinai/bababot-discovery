#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b41_s2_wall_importance_audit as s2

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6I_L_LONG_APPROACH_HABITAT_ANATOMY"
S5_SIG="5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241"
S6H_SIG="a24465be8cadff835f4fad1d4cd01db7dbff9d0f9fe3ee566f1971aded008232"

FEATURES=[
 "down_velocity_30","down_velocity_60","down_velocity_120",
 "trend_eff_60","chop_60","down_bar_fraction_60",
 "range_30_norm","range_60_norm","range_expansion_30v60",
 "return_vol_60","sign_flip_count_60","touch_latency_min",
 "session_down_efficiency","session_up_excursion_norm","wall_distance_pct"
]
COMP=["down_velocity_60","trend_eff_60","down_bar_fraction_60","range_expansion_30v60","session_down_efficiency"]

def verify():
    a=(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6h_l/BNB_B41_S6H_L_LONG_PREENTRY_FAILURE_ANATOMY_Freeze.txt").read_text()
    if f"S5_SIGNATURE_SHA256={S5_SIG}" not in a: raise RuntimeError("S5 mismatch")
    if f"S6H_L_SIGNATURE_SHA256={S6H_SIG}" not in b: raise RuntimeError("S6H mismatch")

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
    med=float(x.median()); q1=float(x.quantile(.25)); q3=float(x.quantile(.75)); den=q3-q1
    if not np.isfinite(den) or den<=1e-12: den=float(x.std(ddof=0))
    if not np.isfinite(den) or den<=1e-12: den=1.0
    return med,den

def rz(s,p):
    med,den=p
    return (pd.Series(s,dtype=float)-med)/den

def trend_eff(closes):
    c=np.asarray(closes,dtype=float)
    if len(c)<2:return np.nan
    path=float(np.abs(np.diff(c)).sum())
    return float(abs(c[-1]-c[0])/path) if path>1e-12 else 0.0

def sign_flips(closes):
    d=np.diff(np.asarray(closes,dtype=float))
    s=np.sign(d)
    s=s[s!=0]
    return int(np.sum(s[1:]!=s[:-1])) if len(s)>1 else 0

def ret_vol(closes):
    c=np.asarray(closes,dtype=float)
    if len(c)<4:return np.nan
    r=c[1:]/c[:-1]-1.0
    return float(np.std(r,ddof=0))

def main():
    verify()

    s5=pd.read_csv(
      ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
      compression="gzip",parse_dates=["session_day","detector_ts"]
    )
    s5=s5[
      (s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&
      (s5.character=="C2_RECLAIM_AFTER_CLOSE")&(s5.direction=="LONG")&
      (s5.tf=="TF60")&(s5.valid180)
    ].copy()
    if len(s5)!=118: raise RuntimeError(f"S5 parity {len(s5)}")

    s4=pd.read_csv(
      ROOT/"results/bnb_b41_s4b/BNB_B41_S4B_MTF_DIRECTION_TIMING_ANATOMY_Ledger.csv.gz",
      compression="gzip",parse_dates=["session_day","first_touch_ts","detector_ts"]
    )
    s4=s4[
      (s4.eligible_tf==True)&(s4.side=="LOWER")&
      (s4.character=="C2_RECLAIM_AFTER_CLOSE")&
      (s4.direction=="LONG")&(s4.tf=="TF60")
    ][["session_day","first_touch_ts","detector_ts"]].copy()

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    allbars=raw[["open","high","low","close"]].astype(float).sort_index()
    xb=s2.session_bars(raw)
    grouped={k:v.copy() for k,v in xb.groupby("session_day",sort=False)}

    rows=[]
    for r in s5.itertuples(index=False):
        day=pd.Timestamp(r.session_day); det=pd.Timestamp(r.detector_ts)
        m=s4[(s4.session_day==day)&(s4.detector_ts==det)]
        if len(m)!=1: raise RuntimeError(f"S4 match {len(m)}")
        touch=pd.Timestamp(m.iloc[0].first_touch_ts)
        if touch not in allbars.index: raise RuntimeError("touch missing global")

        pos=allbars.index.get_loc(touch)
        if not isinstance(pos,(int,np.integer)): raise RuntimeError("nonunique touch")
        if pos<25: raise RuntimeError("insufficient global history")

        pre=allbars.iloc[:pos]  # strictly before touch bar
        anchor=float(pre.close.iloc[-1])

        def win(n):
            return pre.iloc[-n:]

        w6=win(6); w12=win(12); w24=win(24)
        c6=w6.close.to_numpy(float); c12=w12.close.to_numpy(float); c24=w24.close.to_numpy(float)
        wd=abs(float(r.wall)-float(r.session_open))
        if wd<=0: raise RuntimeError("nonpositive wd")

        # Velocity uses first vs final completed close in each fixed pre-touch window.
        dv30=(float(c6[0])-anchor)/wd
        dv60=(float(c12[0])-anchor)/wd
        dv120=(float(c24[0])-anchor)/wd

        te60=trend_eff(c12)
        dfrac=float((np.diff(c12)<0).mean())
        r30=float(w6.high.max()-w6.low.min())/wd
        r60=float(w12.high.max()-w12.low.min())/wd
        expand=r30/r60 if r60>1e-12 else 0.0

        sb=grouped[day]
        before=sb[sb.index<touch]
        if len(before)==0: raise RuntimeError("touch at session first bar unsupported")
        openp=float(r.session_open)
        sess_closes=before.close.to_numpy(float)
        sess_eff=trend_eff(np.r_[openp,sess_closes]) if len(sess_closes)>=3 else np.nan
        up_exc=max(0.0,float(before.high.max())-openp)/wd
        latency=float((touch-sb.index[0])/pd.Timedelta(minutes=1))

        rows.append({
          "signal_key":r.signal_key,"session_day":day,"year":int(r.year),"period":str(r.period),
          "first_touch_ts":touch,"detector_ts":det,
          "entry":float(r.detector_close),"wall":float(r.wall),"wall_distance":wd,
          "aligned180":float(r.aligned180),"label":"LOSER" if float(r.aligned180)<=0 else "WINNER",
          "down_velocity_30":dv30,
          "down_velocity_60":dv60,
          "down_velocity_120":dv120,
          "trend_eff_60":te60,
          "chop_60":1.0-te60 if np.isfinite(te60) else np.nan,
          "down_bar_fraction_60":dfrac,
          "range_30_norm":r30,
          "range_60_norm":r60,
          "range_expansion_30v60":expand,
          "return_vol_60":ret_vol(c12),
          "sign_flip_count_60":float(sign_flips(c12)),
          "touch_latency_min":latency,
          "session_down_efficiency":sess_eff,
          "session_up_excursion_norm":up_exc,
          "wall_distance_pct":wd/openp,
        })

    L=pd.DataFrame(rows)
    L["is_loser"]=L.label.eq("LOSER")
    for per,w,l in [("DEV",49,27),("REF",24,18)]:
        q=L[L.period==per]
        if int((~q.is_loser).sum())!=w or int(q.is_loser.sum())!=l:
            raise RuntimeError(f"{per} parity")

    dev=L[L.period=="DEV"]
    scales={f:fit_scale(dev[f]) for f in COMP}
    L["APPROACH_PRESSURE_COMPOSITE"]=sum(rz(L[f],scales[f]).to_numpy() for f in COMP)/len(COMP)

    allf=FEATURES+["APPROACH_PRESSURE_COMPOSITE"]
    audit=[]
    for f in allf:
        for per in ["DEV","REF","ALL"]:
            q=L if per=="ALL" else L[L.period==per]
            w=q[~q.is_loser][f].dropna(); lo=q[q.is_loser][f].dropna()
            audit.append({
              "feature":f,"period":per,
              "winner_n":len(w),"loser_n":len(lo),
              "winner_median":float(w.median()) if len(w) else np.nan,
              "loser_median":float(lo.median()) if len(lo) else np.nan,
              "failure_auc":auc_failure(q.is_loser,q[f])
            })
    A=pd.DataFrame(audit)

    noms=[]
    for f in allf:
        d=A[(A.feature==f)&(A.period=="DEV")].iloc[0]
        r=A[(A.feature==f)&(A.period=="REF")].iloc[0]
        devnom=bool(d.winner_n>=30 and d.loser_n>=20 and np.isfinite(d.failure_auc) and d.failure_auc>=.60)
        refval=bool(devnom and r.winner_n>=20 and r.loser_n>=15 and np.isfinite(r.failure_auc) and r.failure_auc>=.55)
        noms.append({
          "feature":f,"dev_nominated":devnom,"ref_validated":refval,
          "dev_auc":d.failure_auc,"ref_auc":r.failure_auc,
          "dev_winner_median":d.winner_median,"dev_loser_median":d.loser_median,
          "ref_winner_median":r.winner_median,"ref_loser_median":r.loser_median
        })
    N=pd.DataFrame(noms); V=N[N.ref_validated].copy()

    yearly=[]
    for y in [2022,2023,2024,2025,2026]:
        q=L[L.year==y]
        for f in allf:
            yearly.append({
              "year":y,"feature":f,
              "winner_n":int((~q.is_loser).sum()),"loser_n":int(q.is_loser.sum()),
              "failure_auc":auc_failure(q.is_loser,q[f]) if q.is_loser.any() and (~q.is_loser).any() else np.nan
            })
    Y=pd.DataFrame(yearly)

    status=("BNB_B41_S6I_L_APPROACH_HABITAT_PRECURSOR_FOUND" if len(V)
            else "BNB_B41_S6I_L_NO_STABLE_APPROACH_HABITAT_PRECURSOR")

    sig=hashlib.sha256(json.dumps({
      "parents":[S5_SIG,S6H_SIG],
      "information_set":"STRICTLY_PRE_FIRST_TOUCH_5M_APPROACH",
      "lookbacks_min":[30,60,120],
      "features":FEATURES,"composite":COMP,
      "dev_gate":{"winner_n":30,"loser_n":20,"auc":.60},
      "ref_gate":{"winner_n":20,"loser_n":15,"auc":.55},
      "generic_regime_retest":False,"no_filter_threshold":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_FeatureAudit.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    V.to_csv(ROOT/f"{PFX}_Validated.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
      f"PARENT_S5_SIGNATURE_SHA256={S5_SIG}\nPARENT_S6H_L_SIGNATURE_SHA256={S6H_SIG}\n"
      f"S6I_L_SIGNATURE_SHA256={sig}\nINFORMATION_SET=STRICTLY_PRE_FIRST_TOUCH_5M_APPROACH\n"
      "NO_GENERIC_REGIME_RETEST=TRUE\nNO_FILTER_THRESHOLD=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}"
    lines=[
      "# BNB B41-S6I-L — LONG Pre-Touch Approach Habitat Anatomy","",
      f"**Status: {status}**","",f"S6I-L signature: `{sig}`","",
      "Only completed 5m bars strictly before the first lower-Q80 touch are used. Generic regime/ATR/breadth families are intentionally not repeated.","",
      "## DEV nominations -> REF holdout","",
      "| Feature | DEV AUC | REF AUC | DEV W med | DEV L med | REF W med | REF L med | DEV nom | REF valid |",
      "|---|---:|---:|---:|---:|---:|---:|---|---|"
    ]
    for r in N.itertuples(index=False):
        lines.append(f"| {r.feature} | {num(r.dev_auc)} | {num(r.ref_auc)} | {num(r.dev_winner_median)} | "
                     f"{num(r.dev_loser_median)} | {num(r.ref_winner_median)} | {num(r.ref_loser_median)} | "
                     f"{'YES' if r.dev_nominated else 'NO'} | {'YES' if r.ref_validated else 'NO'} |")
    lines += ["","## Stable approach precursors",""]
    if len(V):
        for r in V.sort_values(["dev_auc","ref_auc"],ascending=False).itertuples(index=False):
            lines.append(f"- **{r.feature}** — DEV AUC {r.dev_auc:.3f}, REF AUC {r.ref_auc:.3f}.")
    else:
        lines.append("- None.")
    lines += ["","## Gate",
      f"- DEV nominees: **{int(N.dev_nominated.sum())}**.",
      f"- REF-validated approach precursors: **{len(V)}**.",
      f"- Next: **{'preregister entry-quality filter construction' if len(V) else 'do not filter LONG from this approach-habitat family'}**.",
      "",
      "No filter threshold, SL, TP, WR optimization, PF, expectancy, leverage, fees/slippage, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
