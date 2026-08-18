#!/usr/bin/env python3
"""Sunday T-Method ST4-ST11 — EMA/FastMR/RunnerRecovery adapted from Tuesday milestones.
Research only; live BBC untouched.
Parent remains Sunday16 SELL TP2.5 SL1.4 hold18h because ST0-ST3 price-path protection failed.
Sunday adaptation:
- hinge = +1.00% MFE (first Sunday milestone where broad protect stopped being deeply destructive)
- lock = +0.40% (same normalized 40% of hinge concept)
- giveback = <=+0.60% (60% of hinge)
- FastMR latency = 120m, reflecting Sunday’s slower path; prior forensic first meaningful zone ~2h
- EMA20 overextension threshold selected on discovery only from a compact Sunday-scaled family
- EMA7 runner recovery uses the same causal rejection concept as Tuesday, scaled progress >=+0.60%.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sunday_tmethod_st0_st3_reset as st03

sun17=st03.sun17
OUT=Path(os.getenv('SUNT11_OUT','sunt11_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83
HINGE=0.010
LOCK=0.004
GIVEBACK=0.006
LATENCY_MIN=120
D20S=[0.004,0.006,0.008,0.010]


def market_exit_pnl(k,f,tr,d):
    if d not in k.index: return float(tr['pnl'])
    px=float(k.loc[d,'open'])
    return st03.funding_pnl(k,f,tr['entry_t'],d+pd.Timedelta(minutes=5),tr['entry'],px)


def hinge_info(k,tr):
    return st03.first_hinge(k,tr,HINGE)


def ema_forensic(k,tr,h):
    if h is None: return None
    b=k.loc[h['bar_t']]
    return {'d20':float(b.ema20)/float(b.close)-1.0,
            'd7':float(b.ema7)/float(b.close)-1.0,
            'ema_spread':float(b.ema7)/float(b.ema20)-1.0,
            'progress':h['close_progress'],'mae':h['cum_mae']}


def confirm_exit(k,f,tr,h,ema='ema7',two=True):
    if h is None: return float(tr['pnl']),False,None
    start=h['decision_t']; bars=k[(k.index>=start)&(k.index<tr['exit_t'])]
    streak=0
    for b in bars.itertuples(index=False):
        above=float(b.close)>float(getattr(b,ema))
        streak=streak+1 if above else 0
        need=2 if two else 1
        if streak>=need:
            d=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=d: return float(tr['pnl']),False,None
            return market_exit_pnl(k,f,tr,d),True,d
    return float(tr['pnl']),False,None


def fastmr_arm(k,tr,h,d20_min):
    if h is None: return None
    hi=ema_forensic(k,tr,h)
    if hi['d20']<d20_min: return None
    start=h['decision_t']; end=min(tr['exit_t'],start+pd.Timedelta(minutes=LATENCY_MIN))
    bars=k[(k.index>=start)&(k.index<end)]
    ep=tr['entry']
    for b in bars.itertuples(index=False):
        progress=1.0-float(b.close)/ep
        if progress<=GIVEBACK:
            d=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=d: return None
            return {'signal_bar':b.ts,'decision_t':d,'progress':progress,'d20':hi['d20']}
    return None


def run_lock(k,f,tr,arm,recovery=False):
    if arm is None: return float(tr['pnl']),False,False,None
    ep=tr['entry']; lock_px=ep*(1.0-LOCK); d=arm['decision_t']
    if d not in k.index: return float(tr['pnl']),False,False,None
    op=float(k.loc[d,'open'])
    if op>=lock_px:
        return st03.funding_pnl(k,f,tr['entry_t'],d+pd.Timedelta(minutes=5),ep,op),True,False,None
    bars=k[(k.index>=d)&(k.index<tr['exit_t'])]
    for b in bars.itertuples(index=False):
        if float(b.high)>=lock_px:
            et=b.ts+pd.Timedelta(minutes=5)
            return st03.funding_pnl(k,f,tr['entry_t'],et,ep,lock_px),True,False,None
        if recovery:
            prog=1.0-float(b.close)/ep
            reject=(float(b.high)>=float(b.ema7) and float(b.close)<float(b.ema7) and prog>=GIVEBACK)
            if reject:
                cancel_t=b.ts+pd.Timedelta(minutes=5)
                if tr['exit_t']>cancel_t:
                    return float(tr['pnl']),True,True,cancel_t
    return float(tr['pnl']),True,False,None


def blocks(a,n=8):
    a=np.asarray(a,float); idx=np.array_split(np.arange(len(a)),n)
    return [st03.metrics(a[x]) for x in idx]


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k)
    trades=[sun17.simulate_parent(k,f,t) for t in es]
    parent=np.array([tr['pnl'] for tr in trades],float); pm=st03.metrics(parent)
    if not (pm['n']==139 and pm['wins']==66 and abs(pm['pnl']-63.599379132074105)<0.25):
        raise RuntimeError(f'parent parity fail {pm}')
    hs=[hinge_info(k,tr) for tr in trades]

    fr=[]
    for i,(tr,h) in enumerate(zip(trades,hs)):
        x=ema_forensic(k,tr,h)
        if x is not None: fr.append({'i':i,'win':tr['pnl']>0,'pnl':tr['pnl'],**x})
    fd=pd.DataFrame(fr)
    forensic={'hinge_n':len(fd),'hinge_wins':int(fd.win.sum()),'hinge_losses':int((~fd.win).sum())}
    for feat in ['d20','d7','ema_spread','progress','mae']:
        forensic[feat]={'winner_median':float(fd[fd.win][feat].median()),'loser_median':float(fd[~fd.win][feat].median())}

    confirms=[]
    for name,ema,two in [('2C_ABOVE_EMA7','ema7',True),('1C_ABOVE_EMA20','ema20',False),('2C_ABOVE_EMA20','ema20',True)]:
        vals=[]; acts=0
        for tr,h in zip(trades,hs):
            p,a,_=confirm_exit(k,f,tr,h,ema,two); vals.append(p); acts+=int(a)
        vals=np.array(vals,float)
        confirms.append({'rule':name,'actions':acts,'full':st03.metrics(vals),'D':st03.metrics(vals[:DISC_N]),'V':st03.metrics(vals[DISC_N:])})

    candidates=[]
    for th in D20S:
        vals=[]; detail=[]
        for i,(tr,h) in enumerate(zip(trades,hs)):
            arm=fastmr_arm(k,tr,h,th)
            p,a,_,_=run_lock(k,f,tr,arm,False); vals.append(p)
            if a: detail.append({'i':i,'date':str(tr['entry_t'].date()),'parent_pnl':tr['pnl'],'managed_pnl':p,'delta':p-tr['pnl'],
                                 'd20':arm['d20'],'signal_progress':arm['progress']})
        vals=np.array(vals,float); dacts=sum(x['i']<DISC_N for x in detail)
        candidates.append({'d20_min':th,'actions':len(detail),'D_actions':dacts,'V_actions':len(detail)-dacts,
                           'full':st03.metrics(vals),'D':st03.metrics(vals[:DISC_N]),'V':st03.metrics(vals[DISC_N:]),'detail':detail})
    elig=[x for x in candidates if x['D_actions']>=3]
    champ=max(elig,key=lambda x:x['D']['pnl']) if elig else max(candidates,key=lambda x:x['D']['pnl'])
    TH=champ['d20_min']

    fast=[]; rec=[]; actions=0; rec_actions=0; rec_detail=[]
    for i,(tr,h) in enumerate(zip(trades,hs)):
        arm=fastmr_arm(k,tr,h,TH)
        p,a,_,_=run_lock(k,f,tr,arm,False); fast.append(p); actions+=int(a)
        q,b,r,rt=run_lock(k,f,tr,arm,True); rec.append(q); rec_actions+=int(r)
        if r: rec_detail.append({'i':i,'date':str(tr['entry_t'].date()),'fast_pnl':p,'recovered_pnl':q,'delta':q-p,'cancel_t':str(rt)})
    fast=np.array(fast,float); rec=np.array(rec,float)
    fm=st03.metrics(fast); rm=st03.metrics(rec)
    fD=st03.metrics(fast[:DISC_N]); fV=st03.metrics(fast[DISC_N:]); rD=st03.metrics(rec[:DISC_N]); rV=st03.metrics(rec[DISC_N:])
    fb=blocks(fast); rb=blocks(rec)

    out={'status':'COMPLETE_SUNDAY_TMETHOD_ST4_ST11','parent':pm,
         'sunday_adaptation':{'hinge':HINGE,'lock':LOCK,'giveback':GIVEBACK,'fastmr_latency_min':LATENCY_MIN,'d20_family':D20S},
         'ST4_forensic':forensic,'ST5_ST6_confirmations':confirms,'ST7_ST9_candidates':candidates,
         'selected_d20':TH,'fastmr':{'full':fm,'D':fD,'V':fV,'actions':actions,'positive_blocks':sum(x['pnl']>0 for x in fb),'blocks':fb},
         'runner_recovery':{'full':rm,'D':rD,'V':rV,'recovery_actions':rec_actions,'detail':rec_detail,'positive_blocks':sum(x['pnl']>0 for x in rb),'blocks':rb},
         'delta_fastmr_vs_parent':fm['pnl']-pm['pnl'],'delta_recovery_vs_fastmr':rm['pnl']-fm['pnl'],'delta_recovery_vs_parent':rm['pnl']-pm['pnl'],
         'guardrail':'Milestone logic mirrors Tuesday but Sunday scaling is predeclared from Sunday geometry/path speed. D selects only EMA20 overextension threshold; V is report-only. Entire historical Sunday sample has prior research exposure, so not untouched OOS.'}
    (OUT/'sunt11_summary.json').write_text(json.dumps(out,indent=2,default=str))

    def pc(m): return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday T-Method — ST4 to ST11','',
        '**Status: COMPLETE — EMA/FastMR/RunnerRecovery milestones rebuilt for Sunday; live BBC untouched.**','',
        '## Reset base',f"- Parent: WR **{pc(pm)}**, PnL **${pm['pnl']:+.2f}**, PF **{pm['pf']:.2f}**.",
        '- ST0-ST3 price-path protection was rejected, so it is NOT carried forward.','',
        '## ST4 EMA forensic at +1.00% favorable hinge',
        f"- Hinge trades {forensic['hinge_n']} = {forensic['hinge_wins']} eventual wins / {forensic['hinge_losses']} losses.",
        f"- EMA20 distance median: winners {100*forensic['d20']['winner_median']:.3f}% vs losers {100*forensic['d20']['loser_median']:.3f}%.",'',
        '## ST5-ST6 broad EMA confirmation','',
        '| Rule | Actions | WR | PnL | D PnL | V PnL |','|---|---:|---:|---:|---:|---:|']
    for x in confirms:
        md.append(f"| {x['rule']} | {x['actions']} | {pc(x['full'])} | ${x['full']['pnl']:+.2f} | ${x['D']['pnl']:+.2f} | ${x['V']['pnl']:+.2f} |")
    md += ['', '## ST7-ST9 Sunday FastMR','',
           'Rule: after +1.00% MFE, require hinge EMA20 overextension; if within 120m close gives back to <=+0.60%, arm +0.40% lock while original TP/SL remain.','',
           '| EMA20 overextension | Actions D/V | WR | PnL | D PnL | V PnL |','|---:|---:|---:|---:|---:|---:|']
    for x in candidates:
        md.append(f"| {100*x['d20_min']:.2f}% | {x['D_actions']}/{x['V_actions']} | {pc(x['full'])} | ${x['full']['pnl']:+.2f} | ${x['D']['pnl']:+.2f} | ${x['V']['pnl']:+.2f} |")
    md += ['',f"Selected discovery threshold **{100*TH:.2f}% below EMA20**.",
           f"- FastMR: WR **{pc(fm)}**, PnL **${fm['pnl']:+.2f}**, PF **{fm['pf']:.2f}**, actions {actions}, blocks {sum(x['pnl']>0 for x in fb)}/8.",
           f"- D: {pc(fD)}, ${fD['pnl']:+.2f}; V: {pc(fV)}, ${fV['pnl']:+.2f}.",'',
           '## ST10-ST11 EMA7 runner recovery',
           'Before +0.40 lock is touched: if completed 5m tests/gets above EMA7 but closes back below EMA7 while SELL progress remains >=+0.60%, cancel lock next open and restore original runner.',
           f"- Recovery actions **{rec_actions}**.",
           f"- FastMR ${fm['pnl']:+.2f} -> recovery **${rm['pnl']:+.2f}** (delta **${rm['pnl']-fm['pnl']:+.2f}**).",
           f"- WR **{pc(rm)}**, PF **{rm['pf']:.2f}**, blocks **{sum(x['pnl']>0 for x in rb)}/8**.",
           f"- D: {pc(rD)}, ${rD['pnl']:+.2f}; V: {pc(rV)}, ${rV['pnl']:+.2f}.",'',
           '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_TMETHOD_ST4_ST11_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
