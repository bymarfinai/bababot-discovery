#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A27_PATH=Path(__file__).resolve().parent/"sol_long_15utc_reclaim_conversion_a27.py"
spec=importlib.util.spec_from_file_location("a27",A27_PATH)
a27=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a27)
a26=a27.a26; a4=a27.a4; a2=a27.a2

OUT_MD=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_Result.md"
OUT_COHORT=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_COHORT.csv"
OUT_SUM=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_SUMMARY.csv"
OUT_SNAP=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_SNAPSHOTS.csv"
OUT_SEP=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_SEPARATION.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_RC30C2_POSTENTRY_ANATOMY_A30_Status.txt"

CELLS=a27.CELLS; LANE="RC30_C2"; LEVELS=(.10,.20,.30,.40); SNAPS=(5,10,15,30,60)

def fmt(v,d=3):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"

def anatomy_one(m,p,t):
    idx=m["idx"]; op=m["open"]; hi=m["high"]; lo=m["low"]; cl=m["close"]
    ei=int(idx.searchsorted(pd.Timestamp(t.reentry_ts),"left")); xi=int(idx.searchsorted(pd.Timestamp(t.exit_ts),"left"))
    if ei>=len(idx) or xi>=len(idx) or idx[ei]!=pd.Timestamp(t.reentry_ts) or idx[xi]!=pd.Timestamp(t.exit_ts): return None,[]
    H=float(p.H); R=float(p.R); entry=float(t.reentry_price); entry_R=(entry-H)/R
    seg_hi=np.asarray(hi[ei:xi+1],float); seg_lo=np.asarray(lo[ei:xi+1],float); seg_cl=np.asarray(cl[ei:xi+1],float)
    max_R=(float(seg_hi.max())-H)/R; min_R=(float(seg_lo.min())-H)/R
    out={"role":p.role,"partition":p.partition,"dev_block":p.dev_block,"ref_min":getattr(p,"ref_min",np.nan),"hour":getattr(p,"hour",np.nan),
         "parent_entry_ts":p.entry_ts,"parent_exit_ts":p.exit_ts,"reentry_ts":t.reentry_ts,"recovery_exit_ts":t.exit_ts,"exit_reason":t.exit_reason,
         "parent_pnl":float(p.pnl),"parent_loss_dollars":float(-p.pnl),"parent_loss_ret":float(-p.pnl/a2.NOTIONAL),
         "entry_price":entry,"entry_R":entry_R,"remaining_E40_R":.40-entry_R,"risk_to_H_R":entry_R,
         "reward_to_Hrisk":((.40-entry_R)/entry_R if entry_R>0 else np.inf),
         "required_recovery_ret_to_episode_be":float(-p.pnl/a2.NOTIONAL),"required_exit_price_to_episode_be":entry*(1.0+float(-p.pnl/a2.NOTIONAL)),
         "required_exit_R_to_episode_be":(entry*(1.0+float(-p.pnl/a2.NOTIONAL))-H)/R,
         "recovery_pnl":float(t.recovery_pnl),"recovery_pnl_5bps":float(t.recovery_pnl_5bps),"combined_episode_pnl":float(t.combined_episode_pnl),
         "recovery_hold_min":float((pd.Timestamp(t.exit_ts)-pd.Timestamp(t.reentry_ts))/pd.Timedelta(minutes=1)),
         "max_price_R":max_R,"min_price_R":min_R,"mfe_from_entry_R":max(0.,max_R-entry_R),"mae_from_entry_R":max(0.,entry_R-min_R)}
    if str(t.exit_reason)=="TARGET": oc="REC_TARGET"
    elif float(t.recovery_pnl)>0: oc="REC_POSITIVE_OTHER"
    else: oc="REC_FAIL"
    out["outcome_class"]=oc; out["recovery_win"]=float(t.recovery_pnl)>0; out["episode_rescue"]=float(t.combined_episode_pnl)>0
    for lv in LEVELS:
        hit=-1
        target=H+lv*R
        # no credit on re-entry bar; first actionable target touch starts next bar as in frozen recovery lifecycle
        for i in range(ei+1,xi+1):
            if float(hi[i])>=target: hit=i; break
        key=int(round(lv*100))
        out[f"hit_E{key:02d}"]=hit>=0
        out[f"hit_E{key:02d}_min"]=float((idx[hit]-idx[ei])/pd.Timedelta(minutes=1)) if hit>=0 else np.nan
        # counterfactual anatomy only: if fixed target were filled at exact level, does it cover the original parent loss?
        target_pnl=(target/entry-1.0)*a2.NOTIONAL
        out[f"E{key:02d}_episode_rescue_if_hit"]=bool(hit>=0 and float(p.pnl)+target_pnl>0)
    fail_close_overshoot=np.nan; fail_open_overshoot=np.nan
    if str(t.exit_reason)=="FAILED_RECLAIM" and pd.notna(t.invalidation_close_ts):
        fi=int(idx.searchsorted(pd.Timestamp(t.invalidation_close_ts),"left"))
        if fi<len(idx) and idx[fi]==pd.Timestamp(t.invalidation_close_ts):
            fail_close_overshoot=(H-float(cl[fi]))/R
            ni=fi+1
            if ni<len(idx): fail_open_overshoot=(H-float(op[ni]))/R
    out["fail_close_below_H_R"]=fail_close_overshoot; out["exit_open_below_H_R"]=fail_open_overshoot
    snaps=[]
    for sm in SNAPS:
        si=ei+(sm//5)-1
        if si>xi or si>=len(idx): continue
        sh=np.asarray(hi[ei:si+1],float); sl=np.asarray(lo[ei:si+1],float); sc=np.asarray(cl[ei:si+1],float)
        snaps.append({"role":p.role,"partition":p.partition,"ref_min":getattr(p,"ref_min",np.nan),"hour":getattr(p,"hour",np.nan),
                      "parent_entry_ts":p.entry_ts,"outcome_class":oc,"recovery_win":out["recovery_win"],"snapshot_min":sm,
                      "close_R":(float(sc[-1])-H)/R,"running_mfe_from_entry_R":max(0.,(float(sh.max())-entry)/R),
                      "running_mae_from_entry_R":max(0.,(entry-float(sl.min()))/R),"closes_above_H":int((sc>H).sum()),"closes_le_H":int((sc<=H).sum())})
    return out,snaps

def build(m):
    rows=[]; snaps=[]
    for role,ref,hour in CELLS:
      for part in ("development","external","reference_validation"):
        p=a26.parent_cell(m,part,role,ref,hour); pm={pd.Timestamp(r.entry_ts):r for _,r in p.iterrows()}; t=a27.simulate_lane(m,p,LANE)
        for _,z in t.iterrows():
            pr=pm.get(pd.Timestamp(z.parent_entry_ts));
            if pr is None: continue
            a,ss=anatomy_one(m,pr,z)
            if a is not None:
                a["ref_min"]=ref; a["hour"]=hour; rows.append(a)
                for s in ss: s["ref_min"]=ref; s["hour"]=hour; snaps.append(s)
    return pd.DataFrame(rows),pd.DataFrame(snaps)

def summarize(cohort):
    rows=[]
    for (role,part,oc),q in cohort.groupby(["role","partition","outcome_class"],sort=False):
        row={"role":role,"partition":part,"outcome_class":oc,"n":len(q),"episode_rescue_rate":float(q.episode_rescue.mean()),
             "median_entry_R":float(q.entry_R.median()),"median_reward_risk":float(q.reward_to_Hrisk.replace(np.inf,np.nan).median()),
             "median_mfe_entry_R":float(q.mfe_from_entry_R.median()),"median_mae_entry_R":float(q.mae_from_entry_R.median()),
             "median_parent_loss":float(q.parent_loss_dollars.median()),"median_required_exit_R":float(q.required_exit_R_to_episode_be.median()),
             "median_hold_min":float(q.recovery_hold_min.median())}
        for lv in LEVELS:
            k=int(round(lv*100)); row[f"hit_E{k:02d}_rate"]=float(q[f"hit_E{k:02d}"].mean()); row[f"E{k:02d}_rescue_if_hit_rate"]=float(q[f"E{k:02d}_episode_rescue_if_hit"].mean())
        rows.append(row)
    return pd.DataFrame(rows)

def separation(cohort,snaps):
    features=["entry_R","remaining_E40_R","risk_to_H_R","reward_to_Hrisk","parent_loss_dollars","required_exit_R_to_episode_be","mfe_from_entry_R","mae_from_entry_R","fail_close_below_H_R","exit_open_below_H_R"]
    rows=[]
    for (role,part),q in cohort.groupby(["role","partition"],sort=False):
      a=q[q.recovery_win]; b=q[~q.recovery_win]
      if len(a)<10 or len(b)<10: continue
      for f in features:
        x=pd.to_numeric(a[f],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna(); y=pd.to_numeric(b[f],errors="coerce").replace([np.inf,-np.inf],np.nan).dropna()
        if len(x)>=10 and len(y)>=10: rows.append({"role":role,"partition":part,"snapshot_min":0,"feature":f,"winner_median":float(x.median()),"fail_median":float(y.median()),"gap":float(x.median()-y.median())})
    for (role,part,sm),q in snaps.groupby(["role","partition","snapshot_min"],sort=False):
      a=q[q.recovery_win]; b=q[~q.recovery_win]
      if len(a)<10 or len(b)<10: continue
      for f in ["close_R","running_mfe_from_entry_R","running_mae_from_entry_R","closes_above_H","closes_le_H"]:
        x=pd.to_numeric(a[f],errors="coerce").dropna(); y=pd.to_numeric(b[f],errors="coerce").dropna()
        if len(x)>=10 and len(y)>=10: rows.append({"role":role,"partition":part,"snapshot_min":sm,"feature":f,"winner_median":float(x.median()),"fail_median":float(y.median()),"gap":float(x.median()-y.median())})
    raw=pd.DataFrame(rows); dev=raw[(raw.role=="CENTRAL")&(raw.partition=="development")].copy()
    ext=raw[(raw.role=="CENTRAL")&(raw.partition=="external")][["snapshot_min","feature","gap"]].rename(columns={"gap":"gap_ext"}); rv=raw[(raw.role=="CENTRAL")&(raw.partition=="reference_validation")][["snapshot_min","feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on=["snapshot_min","feature"],how="left").merge(rv,on=["snapshot_min","feature"],how="left").rename(columns={"gap":"gap_dev"})
    z["central_replicated"]=(np.sign(z.gap_dev)!=0)&(np.sign(z.gap_dev)==np.sign(z.gap_ext))&(np.sign(z.gap_dev)==np.sign(z.gap_rv))
    return z

def main():
    x,coverage=a2.a1.load5(); m=a2.make_market_with_open(x); cohort,snaps=build(m); summary=summarize(cohort); sep=separation(cohort,snaps)
    cohort.to_csv(OUT_COHORT,index=False); summary.to_csv(OUT_SUM,index=False); snaps.to_csv(OUT_SNAP,index=False); sep.to_csv(OUT_SEP,index=False)
    cd=cohort[(cohort.role=="CENTRAL")&(cohort.partition=="development")]; fail=cd[~cd.recovery_win]
    lines=["# SOL LONG 15:00 UTC RC30_C2 Post-Entry Anatomy — A30 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A30 is forensic only. It explains the payoff failure of the otherwise WR-improving RC30_C2 mechanism.","","## Central Development outcomes","",
      "| Outcome | N | Episode rescue | Entry R | Reward/H-risk | MFE after entry | MAE after entry | Parent loss | Required episode-BE exit R | Hold | E10 hit | E20 hit | E30 hit | E40 hit |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in summary[(summary.role=="CENTRAL")&(summary.partition=="development")].iterrows():
      lines.append(f"| {r.outcome_class} | {int(r.n)} | {pct(r.episode_rescue_rate)} | {fmt(r.median_entry_R)}R | {fmt(r.median_reward_risk,2)} | {fmt(r.median_mfe_entry_R)}R | {fmt(r.median_mae_entry_R)}R | ${fmt(r.median_parent_loss,2)} | {fmt(r.median_required_exit_R)}R | {fmt(r.median_hold_min,0)}m | {pct(r.hit_E10_rate)} | {pct(r.hit_E20_rate)} | {pct(r.hit_E30_rate)} | {pct(r.hit_E40_rate)} |")
    lines += ["","## RC30_C2 failures: lower target conversion opportunity","","| Level | Failure touch rate | Failure episode-rescue-if-hit rate |","|---|---:|---:|"]
    for lv in LEVELS:
        k=int(round(lv*100)); lines.append(f"| E{k:02d} | {pct(fail[f'hit_E{k:02d}'].mean() if len(fail) else np.nan)} | {pct(fail[f'E{k:02d}_episode_rescue_if_hit'].mean() if len(fail) else np.nan)} |")
    lines += ["","## Central-OOS replicated winner vs failure separation","","| Snapshot | Feature | Winner median | Failure median | Dev gap | External gap | RefVal gap |","|---|---|---:|---:|---:|---:|---:|"]
    for _,r in sep[sep.central_replicated].sort_values(["snapshot_min","feature"]).iterrows(): lines.append(f"| {'entry/path' if int(r.snapshot_min)==0 else '+'+str(int(r.snapshot_min))+'m'} | {r.feature} | {fmt(r.winner_median)} | {fmt(r.fail_median)} | {fmt(r.gap_dev)} | {fmt(r.gap_ext)} | {fmt(r.gap_rv)} |")
    # route decision: fixed levels among failures; material means >=20% touched AND >=15% of failures would rescue episode if exact target filled
    candidates=[]
    for lv in (.10,.20,.30):
        k=int(round(lv*100)); touch=float(fail[f"hit_E{k:02d}"].mean()) if len(fail) else 0.; rescue=float(fail[f"E{k:02d}_episode_rescue_if_hit"].mean()) if len(fail) else 0.
        if touch>=.20 and rescue>=.15: candidates.append((lv,touch,rescue))
    entry_rep=sep[(sep.central_replicated)&sep.feature.isin(["entry_R","reward_to_Hrisk"])]; route="TARGET" if candidates else ("ENTRY" if len(entry_rep) else "LIFECYCLE_OR_STOP")
    status="SOL_LONG_15UTC_RC30C2_POSTENTRY_A30_SUPPORTED_FOR_A31"
    lines += ["","## Decision","",f"Anatomy-indicated next route: **{route}**.","",f"**Status: {status}**","",
      "A31 may test only the fixed intervention family directly indicated above. No threshold grid or OOS retuning.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8"); OUT_STATUS.write_text(status+"\n",encoding="utf-8"); print(status)
if __name__=="__main__":main()
