#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A36_PATH=Path(__file__).resolve().parent/"sol_long_15utc_confirmed_e10_floor_a36.py"
spec=importlib.util.spec_from_file_location("a36",A36_PATH)
a36=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a36)
a34=a36.a34; a26=a36.a26; a2=a36.a2
CELLS=a36.CELLS

OUT_MD=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_Result.md"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_TRADES.csv"
OUT_SEP=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_SEPARATION.csv"
OUT_BLOCK=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_BLOCKS.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_Status.txt"

FEATURES=[
 "parent_loss_R","parent_mfe_R","parent_mae_R","parent_hold_min","ref_width_pct",
 "exit_to_signal_min","signal_to_confirm_min","signal_close_R","confirm_close_R","confirm_body_R",
 "max_close_R_to_confirm","running_mfe_R_to_confirm","running_mae_R_to_confirm","above_H_frac_to_confirm",
 "closes_above_H_to_confirm","reentry_R","preconfirm_30m_return_R","preexit_60m_return_R","preexit_60m_range_R"
]

def fmt(v,d=3):
    if pd.isna(v): return "-"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"
def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna(); gp=float(x[x>0].sum()); gl=float(-x[x<=0].sum())
    if gl==0:return np.inf if gp>0 else np.nan
    return gp/gl

def parent_features(m,r,z):
    idx=m["idx"]; op=m["open"]; hi=m["high"]; lo=m["low"]; cl=m["close"]
    H=float(r.H); R=float(r.R)
    ei=int(idx.searchsorted(pd.Timestamp(r.entry_ts),"left")); xi=int(idx.searchsorted(pd.Timestamp(r.exit_ts),"left"))
    si=int(idx.searchsorted(pd.Timestamp(z.signal_ts),"left")); ci=int(idx.searchsorted(pd.Timestamp(z.confirm_ts),"left")); ri=int(idx.searchsorted(pd.Timestamp(z.reentry_ts),"left"))
    pseg_hi=np.asarray(hi[ei:xi+1],float); pseg_lo=np.asarray(lo[ei:xi+1],float)
    ec=np.asarray(cl[xi:ci+1],float); eh=np.asarray(hi[xi:ci+1],float); el=np.asarray(lo[xi:ci+1],float)
    pc=max(0,ci-6); pre30=(float(cl[ci])-float(cl[pc]))/R if ci>pc else np.nan
    pe=max(0,xi-12); seg60c=np.asarray(cl[pe:xi+1],float); seg60h=np.asarray(hi[pe:xi+1],float); seg60l=np.asarray(lo[pe:xi+1],float)
    pre60=(float(cl[xi])-float(cl[pe]))/R if xi>pe else np.nan
    range60=(float(seg60h.max())-float(seg60l.min()))/R if len(seg60h) else np.nan
    signal_close_R=(float(cl[si])-H)/R
    confirm_close_R=(float(cl[ci])-H)/R
    confirm_body_R=(float(cl[ci])-float(op[ci]))/R
    return {
      "loss_class":getattr(r,"loss_class",None),
      "parent_loss_R":max(0.0,(-float(r.pnl)/a2.NOTIONAL)/(R/H)),
      "parent_mfe_R":max(0.0,(float(pseg_hi.max())-H)/R),
      "parent_mae_R":max(0.0,(H-float(pseg_lo.min()))/R),
      "parent_hold_min":float((pd.Timestamp(r.exit_ts)-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)),
      "ref_width_pct":R/H,
      "exit_to_signal_min":float((pd.Timestamp(z.signal_ts)-pd.Timestamp(r.exit_ts))/pd.Timedelta(minutes=1)),
      "signal_to_confirm_min":float((pd.Timestamp(z.confirm_ts)-pd.Timestamp(z.signal_ts))/pd.Timedelta(minutes=1)),
      "signal_close_R":signal_close_R,
      "confirm_close_R":confirm_close_R,
      "confirm_body_R":confirm_body_R,
      "max_close_R_to_confirm":float((ec.max()-H)/R),
      "running_mfe_R_to_confirm":max(0.0,(float(eh.max())-H)/R),
      "running_mae_R_to_confirm":max(0.0,(H-float(el.min()))/R),
      "above_H_frac_to_confirm":float((ec>H).mean()),
      "closes_above_H_to_confirm":int((ec>H).sum()),
      "reentry_R":float(z.reentry_R),
      "preconfirm_30m_return_R":pre30,
      "preexit_60m_return_R":pre60,
      "preexit_60m_range_R":range60,
    }

def build_cell(m,part,role,ref,hour):
    p=a26.parent_cell(m,part,role,ref,hour)
    t=a36.simulate(m,p)
    pmap={pd.Timestamp(r.entry_ts):r for _,r in p.iterrows()}
    rows=[]
    for _,z in t.iterrows():
        r=pmap.get(pd.Timestamp(z.parent_entry_ts))
        if r is None: continue
        f=parent_features(m,r,z)
        rows.append({**z.to_dict(),**f,
          "stress_outcome":"WIN" if float(z.recovery_pnl_5bps)>0 else "FAIL",
          "raw_outcome":"WIN" if float(z.recovery_pnl)>0 else "FAIL"})
    return pd.DataFrame(rows)

def robust_sep(q,feature):
    w=pd.to_numeric(q.loc[q.stress_outcome=="WIN",feature],errors="coerce").dropna()
    l=pd.to_numeric(q.loc[q.stress_outcome=="FAIL",feature],errors="coerce").dropna()
    if len(w)<4 or len(l)<4:return None
    wm=float(w.median()); lm=float(l.median()); gap=wm-lm
    wi=float(w.quantile(.75)-w.quantile(.25)); li=float(l.quantile(.75)-l.quantile(.25)); pooled=(wi+li)/2
    eff=abs(gap)/pooled if pooled>1e-12 else (np.inf if abs(gap)>1e-12 else 0.0)
    return len(w),len(l),wm,lm,gap,eff

def separation(allt):
    rows=[]
    for (role,part),q in allt.groupby(["role","partition"],sort=False):
        for f in FEATURES:
            z=robust_sep(q,f)
            if z is None: continue
            wn,ln,wm,lm,gap,eff=z
            rows.append({"role":role,"partition":part,"feature":f,"win_n":wn,"fail_n":ln,"win_median":wm,"fail_median":lm,"gap":gap,"effect":eff})
    s=pd.DataFrame(rows)
    dev=s[(s.role=="CENTRAL")&(s.partition=="development")].copy()
    ext=s[(s.role=="CENTRAL")&(s.partition=="external")][["feature","gap"]].rename(columns={"gap":"gap_ext"})
    rv=s[(s.role=="CENTRAL")&(s.partition=="reference_validation")][["feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on="feature",how="left").merge(rv,on="feature",how="left").rename(columns={"gap":"gap_dev","effect":"effect_dev"})
    supports=s[s.role!="CENTRAL"]
    same=[];avail=[]
    for _,r in z.iterrows():
        ss=supports[supports.feature==r.feature]; sg=np.sign(float(r.gap_dev)); dirs=np.sign(pd.to_numeric(ss.gap,errors="coerce"))
        same.append(int((dirs==sg).sum()) if sg!=0 else 0); avail.append(len(ss))
    z["support_same_direction"]=same; z["support_available"]=avail
    z["material_dev"]=z.effect_dev>=0.50
    z["central_replicated"]=z.material_dev & (np.sign(z.gap_dev)!=0) & (np.sign(z.gap_dev)==np.sign(z.gap_ext)) & (np.sign(z.gap_dev)==np.sign(z.gap_rv))
    z["strong_replicated"]=z.central_replicated & (z.support_available>=4) & (z.support_same_direction>=3)
    return s,z

def block_stats(dev,top):
    rows=[]
    for bi in range(6):
        q=dev[pd.to_numeric(dev.dev_block,errors="coerce")==bi].copy(); rp=pd.to_numeric(q.recovery_pnl,errors="coerce"); rp5=pd.to_numeric(q.recovery_pnl_5bps,errors="coerce")
        row={"block":bi+1,"n":len(q),"raw_wr":float((rp>0).mean()) if len(q) else np.nan,"stress_wr":float((rp5>0).mean()) if len(q) else np.nan,
             "raw_pf":pf(rp),"stress_pf":pf(rp5),"raw_net":float(rp.sum()),"stress_net":float(rp5.sum()),"rescue_rate":float(q.rescued.mean()) if len(q) else np.nan}
        for f in top: row[f"median_{f}"]=float(pd.to_numeric(q[f],errors="coerce").median()) if len(q) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x)
    frames=[]
    for role,ref,hour in CELLS:
      for part in ("development","external","reference_validation"):
        q=build_cell(m,part,role,ref,hour)
        if len(q):frames.append(q)
    allt=pd.concat(frames,ignore_index=True);allt.to_csv(OUT_TRADES,index=False)
    raw,rep=separation(allt);rep.to_csv(OUT_SEP,index=False)
    strong=rep[rep.strong_replicated].sort_values(["effect_dev","support_same_direction"],ascending=[False,False])
    top=list(strong.feature.head(4))
    dev=allt[(allt.role=="CENTRAL")&(allt.partition=="development")]
    blocks=block_stats(dev,top);blocks.to_csv(OUT_BLOCK,index=False)
    status="SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_SUPPORTED_FOR_A38" if len(strong)>=2 else "SOL_LONG_15UTC_A36_BLOCK_REGIME_A37_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC A36 Block / Regime Anatomy — A37 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A37 is forensic only. All studied features are observable by the A36 recovery entry.","",
      "## Strong replicated pre-entry separation","","| Feature | Stress-win median | Stress-fail median | Dev gap | Robust effect | External gap | RefVal gap | Support same dir |","|---|---:|---:|---:|---:|---:|---:|---:|"]
    if len(strong):
      for _,r in strong.iterrows():lines.append(f"| {r.feature} | {fmt(r.win_median)} | {fmt(r.fail_median)} | {fmt(r.gap_dev)} | {fmt(r.effect_dev,2)} | {fmt(r.gap_ext)} | {fmt(r.gap_rv)} | {int(r.support_same_direction)}/4 |")
    else:lines.append("| none | - | - | - | - | - | - | - |")
    lines += ["","## Development block anatomy","","| Block | N | Raw WR | Stress WR | Raw PF | Stress PF | Raw net | Stress net | Rescue |" + "".join([f" Median {f} |" for f in top]),
              "|---:|---:|---:|---:|---:|---:|---:|---:|---:|" + "---:|"*len(top)]
    for _,r in blocks.iterrows():
      lines.append(f"| {int(r.block)} | {int(r.n)} | {pct(r.raw_wr)} | {pct(r.stress_wr)} | {fmt(r.raw_pf,2)} | {fmt(r.stress_pf,2)} | ${fmt(r.raw_net,2)} | ${fmt(r.stress_net,2)} | {pct(r.rescue_rate)} |" + "".join([f" {fmt(r.get('median_'+f,np.nan))} |" for f in top]))
    lines += ["","## Decision","",f"Strong replicated causal features: **{len(strong)}**.","",f"**Status: {status}**","",
      "If supported, A38 may test at most three Development-derived guards from these features. No threshold grid and no OOS retuning.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
