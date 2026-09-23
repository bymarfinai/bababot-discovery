#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6F_L_FAILED_RECOVERY_EXIT_PATH_ANATOMY"
S6D_SIG="fc4ec7581c282e2f61f578df00ace715451381b92d15c82453d56f369e33281a"
S6E_SIG="953f2a9a1a721fbe0c8fcefcaa73feb4470ae72e7407b9e4cb14aab4f4b7a5e8"
HORIZONS=[5,10,15,30,45,60]
PROBES=["FIRST_CLOSE_ABOVE_FAILURE_30","FIRST_WALL_TOUCH_60","FIRST_WALL_CLOSE_60"]

def verify():
    a=(ROOT/"results/bnb_b41_s6d_l/BNB_B41_S6D_L_TRIGGERED_LONG_RECOVERY_ANATOMY_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6e_l/BNB_B41_S6E_L_LONG_RECOVERY_TEST_EXIT_Freeze.txt").read_text()
    if f"S6D_L_SIGNATURE_SHA256={S6D_SIG}" not in a: raise RuntimeError("S6D mismatch")
    if f"S6E_L_SIGNATURE_SHA256={S6E_SIG}" not in b: raise RuntimeError("S6E mismatch")

def med(x):
    s=pd.Series(x).dropna()
    return float(s.median()) if len(s) else np.nan

def main():
    verify()
    E=pd.read_csv(
        ROOT/"results/bnb_b41_s6e_l/BNB_B41_S6E_L_LONG_RECOVERY_TEST_EXIT_Ledger.csv.gz",
        compression="gzip",parse_dates=["detector_ts","endpoint_ts"]
    )
    q=E[(E.policy=="E1_45M_WALL_RECLAIM")&(E.stop==True)].copy()
    if len(q)!=14: raise RuntimeError(f"failed-recovery parity {len(q)} !=14")
    d=q[q.period=="DEV"]; r=q[q.period=="REF"]
    if len(d)!=7 or int(d.baseline_winner.sum())!=1 or len(r)!=7 or int(r.baseline_winner.sum())!=0:
        raise RuntimeError("cohort composition mismatch")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["open","high","low","close"]].astype(float).sort_index()

    rows=[]; probe_rows=[]; full_rows=[]
    for x in q.itertuples(index=False):
        det=pd.Timestamp(x.detector_ts)
        fail_ts=det+pd.Timedelta(minutes=105)
        end_ts=det+pd.Timedelta(minutes=180)
        if fail_ts not in k.index or end_ts not in k.index:
            raise RuntimeError("missing anchor")
        fail_close=float(k.loc[fail_ts,"close"])
        entry=float(x.entry); wall=float(x.wall); wd=float(x.wall_distance)
        immediate=(fail_close-entry)/wd
        baseline=float(x.baseline_aligned180)
        label="BASELINE_WINNER" if bool(x.baseline_winner) else "BASELINE_LOSER"

        for h in HORIZONS:
            ts=fail_ts+pd.Timedelta(minutes=h)
            if ts not in k.index: raise RuntimeError(f"missing checkpoint {ts}")
            z=k[(k.index>fail_ts)&(k.index<=ts)]
            c=float(k.loc[ts,"close"])
            out=(c-entry)/wd
            rows.append({
                "signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "horizon_min":h,"failure_ts":fail_ts,"entry":entry,"wall":wall,"wall_distance":wd,
                "failure_close":fail_close,"immediate_outcome":immediate,"baseline_outcome":baseline,
                "close_delta_from_failure":(c-fail_close)/wd,
                "mfe_from_failure":max(0.0,float(z.high.max())-fail_close)/wd,
                "mae_from_failure":max(0.0,fail_close-float(z.low.min()))/wd,
                "wait_outcome":out,
                "wait_improve_vs_immediate":out-immediate,
                "wait_improve_vs_endpoint":out-baseline,
                "close_above_failure":bool(c>fail_close),
                "touch_wall_after_failure":bool(float(z.high.max())>=wall),
                "close_wall_after_failure":bool((z.close>=wall).any()),
            })

        rem=k[(k.index>fail_ts)&(k.index<=end_ts)]
        above=rem[rem.close>fail_close]
        walltouch=rem[rem.high>=wall]
        wallclose=rem[rem.close>=wall]
        full_rows.append({
            "signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
            "mfe75":max(0.0,float(rem.high.max())-fail_close)/wd,
            "mae75":max(0.0,fail_close-float(rem.low.min()))/wd,
            "first_close_above_failure_min": float((above.index[0]-fail_ts)/pd.Timedelta(minutes=1)) if len(above) else np.nan,
            "first_wall_touch_min": float((walltouch.index[0]-fail_ts)/pd.Timedelta(minutes=1)) if len(walltouch) else np.nan,
            "first_wall_close_min": float((wallclose.index[0]-fail_ts)/pd.Timedelta(minutes=1)) if len(wallclose) else np.nan,
        })

        # Probe A
        a=rem[(rem.index<=fail_ts+pd.Timedelta(minutes=30)) & (rem.close>fail_close)]
        if len(a):
            ts=a.index[0]; px=float(a.iloc[0].close); outcome=(px-entry)/wd
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_CLOSE_ABOVE_FAILURE_30","filled":True,"event_min":float((ts-fail_ts)/pd.Timedelta(minutes=1)),
                "exit_price":px,"outcome":outcome,"improve_vs_immediate":outcome-immediate,"improve_vs_endpoint":outcome-baseline})
        else:
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_CLOSE_ABOVE_FAILURE_30","filled":False,"event_min":np.nan,
                "exit_price":np.nan,"outcome":np.nan,"improve_vs_immediate":np.nan,"improve_vs_endpoint":np.nan})

        # Probe B
        b=rem[(rem.index<=fail_ts+pd.Timedelta(minutes=60)) & (rem.high>=wall)]
        if len(b):
            ts=b.index[0]; px=wall; outcome=(px-entry)/wd
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_WALL_TOUCH_60","filled":True,"event_min":float((ts-fail_ts)/pd.Timedelta(minutes=1)),
                "exit_price":px,"outcome":outcome,"improve_vs_immediate":outcome-immediate,"improve_vs_endpoint":outcome-baseline})
        else:
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_WALL_TOUCH_60","filled":False,"event_min":np.nan,
                "exit_price":np.nan,"outcome":np.nan,"improve_vs_immediate":np.nan,"improve_vs_endpoint":np.nan})

        # Probe C
        c=rem[(rem.index<=fail_ts+pd.Timedelta(minutes=60)) & (rem.close>=wall)]
        if len(c):
            ts=c.index[0]; px=float(c.iloc[0].close); outcome=(px-entry)/wd
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_WALL_CLOSE_60","filled":True,"event_min":float((ts-fail_ts)/pd.Timedelta(minutes=1)),
                "exit_price":px,"outcome":outcome,"improve_vs_immediate":outcome-immediate,"improve_vs_endpoint":outcome-baseline})
        else:
            probe_rows.append({"signal_key":x.signal_key,"period":x.period,"year":int(x.year),"label":label,
                "probe":"FIRST_WALL_CLOSE_60","filled":False,"event_min":np.nan,
                "exit_price":np.nan,"outcome":np.nan,"improve_vs_immediate":np.nan,"improve_vs_endpoint":np.nan})

    L=pd.DataFrame(rows); P=pd.DataFrame(probe_rows); F=pd.DataFrame(full_rows)

    effects=[]; candidates=[]
    for h in HORIZONS:
        for per in ["DEV","REF","ALL"]:
            z=L[(L.horizon_min==h)&(L.label=="BASELINE_LOSER")]
            if per!="ALL": z=z[z.period==per]
            effects.append({
                "type":"FIXED_WAIT","name":f"WAIT_{h}M","period":per,"n":len(z),
                "fill_rate":1.0 if len(z) else np.nan,
                "median_improve_immediate":med(z.wait_improve_vs_immediate),
                "positive_improve_immediate":float((z.wait_improve_vs_immediate>0).mean()) if len(z) else np.nan,
                "median_improve_endpoint":med(z.wait_improve_vs_endpoint),
                "median_event_min":float(h),
            })
    for probe in PROBES:
        for per in ["DEV","REF","ALL"]:
            z=P[(P.probe==probe)&(P.label=="BASELINE_LOSER")]
            if per!="ALL": z=z[z.period==per]
            f=z[z.filled]
            effects.append({
                "type":"PROBE","name":probe,"period":per,"n":len(z),
                "fill_rate":float(z.filled.mean()) if len(z) else np.nan,
                "median_improve_immediate":med(f.improve_vs_immediate),
                "positive_improve_immediate":float((f.improve_vs_immediate>0).mean()) if len(f) else np.nan,
                "median_improve_endpoint":med(f.improve_vs_endpoint),
                "median_event_min":med(f.event_min),
            })
    A=pd.DataFrame(effects)

    for typ,name in [(r.type,r.name) for r in A[A.period=="DEV"].itertuples(index=False)]:
        d=A[(A.period=="DEV")&(A.type==typ)&(A.name==name)].iloc[0]
        r=A[(A.period=="REF")&(A.type==typ)&(A.name==name)].iloc[0]
        if typ=="FIXED_WAIT":
            devcand=bool(d.n>=6 and d.median_improve_immediate>0 and
                         d.positive_improve_immediate>=.50 and d.median_improve_endpoint>0)
            refdir=bool(devcand and r.n>=6 and r.median_improve_immediate>0 and r.median_improve_endpoint>0)
        else:
            devcand=bool(d.n>=6 and d.fill_rate>=.50 and d.median_improve_immediate>0 and d.median_improve_endpoint>0)
            refdir=bool(devcand and r.n>=6 and r.fill_rate>=.40 and
                        r.median_improve_immediate>0 and r.median_improve_endpoint>0)
        candidates.append({"type":typ,"name":name,"dev_bounce_candidate":devcand,
                           "ref_directionally_consistent":refdir,
                           "dev_fill_rate":d.fill_rate,"ref_fill_rate":r.fill_rate,
                           "dev_improve_immediate":d.median_improve_immediate,
                           "ref_improve_immediate":r.median_improve_immediate,
                           "dev_improve_endpoint":d.median_improve_endpoint,
                           "ref_improve_endpoint":r.median_improve_endpoint})
    N=pd.DataFrame(candidates)
    stable=N[N.dev_bounce_candidate & N.ref_directionally_consistent].copy()
    status=("BNB_B41_S6F_L_FAILED_RECOVERY_BOUNCE_MECHANISM_FOUND" if len(stable)
            else "BNB_B41_S6F_L_NO_STABLE_FAILED_RECOVERY_BOUNCE_MECHANISM")

    sig=hashlib.sha256(json.dumps({
        "parents":[S6D_SIG,S6E_SIG],"cohort":"E1_45M_WALL_RECLAIM_FAILED_ONLY",
        "horizons":HORIZONS,"probes":PROBES,
        "dev_fixed":{"n":6,"median_vs_immediate":">0","positive_frac":.50,"median_vs_endpoint":">0"},
        "dev_probe":{"n":6,"fill":.50,"median_vs_immediate":">0","median_vs_endpoint":">0"},
        "ref":"DIRECTIONAL_ONLY","no_exit_rule":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_CheckpointLedger.csv.gz",index=False,compression="gzip")
    P.to_csv(ROOT/f"{PFX}_ProbeLedger.csv.gz",index=False,compression="gzip")
    F.to_csv(ROOT/f"{PFX}_FullPath.csv",index=False)
    A.to_csv(ROOT/f"{PFX}_Effects.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Candidates.csv",index=False)
    stable.to_csv(ROOT/f"{PFX}_Stable.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S6D_L_SIGNATURE_SHA256={S6D_SIG}\nPARENT_S6E_L_SIGNATURE_SHA256={S6E_SIG}\n"
        f"S6F_L_SIGNATURE_SHA256={sig}\nCOHORT=E1_FAILED_RECOVERY_ONLY\n"
        "CHECKPOINTS=5,10,15,30,45,60\nNO_EXIT_RULE=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"
    lines=[
        "# BNB B41-S6F-L — Failed-Recovery Exit Path Anatomy","",
        f"**Status: {status}**","",f"S6F-L signature: `{sig}`","",
        "Cohort is frozen to E1_45M_WALL_RECLAIM failures. S6F-L studies executable post-failure bounce opportunities; it does not create an exit rule.","",
        "## Failed-recovery cohort",
        f"- DEV: {len(d)} total failed recoveries, {int((d.baseline_winner==False).sum())} baseline losers, {int(d.baseline_winner.sum())} baseline winner.",
        f"- REF: {len(r)} total failed recoveries, {int((r.baseline_winner==False).sum())} baseline losers, {int(r.baseline_winner.sum())} baseline winners.","",
        "## Baseline-loser exit-path audit","",
        "| Type | Probe/checkpoint | Period | N | Fill | Med improve vs immediate | > immediate | Med improve vs endpoint | Event min |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|"
    ]
    for x in A.itertuples(index=False):
        lines.append(f"| {x.type} | {x.name} | {x.period} | {x.n} | {pct(x.fill_rate)} | "
                     f"{num(x.median_improve_immediate)} | {pct(x.positive_improve_immediate)} | "
                     f"{num(x.median_improve_endpoint)} | {num(x.median_event_min)} |")
    lines += ["","## DEV bounce candidates","",
              "| Type | Candidate | DEV fill | REF fill | DEV vs immediate | REF vs immediate | DEV vs endpoint | REF vs endpoint | REF consistent |",
              "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    cc=N[N.dev_bounce_candidate]
    if len(cc):
        for x in cc.itertuples(index=False):
            lines.append(f"| {x.type} | {x.name} | {pct(x.dev_fill_rate)} | {pct(x.ref_fill_rate)} | "
                         f"{num(x.dev_improve_immediate)} | {num(x.ref_improve_immediate)} | "
                         f"{num(x.dev_improve_endpoint)} | {num(x.ref_improve_endpoint)} | "
                         f"{'YES' if x.ref_directionally_consistent else 'NO'} |")
    else:
        lines.append("| — | None | — | — | — | — | — | — | NO |")
    lines += ["","## Stable mechanisms",""]
    if len(stable):
        for x in stable.itertuples(index=False):
            lines.append(f"- **{x.name}** ({x.type})")
    else:
        lines.append("- None.")
    lines += ["","## Gate",
              f"- DEV bounce candidates: **{int(N.dev_bounce_candidate.sum())}**.",
              f"- REF-directionally-consistent: **{len(stable)}**.",
              f"- Next step: **{'S6G-L preregistered exit-timing rule' if len(stable) else 'do not add a post-failure bounce exit rule'}**.",
              "",
              "No TP, EMA/Fibonacci, leverage, PF, expectancy, fees/slippage optimization, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
