#!/usr/bin/env python3
"""Sunday T-Method reset ST0-ST3 — Tuesday A5.0-A5.3 methodology adapted to Sunday.
Research only; live BBC untouched.
Parent: Sunday 16:00 WIB SELL, TP2.5%, SL1.4%, max hold18h.
Same conceptual milestone as Tuesday:
 ST0 loss/path forensics
 ST1 unconditional profit-protection frontier
 ST2 conditional RUNNER vs PROTECT
 ST3 chronological robustness
Adaptation: favorable hinge is selected from natural Sunday path milestones on discovery only;
protection uses the same normalized Tuesday concepts: lock=40% of hinge, weak-close<=70% of hinge,
prior adverse pressure >=25% of parent SL. Validation is report-only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17b_sunday16_loss_prevday_forensics_exactfunding as sun17b

sun17=sun17b.base
sun17.funding_short=sun17b.exact_sun16_funding
OUT=Path(os.getenv('SUNT03_OUT','sunt03_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83
HINGES=[0.005,0.008,0.010,0.015]
LOCK_FRAC=0.40
WEAK_RETAIN=0.70
MAE_FRAC_SL=0.25


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'pf':None,'exp':None,'dd':0.0,'loss_streak':0}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.,eq]); dd=float(np.max(peak[1:]-eq))
    cur=best=0
    for x in a:
        if x<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return {'n':len(a),'wins':wins,'losses':len(a)-wins,'wr':wins/len(a),'pnl':float(a.sum()),
            'pf':gp/gl if gl>0 else 999.0,'exp':float(a.mean()),'dd':dd,'loss_streak':best}


def funding_pnl(k,f,t,exit_t,ep,exit_px):
    gross=1.0-exit_px/ep
    fc,_=sun17.funding_short(k,f,t,exit_t,ep)
    return float(sun17.NOTIONAL*gross-sun17.FEE-fc)


def first_hinge(k,tr,hinge):
    t=tr['entry_t']; ep=tr['entry']; bars=k[(k.index>=t)&(k.index<tr['exit_t'])]
    for b in bars.itertuples(index=False):
        if 1.0-float(b.low)/ep >= hinge:
            decision_t=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=decision_t: return None
            hist=k[(k.index>=t)&(k.index<decision_t)]
            return {'bar_t':b.ts,'decision_t':decision_t,
                    'close_progress':1.0-float(b.close)/ep,
                    'cum_mae':float(hist.high.max())/ep-1.0,
                    'close_vs_ema20':float(b.ema20)/float(b.close)-1.0,
                    'close_vs_ema7':float(b.ema7)/float(b.close)-1.0}
    return None


def protect_outcome(k,f,tr,hinge,conditional):
    h=first_hinge(k,tr,hinge)
    if h is None: return float(tr['pnl']),False,None
    lock=LOCK_FRAC*hinge
    weak=h['close_progress']<=WEAK_RETAIN*hinge
    adverse=h['cum_mae']>=MAE_FRAC_SL*sun17.SL
    act=(weak and adverse) if conditional else True
    if not act: return float(tr['pnl']),False,h
    ep=tr['entry']; lock_px=ep*(1.0-lock); d=h['decision_t']
    if d not in k.index: return float(tr['pnl']),False,h
    op=float(k.loc[d,'open'])
    if op>=lock_px:
        return funding_pnl(k,f,tr['entry_t'],d+pd.Timedelta(minutes=5),ep,op),True,h
    scan=k[(k.index>=d)&(k.index<tr['exit_t'])]
    tp_px=ep*(1.0-sun17.TP)
    for b in scan.itertuples(index=False):
        hit_lock=float(b.high)>=lock_px
        hit_tp=float(b.low)<=tp_px
        if hit_lock:
            et=b.ts+pd.Timedelta(minutes=5)
            return funding_pnl(k,f,tr['entry_t'],et,ep,lock_px),True,h
        if hit_tp:
            return float(tr['pnl']),True,h
    return float(tr['pnl']),True,h


def blocks(a,n=8):
    a=np.asarray(a,float); idx=np.array_split(np.arange(len(a)),n)
    return [metrics(a[x]) for x in idx]


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k)
    trades=[sun17.simulate_parent(k,f,t) for t in es]
    parent=np.array([x['pnl'] for x in trades],float)
    pm=metrics(parent)
    if not (pm['n']==139 and pm['wins']==66 and abs(pm['pnl']-63.599379132074105)<0.25):
        raise RuntimeError(f'parent parity fail {pm}')

    winners=[x for x in trades if x['pnl']>0]; losers=[x for x in trades if x['pnl']<=0]
    anatomy={
      'winner_mfe_median':float(np.median([x['mfe'] for x in winners])),
      'winner_mae_median':float(np.median([x['mae'] for x in winners])),
      'loser_mfe_median':float(np.median([x['mfe'] for x in losers])),
      'loser_mae_median':float(np.median([x['mae'] for x in losers])),
      'loser_hinge_capacity':{str(h):int(sum(x['mfe']>=h for x in losers)) for h in HINGES},
      'winner_hinge_reach':{str(h):int(sum(x['mfe']>=h for x in winners)) for h in HINGES},
    }

    frontier=[]; conditional=[]
    for h in HINGES:
        ua=[]; uacts=0; ca=[]; cacts=0; detail=[]
        for i,tr in enumerate(trades):
            p,a,st=protect_outcome(k,f,tr,h,False); ua.append(p); uacts+=int(a)
            q,b,st2=protect_outcome(k,f,tr,h,True); ca.append(q); cacts+=int(b)
            if b:
                detail.append({'i':i,'date':str(tr['entry_t'].date()),'parent_pnl':tr['pnl'],'managed_pnl':q,
                               'delta':q-tr['pnl'],'close_progress':st2['close_progress'],'cum_mae':st2['cum_mae']})
        ua=np.array(ua); ca=np.array(ca)
        frontier.append({'hinge':h,'lock':LOCK_FRAC*h,'actions':uacts,'full':metrics(ua),'D':metrics(ua[:DISC_N]),'V':metrics(ua[DISC_N:])})
        conditional.append({'hinge':h,'lock':LOCK_FRAC*h,'weak_close_max':WEAK_RETAIN*h,'mae_min':MAE_FRAC_SL*sun17.SL,
                            'actions':cacts,'full':metrics(ca),'D':metrics(ca[:DISC_N]),'V':metrics(ca[DISC_N:]),'detail':detail})

    eligible=[]
    for x in conditional:
        dacts=sum(d['i']<DISC_N for d in x['detail'])
        x['D_actions']=dacts; x['V_actions']=x['actions']-dacts
        if dacts>=3: eligible.append(x)
    champ=max(eligible,key=lambda x:x['D']['pnl']) if eligible else max(conditional,key=lambda x:x['D']['pnl'])
    h=champ['hinge']
    managed=[]
    for tr in trades:
        p,_,_=protect_outcome(k,f,tr,h,True); managed.append(p)
    managed=np.array(managed,float); mm=metrics(managed)
    bs=blocks(managed)
    positive_blocks=sum(b['pnl']>0 for b in bs)

    out={'status':'COMPLETE_SUNDAY_TMETHOD_ST0_ST3','method':'Tuesday A5.0-A5.3 concept, Sunday-scaled geometry',
         'parent_definition':{'entry':'Sunday 16:00 WIB SELL','tp':sun17.TP,'sl':sun17.SL,'hold_h':18},
         'normalized_rule':{'lock_frac_hinge':LOCK_FRAC,'weak_close_retain_max':WEAK_RETAIN,'mae_min_frac_sl':MAE_FRAC_SL},
         'parent':pm,'anatomy':anatomy,'unconditional_frontier':frontier,'conditional_candidates':conditional,
         'selected_hinge':h,'selected':champ,'champion_full':mm,'blocks':bs,'positive_blocks':positive_blocks,
         'delta_vs_parent':mm['pnl']-pm['pnl'],
         'guardrail':'Discovery selects only the natural favorable hinge. Validation is report-only, but the broader Sunday history was previously inspected, so this is same-sample methodology reset, not untouched OOS.'}
    (OUT/'sunt03_summary.json').write_text(json.dumps(out,indent=2,default=str))

    def pct(m): return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday T-Method Reset — ST0 to ST3','',
        '**Status: COMPLETE — Tuesday A5.0-A5.3 methodology rebuilt for Sunday; live BBC untouched.**','',
        '## Parent',
        f"- Sunday 16:00 WIB SELL / TP2.5 / SL1.4 / hold18h: N {pm['n']}, WR **{pct(pm)}**, PnL **${pm['pnl']:+.2f}**, PF **{pm['pf']:.2f}**.",'',
        '## ST0 path anatomy',
        f"- Winner median MFE {100*anatomy['winner_mfe_median']:.2f}%, MAE {100*anatomy['winner_mae_median']:.2f}%.",
        f"- Loser median MFE {100*anatomy['loser_mfe_median']:.2f}%, MAE {100*anatomy['loser_mae_median']:.2f}%.",'',
        '## ST1 unconditional protection frontier','',
        '| Hinge | Lock | Actions | WR | PnL | D PnL | V PnL |','|---:|---:|---:|---:|---:|---:|---:|']
    for x in frontier:
        md.append(f"| {100*x['hinge']:.2f}% | {100*x['lock']:.2f}% | {x['actions']} | {pct(x['full'])} | ${x['full']['pnl']:+.2f} | ${x['D']['pnl']:+.2f} | ${x['V']['pnl']:+.2f} |")
    md += ['', '## ST2 conditional RUNNER vs PROTECT','',
           'Same conceptual Tuesday rule, normalized to Sunday: after favorable hinge, PROTECT only if trigger close retains <=70% of hinge and cumulative MAE >=25% of SL; lock at 40% of hinge. Otherwise RUNNER.','',
           '| Hinge | Actions D/V | Full WR | Full PnL | D PnL | V PnL |','|---:|---:|---:|---:|---:|---:|']
    for x in conditional:
        md.append(f"| {100*x['hinge']:.2f}% | {x['D_actions']}/{x['V_actions']} | {pct(x['full'])} | ${x['full']['pnl']:+.2f} | ${x['D']['pnl']:+.2f} | ${x['V']['pnl']:+.2f} |")
    md += ['', '## ST3 discovery-selected Sunday candidate',
           f"- Selected favorable hinge **{100*h:.2f}%**; lock **{100*LOCK_FRAC*h:.2f}%**.",
           f"- Parent ${pm['pnl']:+.2f} -> candidate **${mm['pnl']:+.2f}** (delta **${mm['pnl']-pm['pnl']:+.2f}**).",
           f"- WR {pct(pm)} -> **{pct(mm)}**; PF {pm['pf']:.2f} -> **{mm['pf']:.2f}**; DD ${pm['dd']:.2f} -> **${mm['dd']:.2f}**.",
           f"- Discovery: {pct(champ['D'])}, ${champ['D']['pnl']:+.2f}; validation: {pct(champ['V'])}, ${champ['V']['pnl']:+.2f}.",
           f"- Positive chronological blocks **{positive_blocks}/8**.",'',
           '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_TMETHOD_ST0_ST3_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
