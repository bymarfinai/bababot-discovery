#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math, hashlib, json
import numpy as np
import pandas as pd

import bnb_b31_s1_swing_structure_library as b31
import bnb_b38_s1_lower_tf_demand_rebound as s1
import bnb_b39_s1_real_expansion_universe as s39
import bnb_b39_s3_early_reaction_character as s3

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B39_S4_FIRST5_EXPANSION_DETECTOR"
START=pd.Timestamp("2022-01-01T00:00:00Z")
DEV_END=pd.Timestamp("2024-12-31T23:59:59Z")
D1_CUT=0.20335748322474653
B15_CUT=0.2591007864238388

DETECTOR_SPEC={
    "name":"D1_FIRST5_DISPLACEMENT",
    "decision":"PLUS5_CLOSE",
    "eligibility":"B39-S3 PLUS5 ELIGIBLE",
    "feature":"p5_close_r",
    "op":">",
    "cut":D1_CUT,
    "parent":"B39-S1 real expansion universe",
}
DETECTOR_SIGNATURE=hashlib.sha256(
    json.dumps(DETECTOR_SPEC,sort_keys=True,separators=(",",":")).encode()
).hexdigest()

def period(ts):
    return "DEV" if pd.Timestamp(ts)<=DEV_END else "REF"

def fmt_pct(x):
    return "—" if not np.isfinite(x) else f"{100*x:.1f}%"

def fmt_num(x,d=3):
    return "—" if not np.isfinite(x) else f"{x:.{d}f}"

def wilson(k,n,z=1.959963984540054):
    if n<=0: return (np.nan,np.nan)
    p=k/n
    den=1+z*z/n
    centre=(p+z*z/(2*n))/den
    half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return centre-half,centre+half

def outcome_row(raw5,r,end):
    z=s3.label_outcomes(raw5,r,end)
    if z is None: return None
    p2=s39.threshold_probe(raw5,r.first_touch_ts,float(r.touch_close),float(r.demand_low),end,2.0,hours=24)
    return {
        **z,
        "GE2R":bool(p2["reached"]),
    }

def build_ledger(raw5,m15,h1,fam,end):
    rows=[]
    for r in fam.itertuples(index=False):
        out=outcome_row(raw5,r,end)
        if out is None: continue
        inh=s3.inherited_features(m15,h1,r)
        if inh is None: continue
        tf=s3.touch_features(r)
        anchor=float(out["anchor_price"]); risk=float(out["event_risk"])

        st5,dt5,b5=s3.decision_scan(raw5,r.first_touch_ts,anchor,float(r.demand_low),1)
        rec5={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "decision":"PLUS5_CLOSE","decision_status":st5,"decision_ts":dt5,
            "first_touch_ts":r.first_touch_ts,
            "anchor_price":anchor,"event_risk":risk,"demand_low":float(r.demand_low),
            **out,**inh,**tf
        }
        if len(b5)>=1:
            rec5.update(s3.plus5_features(b5,r,anchor,risk))
        rows.append(rec5)

        st15,dt15,b15=s3.decision_scan(raw5,r.first_touch_ts,anchor,float(r.demand_low),3)
        rec15={
            "zone_id":r.zone_id,"period":r.period,"year":int(r.year),
            "decision":"PLUS15_CLOSE","decision_status":st15,"decision_ts":dt15,
            "first_touch_ts":r.first_touch_ts,
            "anchor_price":anchor,"event_risk":risk,"demand_low":float(r.demand_low),
            **out,**inh,**tf
        }
        if len(b15)>=1:
            rec15.update(s3.plus5_features(b15.iloc[:1],r,anchor,risk))
        if len(b15)>=3:
            rec15.update(s3.plus15_features(b15,r,anchor,risk))
        rows.append(rec15)
    return pd.DataFrame(rows)

def metrics(q,whole_ge1r,too_fast_win,feature,cut):
    elig=q[q.decision_status=="ELIGIBLE"].copy()
    elig["signal"]=pd.to_numeric(elig[feature],errors="coerce")>cut
    sig=elig[elig.signal].copy()
    base_ge1=int(elig.GE1R.sum())
    tp=int(sig.GE1R.sum())
    fp=len(sig)-tp
    lo,hi=wilson(tp,len(sig))
    out={
        "eligible":len(elig),
        "eligible_ge1r":base_ge1,
        "eligible_base_rate":float(elig.GE1R.mean()) if len(elig) else np.nan,
        "signals":len(sig),
        "signal_rate":len(sig)/len(elig) if len(elig) else np.nan,
        "ge1r_tp":tp,
        "ge1r_fp":fp,
        "ge1r_rate":tp/len(sig) if len(sig) else np.nan,
        "ge1r_wilson_lo":lo,
        "ge1r_wilson_hi":hi,
        "ge1_5r":int(sig.GE1_5R.sum()),
        "ge1_5r_rate":float(sig.GE1_5R.mean()) if len(sig) else np.nan,
        "ge2r":int(sig.GE2R.sum()),
        "ge2r_rate":float(sig.GE2R.mean()) if len(sig) else np.nan,
        "clean1r":int(sig.CLEAN1R.sum()),
        "clean1r_rate":float(sig.CLEAN1R.mean()) if len(sig) else np.nan,
        "clean1_5r":int(sig.CLEAN1_5R.sum()),
        "clean1_5r_rate":float(sig.CLEAN1_5R.mean()) if len(sig) else np.nan,
        "winner_retention_unresolved":tp/base_ge1 if base_ge1 else np.nan,
        "whole_ge1r":whole_ge1r,
        "whole_ge1r_capture":tp/whole_ge1r if whole_ge1r else np.nan,
        "too_fast_win":too_fast_win,
        "uplift_pp":100*((tp/len(sig))-(base_ge1/len(elig))) if len(sig) and len(elig) else np.nan,
        "relative_lift":(tp/len(sig))/(base_ge1/len(elig)) if len(sig) and base_ge1 and len(elig) else np.nan,
    }
    return out,sig

def main():
    raw,diag=b31.load_raw()
    if diag["coverage"]<.995: raise RuntimeError(diag)
    a1=b31.load_a1(); ident=b31.identity(raw,a1)
    if ident["max_ret15_diff"]>5e-8 or ident["max_close_location_diff"]>5e-8:
        raise RuntimeError(ident)

    end=raw.index.max()
    s1.START=START; s1.END=end
    h1=s1.exact_exec(raw,"1h",12); h1=h1[h1.index<=end].copy()
    m15=s1.exact_exec(raw,"15min",3); m15=m15[m15.index<=end].copy()
    raw5=raw[["open","high","low","close"]].astype(float)

    zones=s1.demand_zones(h1)
    fam=s1.visual_family(m15,zones)
    fam=fam[
        (pd.to_datetime(fam.first_touch_ts,utc=True)>=START)&
        (pd.to_datetime(fam.first_touch_ts,utc=True)<=end)
    ].copy()
    fam["period"]=[period(x) for x in fam.first_touch_ts]
    fam["year"]=pd.to_datetime(fam.first_touch_ts,utc=True).dt.year
    if int((fam.period=="DEV").sum())!=788 or int((fam.period=="REF").sum())!=463:
        raise RuntimeError("parent parity drift")

    L=build_ledger(raw5,m15,h1,fam,end)
    p5=L[L.decision=="PLUS5_CLOSE"]
    if len(p5)!=1248 or int((p5.period=="DEV").sum())!=785 or int((p5.period=="REF").sum())!=463:
        raise RuntimeError("normalizable parity drift")
    expected={("DEV","GE1R"):375,("REF","GE1R"):241}
    for (per,lab),n in expected.items():
        got=int(p5.loc[p5.period==per,lab].sum())
        if got!=n: raise RuntimeError(f"label parity drift {per} {lab} {got}!={n}")

    # Frozen S3 decision-census parity.
    census_expected={
        ("PLUS5_CLOSE","DEV"):(604,58,78,45),
        ("PLUS5_CLOSE","REF"):(369,34,37,23),
        ("PLUS15_CLOSE","DEV"):(498,107,135,45),
        ("PLUS15_CLOSE","REF"):(309,70,61,23),
    }
    for (dec,per),(eligible,tw,tf,amb) in census_expected.items():
        q=L[(L.decision==dec)&(L.period==per)]
        got=(
            int((q.decision_status=="ELIGIBLE").sum()),
            int((q.decision_status=="TOO_FAST_WIN").sum()),
            int((q.decision_status=="TOO_FAST_FAIL").sum()),
            int((q.decision_status=="AMBIGUOUS_RESOLUTION").sum())
        )
        if got!=(eligible,tw,tf,amb):
            raise RuntimeError(f"S3 census parity drift {dec} {per}: {got}")

    SUM=[]; signal_ledgers=[]
    whole={"DEV":375,"REF":241}
    tf5={"DEV":58,"REF":34}
    for per in ["DEV","REF"]:
        q=L[(L.decision=="PLUS5_CLOSE")&(L.period==per)]
        m,sig=metrics(q,whole[per],tf5[per],"p5_close_r",D1_CUT)
        SUM.append({"detector":"D1_FIRST5_DISPLACEMENT","period":per,**m})
        sig=sig.copy()
        sig["detector"]="D1_FIRST5_DISPLACEMENT"
        signal_ledgers.append(sig)

    # Frozen +15m latency benchmark, not promotable.
    tf15={"DEV":107,"REF":70}
    for per in ["DEV","REF"]:
        q=L[(L.decision=="PLUS15_CLOSE")&(L.period==per)]
        m,sig=metrics(q,whole[per],tf15[per],"p15_close_r",B15_CUT)
        SUM.append({"detector":"B15_DISPLACEMENT_BENCHMARK","period":per,**m})
        sig=sig.copy()
        sig["detector"]="B15_DISPLACEMENT_BENCHMARK"
        signal_ledgers.append(sig)

    SUM=pd.DataFrame(SUM)
    SIG=pd.concat(signal_ledgers,ignore_index=True)

    # Hard parity with frozen S3 Q4 observations.
    hard={
        ("D1_FIRST5_DISPLACEMENT","DEV"):(151,108),
        ("D1_FIRST5_DISPLACEMENT","REF"):(101,83),
        ("B15_DISPLACEMENT_BENCHMARK","DEV"):(125,101),
        ("B15_DISPLACEMENT_BENCHMARK","REF"):(80,64),
    }
    for (det,per),(sn,tp) in hard.items():
        r=SUM[(SUM.detector==det)&(SUM.period==per)].iloc[0]
        if int(r.signals)!=sn or int(r.ge1r_tp)!=tp:
            raise RuntimeError(f"frozen Q4 parity drift {det} {per}: {r.signals}/{r.ge1r_tp}")

    # Year-by-year for D1 only.
    Y=[]
    for y in [2022,2023,2024,2025,2026]:
        q=L[(L.decision=="PLUS5_CLOSE")&(L.year==y)]
        whole_y=int(q.GE1R.sum())
        tf_y=int((q.decision_status=="TOO_FAST_WIN").sum())
        m,_=metrics(q,whole_y,tf_y,"p5_close_r",D1_CUT)
        Y.append({"year":y,**m})
    Y=pd.DataFrame(Y)

    # Signal-entry lateness diagnostics.
    D=[]
    for per in ["DEV","REF"]:
        q=SIG[(SIG.detector=="D1_FIRST5_DISPLACEMENT")&(SIG.period==per)].copy()
        # p5_close_r = displacement from anchor in original event-R.
        q["remaining_to_anchor_1r_event_r"]=1.0-q.p5_close_r
        q["structural_risk_from_signal_event_r"]=1.0+q.p5_close_r
        q["implied_reward_risk"]=q.remaining_to_anchor_1r_event_r/q.structural_risk_from_signal_event_r
        D.append({
            "period":per,"signals":len(q),
            "median_signal_displacement_event_r":float(q.p5_close_r.median()),
            "q25_signal_displacement_event_r":float(q.p5_close_r.quantile(.25)),
            "q75_signal_displacement_event_r":float(q.p5_close_r.quantile(.75)),
            "median_remaining_reward_event_r":float(q.remaining_to_anchor_1r_event_r.median()),
            "median_structural_risk_event_r":float(q.structural_risk_from_signal_event_r.median()),
            "median_implied_reward_risk":float(q.implied_reward_risk.median()),
            "q25_implied_reward_risk":float(q.implied_reward_risk.quantile(.25)),
            "q75_implied_reward_risk":float(q.implied_reward_risk.quantile(.75)),
        })
    D=pd.DataFrame(D)

    L.to_csv(ROOT/f"{PFX}_DecisionLedger.csv.gz",index=False,compression="gzip")
    SIG.to_csv(ROOT/f"{PFX}_SignalLedger.csv.gz",index=False,compression="gzip")
    SUM.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    D.to_csv(ROOT/f"{PFX}_EntryLateness.csv",index=False)
    (ROOT/f"{PFX}_Freeze.txt").write_text(
        f"DETECTOR=D1_FIRST5_DISPLACEMENT\nDETECTOR_SIGNATURE_SHA256={DETECTOR_SIGNATURE}\n"
        f"D1_P5_CLOSE_R_GT={D1_CUT:.17f}\n"
        f"B15_BENCHMARK_P15_CLOSE_R_GT={B15_CUT:.16f}\n"
        "PARENT=B39_S1_REAL_EXPANSION_UNIVERSE\n"
        "DECISION=FIRST_RAW5_CLOSE_STRICTLY_AFTER_TOUCH_CLOSE\n",
        encoding="utf-8"
    )

    lines=[
        "# BNB B39-S4 — Frozen First-5m Expansion Detector Validation","",
        f"Detector signature: `{DETECTOR_SIGNATURE}`",
        f"Frozen D1: `p5_close_r > {D1_CUT:.17f}`","",
        "## Detector validation","",
        "| Detector | Period | Eligible | Signals | GE1R | Base | Uplift | Rel lift | 95% Wilson | >=1.5R | >=2R | Clean1R | Winner retention | Whole GE1R capture | Too-fast win |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in SUM.itertuples(index=False):
        lines.append(
            f"| {r.detector} | {r.period} | {r.eligible} | {r.signals} ({fmt_pct(r.signal_rate)}) | "
            f"{r.ge1r_tp}/{r.signals} ({fmt_pct(r.ge1r_rate)}) | {fmt_pct(r.eligible_base_rate)} | "
            f"{fmt_num(r.uplift_pp,1)}pp | {fmt_num(r.relative_lift,2)}x | "
            f"{fmt_pct(r.ge1r_wilson_lo)}–{fmt_pct(r.ge1r_wilson_hi)} | "
            f"{r.ge1_5r}/{r.signals} ({fmt_pct(r.ge1_5r_rate)}) | "
            f"{r.ge2r}/{r.signals} ({fmt_pct(r.ge2r_rate)}) | "
            f"{r.clean1r}/{r.signals} ({fmt_pct(r.clean1r_rate)}) | "
            f"{fmt_pct(r.winner_retention_unresolved)} | {fmt_pct(r.whole_ge1r_capture)} | {r.too_fast_win} |"
        )

    lines += ["","## D1 year stability","",
        "| Year | Eligible | Signals | GE1R | Base | Uplift | >=1.5R | >=2R | Whole GE1R capture | Too-fast win |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    ]
    for r in Y.itertuples(index=False):
        lines.append(
            f"| {r.year} | {r.eligible} | {r.signals} | {r.ge1r_tp}/{r.signals} ({fmt_pct(r.ge1r_rate)}) | "
            f"{fmt_pct(r.eligible_base_rate)} | {fmt_num(r.uplift_pp,1)}pp | "
            f"{r.ge1_5r}/{r.signals} ({fmt_pct(r.ge1_5r_rate)}) | "
            f"{r.ge2r}/{r.signals} ({fmt_pct(r.ge2r_rate)}) | "
            f"{fmt_pct(r.whole_ge1r_capture)} | {r.too_fast_win} |"
        )

    lines += ["","## Market-at-signal lateness diagnostic","",
        "| Period | Signals | Med displacement | Med reward left to anchor+1R | Med risk to floor | Med implied R:R | IQR implied R:R |",
        "|---|---:|---:|---:|---:|---:|---:|"
    ]
    for r in D.itertuples(index=False):
        lines.append(
            f"| {r.period} | {r.signals} | {fmt_num(r.median_signal_displacement_event_r)} event-R | "
            f"{fmt_num(r.median_remaining_reward_event_r)} | {fmt_num(r.median_structural_risk_event_r)} | "
            f"{fmt_num(r.median_implied_reward_risk)} | "
            f"{fmt_num(r.q25_implied_reward_risk)}–{fmt_num(r.q75_implied_reward_risk)} |"
        )

    lines += ["","## Interpretation boundary",
        "S4 validates the frozen D1 character only.",
        "B15 is a timing benchmark and cannot be promoted from this test.",
        "Market-at-signal R:R is diagnostic only; no entry policy is optimized here.",
        "If D1 passes robustness but market entry is late, the next stage must discover entry geometry around the same frozen D1 character without changing its threshold."
    ]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    (ROOT/f"{PFX}_Status.txt").write_text("BNB_B39_S4_FIRST5_EXPANSION_DETECTOR_COMPLETE\n",encoding="utf-8")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
