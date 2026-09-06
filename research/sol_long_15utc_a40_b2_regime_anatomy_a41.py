#!/usr/bin/env python3
from __future__ import annotations
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
A40_PATH=Path(__file__).resolve().parent/"sol_long_15utc_confirmed_e20_continuation_a40.py"
spec=importlib.util.spec_from_file_location("a40",A40_PATH)
a40=importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(a40)
a36=a40.a36; a34=a40.a34; a26=a40.a26; a2=a40.a2; CELLS=a40.CELLS

OUT_MD=ROOT/"SOL_LONG_15UTC_A40_B2_REGIME_ANATOMY_A41_Result.md"
OUT_TRADES=ROOT/"SOL_LONG_15UTC_A40_B2_REGIME_ANATOMY_A41_TRADES.csv"
OUT_SEP=ROOT/"SOL_LONG_15UTC_A40_B2_REGIME_ANATOMY_A41_SEPARATION.csv"
OUT_BLOCK=ROOT/"SOL_LONG_15UTC_A40_B2_REGIME_ANATOMY_A41_BLOCKS.csv"
OUT_STATUS=ROOT/"SOL_LONG_15UTC_A40_B2_REGIME_ANATOMY_A41_Status.txt"

FEATURES=[
 "ref_width_pct","parent_mfe_R","parent_mae_R","parent_hold_min",
 "exit_to_signal_min","signal_to_confirm_min","confirm_to_e20_min",
 "confirm_close_R","confirm_body_R","running_mfe_R_to_confirm","running_mae_R_to_confirm",
 "preconfirm_30m_return_R","preexit_60m_return_R","preexit_60m_range_R",
 "preentry_30m_return_R","preentry_30m_range_R","preentry_60m_return_R","preentry_60m_range_R",
 "last_completed_close_R_before_e20"
]

def fmt(v,d=3):
    if pd.isna(v): return "-"
    if np.isinf(v): return "inf"
    return f"{float(v):.{d}f}"
def pct(v): return "-" if pd.isna(v) else f"{100*float(v):.1f}%"
def pf(v):
    x=pd.to_numeric(v,errors="coerce").dropna();gp=float(x[x>0].sum());gl=float(-x[x<=0].sum())
    if gl==0:return np.inf if gp>0 else np.nan
    return gp/gl

def enrich(m,r,z):
    idx=m["idx"];op=m["open"];hi=m["high"];lo=m["low"];cl=m["close"]
    H=float(r.H);R=float(r.R)
    ei=int(idx.searchsorted(pd.Timestamp(r.entry_ts),"left"));xi=int(idx.searchsorted(pd.Timestamp(r.exit_ts),"left"))
    si=int(idx.searchsorted(pd.Timestamp(z.signal_ts),"left"));ci=int(idx.searchsorted(pd.Timestamp(z.confirm_ts),"left"));ri=int(idx.searchsorted(pd.Timestamp(z.reentry_ts),"left"))
    p_hi=np.asarray(hi[ei:xi+1],float);p_lo=np.asarray(lo[ei:xi+1],float)
    ec=np.asarray(cl[xi:ci+1],float);eh=np.asarray(hi[xi:ci+1],float);el=np.asarray(lo[xi:ci+1],float)
    pc=max(0,ci-6);preconfirm=(float(cl[ci])-float(cl[pc]))/R if ci>pc else np.nan
    pe=max(0,xi-12);s60h=np.asarray(hi[pe:xi+1],float);s60l=np.asarray(lo[pe:xi+1],float)
    preexit=(float(cl[xi])-float(cl[pe]))/R if xi>pe else np.nan
    preexit_range=(float(s60h.max())-float(s60l.min()))/R if len(s60h) else np.nan
    last_i=ri-1
    p30=max(0,ri-6);q30h=np.asarray(hi[p30:ri],float);q30l=np.asarray(lo[p30:ri],float)
    p60=max(0,ri-12);q60h=np.asarray(hi[p60:ri],float);q60l=np.asarray(lo[p60:ri],float)
    pre30=(float(cl[last_i])-float(cl[p30]))/R if last_i>=p30 and last_i>=0 else np.nan
    pre60=(float(cl[last_i])-float(cl[p60]))/R if last_i>=p60 and last_i>=0 else np.nan
    r30=(float(q30h.max())-float(q30l.min()))/R if len(q30h) else np.nan
    r60=(float(q60h.max())-float(q60l.min()))/R if len(q60h) else np.nan
    return {
      "ref_width_pct":R/H,
      "parent_mfe_R":max(0.0,(float(p_hi.max())-H)/R),
      "parent_mae_R":max(0.0,(H-float(p_lo.min()))/R),
      "parent_hold_min":float((pd.Timestamp(r.exit_ts)-pd.Timestamp(r.entry_ts))/pd.Timedelta(minutes=1)),
      "exit_to_signal_min":float((pd.Timestamp(z.signal_ts)-pd.Timestamp(r.exit_ts))/pd.Timedelta(minutes=1)),
      "signal_to_confirm_min":float((pd.Timestamp(z.confirm_ts)-pd.Timestamp(z.signal_ts))/pd.Timedelta(minutes=1)),
      "confirm_to_e20_min":float((pd.Timestamp(z.reentry_ts)-pd.Timestamp(z.confirm_ts))/pd.Timedelta(minutes=1)),
      "confirm_close_R":float((cl[ci]-H)/R),
      "confirm_body_R":float((cl[ci]-op[ci])/R),
      "running_mfe_R_to_confirm":max(0.0,(float(eh.max())-H)/R),
      "running_mae_R_to_confirm":max(0.0,(H-float(el.min()))/R),
      "preconfirm_30m_return_R":preconfirm,
      "preexit_60m_return_R":preexit,
      "preexit_60m_range_R":preexit_range,
      "preentry_30m_return_R":pre30,
      "preentry_30m_range_R":r30,
      "preentry_60m_return_R":pre60,
      "preentry_60m_range_R":r60,
      "last_completed_close_R_before_e20":float((cl[last_i]-H)/R) if last_i>=0 else np.nan,
    }

def build_cell(m,part,role,ref,hour):
    p=a26.parent_cell(m,part,role,ref,hour);t=a40.simulate(m,p)
    pmap={pd.Timestamp(r.entry_ts):r for _,r in p.iterrows()}
    rows=[]
    for _,z in t.iterrows():
        r=pmap.get(pd.Timestamp(z.parent_entry_ts))
        if r is None:continue
        f=enrich(m,r,z)
        rows.append({**z.to_dict(),**f,
          "stress_outcome":"WIN" if float(z.recovery_pnl_5bps)>0 else "FAIL",
          "raw_outcome":"WIN" if float(z.recovery_pnl)>0 else "FAIL"})
    return pd.DataFrame(rows)

def robust_sep(q,f):
    w=pd.to_numeric(q.loc[q.stress_outcome=="WIN",f],errors="coerce").dropna();l=pd.to_numeric(q.loc[q.stress_outcome=="FAIL",f],errors="coerce").dropna()
    if len(w)<4 or len(l)<4:return None
    wm=float(w.median());lm=float(l.median());gap=wm-lm
    wi=float(w.quantile(.75)-w.quantile(.25));li=float(l.quantile(.75)-l.quantile(.25));pool=(wi+li)/2
    eff=abs(gap)/pool if pool>1e-12 else (np.inf if abs(gap)>1e-12 else 0.0)
    return wm,lm,gap,eff

def block_table(dev):
    rows=[]
    for bi in range(6):
        q=dev[pd.to_numeric(dev.dev_block,errors="coerce")==bi];rp=pd.to_numeric(q.recovery_pnl,errors="coerce");rp5=pd.to_numeric(q.recovery_pnl_5bps,errors="coerce")
        row={"block":bi+1,"n":len(q),"raw_wr":float((rp>0).mean()) if len(q) else np.nan,"stress_wr":float((rp5>0).mean()) if len(q) else np.nan,
             "raw_pf":pf(rp),"stress_pf":pf(rp5),"raw_net":float(rp.sum()),"stress_net":float(rp5.sum())}
        for f in FEATURES:row[f"median_{f}"]=float(pd.to_numeric(q[f],errors="coerce").median()) if len(q) else np.nan
        rows.append(row)
    return pd.DataFrame(rows)

def analyze(allt):
    rows=[]
    for (role,part),q in allt.groupby(["role","partition"],sort=False):
        for f in FEATURES:
            z=robust_sep(q,f)
            if z is None:continue
            wm,lm,gap,eff=z;rows.append({"role":role,"partition":part,"feature":f,"win_median":wm,"fail_median":lm,"gap":gap,"effect":eff})
    raw=pd.DataFrame(rows)
    dev=raw[(raw.role=="CENTRAL")&(raw.partition=="development")].copy()
    ext=raw[(raw.role=="CENTRAL")&(raw.partition=="external")][["feature","gap"]].rename(columns={"gap":"gap_ext"})
    rv=raw[(raw.role=="CENTRAL")&(raw.partition=="reference_validation")][["feature","gap"]].rename(columns={"gap":"gap_rv"})
    z=dev.merge(ext,on="feature",how="left").merge(rv,on="feature",how="left").rename(columns={"gap":"gap_dev","effect":"effect_dev"})
    devtr=allt[(allt.role=="CENTRAL")&(allt.partition=="development")]
    b2=devtr[pd.to_numeric(devtr.dev_block,errors="coerce")==1]
    pos=devtr[pd.to_numeric(devtr.dev_block,errors="coerce").isin([0,4,5])]
    b2med=[];posmed=[];b2_fail_side=[]
    for _,r in z.iterrows():
        f=r.feature;bm=float(pd.to_numeric(b2[f],errors="coerce").median());pm=float(pd.to_numeric(pos[f],errors="coerce").median());sg=np.sign(float(r.gap_dev))
        # win direction positive => fail side lower; win direction negative => fail side higher
        fail_side=(bm<pm) if sg>0 else ((bm>pm) if sg<0 else False)
        b2med.append(bm);posmed.append(pm);b2_fail_side.append(bool(fail_side))
    z["b2_median"]=b2med;z["positive_blocks_median"]=posmed;z["b2_on_fail_side"]=b2_fail_side
    supports=raw[(raw.role!="CENTRAL")&(raw.partition.isin(["external","reference_validation"]))]
    same=[];avail=[]
    for _,r in z.iterrows():
        ss=supports[supports.feature==r.feature];sg=np.sign(float(r.gap_dev));dirs=np.sign(pd.to_numeric(ss.gap,errors="coerce"))
        same.append(int((dirs==sg).sum()) if sg!=0 else 0);avail.append(len(ss))
    z["support_same_direction"]=same;z["support_available"]=avail
    z["strong"]=((z.effect_dev>=.50)&z.b2_on_fail_side&(np.sign(z.gap_dev)!=0)&(np.sign(z.gap_dev)==np.sign(z.gap_ext))&(np.sign(z.gap_dev)==np.sign(z.gap_rv))&(z.support_available==4)&(z.support_same_direction>=3))
    return raw,z

def main():
    x,coverage=a2.a1.load5();m=a2.make_market_with_open(x);frames=[]
    for role,ref,hour in CELLS:
      for part in ("development","external","reference_validation"):
        q=build_cell(m,part,role,ref,hour)
        if len(q):frames.append(q)
    allt=pd.concat(frames,ignore_index=True);allt.to_csv(OUT_TRADES,index=False)
    raw,rep=analyze(allt);rep.to_csv(OUT_SEP,index=False)
    dev=allt[(allt.role=="CENTRAL")&(allt.partition=="development")];blocks=block_table(dev);blocks.to_csv(OUT_BLOCK,index=False)
    strong=rep[rep.strong].sort_values(["effect_dev","support_same_direction"],ascending=[False,False])
    status="SOL_LONG_15UTC_A40_B2_REGIME_A41_SUPPORTED_FOR_A42" if len(strong)>=1 else "SOL_LONG_15UTC_A40_B2_REGIME_A41_INCONCLUSIVE"
    lines=["# SOL LONG 15:00 UTC A40 B2 Regime Anatomy — A41 Result","",f"Raw SOLUSDT 5m coverage: **{100*coverage:.4f}%**.","",
      "A41 is forensic only. E20/E10/E40 geometry is frozen; all features are observable by the E20 entry.","","## Strong replicated B2 separators","",
      "| Feature | Stress-win median | Stress-fail median | Dev gap | Effect | B2 median | B1/B5/B6 median | External gap | RefVal gap | Support |","|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    if len(strong):
      for _,r in strong.iterrows():lines.append(f"| {r.feature} | {fmt(r.win_median)} | {fmt(r.fail_median)} | {fmt(r.gap_dev)} | {fmt(r.effect_dev,2)} | {fmt(r.b2_median)} | {fmt(r.positive_blocks_median)} | {fmt(r.gap_ext)} | {fmt(r.gap_rv)} | {int(r.support_same_direction)}/4 |")
    else:lines.append("| none | - | - | - | - | - | - | - | - | - |")
    lines += ["","## Development blocks","","| Block | N | WR | Stress WR | PF | Stress PF | Net | Stress Net |","|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for _,r in blocks.iterrows():lines.append(f"| {int(r.block)} | {int(r.n)} | {pct(r.raw_wr)} | {pct(r.stress_wr)} | {fmt(r.raw_pf,2)} | {fmt(r.stress_pf,2)} | ${fmt(r.raw_net,2)} | ${fmt(r.stress_net,2)} |")
    lines += ["","## Decision","",f"Strong B2 separators: **{len(strong)}**.","",f"**Status: {status}**","",
      "If supported, A42 may test at most three Development-midpoint guards from these exact features. No E20/E10 change and no OOS retuning.","","Research only. Live Baba Bot remains unchanged."]
    OUT_MD.write_text("\n".join(lines)+"\n",encoding="utf-8");OUT_STATUS.write_text(status+"\n",encoding="utf-8");print(status)
if __name__=="__main__":main()
