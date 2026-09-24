#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
from hashlib import sha256
import json

import numpy as np
import pandas as pd

import bnb_b42_s1_opportunity_atlas as s1
import bnb_b31_s1_swing_structure_library as b31

ROOT=Path(__file__).resolve().parent.parent
PFX="BNB_B42_S3_TURNING_POINT_GATE"
PARENT_SIG="ce5dcd0bdb095d6aa9ea8991e851e44c9f21fb898d36ff9848cb5884ef9a14fd"
START=pd.Timestamp("2022-01-01T00:00:00Z")
END=pd.Timestamp("2026-08-26T00:00:00Z")
BAR15=pd.Timedelta(minutes=15)
COOLDOWN=pd.Timedelta(minutes=60)
FAMS=[
 ("E1","Q80_LOWER_RECLAIM","LONG","Q80"),
 ("E2","Q80_UPPER_REJECT","SHORT","Q80"),
 ("E3","SWING_LOW_SWEEP_RECLAIM","LONG","SWING"),
 ("E4","SWING_HIGH_SWEEP_REJECT","SHORT","SWING"),
 ("E5","PRIOR24H_LOW_SWEEP_RECLAIM","LONG","PRIOR24H"),
 ("E6","PRIOR24H_HIGH_SWEEP_REJECT","SHORT","PRIOR24H"),
]

def verify_parent():
    p=ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Freeze.txt"
    if f"S1_SIGNATURE_SHA256={PARENT_SIG}" not in p.read_text():
        raise RuntimeError("B42-S1 parent signature mismatch")

def bars15(raw):
    same2=(raw.index.to_series().diff().eq(pd.Timedelta(minutes=5)) &
           raw.index.to_series().diff(2).eq(pd.Timedelta(minutes=10)))
    b=pd.DataFrame(index=raw.index)
    b["open"]=raw.open.shift(2)
    b["high"]=raw.high.rolling(3,min_periods=3).max()
    b["low"]=raw.low.rolling(3,min_periods=3).min()
    b["close"]=raw.close
    b=b[(b.index.minute%15==0)&same2].copy()
    return b[(b.index>=START-pd.Timedelta(days=70))&(b.index<=END)]

def cooldown(df):
    if df.empty: return df
    keep=[]; last={}
    for r in df.sort_values(["event_ts","family_id"]).itertuples(index=False):
        k=r.family_id
        if k not in last or r.event_ts-last[k]>=COOLDOWN:
            keep.append(r); last[k]=r.event_ts
    return pd.DataFrame(keep,columns=df.columns)

def q80_events(raw,b):
    # build completed UTC daily bars from close-timestamp-indexed 5m data
    x=raw.copy()
    x=x[(x.index>=START-pd.Timedelta(days=70))&(x.index<END+pd.Timedelta(days=1))]
    day=(x.index-pd.Timedelta(microseconds=1)).floor("D")
    d=x.groupby(day).agg(open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"))
    d["up"]=d.high/d.open-1
    d["dn"]=1-d.low/d.open
    d["q80_up"]=d.up.shift(1).rolling(60,min_periods=60).quantile(.80)
    d["q80_dn"]=d.dn.shift(1).rolling(60,min_periods=60).quantile(.80)
    rows=[]
    for day_ts,r in d.loc[START.floor("D"):END.floor("D")].iterrows():
        if not np.isfinite(r.q80_up) or not np.isfinite(r.q80_dn): continue
        upper=float(r.open*(1+r.q80_up)); lower=float(r.open*(1-r.q80_dn))
        z=b[(b.index>day_ts)&(b.index<=day_ts+pd.Timedelta(days=1))]
        got_l=False; got_s=False
        for t,xr in z.iterrows():
            if not got_l and xr.low<=lower and xr.close>lower:
                rows.append((t,"E1","Q80_LOWER_RECLAIM","LONG","Q80",lower)); got_l=True
            if not got_s and xr.high>=upper and xr.close<upper:
                rows.append((t,"E2","Q80_UPPER_REJECT","SHORT","Q80",upper)); got_s=True
            if got_l and got_s: break
    return pd.DataFrame(rows,columns=["event_ts","family_id","family","side","concept","level"])

def swing_events(raw):
    bb=b31.bars15(raw[["open","high","low","close"]])
    e=b31.detect(bb)
    keep=e[e.structure_id.isin(["S01","S05"])].copy()
    mp={"S01":("E3","SWING_LOW_SWEEP_RECLAIM","LONG","SWING"),
        "S05":("E4","SWING_HIGH_SWEEP_REJECT","SHORT","SWING")}
    rows=[]
    for r in keep.itertuples(index=False):
        fid,name,side,concept=mp[r.structure_id]
        rows.append((r.event_ts,fid,name,side,concept,float(r.level)))
    return pd.DataFrame(rows,columns=["event_ts","family_id","family","side","concept","level"])

def prior24_events(b):
    prior_low=b.low.shift(1).rolling(96,min_periods=96).min()
    prior_high=b.high.shift(1).rolling(96,min_periods=96).max()
    rows=[]
    for t,r in b[(b.index>=START)&(b.index<=END)].iterrows():
        lo=prior_low.get(t,np.nan); hi=prior_high.get(t,np.nan)
        if np.isfinite(lo) and r.low<lo and r.close>=lo:
            rows.append((t,"E5","PRIOR24H_LOW_SWEEP_RECLAIM","LONG","PRIOR24H",float(lo)))
        if np.isfinite(hi) and r.high>hi and r.close<=hi:
            rows.append((t,"E6","PRIOR24H_HIGH_SWEEP_REJECT","SHORT","PRIOR24H",float(hi)))
    return cooldown(pd.DataFrame(rows,columns=["event_ts","family_id","family","side","concept","level"]))

def add_confluence(e):
    rows=[]
    for (t,side),g in e.groupby(["event_ts","side"]):
        concepts=sorted(set(g.concept))
        if len(concepts)>=2:
            rows.append((t,"C2PLUS","CONFLUENCE_2PLUS",side,"+".join(concepts),float(g.level.mean())))
    c=pd.DataFrame(rows,columns=e.columns)
    return pd.concat([e,c],ignore_index=True).sort_values(["event_ts","family_id"])

def attach_labels(e):
    L=pd.read_csv(ROOT/"results/bnb_b42_s1/BNB_B42_S1_OPPORTUNITY_ATLAS_Ledger.csv.gz",
                  compression="gzip",parse_dates=["decision_ts","decision_day"])
    cols=["decision_ts","side","year","decision_day","outcome","first_touch_min","timeout_signed_return","entry","tp","sl"]
    q=L[cols].copy()
    z=e.merge(q,left_on=["event_ts","side"],right_on=["decision_ts","side"],how="left",validate="many_to_one")
    if z.outcome.isna().any():
        raise RuntimeError(f"unmatched labels {z.outcome.isna().sum()}")
    z["period"]=np.where(z.year<=2024,"DEV","REF")
    z["realized_R"]=np.select(
        [z.outcome.eq("WIN"),z.outcome.eq("LOSS"),z.outcome.eq("AMBIGUOUS")],
        [1.0,-1.0,-1.0],
        default=np.clip(pd.to_numeric(z.timeout_signed_return,errors="coerce").fillna(0).to_numpy()/0.01,-1,1)
    )
    return z

def summarize(z):
    rows=[]
    total_days={"DEV":1096,"REF":603}
    for fam in list([x[0] for x in FAMS])+["C2PLUS"]:
        for period in ["DEV","REF"]:
            x=z[(z.family_id==fam)&(z.period==period)]
            n=len(x); wins=int(x.outcome.eq("WIN").sum()); losses=int(x.outcome.eq("LOSS").sum())
            amb=int(x.outcome.eq("AMBIGUOUS").sum()); tout=int(x.outcome.eq("TIMEOUT").sum())
            resolved=wins+losses+amb
            rows.append({
              "family_id":fam,"period":period,"n":n,
              "events_per365":n/total_days[period]*365 if total_days[period] else np.nan,
              "event_days":int(x.decision_day.nunique()),"event_day_share":x.decision_day.nunique()/total_days[period],
              "wins":wins,"losses":losses,"timeouts":tout,"ambiguous":amb,
              "win_rate":wins/n if n else np.nan,
              "resolved_wr":wins/resolved if resolved else np.nan,
              "mean_R":float(x.realized_R.mean()) if n else np.nan,
              "median_win_touch_min":float(pd.to_numeric(x.loc[x.outcome.eq("WIN"),"first_touch_min"],errors="coerce").median()) if wins else np.nan,
              "median_loss_touch_min":float(pd.to_numeric(x.loc[x.outcome.eq("LOSS"),"first_touch_min"],errors="coerce").median()) if losses else np.nan,
            })
    return pd.DataFrame(rows)

def yearly(z):
    out=[]
    for (fam,y),x in z.groupby(["family_id","year"]):
        out.append({"family_id":fam,"year":int(y),"n":len(x),"win_rate":float(x.outcome.eq("WIN").mean()),
                    "mean_R":float(x.realized_R.mean())})
    return pd.DataFrame(out)

def nominate(S,Y):
    rows=[]
    for fam in list([x[0] for x in FAMS])+["C2PLUS"]:
        d=S[(S.family_id==fam)&(S.period=="DEV")].iloc[0]
        r=S[(S.family_id==fam)&(S.period=="REF")].iloc[0]
        yy=Y[Y.family_id==fam]
        robust_years=int((yy.win_rate>=.50).sum())
        nd=75 if fam=="C2PLUS" else 150
        nr=40 if fam=="C2PLUS" else 75
        passed=bool(
          d.n>=nd and r.n>=nr and d.win_rate>=.55 and r.win_rate>=.52 and
          d.mean_R>0 and r.mean_R>0 and robust_years>=4
        )
        rows.append({"family_id":fam,"dev_n":int(d.n),"ref_n":int(r.n),
                     "dev_wr":float(d.win_rate) if np.isfinite(d.win_rate) else np.nan,
                     "ref_wr":float(r.win_rate) if np.isfinite(r.win_rate) else np.nan,
                     "dev_mean_R":float(d.mean_R) if np.isfinite(d.mean_R) else np.nan,
                     "ref_mean_R":float(r.mean_R) if np.isfinite(r.mean_R) else np.nan,
                     "years_wr_ge50":robust_years,"nominated":passed})
    return pd.DataFrame(rows)

def main():
    verify_parent()
    raw,diag=s1.load_raw()
    if diag["sha256"]!="95ad73ce949a6e622a1b7e120eeaa23d853de2a0f4cd9c6f1533b20c37ee2334":
        raise RuntimeError("raw identity mismatch")
    b=bars15(raw)
    e=pd.concat([q80_events(raw,b),swing_events(raw),prior24_events(b)],ignore_index=True)
    e=e[(e.event_ts>=START)&(e.event_ts<=END)].drop_duplicates(["event_ts","family_id"]).copy()
    e=add_confluence(e)
    z=attach_labels(e)
    S=summarize(z); Y=yearly(z); N=nominate(S,Y)
    status="BNB_B42_S3_TURNING_POINT_GATE_READY" if N.nominated.any() else "BNB_B42_S3_NO_ROBUST_TURNING_POINT_EVENT"

    sig=sha256(json.dumps({
      "parent":PARENT_SIG,
      "events":["Q80_PRIOR60_FIRST_DAILY_RECLAIM","B31_CAUSAL_SWING_SWEEP","PRIOR96_15M_SWEEP"],
      "cooldown":"60m for swing/prior24h","confluence":"same_ts_same_side_2plus_concepts",
      "gates":{"standalone_dev_n":150,"standalone_ref_n":75,"c2_dev_n":75,"c2_ref_n":40,
               "dev_wr":.55,"ref_wr":.52,"mean_R":"positive both","years_wr_ge50":4}
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()

    z.to_csv(ROOT/f"{PFX}_Events.csv.gz",index=False,compression="gzip")
    S.to_csv(ROOT/f"{PFX}_Summary.csv",index=False)
    Y.to_csv(ROOT/f"{PFX}_ByYear.csv",index=False)
    N.to_csv(ROOT/f"{PFX}_Nominations.csv",index=False)
    (ROOT/f"{PFX}_Status.txt").write_text(status+"\n")
    (ROOT/f"{PFX}_Freeze.txt").write_text(f"S3_SIGNATURE_SHA256={sig}\nPARENT_S1_SIGNATURE_SHA256={PARENT_SIG}\n")

    def pct(x): return "—" if pd.isna(x) else f"{100*x:.2f}%"
    names={fid:name for fid,name,_,_ in FAMS}; names["C2PLUS"]="CONFLUENCE_2PLUS"
    lines=["# BNB B42-S3 — Causal Turning-Point Event Gate Result","",f"**Status: {status}**","",
           f"Signature: `{sig}`","","## Event quality","",
           "| Family | Period | N | /yr | Event-day share | WIN rate | Mean R | Med WIN min | Med LOSS min |",
           "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    for r in S.itertuples(index=False):
        lines.append(f"| {r.family_id} {names.get(r.family_id,'')} | {r.period} | {r.n} | {r.events_per365:.1f} | {pct(r.event_day_share)} | **{pct(r.win_rate)}** | {r.mean_R:.3f} | {r.median_win_touch_min:.0f} | {r.median_loss_touch_min:.0f} |")
    lines += ["","## Nominations","",
              "| Family | DEV N | REF N | DEV WR | REF WR | DEV R | REF R | Years >=50% | Nominate |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for r in N.itertuples(index=False):
        lines.append(f"| {r.family_id} | {r.dev_n} | {r.ref_n} | {pct(r.dev_wr)} | {pct(r.ref_wr)} | {r.dev_mean_R:.3f} | {r.ref_mean_R:.3f} | {r.years_wr_ge50} | {'YES' if r.nominated else 'NO'} |")
    lines += ["","## Decision",f"**{status}**","",
              ("At least one causal turning-point family has robust positive edge and may advance to event-only confirmation/ranking."
               if N.nominated.any() else
               "None of the frozen turning-point events is robust enough. Do not force a classifier on these event families.")]
    (ROOT/f"{PFX}_Result.md").write_text("\n".join(lines)+"\n")
    print("\n".join(lines),flush=True)

if __name__=="__main__":
    main()
