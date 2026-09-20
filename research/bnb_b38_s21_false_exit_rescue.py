#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b38_s14_post_tp1_continuation as s14
import bnb_b38_s18_wide_sl_structural_invalidation as s18
import bnb_b38_s20_post_entry_failure_character as s20

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B38_S21_FALSE_EXIT_RESCUE"
EXPECTED_SIGNATURE="d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267"
WIDE_CUT=0.017122292197580727

RECOVERY_STATES=[
    "NEXT5_RECLAIM",
    "NEXT15_RECLAIM",
    "RECLAIM_HOLD",
    "RECLAIM_FAILURE_HIGH_BREAK",
    "RECLAIM_BREAK_LEVEL",
]

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def maxdd(rs):
    if not len(rs): return np.nan
    c=np.cumsum(np.asarray(rs,float))
    p=np.maximum.accumulate(np.concatenate([[0.0],c]))[:-1]
    return float(np.max(p-c))

def bar_resolution(raw5, ts, sl, tp):
    if ts not in raw5.index:
        return False
    b=raw5.loc[ts]
    return bool(float(b.high)>=tp or float(b.low)<=sl)

def segment_has_resolution(raw5,start_ts,end_ts,sl,tp):
    idx=raw5.index
    i0=int(idx.searchsorted(start_ts,side="right"))
    i1=int(idx.searchsorted(end_ts,side="right"))
    if i1<=i0:return False
    seg=raw5.iloc[i0:i1]
    return bool((seg.high>=tp).any() or (seg.low<=sl).any())

def recovery_eval(raw5,m15,r,end):
    idx=raw5.index
    sig_ts=pd.Timestamp(r.failure_ts)
    resolution_ts=pd.Timestamp(r.baseline_resolution_ts)
    i_sig=int(idx.get_loc(sig_ts))
    risk=float(r.entry_price-r.structural_sl)

    failure_high=float(raw5.loc[sig_ts,"high"])
    out={}

    # NEXT5_RECLAIM
    j=i_sig+1
    if j>=len(idx) or idx[j]>resolution_ts:
        out["NEXT5_RECLAIM"]={"status":"PREEMPTED","recovery":False,"decision_ts":resolution_ts,"decision_close":np.nan}
    else:
        t=idx[j]
        if bar_resolution(raw5,t,float(r.structural_sl),float(r.tp1)):
            out["NEXT5_RECLAIM"]={"status":"PREEMPTED","recovery":False,"decision_ts":t,"decision_close":np.nan}
        else:
            cl=float(raw5.close.iloc[j])
            rec=cl>=float(r.reclaim_close)
            out["NEXT5_RECLAIM"]={"status":"RECOVERY" if rec else "FAIL","recovery":rec,"decision_ts":t,"decision_close":cl}

    # NEXT15_RECLAIM
    midx=m15.index
    mi=int(midx.searchsorted(sig_ts,side="right"))
    if mi>=len(midx) or midx[mi]>resolution_ts:
        out["NEXT15_RECLAIM"]={"status":"PREEMPTED","recovery":False,"decision_ts":resolution_ts,"decision_close":np.nan}
    else:
        t=midx[mi]
        if segment_has_resolution(raw5,sig_ts,t,float(r.structural_sl),float(r.tp1)):
            out["NEXT15_RECLAIM"]={"status":"PREEMPTED","recovery":False,"decision_ts":t,"decision_close":np.nan}
        else:
            cl=float(m15.close.iloc[mi])
            rec=cl>=float(r.reclaim_close)
            out["NEXT15_RECLAIM"]={"status":"RECOVERY" if rec else "FAIL","recovery":rec,"decision_ts":t,"decision_close":cl}

    # Discovery-only structural recovery scans until frozen baseline resolution.
    i_end=int(idx.searchsorted(resolution_ts,side="left"))
    reclaim_i=None
    reclaim_ts=pd.NaT
    reclaim_adverse=np.nan
    run_min=float(raw5.low.iloc[i_sig])
    for i in range(i_sig+1,min(i_end+1,len(idx))):
        t=idx[i]
        if t>=resolution_ts: break
        run_min=min(run_min,float(raw5.low.iloc[i]))
        if reclaim_i is None and float(raw5.close.iloc[i])>=float(r.reclaim_close):
            reclaim_i=i; reclaim_ts=t; reclaim_adverse=(run_min-float(r.entry_price))/risk
            break

    # RECLAIM_HOLD
    if reclaim_i is None:
        out["RECLAIM_HOLD"]={"status":"NO_RECOVERY","recovery":False,"decision_ts":pd.NaT,"decision_close":np.nan}
    else:
        k=reclaim_i+1
        if k<len(idx) and idx[k]<resolution_ts and not bar_resolution(raw5,idx[k],float(r.structural_sl),float(r.tp1)):
            rec=float(raw5.close.iloc[k])>=float(r.reclaim_close)
            out["RECLAIM_HOLD"]={"status":"RECOVERY" if rec else "FAIL_AFTER_RECLAIM","recovery":rec,
                                  "decision_ts":idx[k],"decision_close":float(raw5.close.iloc[k])}
        else:
            out["RECLAIM_HOLD"]={"status":"PREEMPTED_AFTER_RECLAIM","recovery":False,
                                  "decision_ts":resolution_ts,"decision_close":np.nan}

    # RECLAIM_FAILURE_HIGH_BREAK
    rec=False; dt=pd.NaT; dc=np.nan
    if reclaim_i is not None:
        for i in range(reclaim_i+1,min(i_end+1,len(idx))):
            t=idx[i]
            if t>=resolution_ts: break
            if float(raw5.close.iloc[i])>failure_high:
                rec=True; dt=t; dc=float(raw5.close.iloc[i]); break
    out["RECLAIM_FAILURE_HIGH_BREAK"]={"status":"RECOVERY" if rec else "NO_RECOVERY","recovery":rec,
                                        "decision_ts":dt,"decision_close":dc}

    # RECLAIM_BREAK_LEVEL
    rec=False; dt=pd.NaT; dc=np.nan
    for i in range(i_sig+1,min(i_end+1,len(idx))):
        t=idx[i]
        if t>=resolution_ts: break
        if float(raw5.close.iloc[i])>float(r.break_level):
            rec=True; dt=t; dc=float(raw5.close.iloc[i]); break
    out["RECLAIM_BREAK_LEVEL"]={"status":"RECOVERY" if rec else "NO_RECOVERY","recovery":rec,
                                 "decision_ts":dt,"decision_close":dc}

    # Attach common timing / adverse metrics to each state when recovery occurs.
    for name,z in out.items():
        if z["recovery"] and pd.notna(z["decision_ts"]):
            dts=pd.Timestamp(z["decision_ts"])
            i1=int(idx.searchsorted(dts,side="right"))
            seg=raw5.iloc[i_sig:i1]
            mn=float(seg.low.min()) if len(seg) else np.nan
            z["minutes_to_recovery"]=float((dts-sig_ts)/pd.Timedelta(minutes=1))
            z["adverse_r_to_recovery"]=(mn-float(r.entry_price))/risk if np.isfinite(mn) else np.nan
            z["minutes_recovery_to_resolution"]=float((resolution_ts-dts)/pd.Timedelta(minutes=1))
        else:
            z["minutes_to_recovery"]=np.nan
            z["adverse_r_to_recovery"]=np.nan
            z["minutes_recovery_to_resolution"]=np.nan
    return out

def separator_summary(q):
    wins=q[q.baseline_outcome=="WIN"]
    losses=q[q.baseline_outcome=="LOSS"]
    rec=q[q.recovery]
    recw=rec[rec.baseline_outcome=="WIN"]
    recl=rec[rec.baseline_outcome=="LOSS"]
    return {
        "n":len(q),"wins":len(wins),"losses":len(losses),
        "recoveries":len(rec),
        "winner_recovered":len(recw),
        "winner_recovery_rate":len(recw)/len(wins) if len(wins) else np.nan,
        "loss_leaked":len(recl),
        "loss_leak_rate":len(recl)/len(losses) if len(losses) else np.nan,
        "recovery_precision_win":len(recw)/len(rec) if len(rec) else np.nan,
        "median_minutes_recovery_win":float(recw.minutes_to_recovery.median()) if len(recw) else np.nan,
        "median_minutes_recovery_loss":float(recl.minutes_to_recovery.median()) if len(recl) else np.nan,
        "median_adverse_r_win":float(recw.adverse_r_to_recovery.median()) if len(recw) else np.nan,
        "median_adverse_r_loss":float(recl.adverse_r_to_recovery.median()) if len(recl) else np.nan,
        "median_recovery_to_resolution_win":float(recw.minutes_recovery_to_resolution.median()) if len(recw) else np.nan,
        "median_recovery_to_resolution_loss":float(recl.minutes_recovery_to_resolution.median()) if len(recl) else np.nan,
    }

def policy_score(trigger_q,state):
    # Executable only for NEXT5/NEXT15:
    # recovery => restore frozen baseline; fail => exit at decision close;
    # preempted => frozen baseline resolved before decision.
    vals=[]
    for r in trigger_q[trigger_q.state==state].itertuples(index=False):
        if r.status=="RECOVERY" or r.status=="PREEMPTED":
            rr=float(r.baseline_realized_r)
        elif r.status=="FAIL":
            rr=(float(r.decision_close)-float(r.entry_price))/float(r.entry_price-r.structural_sl)
        else:
            # unexpected state for fixed-horizon policies: conservative baseline
            rr=float(r.baseline_realized_r)
        vals.append({"zone_id":r.zone_id,"period":r.period,"year":r.year,"policy_r":rr,
                     "baseline_outcome":r.baseline_outcome})
    return pd.DataFrame(vals)

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    raw5,m15,h1,P,sig=s14.build_frozen(raw,end)
    if sig!=EXPECTED_SIGNATURE: raise RuntimeError(f"signature drift {sig}")

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=pd.Timestamp("2022-01-01T00:00:00Z"))&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    F=fam.set_index("zone_id")

    structs=[]
    for r in P.itertuples(index=False):
        fr=F.loc[r.zone_id]
        rec=s18.reconstruct_e2(m15,fr,end)
        if rec is None or pd.Timestamp(rec["entry_ts"])!=pd.Timestamp(r.entry_ts):
            raise RuntimeError(f"E2 reconstruction drift {r.zone_id}")
        structs.append({
            "zone_id":r.zone_id,
            "reclaim_close":float(m15.close.iloc[rec["reclaim_i"]]),
            "break_level":max(float(m15.high.iloc[rec["reclaim_i"]]),float(rec["hold_high"])),
        })
    P=P.merge(pd.DataFrame(structs),on="zone_id",how="left",validate="one_to_one")
    P["baseline_sl_pct"]=(P.entry_price-P.touch_low_sl)/P.entry_price
    Q=P[P.baseline_sl_pct>WIDE_CUT].copy()
    if int((Q.period=="DEV").sum())!=110 or int((Q.period=="REF").sum())!=50:
        raise RuntimeError("Q4 parity drift")

    # Exact S20 clean failure trigger population.
    trig=[]
    for r in Q.itertuples(index=False):
        z=s20.eval_5m_signal(raw5,r.entry_ts,float(r.entry_price),float(r.touch_low_sl),
                             float(r.tp1),float(r.reclaim_close),"CLOSE_BELOW",end)
        if z["signal_status"]!="CLEAN_SIGNAL":
            continue
        risk=float(r.entry_price-r.touch_low_sl)
        trig.append({
            "zone_id":r.zone_id,"period":r.period,"year":r.year,"entry_ts":r.entry_ts,
            "entry_price":float(r.entry_price),"structural_sl":float(r.touch_low_sl),"tp1":float(r.tp1),
            "reclaim_close":float(r.reclaim_close),"break_level":float(r.break_level),
            "failure_ts":z["signal_ts"],"failure_close":float(z["exit_price"]),
            "failure_r":(float(z["exit_price"])-float(r.entry_price))/risk,
            "baseline_outcome":r.baseline_outcome,
            "baseline_realized_r":float(r.baseline_realized_r),
            "baseline_resolution_ts":r.baseline_resolution_ts,
        })
    T=pd.DataFrame(trig)
    if int((T.period=="DEV").sum())!=31 or int((T.period=="REF").sum())!=8:
        raise RuntimeError(f"trigger parity drift DEV={sum(T.period=='DEV')} REF={sum(T.period=='REF')}")
    if int(((T.period=="DEV")&(T.baseline_outcome=="LOSS")).sum())!=21 or int(((T.period=="DEV")&(T.baseline_outcome=="WIN")).sum())!=10:
        raise RuntimeError("DEV label parity drift")
    if int(((T.period=="REF")&(T.baseline_outcome=="LOSS")).sum())!=6 or int(((T.period=="REF")&(T.baseline_outcome=="WIN")).sum())!=2:
        raise RuntimeError("REF label parity drift")

    rows=[]
    for r in T.itertuples(index=False):
        ev=recovery_eval(raw5,m15,r,end)
        for state,z in ev.items():
            rows.append({
                **r._asdict(),"state":state,"status":z["status"],"recovery":bool(z["recovery"]),
                "decision_ts":z["decision_ts"],"decision_close":z["decision_close"],
                "minutes_to_recovery":z["minutes_to_recovery"],
                "adverse_r_to_recovery":z["adverse_r_to_recovery"],
                "minutes_recovery_to_resolution":z["minutes_recovery_to_resolution"],
            })
    L=pd.DataFrame(rows)

    S=[]
    for per in ["DEV","REF"]:
        for state in RECOVERY_STATES:
            q=L[(L.period==per)&(L.state==state)]
            S.append({"period":per,"state":state,**separator_summary(q)})
    S=pd.DataFrame(S)

    # Fixed-horizon executable rescue policies.
    polrows=[]
    for state in ["NEXT5_RECLAIM","NEXT15_RECLAIM"]:
        pol=policy_score(L,state)
        for per in ["DEV","REF"]:
            q=pol[pol.period==per]
            if len(q):
                polrows.append({
                    "period":per,"policy":state,"trigger_n":len(q),
                    "trigger_total_r":float(q.policy_r.sum()),
                    "trigger_expectancy_r":float(q.policy_r.mean()),
                    "trigger_positive":int((q.policy_r>0).sum()),
                    "trigger_negative":int((q.policy_r<0).sum()),
                })
    POL=pd.DataFrame(polrows)

    # Full E2 portfolio comparison: baseline, S20 immediate Q4 exit, and fixed rescue policies.
    port=[]
    for per in ["DEV","REF"]:
        full=P[P.period==per].copy()
        trigp=T[T.period==per].set_index("zone_id")
        policy_maps={}
        for state in ["NEXT5_RECLAIM","NEXT15_RECLAIM"]:
            pp=policy_score(L[L.period==per],state)
            policy_maps[state]=pp.set_index("zone_id").policy_r.to_dict()

        configs=["BASELINE","S20_IMMEDIATE_EXIT","NEXT5_RESCUE","NEXT15_RESCUE"]
        for cfg in configs:
            vals=[]
            for r in full.itertuples(index=False):
                if r.zone_id not in trigp.index:
                    vals.append(float(r.baseline_realized_r)); continue
                tr=trigp.loc[r.zone_id]
                if cfg=="BASELINE":
                    vals.append(float(r.baseline_realized_r))
                elif cfg=="S20_IMMEDIATE_EXIT":
                    vals.append(float(tr.failure_r))
                elif cfg=="NEXT5_RESCUE":
                    vals.append(float(policy_maps["NEXT5_RECLAIM"][r.zone_id]))
                elif cfg=="NEXT15_RESCUE":
                    vals.append(float(policy_maps["NEXT15_RECLAIM"][r.zone_id]))
            a=np.asarray(vals,float)
            port.append({
                "period":per,"config":cfg,"trades":len(a),
                "total_r":float(a.sum()),"expectancy_r":float(a.mean()),
                "positive_r":int((a>0).sum()),"negative_r":int((a<0).sum()),
                "max_dd_r":maxdd(a.tolist()),
            })
    PORT=pd.DataFrame(port)

    # Annual separator stability.
    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        for state in RECOVERY_STATES:
            q=L[(L.year==y)&(L.state==state)]
            if len(q): Y.append({"year":y,"state":state,**separator_summary(q)})
    Y=pd.DataFrame(Y)

    T.to_csv(ROOT/f"{PFX}_TriggerPopulation.csv",index=False)
    L.to_csv(ROOT/f"{PFX}_RecoveryLedger.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    POL.to_csv(ROOT/f"{PFX}_FixedPolicy.csv",index=False)
    PORT.to_csv(ROOT/f"{PFX}_Portfolio.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"E2_FROZEN=TRUE\nPLAN_SIGNATURE_SHA256={sig}\nWIDE_CUT={WIDE_CUT:.18f}\n"
        "FAILURE_TRIGGER=CLOSE5_BELOW_RECLAIM_CLOSE\nDEV_TRIGGER=31\nDEV_LOSS=21\nDEV_WIN=10\n"
        "REF_TRIGGER=8\nREF_LOSS=6\nREF_WIN=2\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B38-S21 — False-Exit Winner Rescue","",
        "Population is frozen S20 Q4-wide clean failure triggers only.","",
        "## Recovery separator audit","",
        "| Period | Recovery state | Winner recovered | Loss leaked | Precision(win) | Med recovery time WIN | Med recovery time LOSS | Adverse R WIN | Adverse R LOSS |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in S.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.state} | {r.winner_recovered}/{r.wins} ({fmt_pct(r.winner_recovery_rate)}) | "
            f"{r.loss_leaked}/{r.losses} ({fmt_pct(r.loss_leak_rate)}) | {fmt_pct(r.recovery_precision_win)} | "
            f"{fmt_num(r.median_minutes_recovery_win,1)}m | {fmt_num(r.median_minutes_recovery_loss,1)}m | "
            f"{fmt_num(r.median_adverse_r_win)}R | {fmt_num(r.median_adverse_r_loss)}R |"
        )

    lines += ["","## Fixed-horizon executable rescue policies","",
        "| Period | Policy | Trigger N | Positive/Negative | Trigger Exp | Trigger Total R |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in POL.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.trigger_n} | {r.trigger_positive}/{r.trigger_negative} | "
            f"{fmt_num(r.trigger_expectancy_r)}R | {fmt_num(r.trigger_total_r)}R |"
        )

    lines += ["","## Full E2 portfolio comparison","",
        "| Period | Config | Positive/Negative | Exp | Total R | Max DD |",
        "|---|---|---:|---:|---:|---:|"
    ]
    for r in PORT.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.config} | {r.positive_r}/{r.negative_r} | "
            f"{fmt_num(r.expectancy_r)}R | {fmt_num(r.total_r)}R | {fmt_num(r.max_dd_r)}R |"
        )

    lines += ["","## Annual recovery stability","",
        "| Year | State | Winner recovered | Loss leaked | Precision(win) |",
        "|---:|---|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.state} | {r.winner_recovered}/{r.wins} ({fmt_pct(r.winner_recovery_rate)}) | "
            f"{r.loss_leaked}/{r.losses} ({fmt_pct(r.loss_leak_rate)}) | {fmt_pct(r.recovery_precision_win)} |"
        )

    lines += ["","## Stop rule",
      "This is the only false-exit rescue discovery round.",
      "If recovery separation is not consistent in DEV and REF, no further rescue tuning is allowed before expansion-character discovery."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B38_S21_FALSE_EXIT_RESCUE_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
