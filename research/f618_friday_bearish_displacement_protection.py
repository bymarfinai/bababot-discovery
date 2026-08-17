#!/usr/bin/env python3
"""F6.18 — Friday post-+1R bearish-displacement protection.

Research only; live BBC untouched. Existing F6.12/F6.9/F6.5 unchanged.

This stage follows F6.17 forensic evidence but does NOT sweep body/wick thresholds.
One natural strong-body definition is frozen before execution:
    bearish real body > 2 * (upper wick + lower wick)
which means the directional body dominates at least two-thirds of the range.

All candidates require the existing F6.16 alert state at the exact same causal
+20m decision open after first +1R:
    median taker over the four known bars < 0 AND latest close < EMA7.

Predeclared displacement confirmations:
 D1 STRONG_BODY: alert + strong bearish body.
 D2 STRONG_BODY_RANGE_EXPAND: D1 + latest range > median range of prior 3 known bars.
 D3 STRONG_BODY_BREAK_PRIOR_LOW: D1 + latest close < previous completed 5m low.
 D4 STRONG_BODY_EMA20_LOSS: D1 + latest close < EMA20.

No alternative body ratio, wick threshold, timing, EMA, or range horizon is swept.
Action is at the same actual decision-time 5m open used by F6.16.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f616_friday_post1r_profit_protection as f616

OUT = Path(os.getenv("F618_OUT", "f618_out")); OUT.mkdir(parents=True, exist_ok=True)
R = f517.SL
RULES = [
    "D1_STRONG_BODY",
    "D2_STRONG_BODY_RANGE_EXPAND",
    "D3_STRONG_BODY_BREAK_PRIOR_LOW",
    "D4_STRONG_BODY_EMA20_LOSS",
]


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {"n":int(len(p)),"wins":wins,"losses":int(len(p)-wins),
            "wr":float(wins/len(p)) if len(p) else np.nan,
            "pnl":float(p.sum()),"pf":float(gp/gl) if gl>0 else math.inf,
            "dd":dd,"ls":int(ls)}


def displacement_state(k,tr,ps):
    if ps is None or not ps["P1_FLOW_EMA15"]: return None
    ht=ps["hit_t"]; dt=ps["decision_t"]
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    if len(w)!=4: return None
    last=w.iloc[-1]; prev=w.iloc[-2]
    rng=max(float(last.high-last.low),1e-12)
    body=abs(float(last.close-last.open))
    uw=float(last.high-max(last.open,last.close))
    lw=float(min(last.open,last.close)-last.low)
    total_wicks=uw+lw
    strong_body=bool(last.close<last.open and body > 2.0*total_wicks)
    prev3_ranges=(w.iloc[:3].high-w.iloc[:3].low).to_numpy(float)
    range_expand=bool(rng > float(np.median(prev3_ranges)))
    break_prior_low=bool(float(last.close) < float(prev.low))
    ema20_loss=bool(float(last.close) < float(last.ema20))
    return {
        "decision_t":dt,
        "decision_open":float(ps["decision_open"]),
        "last_body_ratio":body/rng,
        "last_upper_wick_ratio":uw/rng,
        "last_lower_wick_ratio":lw/rng,
        "last_range":rng,
        "prior3_range_med":float(np.median(prev3_ranges)),
        "strong_body":strong_body,
        "range_expand":range_expand,
        "break_prior_low":break_prior_low,
        "ema20_loss":ema20_loss,
        "D1_STRONG_BODY":strong_body,
        "D2_STRONG_BODY_RANGE_EXPAND":bool(strong_body and range_expand),
        "D3_STRONG_BODY_BREAK_PRIOR_LOW":bool(strong_body and break_prior_low),
        "D4_STRONG_BODY_EMA20_LOSS":bool(strong_body and ema20_loss),
    }


def apply(k,t,tr,ps,ds,rule):
    ev=f616.existing_events(k,t,tr)
    if ds is not None and ds[rule] and tr.exit_t>ds["decision_t"]:
        ev.append((ds["decision_t"],rule,f616.cut_pnl(tr.entry,ds["decision_open"])))
    if not ev: return float(tr.pnl),"PARENT",None
    ev.sort(key=lambda x:x[0]); dt,layer,pnl=ev[0]
    return float(pnl),layer,dt


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive="left",freq="D") if d.weekday()==4]
    parents=[]; rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz="UTC")+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        ps=f616.protection_state(k,tr); ds=displacement_state(k,tr,ps)
        existing=f616.existing_events(k,t,tr)
        if existing:
            existing.sort(key=lambda x:x[0]); base_pnl=float(existing[0][2]); base_layer=existing[0][1]
        else:
            base_pnl=float(tr.pnl); base_layer="PARENT"
        row={"i":i,"period":"discovery" if i<f517.SPLIT_N else "validation","date":tr.date,
             "parent_pnl":float(tr.pnl),"parent_win":bool(tr.pnl>0),"parent_mfe_r":float(tr.mfe/R),
             "existing_pnl":base_pnl,"existing_layer":base_layer,
             "p1_alert":bool(ps is not None and ps["P1_FLOW_EMA15"])}
        if ds is not None:
            for kk,v in ds.items():
                row[f"d_{kk}"]=str(v) if isinstance(v,pd.Timestamp) else v
        for rule in RULES:
            pnl,layer,dt=apply(k,t,tr,ps,ds,rule)
            row[f"{rule}_pnl"]=pnl; row[f"{rule}_layer"]=layer
            row[f"{rule}_inc"]=pnl-base_pnl
            row[f"{rule}_dt"]=None if dt is None else str(dt)
        rows.append(row)

    f517.assert_parent(parents)
    df=pd.DataFrame(rows); df.to_csv(OUT/"f618_rows.csv",index=False)
    parent_m=metrics(df.parent_pnl); existing_m=metrics(df.existing_pnl)
    if abs(existing_m["pnl"]-105.8182)>0.08:
        raise AssertionError(f"existing stack parity mismatch {existing_m}")

    # F6.16 alert parity before displacement filtering.
    active_alerts=0
    for _,r in df.iterrows():
        if not bool(r.get("p1_alert",False)): continue
        # Alert counts only when no earlier frozen event has already taken priority.
        i=int(r.i); d0=days[i]; t=pd.Timestamp(d0.date(),tz="UTC")+pd.Timedelta(hours=8)
        tr=parents[i]; ps=f616.protection_state(k,tr)
        if ps is None: continue
        pnl,layer,dt=f616.apply_rule(k,t,tr,ps,"P1_FLOW_EMA15")
        if layer=="P1_FLOW_EMA15": active_alerts+=1
    if active_alerts!=16:
        raise AssertionError(f"F6.16 P1 active alert parity mismatch {active_alerts}")

    out={"parent":parent_m,"existing_three_layer":existing_m,"active_p1_alerts":active_alerts,"rules":{}}
    for rule in RULES:
        pnlcol=f"{rule}_pnl"; layercol=f"{rule}_layer"; inccol=f"{rule}_inc"
        m=metrics(df[pnlcol]); acts=df[df[layercol]==rule].copy()
        d=df[df.i<f517.SPLIT_N]; v=df[df.i>=f517.SPLIT_N]
        truegb=acts[(acts.parent_pnl<=0)&(acts.parent_mfe_r>=1.0)&(acts.parent_mfe_r<2.0)]
        vals={
            "metrics":m,"incremental_vs_existing":float(m["pnl"]-existing_m["pnl"]),
            "incremental_discovery":float(d[inccol].sum()),"incremental_validation":float(v[inccol].sum()),
            "actions":int(len(acts)),"actions_D":int((acts.i<f517.SPLIT_N).sum()),"actions_V":int((acts.i>=f517.SPLIT_N).sum()),
            "parent_winners_acted":int(acts.parent_win.sum()),"parent_losses_acted":int((~acts.parent_win).sum()),
            "true_1r_givebacks_acted":int(len(truegb)),
            "loss_to_positive":int(((acts.parent_pnl<=0)&(acts[pnlcol]>0)).sum()),
            "winner_to_nonpositive":int(((acts.parent_pnl>0)&(acts[pnlcol]<=0)).sum()),
            "action_positive_inc":int((acts[inccol]>0).sum()),"action_negative_inc":int((acts[inccol]<0).sum()),
            "action_inc_sum":float(acts[inccol].sum()),
            "wr_gain_pp":float((m["wr"]-existing_m["wr"])*100),
            "dd_improvement":float(existing_m["dd"]-m["dd"]),
            "action_dates":acts[["date","period","parent_pnl","parent_mfe_r",pnlcol,inccol,
                                  "d_last_body_ratio","d_last_upper_wick_ratio","d_range_expand","d_break_prior_low","d_ema20_loss"]].to_dict("records") if len(acts) else [],
        }
        vals["screen_pass"]=bool(vals["incremental_vs_existing"]>0 and vals["incremental_discovery"]>=0 and vals["incremental_validation"]>=0 and vals["loss_to_positive"]>0)
        out["rules"][rule]=vals

    passed=[r for r in RULES if out["rules"][r]["screen_pass"]]
    out["screen_pass_rules"]=passed
    out["best_predeclared"]=max(passed,key=lambda r:out["rules"][r]["incremental_vs_existing"]) if passed else None
    (OUT/"f618_summary.json").write_text(json.dumps(out,indent=2,default=str))

    md=["# Friday F6.18 — Bearish Displacement Profit Protection","",
        "**Status: COMPLETE — same-sample provisional causal test; no threshold sweep.**",
        "**Live BBC untouched; F6.12/F6.9/F6.5 unchanged.**","",
        "Frozen strong-body definition: bearish body > 2 × total wicks. All rules require F6.16 +1R flow<0 + below-EMA7 alert and act at the same actual decision open.","",
        f"Existing 3-layer: PnL **{existing_m['pnl']:+.3f}**, WR **{existing_m['wr']*100:.2f}%**, PF **{existing_m['pf']:.3f}**, DD **{existing_m['dd']:.3f}**.","",
        "## Results"]
    for rule in RULES:
        x=out["rules"][rule]; m=x["metrics"]
        md += [f"### {rule}",
               f"- actions **{x['actions']}** (D {x['actions_D']} / V {x['actions_V']}); winners cut {x['parent_winners_acted']}; true +1R givebacks {x['true_1r_givebacks_acted']}",
               f"- incremental **{x['incremental_vs_existing']:+.3f}**; D/V **{x['incremental_discovery']:+.3f} / {x['incremental_validation']:+.3f}**",
               f"- loss→positive **{x['loss_to_positive']}**; winner→nonpositive **{x['winner_to_nonpositive']}**",
               f"- managed PnL **{m['pnl']:+.3f}**, WR **{m['wr']*100:.2f}%**, PF **{m['pf']:.3f}**, DD **{m['dd']:.3f}**",
               f"- screen **{'PASS' if x['screen_pass'] else 'FAIL'}**",""]
    md += ["## Verdict",f"Screen-pass: {', '.join(passed) if passed else 'none'}.",
           f"Best predeclared: **{out['best_predeclared']}**." if out['best_predeclared'] else "No displacement rule promoted.",
           "", "Guardrail: this rule family was motivated by F6.17 on the same historical sample. A PASS is same-sample provisional, not independent OOS confirmation."]
    (OUT/"F6.18_CHECKPOINT.md").write_text("\n".join(md)+"\n")
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=="__main__": main()
