#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B41_S6E_L_LONG_RECOVERY_TEST_EXIT"
S6C_SIG="75fac38b1ff31e8fc29003ba87109c66ca6da27b9f011c68044aaee21546aa8f"
S6D_SIG="fc4ec7581c282e2f61f578df00ace715451381b92d15c82453d56f369e33281a"
POLICIES=[
    ("E1_45M_WALL_RECLAIM",45,"WALL"),
    ("E2_60M_POSITIVE_PROGRESS",60,"PROGRESS"),
]

def verify():
    a=(ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Freeze.txt").read_text()
    b=(ROOT/"results/bnb_b41_s6d_l/BNB_B41_S6D_L_TRIGGERED_LONG_RECOVERY_ANATOMY_Freeze.txt").read_text()
    if f"S6C_L_SIGNATURE_SHA256={S6C_SIG}" not in a: raise RuntimeError("S6C mismatch")
    if f"S6D_L_SIGNATURE_SHA256={S6D_SIG}" not in b: raise RuntimeError("S6D mismatch")

def stats(z):
    bw=z[z.baseline_winner]
    bl=z[~z.baseline_winner]
    fs=bw[bw.stop]
    lc=bl[bl.stop].copy()
    if len(lc): lc["improvement"]=lc.managed_outcome-lc.baseline_aligned180

    aw=z[z.alarm & z.baseline_winner]
    al=z[z.alarm & ~z.baseline_winner]
    preserved=int((~aw.stop).sum())
    caught=int(al.stop.sum())

    return {
        "n180":len(z),
        "baseline_wins":len(bw),"baseline_losers":len(bl),
        "baseline_mean":float(z.baseline_aligned180.mean()),
        "baseline_median":float(z.baseline_aligned180.median()),
        "baseline_q10":float(z.baseline_aligned180.quantile(.10)),
        "alarm_n":int(z.alarm.sum()),
        "alarm_winners":len(aw),"alarm_losers":len(al),
        "stop_n":int(z.stop.sum()),
        "stop_rate":float(z.stop.mean()),
        "false_stop_winners":len(fs),
        "false_stop_rate":len(fs)/len(bw) if len(bw) else np.nan,
        "overall_loser_catch":len(lc)/len(bl) if len(bl) else np.nan,
        "alarm_winner_preservation":preserved/len(aw) if len(aw) else np.nan,
        "alarm_loser_catch":caught/len(al) if len(al) else np.nan,
        "median_loser_improvement":float(lc.improvement.median()) if len(lc) else np.nan,
        "mean_outcome":float(z.managed_outcome.mean()),
        "median_outcome":float(z.managed_outcome.median()),
        "q10_outcome":float(z.managed_outcome.quantile(.10)),
        "positive_rate":float((z.managed_outcome>0).mean()),
        "median_stop_outcome":float(z.loc[z.stop,"managed_outcome"].median()) if z.stop.any() else np.nan,
    }

def main():
    verify()
    C=pd.read_csv(
        ROOT/"results/bnb_b41_s6c_l/BNB_B41_S6C_L_LONG_CAUSAL_INVALIDATION_Ledger.csv.gz",
        compression="gzip",parse_dates=["detector_ts","endpoint_ts"]
    )
    C=C[C.candidate=="R4_60_2OF3_Q85"].copy()
    if len(C)!=118: raise RuntimeError(f"R4 parity {len(C)} !=118")

    # S6C 'stop' is the +60m alarm, not final S6E exit.
    C=C.rename(columns={"stop":"alarm"})
    if int(C.alarm.sum())!=24: raise RuntimeError("alarm count mismatch")

    s5=pd.read_csv(
        ROOT/"results/bnb_b41_s5/BNB_B41_S5_ENTRY_GEOMETRY_DISCOVERY_Ledger.csv.gz",
        compression="gzip",parse_dates=["detector_ts"]
    )
    s5=s5[(s5.candidate=="E0_MARKET")&(s5.side=="LOWER")&(s5.direction=="LONG")&(s5.tf=="TF60")&
          (s5.valid180)][["signal_key","wall"]]
    C=C.merge(s5,on="signal_key",how="left",validate="one_to_one")

    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    k=raw[["close"]].astype(float).sort_index()

    ledgers=[]
    for name,wait,kind in POLICIES:
        z=C.copy()
        stops=[]; recs=[]; exits=[]; managed=[]
        for r in z.itertuples(index=False):
            if not bool(r.alarm):
                stops.append(False); recs.append(False); exits.append(np.nan)
                managed.append(float(r.baseline_aligned180)); continue
            det=pd.Timestamp(r.detector_ts)
            alarm_ts=det+pd.Timedelta(minutes=60)
            check_ts=alarm_ts+pd.Timedelta(minutes=wait)
            if alarm_ts not in k.index or check_ts not in k.index:
                raise RuntimeError(f"missing bar {alarm_ts} / {check_ts}")
            alarm_close=float(k.loc[alarm_ts,"close"])
            check_close=float(k.loc[check_ts,"close"])
            if kind=="WALL":
                recovered=bool(check_close>=float(r.wall))
            elif kind=="PROGRESS":
                recovered=bool(check_close>alarm_close)
            else: raise RuntimeError(kind)
            stop=not recovered
            out=(check_close-float(r.entry))/float(r.wall_distance) if stop else float(r.baseline_aligned180)
            stops.append(stop); recs.append(recovered); exits.append(check_close if stop else np.nan); managed.append(out)
        z["policy"]=name
        z["recovery_wait_min"]=wait
        z["recovered"]=recs
        z["stop"]=stops
        z["exit_price"]=exits
        z["managed_outcome"]=managed
        ledgers.append(z)
    L=pd.concat(ledgers,ignore_index=True)

    rows=[]
    for per in ["DEV","REF","ALL"]:
        p=L if per=="ALL" else L[L.period==per]
        for name,_,_ in POLICIES:
            rows.append({"period":per,"policy":name,**stats(p[p.policy==name])})
    A=pd.DataFrame(rows)

    def eligible(r,min_n):
        return bool(
            r.n180>=min_n and r.false_stop_rate<=.10 and
            r.alarm_winner_preservation>=.80 and r.alarm_loser_catch>=.50 and
            np.isfinite(r.median_loser_improvement) and r.median_loser_improvement>0 and
            r.mean_outcome>=r.baseline_mean and r.q10_outcome>r.baseline_q10
        )

    D=A[A.period=="DEV"].copy()
    D["eligible"]=D.apply(lambda r: eligible(r,30),axis=1)
    if D.eligible.any():
        order={n:i for i,(n,_,_) in enumerate(POLICIES)}
        d=D[D.eligible].copy()
        d["priority"]=d.policy.map(order)
        nominee=str(d.sort_values("priority").iloc[0].policy)
        rr=A[(A.period=="REF")&(A.policy==nominee)].iloc[0]
        ref_ok=eligible(rr,20)
    else:
        nominee="NO_NOMINATION"; ref_ok=False

    status=("BNB_B41_S6E_L_LONG_RECOVERY_INVALIDATION_READY"
            if ref_ok else
            "BNB_B41_S6E_L_LONG_RECOVERY_INVALIDATION_NOT_READY")

    yearly=[]
    if nominee!="NO_NOMINATION":
        for y in [2022,2023,2024,2025,2026]:
            q=L[(L.policy==nominee)&(L.year==y)]
            if len(q): yearly.append({"year":y,**stats(q)})
    Y=pd.DataFrame(yearly)

    sig=hashlib.sha256(json.dumps({
        "parents":[S6C_SIG,S6D_SIG],"alarm":"R4_60_2OF3_Q85",
        "policies":[p[0] for p in POLICIES],
        "E1":"alarm+45m close>=Q80 wall => hold else exit",
        "E2":"alarm+60m close>alarm close => hold else exit",
        "dev_gate":{"false_stop_max":.10,"alarm_winner_preserve_min":.80,
                    "alarm_loser_catch_min":.50,"loser_improve":">0",
                    "mean":">=baseline","q10":">baseline"},
        "selection":"EARLIEST_FIXED_POLICY",
        "ref_gate":"SAME","no_tp":True
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    L.to_csv(ROOT/f"{PFX}_Ledger.csv.gz",index=False,compression="gzip")
    A.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    D.to_csv(ROOT/f"{PFX}_DEV_Eligibility.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_NomineeByYear.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"PARENT_S6C_L_SIGNATURE_SHA256={S6C_SIG}\nPARENT_S6D_L_SIGNATURE_SHA256={S6D_SIG}\n"
        f"S6E_L_SIGNATURE_SHA256={sig}\nNOMINEE={nominee}\nREF_VALIDATED={'TRUE' if ref_ok else 'FALSE'}\n"
        "ALARM=R4_60_2OF3_Q85\nNO_TP=TRUE\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n",encoding="utf-8")

    def pct(x): return "—" if not np.isfinite(x) else f"{100*x:.1f}%"
    def num(x): return "—" if not np.isfinite(x) else f"{x:.3f}x"
    lines=[
        "# BNB B41-S6E-L — LONG Recovery-Test Exit Rule","",
        f"**Status: {status}**","",f"S6E-L signature: `{sig}`","",
        "The +60m 2-of-3 signal is treated as an alarm. Only failed recovery exits; recovered alarms hold to detector+180m.","",
        "## Policy audit","",
        "| Period | Policy | Alarms W/L | Exits | False-stop | Alarm winner preserved | Alarm loser caught | Med loser improve | Mean Δ | q10 Δ | Positive |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in A.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.policy} | {r.alarm_winners}/{r.alarm_losers} | {r.stop_n} | "
            f"{r.false_stop_winners}/{r.baseline_wins} ({pct(r.false_stop_rate)}) | "
            f"{pct(r.alarm_winner_preservation)} | {pct(r.alarm_loser_catch)} | "
            f"{num(r.median_loser_improvement)} | {num(r.mean_outcome-r.baseline_mean)} | "
            f"{num(r.q10_outcome-r.baseline_q10)} | {pct(r.positive_rate)} |"
        )
    lines += ["","## DEV gate","",
              "| Policy | Eligible |","|---|---|"]
    for r in D.itertuples(index=False):
        lines.append(f"| {r.policy} | {'YES' if r.eligible else 'NO'} |")
    lines += ["","## Nomination",
              f"- DEV nominee: **{nominee}**.",
              f"- REF validated: **{'YES' if ref_ok else 'NO'}**.",
              f"- LONG recovery invalidation: **{'READY' if ref_ok else 'NOT READY'}**.",
              "",
              "No TP, WR optimization, PF, expectancy, leverage, fees/slippage optimization, or PnL optimization."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
