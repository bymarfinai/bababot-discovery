#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6D_L_TRIGGERED_LONG_RECOVERY_ANATOMY"
PARENT_SIG="75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f"
HORIZONS=[15,30,45,60]
CONT_HEALTH=["close_progress","mfe_from_alarm","recovery_ratio","up_slope_3","mae_from_alarm"]
BINARY=[
    "close_above_alarm","touch_reclaim_entry","close_reclaim_entry",
    "touch_reclaim_wall","close_reclaim_wall","close_break_pre15_high",
    "no_new_low_after_alarm"
]

def verify():
    txt=(ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Freeze.txt").read_text()
    if f"S6C_L_SIGNATURE_SHA256={PARENT_SIG}" not in txt:
        raise RuntimeError("S6C-L signature mismatch")

def auc(w,l):
    w=pd.Series(w).dropna().astype(float)
    l=pd.Series(l).dropna().astype(float)
    if len(w)==0 or len(l)==0:return np.nan
    x=pd.concat([l,w],ignore_index=True)
    ranks=x.rank(method="average")
    nw=len(w); nl=len(l)
    rw=float(ranks.iloc[nl:].sum())
    return float((rw-nw*(nw+1)/2)/(nw*nl))

def main():
    verify()
    C=pd.read_csv(
        ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Ledger.csv.gz",
        compression="gzip",parse_dates=["detector_ts","endpoint_ts"]
    )
    C=C[(C.candidate=="R4_60_2OF3_Q85")&(C.stop==True)].copy()
    if len(C)!=24: raise RuntimeError(f"R4 alarm parity {len(C)} !=24")
    dev=C[C.period=="DEV"]; ref=C[C.period=="REF"]
    if len(dev)!=14 or int(dev.baseline_winner.sum())!=6 or len(dev)-int(dev.baseline_winner.sum())!=8:
        raise RuntimeError("DEV alarm cohort parity mismatch")
    if len(ref)!=10 or int(ref.baseline_winner.sum())!=2 or len(ref)-int(ref.baseline_winner.sum())!=8:
        raise RuntimeError("REF alarm cohort parity mismatch")

    # Get wall level from frozen S5 market ledger.
    s5=pd.read_csv(
        ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
        compression="gzip",parse_dates=["detector_ts"]
    )
    s5=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")&
          (s5.valid180)][["signal_key","wall"]].copy()
    C=C.merge(s5,on="signal_key",how="left",validate="many_to_one")
    if C.wall.isna().any(): raise RuntimeError("missing wall")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["open","high","low","close"]].astype(float).sort_index()

    rows=[]
    for r in C.itertuples(index=False):
        det=pd.Timestamp(r.detector_ts)
        alarm=det+pd.Timedelta(minutes=60)
        if alarm not in k.index: raise RuntimeError(f"missing alarm bar {alarm}")
        alarm_bar=k.loc[alarm]
        alarm_close=float(alarm_bar.close)
        alarm_low=float(alarm_bar.low)
        entry=float(r.entry); wall=float(r.wall); wd=float(r.wall_distance)
        pre=k[(k.index>=alarm-pd.Timedelta(minutes=15))&(k.index<=alarm)]
        pre15_close_high=float(pre.close.max())
        cohort="FALSE_STOP_WINNER" if bool(r.baseline_winner) else "TRUE_FAILURE_LOSER"

        for h in HORIZONS:
            end=alarm+pd.Timedelta(minutes=h)
            if end not in k.index: raise RuntimeError(f"missing recovery snapshot {end}")
            z=k[(k.index>alarm)&(k.index<=end)]
            close=float(k.loc[end,"close"])
            hi=float(z.high.max()); lo=float(z.low.min())
            if len(z)>=4:
                up=(float(z.close.iloc[-1])-float(z.close.iloc[-4]))/wd
            elif len(z)>=2:
                up=(float(z.close.iloc[-1])-float(z.close.iloc[0]))/wd
            else: up=0.0
            denom=entry-alarm_close
            rr=(close-alarm_close)/denom if denom>1e-12 else np.nan
            rows.append({
                "signal_key":r.signal_key,"period":r.period,"year":int(r.year),
                "cohort":cohort,"horizon_min":h,
                "entry":entry,"wall":wall,"wall_distance":wd,
                "alarm_ts":alarm,"alarm_close":alarm_close,"alarm_low":alarm_low,
                "baseline_aligned180":float(r.baseline_aligned180),
                "close_progress":(close-alarm_close)/wd,
                "mfe_from_alarm":max(0.0,hi-alarm_close)/wd,
                "recovery_ratio":rr,
                "up_slope_3":up,
                "mae_from_alarm":max(0.0,alarm_close-lo)/wd,
                "close_above_alarm":bool(close>alarm_close),
                "touch_reclaim_entry":bool(hi>=entry),
                "close_reclaim_entry":bool(close>=entry),
                "touch_reclaim_wall":bool(hi>=wall),
                "close_reclaim_wall":bool(close>=wall),
                "close_break_pre15_high":bool(close>pre15_close_high),
                "no_new_low_after_alarm":bool(lo>=alarm_low),
            })
    L=pd.DataFrame(rows)

    effects=[]
    candidates=[]
    for h in HORIZONS:
        for per in ["DEV","REF"]:
            z=L[(L.horizon_min==h)&(L.period==per)]
            w=z[z.cohort=="FALSE_STOP_WINNER"]; l=z[z.cohort=="TRUE_FAILURE_LOSER"]
            for f in CONT_HEALTH:
                ws=w[f]; ls=l[f]
                if f=="mae_from_alarm":
                    a=auc(-ws,-ls)
                    wm=float(ws.median()) if len(ws) else np.nan
                    lm=float(ls.median()) if len(ls) else np.nan
                else:
                    a=auc(ws,ls)
                    wm=float(ws.median()) if len(ws) else np.nan
                    lm=float(ls.median()) if len(ls) else np.nan
                effects.append({
                    "horizon_min":h,"period":per,"feature":f,"kind":"CONT",
                    "winner_n":len(w),"loser_n":len(l),
                    "winner_value":wm,"loser_value":lm,"recovery_auc":a,
                    "winner_rate":np.nan,"loser_rate":np.nan,"rate_gap":np.nan
                })
            for f in BINARY:
                wr=float(w[f].mean()) if len(w) else np.nan
                lr=float(l[f].mean()) if len(l) else np.nan
                effects.append({
                    "horizon_min":h,"period":per,"feature":f,"kind":"BINARY",
                    "winner_n":len(w),"loser_n":len(l),
                    "winner_value":np.nan,"loser_value":np.nan,"recovery_auc":np.nan,
                    "winner_rate":wr,"loser_rate":lr,"rate_gap":wr-lr
                })
    E=pd.DataFrame(effects)

    for h in HORIZONS:
        for f in CONT_HEALTH+BINARY:
            d=E[(E.horizon_min==h)&(E.period=="DEV")&(E.feature==f)].iloc[0]
            r=E[(E.horizon_min==h)&(E.period=="REF")&(E.feature==f)].iloc[0]
            if d.kind=="CONT":
                devcand=bool(d.winner_n>=5 and d.loser_n>=8 and d.recovery_auc>=.70)
                refdir=bool(devcand and np.isfinite(r.recovery_auc) and r.recovery_auc>.50)
                ds=d.recovery_auc; rs=r.recovery_auc
            else:
                devcand=bool(d.winner_n>=5 and d.winner_rate>=.50 and d.loser_rate<=.25 and d.rate_gap>=.40)
                refdir=bool(devcand and r.winner_rate>r.loser_rate)
                ds=d.rate_gap; rs=r.rate_gap
            candidates.append({
                "horizon_min":h,"feature":f,"kind":d.kind,
                "dev_mechanism_candidate":devcand,
                "ref_directionally_consistent":refdir,
                "dev_strength":ds,"ref_strength":rs
            })
    N=pd.DataFrame(candidates)
    stable=N[N.dev_mechanism_candidate & N.ref_directionally_consistent].copy()
    status=("BNB_B41_S6D_L_RECOVERY_MECHANISM_CANDIDATE_FOUND"
            if len(stable) else
            "BNB_B41_S6D_L_NO_STABLE_RECOVERY_MECHANISM_FOUND")

    sig=hashlib.sha256(json.dumps({
        "parent":PARENT_SIG,"alarm":"R4_60_2OF3_Q85",
        "horizons_after_alarm":HORIZONS,
        "continuous":CONT_HEALTH,"binary":BINARY,
        "dev_binary":{"winner_rate_min":.50,"loser_rate_max":.25,"gap_min":.40,"winner_n":5,"loser_n":8},
        "dev_cont":{"auc_min":.70,"winner_n":5,"loser_n":8},
        "ref":"DIRECTIONAL_ONLY_SMALL_N",
        "no_exit_rule":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    E.to_csv(ROOT/f"{PFX}_Effects.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Candidates.csv",index=False)
    stable.to_csv(ROOT/f"{PFX}_Stable.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S6C_L_SIGNATURE_SHA256={PARENT_SIG}\nS6D_L_SIGNATURE_SHA256={sig}\n"
        "ALARM=R4_60_2OF3_Q85\nPOST_ALARM_HORIZONS=15,30,45,60\n"
        "REF_STATUS=DIRECTIONAL_ONLY_SMALL_N\nNO_EXIT_RULE=TRUE\n",
        encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}"
    lines=[
        "# BNB B41-S6D-L — Triggered LONG Recovery Anatomy","",
        f"**Status: {status}**","",f"S6D-L signature: `{sig}`","",
        "Cohort is frozen to R4_60_2OF3_Q85 alarms only. REF has only two false-stop winners, so REF is directional/descriptive rather than a promotion gate.","",
        "## DEV mechanism candidates","",
        "| After alarm | Feature | Kind | DEV strength | REF strength | REF direction consistent |",
        "|---:|---|---|---:|---:|---|"
    ]
    dd=N[N.dev_mechanism_candidate].sort_values(["horizon_min","feature"])
    if len(dd):
        for r in dd.itertuples(index=False):
            ds=pct(r.dev_strength) if r.kind=="BINARY" else num(r.dev_strength)
            rs=pct(r.ref_strength) if r.kind=="BINARY" else num(r.ref_strength)
            lines.append(f"| {r.horizon_min}m | {r.feature} | {r.kind} | {ds} | {rs} | {'YES' if r.ref_directionally_consistent else 'NO'} |")
    else:
        lines.append("| — | None | — | — | — | NO |")

    lines += ["","## Stable mechanism candidates","",
              "| After alarm | Feature | Kind | DEV | REF |",
              "|---:|---|---|---:|---:|"]
    if len(stable):
        for r in stable.sort_values(["horizon_min","feature"]).itertuples(index=False):
            ds=pct(r.dev_strength) if r.kind=="BINARY" else num(r.dev_strength)
            rs=pct(r.ref_strength) if r.kind=="BINARY" else num(r.ref_strength)
            lines.append(f"| {r.horizon_min}m | {r.feature} | {r.kind} | {ds} | {rs} |")
    else:
        lines.append("| — | None | — | — | — |")

    lines += ["","## Full cohort effects","",
              "| Period | After alarm | Feature | Kind | False-winner | True-loser | Recovery AUC / gap |",
              "|---|---:|---|---|---:|---:|---:|"]
    for r in E.itertuples(index=False):
        if r.kind=="BINARY":
            wv=pct(r.winner_rate); lv=pct(r.loser_rate); s=pct(r.rate_gap)
        else:
            wv=num(r.winner_value); lv=num(r.loser_value); s=num(r.recovery_auc)
        lines.append(f"| {r.period} | {r.horizon_min}m | {r.feature} | {r.kind} | {wv} | {lv} | {s} |")

    lines += ["","## Gate",
              f"- DEV mechanism candidates: **{int(N.dev_mechanism_candidate.sum())}**.",
              f"- REF-directionally-consistent candidates: **{len(stable)}**.",
              f"- Next step: **{'S6E-L preregistered recovery-test rule construction' if len(stable) else 'do not construct recovery rule yet'}**.",
              "",
              "No exit rule, EMA/Fibonacci, TP, WR optimization, PF, expectancy, leverage, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
