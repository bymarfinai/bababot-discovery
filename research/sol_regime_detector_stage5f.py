#!/usr/bin/env python3
from __future__ import annotations

import io
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT=Path(__file__).resolve().parent.parent
F2=ROOT/"SOL_REGIME_DETECTOR_STAGE2_Features.csv"
F3=ROOT/"SOL_REGIME_DETECTOR_STAGE3_Scores_DEV.csv"
F4=ROOT/"SOL_REGIME_DETECTOR_STAGE4_States_DEV.csv"
S5=ROOT/"SOL_REGIME_DETECTOR_STAGE5_Status.txt"

OUT_MD=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Result.md"
OUT_EVENTS=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Events.csv"
OUT_SUMMARY=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Summary.csv"
OUT_BLOCKS=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Blocks.csv"
OUT_CHAINS=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Chains.csv"
OUT_AUDIT=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Audit.csv"
OUT_STATUS=ROOT/"SOL_REGIME_DETECTOR_STAGE5F_Status.txt"

SYMBOL="SOLUSDT"
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
START=pd.Timestamp("2023-01-01T00:00:00Z")
END=pd.Timestamp("2025-01-01T00:00:00Z")
HORIZONS=(6,12,24)
MILESTONES=["M0_IMPULSE_START","M1_STRUCTURE_BREAK","M2_STRUCTURE_CONFIRM","M3_RAW_SCORE_SWITCH","M4_FINAL_SWITCH"]
SIDES=["BULL","BEAR"]

def month_urls():
    cur=START; out=[]
    while cur<END:
        ym=cur.strftime("%Y-%m")
        out.append(f"{BASE}/{SYMBOL}/5m/{SYMBOL}-5m-{ym}.zip")
        cur += pd.offsets.MonthBegin(1)
    return out

def fetch_one(url):
    r=requests.get(url,timeout=90,headers={"User-Agent":"bababot-stage5f/1.0"})
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names=[n for n in zf.namelist() if n.lower().endswith(".csv")]
        if not names: raise RuntimeError(f"no csv {url}")
        with zf.open(names[0]) as fh:
            return pd.read_csv(fh,header=None,usecols=[0,1,2,3,4,5],
                               names=["ts","open","high","low","close","volume"])

def load5():
    frames=[]
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs=[ex.submit(fetch_one,u) for u in month_urls()]
        for fut in as_completed(futs):
            frames.append(fut.result())
    x=pd.concat(frames,ignore_index=True)
    t=pd.to_numeric(x.ts,errors="coerce")
    t=np.where(t>100_000_000_000_000,t/1000.0,t)
    x["ts"]=pd.to_datetime(t,unit="ms",utc=True,errors="coerce")
    for c in ["open","high","low","close","volume"]:
        x[c]=pd.to_numeric(x[c],errors="coerce")
    x=x.dropna().drop_duplicates("ts").sort_values("ts")
    x=x[(x.ts>=START)&(x.ts<END)].set_index("ts")
    expected=int((END-START)/pd.Timedelta(minutes=5))
    return x,len(x)/expected

def block(ts):
    if ts<pd.Timestamp("2023-07-01",tz="UTC"): return "2023-H1"
    if ts<pd.Timestamp("2024-01-01",tz="UTC"): return "2023-H2"
    if ts<pd.Timestamp("2024-07-01",tz="UTC"): return "2024-H1"
    return "2024-H2"

def future_label(x5,ts,h,side):
    end=ts+pd.Timedelta(hours=h)
    if ts<START or end>=END: return None
    try:
        i0=x5.index.get_loc(ts); i1=x5.index.get_loc(end)
    except KeyError:
        return None
    if not isinstance(i0,(int,np.integer)) or not isinstance(i1,(int,np.integer)): return None
    if i1-i0 != h*12: return None
    ep=float(x5.iloc[i0].open)
    w=x5.iloc[i0:i1]
    highs=w.high.to_numpy(float); lows=w.low.to_numpy(float)
    up=ep*1.01; dn=ep*0.99
    upm=highs>=up; dnm=lows<=dn; anym=upm|dnm
    first="UNRESOLVED"
    if anym.any():
        k=int(np.argmax(anym))
        if upm[k] and dnm[k]: first="AMBIGUOUS"
        elif upm[k]: first="POS_FIRST"
        else: first="NEG_FIRST"
    ret=float(x5.iloc[i1].open)/ep-1.0
    sign=1.0 if side=="BULL" else -1.0
    aligned_hit = ((first=="POS_FIRST") if side=="BULL" else (first=="NEG_FIRST"))
    return {
        f"firsthit_{h}h":first,
        f"aligned_hit_{h}h":aligned_hit if first in ("POS_FIRST","NEG_FIRST") else np.nan,
        f"aligned_ret_{h}h":ret*sign,
        f"aligned_mfe_{h}h":((float(np.max(highs))/ep-1.0) if side=="BULL" else (1.0-float(np.min(lows))/ep)),
        f"aligned_mae_{h}h":((1.0-float(np.min(lows))/ep) if side=="BULL" else (float(np.max(highs))/ep-1.0)),
    }

def load_inputs():
    f2=pd.read_csv(F2,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    f2=f2[(f2.index>=START)&(f2.index<END)].copy()
    f3=pd.read_csv(F3,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    f3=f3[(f3.index>=START)&(f3.index<END)].copy()
    f4=pd.read_csv(F4,parse_dates=["bar_open_ts","decision_time"]).set_index("bar_open_ts").sort_index()
    f4=f4[(f4.index>=START)&(f4.index<END)].copy()
    idx=f2.index.intersection(f3.index).intersection(f4.index)
    z=f2.loc[idx].copy()
    z["provisional_regime"]=f3.loc[idx,"provisional_regime"]
    z["final_regime"]=f4.loc[idx,"final_regime"]
    z["switch_event"]=f4.loc[idx,"switch_event"].astype(bool)
    z["switch_reason"]=f4.loc[idx,"switch_reason"].fillna("")
    return z

def detect_events(z):
    events=[]
    atrn=z["h1_atr_norm"].replace(0,np.nan)
    impulse=z["h1_ret_3"]/atrn
    prev_imp=impulse.shift(1)

    # M0
    bull=(impulse>=1.0)&(prev_imp<1.0)&(z["h1_ema20_slope3_atr"]>0)
    bear=(impulse<=-1.0)&(prev_imp>-1.0)&(z["h1_ema20_slope3_atr"]<0)
    for side,mask in [("BULL",bull),("BEAR",bear)]:
        for ts in z.index[mask.fillna(False)]:
            events.append((ts,"M0_IMPULSE_START",side))

    # M1 rising-edge structure breaks
    for side,col in [("BULL","h1_break_above_last_high"),("BEAR","h1_break_below_last_low")]:
        cur=z[col].fillna(False).astype(bool)
        mask=cur & (~cur.shift(1).fillna(False))
        for ts in z.index[mask]:
            events.append((ts,"M1_STRUCTURE_BREAK",side))

    # M2 state transition into structural sequence
    prev=z["h1_structure_state"].shift(1)
    for side,state in [("BULL","BULL_SEQ"),("BEAR","BEAR_SEQ")]:
        mask=(z["h1_structure_state"]==state)&(prev!=state)
        for ts in z.index[mask.fillna(False)]:
            events.append((ts,"M2_STRUCTURE_CONFIRM",side))

    # M3 raw score switch
    prev=z["provisional_regime"].shift(1)
    for side in SIDES:
        mask=(z["provisional_regime"]==side)&(prev!=side)
        for ts in z.index[mask.fillna(False)]:
            events.append((ts,"M3_RAW_SCORE_SWITCH",side))

    # M4 final non-startup switch
    for side in SIDES:
        mask=(z["switch_event"])&(z["final_regime"]==side)&(z["switch_reason"].isin(["FAST_2BAR","NORMAL_3BAR"]))
        for ts in z.index[mask.fillna(False)]:
            events.append((ts,"M4_FINAL_SWITCH",side))

    e=pd.DataFrame(events,columns=["bar_open_ts","milestone","side"]).drop_duplicates()
    e=e.sort_values(["bar_open_ts","milestone","side"]).reset_index(drop=True)
    return e

def summarize(e):
    rows=[]
    for m in MILESTONES:
        for side in SIDES+["COMBINED"]:
            q=e[e.milestone==m]
            if side!="COMBINED": q=q[q.side==side]
            q24=q[q["firsthit_24h"].notna()]
            resolved=q24[q24["firsthit_24h"].isin(["POS_FIRST","NEG_FIRST"])]
            ah=float(pd.to_numeric(resolved["aligned_hit_24h"],errors="coerce").mean()) if len(resolved) else np.nan
            rows.append({
                "milestone":m,"side":side,
                "events":len(q),"eligible24":len(q24),"resolved24":len(resolved),
                "aligned_hit24":ah,
                "median_pre3":float(q["aligned_pre_3h"].median()) if len(q) else np.nan,
                "median_pre6":float(q["aligned_pre_6h"].median()) if len(q) else np.nan,
                "median_pre12":float(q["aligned_pre_12h"].median()) if len(q) else np.nan,
                "median_pre24":float(q["aligned_pre_24h"].median()) if len(q) else np.nan,
                "median_future6":float(q["aligned_ret_6h"].median()) if len(q) else np.nan,
                "median_future12":float(q["aligned_ret_12h"].median()) if len(q) else np.nan,
                "median_future24":float(q["aligned_ret_24h"].median()) if len(q) else np.nan,
                "ambiguous24_share":float((q24["firsthit_24h"]=="AMBIGUOUS").mean()) if len(q24) else np.nan,
            })
    return pd.DataFrame(rows)

def make_chains(e):
    ev={m:{s:[] for s in SIDES} for m in MILESTONES}
    for _,r in e.iterrows():
        ev[r.milestone][r.side].append(r.decision_time)
    rows=[]
    finals=e[e.milestone=="M4_FINAL_SWITCH"]
    for _,r in finals.iterrows():
        rec={"decision_time":r.decision_time,"side":r.side}
        for m in ["M0_IMPULSE_START","M1_STRUCTURE_BREAK","M2_STRUCTURE_CONFIRM","M3_RAW_SCORE_SWITCH"]:
            arr=ev[m][r.side]
            prior=[x for x in arr if x<=r.decision_time and x>=r.decision_time-pd.Timedelta(hours=72)]
            if prior:
                t=max(prior); rec[m+"_time"]=t; rec[m+"_to_M4_h"]=(r.decision_time-t)/pd.Timedelta(hours=1)
            else:
                rec[m+"_time"]=pd.NaT; rec[m+"_to_M4_h"]=np.nan
        rows.append(rec)
    return pd.DataFrame(rows)

def main():
    s5_failed="SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATION_FAILED" in (S5.read_text() if S5.exists() else "")
    z=load_inputs()
    x5,coverage=load5()
    e=detect_events(z)

    # attach causal decision time + consumed past move
    decision=z["decision_time"]
    pre_cols=["h1_ret_3","h1_ret_6","h1_ret_12","h1_ret_24"]
    recs=[]
    for _,r in e.iterrows():
        ts=r.bar_open_ts; side=r.side; sign=1.0 if side=="BULL" else -1.0
        d={"bar_open_ts":ts,"decision_time":decision.loc[ts],"milestone":r.milestone,"side":side,"block":block(decision.loc[ts])}
        for h,c in [(3,"h1_ret_3"),(6,"h1_ret_6"),(12,"h1_ret_12"),(24,"h1_ret_24")]:
            d[f"aligned_pre_{h}h"]=float(z.loc[ts,c])*sign if pd.notna(z.loc[ts,c]) else np.nan
        for h in HORIZONS:
            lab=future_label(x5,decision.loc[ts],h,side)
            if lab: d.update(lab)
            else:
                d.update({f"firsthit_{h}h":np.nan,f"aligned_hit_{h}h":np.nan,f"aligned_ret_{h}h":np.nan,
                          f"aligned_mfe_{h}h":np.nan,f"aligned_mae_{h}h":np.nan})
        recs.append(d)
    evdf=pd.DataFrame(recs)
    evdf.to_csv(OUT_EVENTS,index=False)

    sdf=summarize(evdf)
    sdf.to_csv(OUT_SUMMARY,index=False)

    blocks=[]
    for m in MILESTONES:
        for b in ["2023-H1","2023-H2","2024-H1","2024-H2"]:
            q=evdf[(evdf.milestone==m)&(evdf.block==b)&(evdf.firsthit_24h.isin(["POS_FIRST","NEG_FIRST"]))]
            blocks.append({"milestone":m,"block":b,"n":len(q),
                           "aligned_hit24":float(pd.to_numeric(q.aligned_hit_24h,errors="coerce").mean()) if len(q) else np.nan})
    bdf=pd.DataFrame(blocks)
    bdf.to_csv(OUT_BLOCKS,index=False)

    chains=make_chains(evdf)
    chains.to_csv(OUT_CHAINS,index=False)

    audit=[]
    def add(name,ok,value):
        audit.append({"audit":name,"pass":bool(ok),"value":value})
    add("stage5_failed_status_present",s5_failed,s5_failed)
    add("raw_5m_coverage_ge_99_5",coverage>=0.995,coverage)
    used=evdf[evdf.firsthit_24h.notna()]
    no_cross=bool((used.decision_time+pd.Timedelta(hours=24)<=END).all()) if len(used) else False
    add("no_24h_window_crosses_2025",no_cross,str(used.decision_time.max()) if len(used) else "")
    future_tokens=[c for c in z.columns if any(k in c.lower() for k in ["forward","future","outcome","mfe","mae","tp_","sl_"])]
    add("milestone_source_has_no_future_fields",len(future_tokens)==0,future_tokens)

    amb={}
    for m in MILESTONES:
        for side in SIDES:
            q=evdf[(evdf.milestone==m)&(evdf.side==side)&evdf.firsthit_24h.notna()]
            amb[f"{m}:{side}"]=float((q.firsthit_24h=="AMBIGUOUS").mean()) if len(q) else np.nan
    add("ambiguous_le_2pct_all",all((pd.isna(v) or v<=0.02) for v in amb.values()),amb)

    counts={m:int(((evdf.milestone==m)&evdf.firsthit_24h.notna()).sum()) for m in MILESTONES}
    add("each_milestone_ge_200_eligible24",all(v>=200 for v in counts.values()),counts)

    adf=pd.DataFrame(audit); adf.to_csv(OUT_AUDIT,index=False)
    tech_pass=bool(adf["pass"].all())

    comb=sdf[sdf.side=="COMBINED"].set_index("milestone")
    m4_hit=float(comb.loc["M4_FINAL_SWITCH","aligned_hit24"])
    early=["M0_IMPULSE_START","M1_STRUCTURE_BREAK","M2_STRUCTURE_CONFIRM"]
    early_gaps={m:float(comb.loc[m,"aligned_hit24"]-m4_hit) for m in early}

    # block superiority vs M4
    block_super={}
    for m in early:
        x=bdf[bdf.milestone==m].set_index("block").aligned_hit24
        y=bdf[bdf.milestone=="M4_FINAL_SWITCH"].set_index("block").aligned_hit24
        block_super[m]=int(sum((x.loc[b]>y.loc[b]) for b in x.index if pd.notna(x.loc[b]) and pd.notna(y.loc[b])))

    delay={}
    found={}
    for m in ["M0_IMPULSE_START","M1_STRUCTURE_BREAK","M2_STRUCTURE_CONFIRM","M3_RAW_SCORE_SWITCH"]:
        col=m+"_to_M4_h"
        delay[m]=float(chains[col].median()) if len(chains) else np.nan
        found[m]=float(chains[col].notna().mean()) if len(chains) else np.nan

    latency_candidates=[]
    m4_pre6=float(comb.loc["M4_FINAL_SWITCH","median_pre6"])
    m4_fut24=float(comb.loc["M4_FINAL_SWITCH","median_future24"])
    for m in early:
        conds=[
            early_gaps[m]>=0.05,
            block_super[m]>=3,
            pd.notna(delay[m]) and delay[m]>0,
            m4_pre6>float(comb.loc[m,"median_pre6"]),
            m4_fut24<float(comb.loc[m,"median_future24"]),
        ]
        if all(conds): latency_candidates.append(m)

    max_early=max(float(comb.loc[m,"aligned_hit24"]) for m in early+["M3_RAW_SCORE_SWITCH","M4_FINAL_SWITCH"])
    directional_weak=(max_early<0.55 and max(early_gaps.values())<0.05)

    rates=[float(comb.loc[m,"aligned_hit24"]) for m in MILESTONES]
    drops=[rates[i+1]-rates[i] for i in range(len(rates)-1)]
    largest_i=int(np.argmin(drops))
    largest_step=f"{MILESTONES[largest_i]}→{MILESTONES[largest_i+1]}"
    largest_drop=float(drops[largest_i])

    if latency_candidates:
        verdict="LATENCY_HYPOTHESIS_SUPPORTED"
        localization=f"EDGE_LOSS_AT_{largest_step}"
    elif directional_weak:
        verdict="DIRECTIONAL_FEATURES_WEAK"
        localization="NO_CLEAR_LATENCY_BOTTLENECK"
    else:
        verdict="MIXED_FORENSIC_RESULT"
        localization=f"LARGEST_DECLINE_{largest_step}"

    lines=[
        "# SOL Regime Detector — Stage 5F Failure Forensics","",
        "Stage 5F used **2023-2024 only** and did not modify the frozen detector.","",
        f"Raw SOLUSDT 5m coverage: **{coverage:.4%}**.","",
        "## Edge decay by causal milestone","",
        "| Milestone | Events | 24H resolved aligned hit | Median pre-6H aligned move | Median future-6H aligned ret | Median future-24H aligned ret |",
        "|---|---:|---:|---:|---:|---:|"
    ]
    for m in MILESTONES:
        x=comb.loc[m]
        lines.append(f"| {m} | {int(x.events)} | {x.aligned_hit24:.1%} | {x.median_pre6:.3%} | {x.median_future6:.3%} | {x.median_future24:.3%} |")

    lines += ["","## 24H aligned hit-rate by half-year","",
              "| Milestone | 2023-H1 | 2023-H2 | 2024-H1 | 2024-H2 |",
              "|---|---:|---:|---:|---:|"]
    for m in MILESTONES:
        q=bdf[bdf.milestone==m].set_index("block")
        vals=[q.loc[b,"aligned_hit24"] if b in q.index else np.nan for b in ["2023-H1","2023-H2","2024-H1","2024-H2"]]
        lines.append(f"| {m} | {vals[0]:.1%} | {vals[1]:.1%} | {vals[2]:.1%} | {vals[3]:.1%} |")

    lines += ["","## Same-side latency into FINAL_SWITCH","",
              "| Earlier milestone | Found within 72H | Median delay to M4 |",
              "|---|---:|---:|"]
    for m in ["M0_IMPULSE_START","M1_STRUCTURE_BREAK","M2_STRUCTURE_CONFIRM","M3_RAW_SCORE_SWITCH"]:
        lines.append(f"| {m} | {found[m]:.1%} | {delay[m]:.1f}h |")

    lines += ["","## Consecutive edge changes","",
              "| Step | Change in combined aligned hit |","|---|---:|"]
    for i,d in enumerate(drops):
        lines.append(f"| {MILESTONES[i]} → {MILESTONES[i+1]} | {d:+.1%} |")

    lines += ["","## Frozen forensic verdict","",
              f"- Verdict: **{verdict}**",
              f"- Localization: **{localization}**",
              f"- Largest consecutive aligned-hit change: **{largest_drop:+.1%}** at **{largest_step}**.",
              f"- Best milestone combined aligned 24H hit: **{max_early:.1%}**.","",
              "## Technical audits","",
              "| Audit | Pass | Value |","|---|---|---|"]
    for _,r in adf.iterrows():
        lines.append(f"| {r.audit} | {'PASS' if r['pass'] else 'FAIL'} | {str(r.value).replace('|','/')} |")

    lines += ["","## Decision",""]
    if tech_pass:
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE5F_FORENSICS_COMPLETE**","",
            "This result diagnoses the failed V1 detector. It does not authorize an OOS Stage 6 run and does not retroactively validate the detector.",
            "Any redesign must be separately preregistered using these forensic findings as disclosed development information."
        ]
        OUT_STATUS.write_text(f"SOL_REGIME_DETECTOR_STAGE5F_FORENSICS_COMPLETE\nVERDICT={verdict}\nLOCALIZATION={localization}\n")
    else:
        failed=adf.loc[~adf["pass"],"audit"].tolist()
        lines += [
            "**Status: SOL_REGIME_DETECTOR_STAGE5F_FORENSICS_INVALID**","",
            f"Failed technical audits: **{failed}**."
        ]
        OUT_STATUS.write_text("SOL_REGIME_DETECTOR_STAGE5F_FORENSICS_INVALID\n")

    OUT_MD.write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    main()
