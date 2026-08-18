#!/usr/bin/env python3
"""Sunday Friday-method SF9 — frozen SF6-SF8 + predeclared Sunday FastMR overlay.

Research only; live BBC untouched.

Frozen baseline (must reproduce exactly):
- Sunday 16:00 WIB SELL
- TP2.5%, SL1.4%, max18h
- SF6-SF8 confirmed-failure management frozen in
  BTC_Temporal_Sunday16_FridayMethod_Frozen_Candidate.md

New layer under test: the ALREADY-SELECTED Sunday-scaled FastMR rule from the prior
Tuesday-method branch. No re-sweep and no retuning:
- first +1.00% favorable MFE hinge
- hinge close >=0.60% below EMA20
- within 2h after hinge, completed close gives back to <=+0.60% SELL progress
- arm +0.40% profit lock from next decision open
- no EMA7 runner recovery

Chronology:
- SF6-SF8 remains frozen and can schedule a +7h CUT.
- FastMR may act only while the frozen baseline trade is still alive.
- whichever executable exit occurs first wins; no retrospective cancellation.
- completed 5m bars only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sunday_fridaymethod_sf6_sf8_confirmed_failure as sf68
import sunday_tmethod_st8_fastmr_family as st8

OUT=Path(os.getenv('SUNFM9_OUT','sunfm9_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83
HINGE=0.010
D20=0.006
GIVEBACK=0.006
LATENCY=120
LOCK=0.004


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'pf':None,'dd':0.0,'ls':0,'exp':None}
    wins=int((a>0).sum());gp=float(a[a>0].sum());gl=float(-a[a<=0].sum())
    eq=np.cumsum(a);peak=np.maximum.accumulate(np.r_[0.,eq]);dd=float(np.max(peak[1:]-eq));cur=ls=0
    for x in a:
        if x<=0:cur+=1;ls=max(ls,cur)
        else:cur=0
    return {'n':int(len(a)),'wins':wins,'losses':int(len(a)-wins),'wr':float(wins/len(a)),
            'pnl':float(a.sum()),'pf':float(gp/gl) if gl>0 else 999.0,'dd':dd,'ls':int(ls),'exp':float(a.mean())}


def funding_pnl(k,f,tr,dt,px):
    # Same Sunday exact-funding/live-decision convention used by frozen SF6-SF8.
    return sf68.funding_pnl(k,f,tr,dt,px)


def frozen_baseline(k,f,tr):
    """Return frozen SF6-SF8 outcome and executable exit anchor."""
    s6=sf68.state(k,tr,360); cand=sf68.candidate6(s6)
    out={'pnl':float(tr['pnl']),'exit_t':tr['exit_t'],'exit_px':float(tr['exit_px']),
         'layer':'PARENT','candidate6':bool(cand)}
    if not cand:
        return out
    s7=sf68.state(k,tr,420)
    if s7 is None:
        out['layer']='PARENT_EXIT_BEFORE7'
        return out
    fl=sf68.flow67(k,tr)
    price_repair=bool(s7['last_close']<s6['last_close'])
    flow_repair=bool(np.isfinite(fl) and fl<0)
    if price_repair or flow_repair:
        out['layer']='RECOVERY7_HOLD'
        return out
    out['pnl']=funding_pnl(k,f,tr,s7['dt'],s7['open'])
    out['exit_t']=s7['dt']
    out['exit_px']=float(s7['open'])
    out['layer']='CUT7'
    return out


def first_hinge_before(k,tr,exit_t):
    t=tr['entry_t'];ep=float(tr['entry'])
    bars=k[(k.index>=t)&(k.index<exit_t)]
    for b in bars.itertuples(index=False):
        if 1.0-float(b.low)/ep >= HINGE:
            dt=b.ts+pd.Timedelta(minutes=5)
            if exit_t<=dt:return None
            return {'bar_t':b.ts,'decision_t':dt}
    return None


def fastmr_arm_before(k,tr,exit_t):
    h=first_hinge_before(k,tr,exit_t)
    if h is None:return None
    hb=k.loc[h['bar_t']]
    d20=float(hb.ema20)/float(hb.close)-1.0
    if d20<D20:return None
    start=h['decision_t'];end=min(exit_t,start+pd.Timedelta(minutes=LATENCY));ep=float(tr['entry'])
    for b in k[(k.index>=start)&(k.index<end)].itertuples(index=False):
        prog=1.0-float(b.close)/ep
        if prog<=GIVEBACK:
            dt=b.ts+pd.Timedelta(minutes=5)
            if exit_t<=dt:return None
            return {'decision_t':dt,'hinge_t':h['bar_t'],'d20':d20,'progress':prog}
    return None


def overlay_outcome(k,f,tr,base):
    """Apply fixed FastMR only until the frozen baseline exit; earliest exit wins."""
    a=fastmr_arm_before(k,tr,base['exit_t'])
    if a is None:
        return {**base,'fastmr_arm':False,'fastmr_lock_exit':False,'fastmr_decision_t':None}
    ep=float(tr['entry']);lp=ep*(1-LOCK);d=a['decision_t']
    if d not in k.index:
        return {**base,'fastmr_arm':False,'fastmr_lock_exit':False,'fastmr_decision_t':None}
    op=float(k.loc[d,'open'])
    # If the protective level is already lost by the decision open, exit at actual open.
    if op>=lp:
        return {'pnl':funding_pnl(k,f,tr,d,op),'exit_t':d,'exit_px':op,'layer':'FASTMR_MARKET',
                'candidate6':base['candidate6'],'fastmr_arm':True,'fastmr_lock_exit':True,
                'fastmr_decision_t':d,'d20':a['d20'],'giveback_progress':a['progress']}
    # Otherwise the +0.40 protective stop stays live until frozen baseline exit.
    for b in k[(k.index>=d)&(k.index<base['exit_t'])].itertuples(index=False):
        if float(b.high)>=lp:
            et=b.ts+pd.Timedelta(minutes=5)
            return {'pnl':funding_pnl(k,f,tr,b.ts,lp),'exit_t':b.ts,'exit_px':lp,'layer':'FASTMR_LOCK',
                    'candidate6':base['candidate6'],'fastmr_arm':True,'fastmr_lock_exit':True,
                    'fastmr_decision_t':d,'d20':a['d20'],'giveback_progress':a['progress']}
    return {**base,'fastmr_arm':True,'fastmr_lock_exit':False,'fastmr_decision_t':d,
            'd20':a['d20'],'giveback_progress':a['progress']}


def pack(a):
    a=np.asarray(a,float)
    return {'full':metrics(a),'D':metrics(a[:DISC_N]),'V':metrics(a[DISC_N:])}


def main():
    k=f517.load_klines();f=s50.load_funding();trs=[sf68.sun17.simulate_parent(k,f,t) for t in sf68.sun17.entries(k)]
    parent=np.asarray([float(tr['pnl']) for tr in trs])
    if len(parent)!=139 or int((parent>0).sum())!=66 or abs(parent.sum()-63.599379132074105)>0.25:
        raise RuntimeError(f'parent parity failed {metrics(parent)}')

    # Old standalone FastMR parity, unchanged from previous branch.
    hs=[st8.hinfo(k,tr) for tr in trs]
    old_fast=[]
    for tr,h in zip(trs,hs):
        a=st8.arm(k,tr,h,D20,GIVEBACK,LATENCY)
        p,_,_=st8.lock_outcome(k,f,tr,a,False,GIVEBACK)
        old_fast.append(p)
    old_fast=np.asarray(old_fast,float)
    if abs(old_fast.sum()-68.17)>0.30:
        raise RuntimeError(f'old FastMR parity failed {metrics(old_fast)}')

    baselines=[];combined=[];rows=[]
    for i,tr in enumerate(trs):
        b=frozen_baseline(k,f,tr);o=overlay_outcome(k,f,tr,b)
        baselines.append(b['pnl']);combined.append(o['pnl'])
        rows.append({'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),
                     'parent_pnl':float(tr['pnl']),'frozen_pnl':float(b['pnl']),'frozen_layer':b['layer'],
                     'combined_pnl':float(o['pnl']),'combined_layer':o['layer'],
                     'incremental':float(o['pnl']-b['pnl']),'candidate6':bool(b['candidate6']),
                     'fastmr_arm':bool(o.get('fastmr_arm',False)),'fastmr_lock_exit':bool(o.get('fastmr_lock_exit',False)),
                     'fastmr_decision_t':None if o.get('fastmr_decision_t') is None else str(o.get('fastmr_decision_t')),
                     'd20':o.get('d20'), 'giveback_progress':o.get('giveback_progress')})
    baselines=np.asarray(baselines,float);combined=np.asarray(combined,float);df=pd.DataFrame(rows)
    B=pack(baselines);C=pack(combined);P=pack(parent);F=pack(old_fast)
    if abs(B['full']['pnl']-75.25)>0.30 or int(B['full']['wins'])!=66:
        raise RuntimeError(f'frozen SF6-SF8 parity failed {B}')

    acts=df[df.fastmr_arm==True].copy();exits=df[df.fastmr_lock_exit==True].copy()
    inc=combined-baselines
    blocks=[metrics(combined[z]) for z in np.array_split(np.arange(139),8)]
    out={
      'status':'COMPLETE_SUNDAY_FROZEN_SF68_PLUS_FIXED_FASTMR',
      'frozen_definition':'Sunday16 SELL TP2.5 SL1.4 18h + frozen SF6-SF8 confirmed-failure management',
      'fastmr_definition':'+1.0% MFE hinge; hinge >=0.60% below EMA20; <=+0.60% progress giveback within2h; arm +0.40% lock; no runner recovery',
      'parent':P,'standalone_old_fastmr':F,'frozen_sf68':B,'combined':C,
      'fastmr_arms':int(len(acts)),'fastmr_arms_D':int((acts.i<DISC_N).sum()),'fastmr_arms_V':int((acts.i>=DISC_N).sum()),
      'fastmr_lock_exits':int(len(exits)),
      'incremental_full':float(inc.sum()),'incremental_D':float(inc[:DISC_N].sum()),'incremental_V':float(inc[DISC_N:].sum()),
      'frozen_winner_to_nonpositive':int(((df.frozen_pnl>0)&(df.combined_pnl<=0)).sum()),
      'frozen_loss_to_positive':int(((df.frozen_pnl<=0)&(df.combined_pnl>0)).sum()),
      'positive_blocks':int(sum(x['pnl']>0 for x in blocks)),
      'guardrail':'SF6-SF8 was frozen before this test. FastMR parameters are reused unchanged from prior Sunday T-method selection; no new threshold/timing selection is performed here. D/V remain robustness slices, not untouched OOS.'
    }
    df.to_csv(OUT/'sunfm9_rows.csv',index=False)
    (OUT/'sunfm9_summary.json').write_text(json.dumps(out,indent=2,default=str))
    def wr(m):return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday Friday-Method SF9 — Frozen SF6-SF8 + Fixed FastMR','',
        '**Status: COMPLETE — frozen Friday-style baseline plus predeclared FastMR overlay; live BBC untouched.**','',
        '## Frozen baseline','- Sunday16 SELL / TP2.5 / SL1.4 / 18h + frozen SF6-SF8.','',
        '## Added FastMR (NO RETUNING)','- +1.00% favorable hinge.','- hinge close at least 0.60% below EMA20.',
        '- within 2h, completed close gives back to <=+0.60% SELL progress.','- arm +0.40% profit lock; no EMA7 runner recovery.','- may act only while frozen SF6-SF8 baseline remains alive.','',
        '## Results',
        f"- Parent: WR **{wr(P['full'])}**, PnL **${P['full']['pnl']:+.2f}**, PF **{P['full']['pf']:.2f}**.",
        f"- Standalone FastMR: WR **{wr(F['full'])}**, PnL **${F['full']['pnl']:+.2f}**, PF **{F['full']['pf']:.2f}**.",
        f"- Frozen SF6-SF8: WR **{wr(B['full'])}**, PnL **${B['full']['pnl']:+.2f}**, PF **{B['full']['pf']:.2f}**, DD **${B['full']['dd']:.2f}**.",
        f"- Combined: WR **{wr(C['full'])}**, PnL **${C['full']['pnl']:+.2f}**, PF **{C['full']['pf']:.2f}**, DD **${C['full']['dd']:.2f}**.",
        f"- incremental vs frozen SF6-SF8 **${inc.sum():+.2f}**; D/V **${inc[:DISC_N].sum():+.2f} / ${inc[DISC_N:].sum():+.2f}**.",
        f"- FastMR arms **{len(acts)}** (D/V {(acts.i<DISC_N).sum()}/{(acts.i>=DISC_N).sum()}); lock/market exits **{len(exits)}**.",
        f"- frozen loss→positive **{((df.frozen_pnl<=0)&(df.combined_pnl>0)).sum()}**; frozen winner→nonpositive **{((df.frozen_pnl>0)&(df.combined_pnl<=0)).sum()}**.",
        f"- positive chronological blocks **{sum(x['pnl']>0 for x in blocks)}/8**.",'',
        '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF9_FASTMR_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
