#!/usr/bin/env python3
"""SOL Indicator Relationship Discovery — Stage 6 regime + market-state mapping."""
from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pandas as pd
import sol_indicator_relationship_s3 as s3
import sol_indicator_relationship_s4 as s4

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6_Result.md"
OUT_JSON=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6_Result.json"
OUT_AUDIT=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6_AUDIT.csv"
OUT_REGIME=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6A_REGIME.csv"
OUT_STATES=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6B_STATES.csv"
OUT_CELLS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6C_REGIME_STATE.csv"
OUT_TRANS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6D_TRANSITIONS.csv"
OUT_STATUS=ROOT/"SOL_INDICATOR_RELATIONSHIP_S6_Status.txt"

PARTS=["development","validation_2025","validation_2026"]
REGIMES=["BULL","BEAR","SIDEWAYS","TRANSITION"]
BEAR_ACCEL=1.101215540095295
BEAR_CLOSE_LOC=0.6260779194779318
SIDE_RV8=0.47186330933162923
SIDE_ATR14=0.9798115352248504
PCTL_LOOKBACK=720
VOL_PCTL=0.85
VOL_VOTES=2
DIST_HIGH_PCTL_MAX=0.25
ARCHETYPES=[
 "EVENT_CONFLICT","POST_BREAKDOWN_UNWIND_30M","UP_POSITION_BUILD","UP_UNWIND_LIKE",
 "DOWN_POSITION_BUILD","DOWN_UNWIND_LIKE","HIGHLOC_BUY_BUILD",
 "HIGHLOC_BUY_EXHAUSTION_LIKE","HIGHLOC_SELL_ABSORPTION_LIKE",
 "HIGHLOC_SELL_UNWIND_LIKE","PRESSURE_BUILD","DELEVERAGING","NEUTRAL_TRANSITION"
]

def pct(v):
    return "-" if v is None or not np.isfinite(v) else f"{100*v:.1f}%"

def rate(s,label):
    return float((s==label).mean()) if len(s) else np.nan

def group_stats(g):
    g=g[g.target_1pct_4h.notna()]
    n=int(len(g)); lr=rate(g.target_1pct_4h,"LONG"); sr=rate(g.target_1pct_4h,"SHORT")
    nr=rate(g.target_1pct_4h,"NONE"); ar=rate(g.target_1pct_4h,"AMBIGUOUS")
    return {
      "n":n,"long_rate":lr,"short_rate":sr,"none_rate":nr,"ambiguous_rate":ar,
      "D":lr-sr if n else np.nan,"expansion_rate":1-nr if n else np.nan,
      "median_fwd_ret_4h":float(g.fwd_ret_4h.median()) if n else np.nan,
      "median_max_up_4h":float(g.max_up_4h.median()) if n else np.nan,
      "median_max_down_4h":float(g.max_down_4h.median()) if n else np.nan,
    }

def load_stage4_specs():
    obj=json.loads((ROOT/"SOL_INDICATOR_RELATIONSHIP_S4_Result.json").read_text())
    specs=obj.get("specs",{})
    req=["oi_chg_15m","loc_24h","taker_imb_15m","quotevol_z_24h",
         "breakout_up_24h","breakout_down_24h","impulse5m_prev"]
    miss=[x for x in req if x not in specs]
    if miss: raise RuntimeError(f"Stage 4 frozen specs missing: {miss}")
    return specs

def prepare_relationship_data():
    raw=s3.load_klines()
    metrics=s3.load_metrics()
    funding=pd.DataFrame(columns=["ts","funding_rate","funding_z_30","funding_change"])
    a=s3.add_targets(s3.add_derivatives(s3.build_15m(raw),metrics,funding),raw)
    a=a[(a.decision_time>=s3.SCORE_START)&(a.decision_time<s3.END)].copy()
    a=s4.attach_impulse(a,raw)
    return raw,a.sort_values("decision_time").reset_index(drop=True)

def tr_series(h,l,c):
    prev=c.shift(1)
    return pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)

def causal_pct(arr,start_idx):
    out=np.full(len(arr),np.nan)
    for i in range(start_idx,len(arr)):
        v=arr[i]; hist=arr[i-PCTL_LOOKBACK:i]
        if np.isfinite(v) and len(hist)==PCTL_LOOKBACK and np.isfinite(hist).all():
            out[i]=float(np.mean(hist<=v))
    return out

def build_hourly_regime(raw):
    z=raw.set_index("ts").sort_index()
    cnt=z.close.resample("1h",label="left",closed="left").count()
    h=z.resample("1h",label="left",closed="left").agg(
      open=("open","first"),high=("high","max"),low=("low","min"),close=("close","last"))
    h=h[cnt==12].dropna().copy()
    tr=tr_series(h.high,h.low,h.close)
    h["atr14_pct"]=100*tr.rolling(14,min_periods=14).mean()/h.close
    lr=np.log(h.close/h.close.shift(1))
    h["rv8"]=100*lr.rolling(8,min_periods=8).std(ddof=0)
    h["rv24"]=100*lr.rolling(24,min_periods=24).std(ddof=0)
    hi8=h.high.rolling(8,min_periods=8).max()
    h["dist_high8"]=100*(h.close/hi8-1)
    h["ret4"]=100*(h.close/h.close.shift(4)-1)
    h["ret12"]=100*(h.close/h.close.shift(12)-1)
    h["accel4v12"]=h.ret4-h.ret12/3
    h["close_loc"]=2*(h.close-h.low)/(h.high-h.low+1e-12)-1
    start_idx=24+PCTL_LOOKBACK
    for k in ["rv8","rv24","atr14_pct","dist_high8"]:
        h[k+"_pct720"]=causal_pct(h[k].to_numpy(float),start_idx)
    votes=((h.rv8_pct720>=VOL_PCTL).astype(int)+(h.rv24_pct720>=VOL_PCTL).astype(int)
           +(h.atr14_pct_pct720>=VOL_PCTL).astype(int))
    bull=(votes>=VOL_VOTES)&(h.dist_high8_pct720<=DIST_HIGH_PCTL_MAX)
    bear=(h.accel4v12>=BEAR_ACCEL)&(h.close_loc>=BEAR_CLOSE_LOC)
    side=(h.rv8<SIDE_RV8)&(h.atr14_pct<SIDE_ATR14)
    ready=np.isfinite(h[["rv8_pct720","rv24_pct720","atr14_pct_pct720","dist_high8_pct720"]]).all(axis=1).to_numpy()
    regime=np.full(len(h),"UNAVAILABLE",dtype=object)
    b=bull.to_numpy(bool); r=bear.to_numpy(bool); s=side.to_numpy(bool)
    for i in range(len(h)):
        if not ready[i]: continue
        if b[i] and r[i]: regime[i]="TRANSITION"
        elif b[i]: regime[i]="BULL"
        elif r[i]: regime[i]="BEAR"
        elif s[i]: regime[i]="SIDEWAYS"
        else: regime[i]="TRANSITION"
    h["regime"]=regime
    h["regime_effective_ts"]=h.index+pd.Timedelta(hours=1)
    keep=["regime_effective_ts","regime","rv8","rv24","atr14_pct","dist_high8",
          "accel4v12","close_loc","rv8_pct720","rv24_pct720","atr14_pct_pct720","dist_high8_pct720"]
    return h[keep].reset_index(names="regime_bar_open")

def attach_regime(a,hourly):
    left=a.copy()
    left["decision_time_ns"]=pd.to_datetime(left.decision_time,utc=True).astype("datetime64[ns, UTC]")
    right=hourly.copy()
    right["regime_effective_ts"]=pd.to_datetime(right.regime_effective_ts,utc=True).astype("datetime64[ns, UTC]")
    m=pd.merge_asof(left.sort_values("decision_time_ns"),right.sort_values("regime_effective_ts"),
       left_on="decision_time_ns",right_on="regime_effective_ts",direction="backward",
       tolerance=pd.Timedelta(hours=1))
    m["regime_age_min"]=(m.decision_time_ns-m.regime_effective_ts).dt.total_seconds()/60
    return m.sort_values("decision_time").reset_index(drop=True)

def attach_buckets(a,specs):
    for f in ["oi_chg_15m","loc_24h","taker_imb_15m","quotevol_z_24h",
              "breakout_up_24h","breakout_down_24h","impulse5m_prev"]:
        a[f+"_bucket"]=[s4.bucket(v,specs[f]) for v in a[f]]
    return a

def build_state_tags(a):
    z=a.copy()
    z["oi_state"]=z.oi_chg_15m_bucket.map({"HIGH":"EXPAND","MID":"MID","LOW":"CONTRACT"})
    z["flow_state"]=z.taker_imb_15m_bucket.map({"HIGH":"BUY","MID":"MID","LOW":"SELL"})
    z["volume_state"]=np.where(z.quotevol_z_24h_bucket=="HIGH","HIGH","OTHER")
    z["location_state"]=z.loc_24h_bucket.map({"HIGH":"HIGH","MID":"MID","LOW":"LOW"})
    z["price_event_up"]=(z.impulse5m_prev_bucket=="UP_IMPULSE")|(z.breakout_up_24h_bucket=="POSITIVE")
    z["price_event_down"]=(z.impulse5m_prev_bucket=="DOWN_IMPULSE")|(z.breakout_down_24h_bucket=="POSITIVE")
    z["event_conflict"]=z.price_event_up&z.price_event_down
    prior=z.set_index("decision_time").breakout_down_24h_bucket
    lag_t=pd.DatetimeIndex(z.decision_time)-pd.Timedelta(minutes=30)
    z["downbreak_lag30"]=prior.reindex(lag_t).to_numpy()=="POSITIVE"
    z["post_downbreak_oi_contract_30m"]=z.downbreak_lag30&(z.oi_state=="CONTRACT")
    states=[]
    for r in z.itertuples(index=False):
        no_event=(not bool(r.price_event_up)) and (not bool(r.price_event_down))
        if bool(r.event_conflict): st="EVENT_CONFLICT"
        elif bool(r.post_downbreak_oi_contract_30m): st="POST_BREAKDOWN_UNWIND_30M"
        elif bool(r.price_event_up) and r.oi_state=="EXPAND": st="UP_POSITION_BUILD"
        elif bool(r.price_event_up) and r.oi_state=="CONTRACT": st="UP_UNWIND_LIKE"
        elif bool(r.price_event_down) and r.oi_state=="EXPAND": st="DOWN_POSITION_BUILD"
        elif bool(r.price_event_down) and r.oi_state=="CONTRACT": st="DOWN_UNWIND_LIKE"
        elif no_event and r.location_state=="HIGH" and r.flow_state=="BUY" and r.oi_state=="EXPAND": st="HIGHLOC_BUY_BUILD"
        elif no_event and r.location_state=="HIGH" and r.flow_state=="BUY" and r.oi_state=="CONTRACT": st="HIGHLOC_BUY_EXHAUSTION_LIKE"
        elif no_event and r.location_state=="HIGH" and r.flow_state=="SELL" and r.oi_state=="EXPAND": st="HIGHLOC_SELL_ABSORPTION_LIKE"
        elif no_event and r.location_state=="HIGH" and r.flow_state=="SELL" and r.oi_state=="CONTRACT": st="HIGHLOC_SELL_UNWIND_LIKE"
        elif no_event and r.volume_state=="HIGH" and r.oi_state=="EXPAND": st="PRESSURE_BUILD"
        elif no_event and r.volume_state=="HIGH" and r.oi_state=="CONTRACT": st="DELEVERAGING"
        else: st="NEUTRAL_TRANSITION"
        states.append(st)
    z["market_state"]=states
    return z

def baselines(a):
    return {p:group_stats(a[(a.partition==p)&a.target_1pct_4h.notna()]) for p in PARTS}

def summarize_regimes(a):
    rows=[]
    for p in PARTS:
        for reg in REGIMES:
            g=a[(a.partition==p)&(a.regime==reg)&a.target_1pct_4h.notna()]
            row={"partition":p,"regime":reg}; row.update(group_stats(g)); rows.append(row)
    return pd.DataFrame(rows)

def summarize_states(a,base):
    rows=[]
    for st in ARCHETYPES:
        row={"market_state":st}; support=True; Ds=[]; signs=[]; lifts=[]
        for p in PARTS:
            g=a[(a.partition==p)&(a.market_state==st)&a.target_1pct_4h.notna()]
            s=group_stats(g)
            for k,v in s.items(): row[f"{p}_{k}"]=v
            support &= s["n"] >= (150 if p=="development" else 75)
            d=s["D"]; Ds.append(d); signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
            lifts.append(s["expansion_rate"]-base[p]["expansion_rate"] if np.isfinite(s["expansion_rate"]) else np.nan)
        dd,d25,d26=Ds
        directional=(support and np.isfinite(dd) and abs(dd)>=.08 and signs[0]!=0
                     and signs[1]==signs[0] and signs[2]==signs[0]
                     and abs(d25)>=.04 and abs(d26)>=.04)
        e0,e25,e26=lifts
        expansion=(support and np.isfinite(e0) and e0>=.05 and e25>=.03 and e26>=.03)
        row["development_expansion_lift_pp"]=e0
        row["validation_2025_expansion_lift_pp"]=e25
        row["validation_2026_expansion_lift_pp"]=e26
        tags=[]
        if directional: tags.append("REPLICATED_DIRECTIONAL_STATE")
        if expansion: tags.append("REPLICATED_EXPANSION_STATE")
        row["classification"]=";".join(tags) if tags else "UNSTABLE_OR_WEAK"
        rows.append(row)
    return pd.DataFrame(rows)

def summarize_cells(a):
    rows=[]
    for reg in REGIMES:
      for st in ARCHETYPES:
        row={"regime":reg,"market_state":st}; support=True; Ds=[]; signs=[]
        for p in PARTS:
            g=a[(a.partition==p)&(a.regime==reg)&(a.market_state==st)&a.target_1pct_4h.notna()]
            s=group_stats(g)
            for k,v in s.items(): row[f"{p}_{k}"]=v
            support &= s["n"] >= (100 if p=="development" else 50)
            d=s["D"]; Ds.append(d); signs.append(int(np.sign(d)) if np.isfinite(d) else 0)
        dd,d25,d26=Ds
        stable=(support and np.isfinite(dd) and abs(dd)>=.10 and signs[0]!=0
                and signs[1]==signs[0] and signs[2]==signs[0]
                and abs(d25)>=.05 and abs(d26)>=.05)
        row["classification"]="STABLE_DIRECTIONAL_CELL" if stable else "UNSTABLE_OR_WEAK"
        rows.append(row)
    return pd.DataFrame(rows)

def transitions(a):
    idx=a.set_index("decision_time").market_state
    rows=[]
    for p in PARTS:
      q=a[(a.partition==p)&(a.market_state!="NEUTRAL_TRANSITION")]
      for mins in [15,30]:
        ft=pd.DatetimeIndex(q.decision_time)+pd.Timedelta(minutes=mins)
        dest=idx.reindex(ft).to_numpy()
        full=pd.DataFrame({
          "from_state":q.market_state.to_numpy(),
          "to_state":dest,
          "future_partition":[s3.partition(t) for t in ft]
        }).dropna()
        full=full[full.future_partition==p]
        for fs,g in full.groupby("from_state",sort=True):
          den=len(g)
          for ts,gg in g.groupby("to_state",sort=True):
            rows.append({"partition":p,"horizon_min":mins,"from_state":fs,"to_state":ts,
                         "n":int(len(gg)),"share":float(len(gg)/den),"from_total_n":int(den)})
    return pd.DataFrame(rows)

def audit(raw,a,specs):
    rows=[]
    def add(name,ok,value): rows.append({"audit":name,"pass":bool(ok),"value":value})
    gaps=int((raw.ts.diff().dropna()!=pd.Timedelta(minutes=5)).sum())
    add("raw_5m_contiguous",gaps==0,gaps)
    req=["oi_chg_15m","loc_24h","taker_imb_15m","quotevol_z_24h",
         "breakout_up_24h","breakout_down_24h","impulse5m_prev"]
    add("frozen_stage4_specs_present",all(x in specs for x in req),req)
    av=a[a.regime.isin(REGIMES)]
    add("regime_timestamp_causal",len(av)>0 and bool((av.regime_effective_ts<=av.decision_time_ns).all()),len(av))
    age=float(av.regime_age_min.max()) if len(av) else np.nan
    add("regime_age_le_45m",np.isfinite(age) and age<=45+1e-9,age)
    for p in PARTS:
        q=a[a.partition==p]; cov=float(q.regime.isin(REGIMES).mean()) if len(q) else 0
        add("regime_coverage_"+p,cov>0,cov)
    add("market_state_mutually_exclusive_complete",bool(a.market_state.isin(ARCHETYPES).all()),
        int((~a.market_state.isin(ARCHETYPES)).sum()))
    seq=a[a.post_downbreak_oi_contract_30m]
    add("stage5a_sequence_tag_exact",
        bool((seq.oi_state=="CONTRACT").all() and seq.downbreak_lag30.all()) if len(seq) else True,int(len(seq)))
    dom=[c for c in a.columns if c.lower().startswith(("btcd","usdtd"))]
    add("no_dominance_state_splitter",len(dom)==0,dom)
    return pd.DataFrame(rows)

def main():
    raw,a=prepare_relationship_data()
    specs=load_stage4_specs()
    hourly=build_hourly_regime(raw)
    a=attach_regime(a,hourly)
    a=attach_buckets(a,specs)
    a=build_state_tags(a)

    base=baselines(a)
    rdf=summarize_regimes(a)
    sdf=summarize_states(a,base)
    cdf=summarize_cells(a)
    tdf=transitions(a)
    adf=audit(raw,a,specs)

    rdf.to_csv(OUT_REGIME,index=False); sdf.to_csv(OUT_STATES,index=False)
    cdf.to_csv(OUT_CELLS,index=False); tdf.to_csv(OUT_TRANS,index=False); adf.to_csv(OUT_AUDIT,index=False)

    repd=sdf[sdf.classification.str.contains("REPLICATED_DIRECTIONAL_STATE",na=False)]
    repe=sdf[sdf.classification.str.contains("REPLICATED_EXPANSION_STATE",na=False)]
    stable=cdf[cdf.classification=="STABLE_DIRECTIONAL_CELL"]
    status=("SOL_INDICATOR_RELATIONSHIP_S6_COMPLETED_WITH_REPLICATED_STATES"
            if len(repd) or len(repe) or len(stable) else "SOL_INDICATOR_RELATIONSHIP_S6_COMPLETED_NO_REPLICATED_STATE")
    coverage={p:float(a[a.partition==p].regime.isin(REGIMES).mean()) for p in PARTS}
    payload={
      "status":status,"decision_rows":int(len(a)),
      "regime_model":"V1.5 adaptive BULL + V1 BEAR + V1 SIDEWAYS; conflict->TRANSITION",
      "regime_coverage":coverage,"partition_baselines":base,
      "replicated_directional_states":repd.to_dict(orient="records"),
      "replicated_expansion_states":repe.to_dict(orient="records"),
      "stable_regime_state_cells":stable.to_dict(orient="records"),
      "audit_pass":bool(adf["pass"].all()),"audit":adf.to_dict(orient="records")
    }
    OUT_JSON.write_text(json.dumps(payload,indent=2,default=str)+"\n")
    OUT_STATUS.write_text(status+"\n")

    lines=["# SOL Indicator Relationship Discovery — Stage 6 Result","",
      "**Regime + market-state mapping. Research only; no entry rule is selected here.**","",
      f"- Decision rows: **{len(a):,}**",f"- Replicated directional states: **{len(repd)}**",
      f"- Replicated expansion states: **{len(repe)}**",f"- Stable regime × state cells: **{len(stable)}**","",
      "## Regime baseline","",
      "| Regime | Partition | N | LONG | SHORT | D | Expansion |",
      "|---|---|---:|---:|---:|---:|---:|"]
    for r in rdf.itertuples(index=False):
        lines.append(f"| {r.regime} | {r.partition} | {r.n} | {pct(r.long_rate)} | {pct(r.short_rate)} | {pct(r.D)} | {pct(r.expansion_rate)} |")
    lines+=["","## Replicated market states","",
      "| State | Class | DEV N | DEV D | 2025 D | 2026 D | DEV Exp lift | 2025 | 2026 |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
    reps=sdf[sdf.classification!="UNSTABLE_OR_WEAK"]
    if len(reps):
      for r in reps.itertuples(index=False):
        lines.append(f"| {r.market_state} | {r.classification} | {r.development_n} | {pct(r.development_D)} | {pct(r.validation_2025_D)} | {pct(r.validation_2026_D)} | {pct(r.development_expansion_lift_pp)} | {pct(r.validation_2025_expansion_lift_pp)} | {pct(r.validation_2026_expansion_lift_pp)} |")
    else: lines.append("| none | - | - | - | - | - | - | - | - |")
    lines+=["","## Stable regime × state cells","",
      "| Regime | State | DEV N/D | 2025 N/D | 2026 N/D |","|---|---|---:|---:|---:|"]
    if len(stable):
      for r in stable.itertuples(index=False):
        lines.append(f"| {r.regime} | {r.market_state} | {r.development_n}/{pct(r.development_D)} | {r.validation_2025_n}/{pct(r.validation_2025_D)} | {r.validation_2026_n}/{pct(r.validation_2026_D)} |")
    else: lines.append("| none | - | - | - | - |")
    lines+=["","## Lifecycle self-persistence","",
      "| Partition | State | +15m same-state | +30m same-state |","|---|---|---:|---:|"]
    for p in PARTS:
      for st in ARCHETYPES:
        if st=="NEUTRAL_TRANSITION": continue
        occurred=tdf[(tdf.partition==p)&(tdf.from_state==st)]
        if not len(occurred): continue
        vals=[]
        for mins in [15,30]:
          q=tdf[(tdf.partition==p)&(tdf.horizon_min==mins)&(tdf.from_state==st)&(tdf.to_state==st)]
          vals.append(float(q.share.iloc[0]) if len(q) else np.nan)
        lines.append(f"| {p} | {st} | {pct(vals[0])} | {pct(vals[1])} |")
    lines+=["","## Guardrail","",
      "State names ending in _LIKE are economic interpretations of observed configurations, not causal proof.",
      "BTC.D / USDT.D are not state splitters because Stage 5B found no replicated incremental information.",
      "Stage 7 may only consider states that survive the frozen Stage-6 replication gates; Stage 6 itself does not authorize LONG/SHORT trades.","",
      f"**Status: {status}**"]
    OUT_MD.write_text("\n".join(lines)+"\n")
    print(OUT_MD.read_text())

if __name__=="__main__":
    main()
