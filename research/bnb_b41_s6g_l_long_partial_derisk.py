#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd
import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6G_L_LONG_PARTIAL_DERISK"
S6C_SIG="75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f"
S6E_SIG="953f2a9a1a721fbe0c8fcefcaa73feb4470ae72e7407b9e4cb14aab4f4b7a5e8"
S6F_SIG="d62c788c66afee53a9c6d09fb0fb9e4b5f00d96caa22bafc5c3a34b53e0d2ed4"
POLICIES=[
 ("P25_ALARM",.25,False),
 ("P50_ALARM",.50,False),
 ("P75_ALARM",.75,False),
 ("P25_ALARM_P25_FAILREC",.25,True),
]

def verify():
    a=(ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6e_l/BNB_B41_S6E_L_LONG_RECOVERY_TEST_EXIT_Freeze.txt").read_text()
    c=(ROOT/"results/bnb_b41_s6f_l/BNB_B41_S6F_L_FAILED_RECOVERY_EXIT_PATH_ANATOMY_Freeze.txt").read_text()
    if f"S6C_L_SIGNATURE_SHA256={S6C_SIG}" not in a: raise RuntimeError("S6C mismatch")
    if f"S6E_L_SIGNATURE_SHA256={S6E_SIG}" not in b: raise RuntimeError("S6E mismatch")
    if f"S6F_L_SIGNATURE_SHA256={S6F_SIG}" not in c: raise RuntimeError("S6F mismatch")

def safe_ratio(qimp,mdelta):
    if not np.isfinite(qimp) or not np.isfinite(mdelta): return np.nan
    if mdelta>=0: return np.inf
    return qimp/abs(mdelta) if abs(mdelta)>1e-12 else np.inf

def summarize(z):
    bw=z[z.baseline_winner]; bl=z[~z.baseline_winner]
    aw=z[z.alarm & z.baseline_winner]; al=z[z.alarm & ~z.baseline_winner]
    base_mean=float(z.baseline_aligned180.mean())
    managed_mean=float(z.managed_outcome.mean())
    base_q10=float(z.baseline_aligned180.quantile(.10))
    managed_q10=float(z.managed_outcome.quantile(.10))
    base_pos=float((z.baseline_aligned180>0).mean())
    managed_pos=float((z.managed_outcome>0).mean())
    return {
      "n180":len(z),
      "baseline_mean":base_mean,"managed_mean":managed_mean,"mean_delta":managed_mean-base_mean,
      "baseline_median":float(z.baseline_aligned180.median()),
      "managed_median":float(z.managed_outcome.median()),
      "baseline_q10":base_q10,"managed_q10":managed_q10,"q10_delta":managed_q10-base_q10,
      "baseline_positive_rate":base_pos,"managed_positive_rate":managed_pos,
      "winner_n":len(bw),
      "baseline_winner_mean":float(bw.baseline_aligned180.mean()) if len(bw) else np.nan,
      "managed_winner_mean":float(bw.managed_outcome.mean()) if len(bw) else np.nan,
      "winner_mean_retention":float(bw.managed_outcome.mean()/bw.baseline_aligned180.mean()) if len(bw) and bw.baseline_aligned180.mean()!=0 else np.nan,
      "baseline_winner_median":float(bw.baseline_aligned180.median()) if len(bw) else np.nan,
      "managed_winner_median":float(bw.managed_outcome.median()) if len(bw) else np.nan,
      "loser_n":len(bl),
      "baseline_loser_mean":float(bl.baseline_aligned180.mean()) if len(bl) else np.nan,
      "managed_loser_mean":float(bl.managed_outcome.mean()) if len(bl) else np.nan,
      "loser_mean_improvement":float(bl.managed_outcome.mean()-bl.baseline_aligned180.mean()) if len(bl) else np.nan,
      "baseline_loser_median":float(bl.baseline_aligned180.median()) if len(bl) else np.nan,
      "managed_loser_median":float(bl.managed_outcome.median()) if len(bl) else np.nan,
      "alarm_n":int(z.alarm.sum()),"alarm_winners":len(aw),"alarm_losers":len(al),
      "alarm_winner_mean_retention":float(aw.managed_outcome.mean()/aw.baseline_aligned180.mean()) if len(aw) and aw.baseline_aligned180.mean()!=0 else np.nan,
      "alarm_loser_mean_improvement":float(al.managed_outcome.mean()-al.baseline_aligned180.mean()) if len(al) else np.nan,
      "tail_efficiency":safe_ratio(managed_q10-base_q10,managed_mean-base_mean),
    }

def eligible(r,min_n):
    return bool(
      r.n180>=min_n and
      r.managed_mean>=.95*r.baseline_mean and
      r.winner_mean_retention>=.95 and
      r.managed_positive_rate>=r.baseline_positive_rate-.02 and
      r.managed_q10>r.baseline_q10 and
      r.managed_loser_mean>r.baseline_loser_mean and
      (r.mean_delta>=0 or r.tail_efficiency>=1.0)
    )

def main():
    verify()
    C=pd.read_csv(ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Ledger.csv.gz",
                  compression="gzip",parse_dates=["detector_ts","endpoint_ts"])
    C=C[C.candidate=="R4_60_2OF3_Q85"].copy()
    if len(C)!=118: raise RuntimeError(f"R4 parity {len(C)} !=118")
    C=C.rename(columns={"stop":"alarm"})
    if int(C.alarm.sum())!=24: raise RuntimeError("alarm parity")

    s5=pd.read_csv(ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
                   compression="gzip")
    s5=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")&
          (s5.valid180)][["signal_key","wall"]]
    C=C.merge(s5,on="signal_key",how="left",validate="one_to_one")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["close"]].astype(float).sort_index()

    alarm_out=[]; fail_out=[]; failrec=[]
    for r in C.itertuples(index=False):
        det=pd.Timestamp(r.detector_ts)
        a=det+pd.Timedelta(minutes=60)
        f=det+pd.Timedelta(minutes=105)
        if a not in k.index or f not in k.index: raise RuntimeError("missing checkpoint")
        ao=(float(k.loc[a,"close"])-float(r.entry))/float(r.wall_distance)
        fo=(float(k.loc[f,"close"])-float(r.entry))/float(r.wall_distance)
        alarm_out.append(ao); fail_out.append(fo)
        failrec.append(bool(r.alarm and float(k.loc[f,"close"])<float(r.wall)))
    C["alarm_outcome"]=alarm_out
    C["failrec_outcome"]=fail_out
    C["failed_recovery"]=failrec

    ledgers=[]
    for name,frac,staged in POLICIES:
        z=C.copy()
        vals=[]
        for r in z.itertuples(index=False):
            base=float(r.baseline_aligned180)
            if not bool(r.alarm):
                vals.append(base); continue
            if not staged:
                vals.append(frac*float(r.alarm_outcome)+(1-frac)*base)
            else:
                # 25% at alarm; optional 25% original at failed recovery; rest to endpoint.
                if bool(r.failed_recovery):
                    vals.append(.25*float(r.alarm_outcome)+.25*float(r.failrec_outcome)+.50*base)
                else:
                    vals.append(.25*float(r.alarm_outcome)+.75*base)
        z["policy"]=name
        z["managed_outcome"]=vals
        ledgers.append(z)
    L=pd.concat(ledgers,ignore_index=True)

    rows=[]
    for per in ["DEV","REF","ALL"]:
        p=L if per=="ALL" else L[L.period==per]
        for name,_,_ in POLICIES:
            rows.append({"period":per,"policy":name,**summarize(p[p.policy==name])})
    A=pd.DataFrame(rows)

    D=A[A.period=="DEV"].copy()
    D["eligible"]=D.apply(lambda r:eligible(r,30),axis=1)
    if D.eligible.any():
        order={n:i for i,(n,_,_) in enumerate(POLICIES)}
        dd=D[D.eligible].copy(); dd["priority"]=dd.policy.map(order)
        nominee=str(dd.sort_values("priority").iloc[0].policy)
        rr=A[(A.period=="REF")&(A.policy==nominee)].iloc[0]
        ref_ok=eligible(rr,20)
    else:
        nominee="NO_NOMINATION"; ref_ok=False

    status=("BNB_B41_S6G_L_LONG_PARTIAL_DERISK_READY" if ref_ok
            else "BNB_B41_S6G_L_LONG_PARTIAL_DERISK_NOT_READY")

    yearly=[]
    if nominee!="NO_NOMINATION":
        for y in [2022,2023,2024,2025,2026]:
            q=L[(L.policy==nominee)&(L.year==y)]
            if len(q): yearly.append({"year":y,**summarize(q)})
    Y=pd.DataFrame(yearly)

    sig=hashlib.sha256(json.dumps({
      "parents":[S6C_SIG,S6E_SIG,S6F_SIG],"alarm":"R4_60_2OF3_Q85",
      "policies":[p[0] for p in POLICIES],
      "fractions":{"P25":.25,"P50":.50,"P75":.75,"staged":[.25,.25,.50]},
      "dev_gate":{"mean_retention":.95,"winner_mean_retention":.95,"positive_rate_tolerance_pp":2,
                  "q10":">baseline","loser_mean":">baseline","tail_efficiency_min":1.0},
      "selection":"SMALLEST_FIXED_DERISK_ACTION","ref_gate":"SAME","no_tp":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    D.to_csv(ROOT/f"{PFX}_DEV_Eligibility.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_NomineeByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
      f"PARENT_S6C_L_SIGNATURE_SHA256={S6C_SIG}\nPARENT_S6E_L_SIGNATURE_SHA256={S6E_SIG}\n"
      f"PARENT_S6F_L_SIGNATURE_SHA256={S6F_SIG}\nS6G_L_SIGNATURE_SHA256={sig}\n"
      f"NOMINEE={nominee}\nREF_VALIDATED={'TRUE' if ref_ok else 'FALSE'}\n"
      "ALARM=R4_60_2OF3_Q85\nNO_TP=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"
    lines=[
      "# BNB B41-S6G-L — LONG Partial De-Risk","",
      f"**Status: {status}**","",f"S6G-L signature: `{sig}`","",
      "The frozen +60m failure state is used only to reduce exposure. No new alarm/SL/TP is searched.","",
      "## Policy audit","",
      "| Period | Policy | Mean Δ | Mean retained | q10 Δ | Positive Δ | Winner mean retained | Loser mean improve | Alarm winner retained | Alarm loser improve | Tail efficiency |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        meanret=r.managed_mean/r.baseline_mean if r.baseline_mean!=0 else np.nan
        lines.append(f"| {r.period} | {r.policy} | {num(r.mean_delta)} | {pct(meanret)} | {num(r.q10_delta)} | "
                     f"{pct(r.managed_positive_rate-r.baseline_positive_rate)} | {pct(r.winner_mean_retention)} | "
                     f"{num(r.loser_mean_improvement)} | {pct(r.alarm_winner_mean_retention)} | "
                     f"{num(r.alarm_loser_mean_improvement)} | {('∞' if np.isinf(r.tail_efficiency) else num(r.tail_efficiency))} |")
    lines += ["","## DEV gate","",
              "| Policy | Eligible |","|---|---|"]
    for r in D.itertuples(index=False):
        lines.append(f"| {r.policy} | {'YES' if r.eligible else 'NO'} |")
    lines += ["","## Nomination",
              f"- DEV nominee: **{nominee}**.",
              f"- REF validated: **{'YES' if ref_ok else 'NO'}**.",
              f"- LONG partial de-risk gate: **{'READY' if ref_ok else 'NOT READY'}**.",
              "",
              "No TP, PF, expectancy, leverage, fee/slippage optimization, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
