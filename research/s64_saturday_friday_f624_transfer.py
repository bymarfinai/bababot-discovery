#!/usr/bin/env python3
"""S6.4 — Exact Friday F6.24 transfer to Saturday18 BUY.

Research only; live BBC untouched.

Transfer semantics are frozen, not re-fit to Saturday:
- first +0.5R milestone, where R is the frozen session SL (Saturday R=1.2%, so +0.5R=+0.6%);
- decision exactly +65m from the first hit-bar timestamp, matching Friday implementation;
- final four completed 5m closes all below EMA7;
- mean taker imbalance of final two completed 5m bars < 0;
- strictly pre-entry 2h entry range position > 50%;
- zero EMA20 close reclaims from milestone through decision;
- exit at actual decision-time open.

No Saturday threshold/timing/EMA/taker tuning is allowed.

Evaluate both:
A) static Saturday parent; and
B) frozen Saturday S5.7G + transferred FIB5 S6.3 baseline, with exact chronology
   against FIB5, S5.7G/A7.19 exits, and F6.24.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s50a_saturday_adaptive_atlas_v2 as a50
import s52a_post_failure_recovery_forensics as a52
import s57c_hinge_rejection_robustness_management as c57
import s57e_post_rejection_expansion_stall_atlas as e57
import s57f_frozen_recovery_management_counterfactual as f57
import s63_saturday_friday_fib5_transfer as s63

OUT=Path(os.getenv('S64_OUT','s64_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83
R=s50.SL
HALF_R=0.5*R
RULE='FRIDAY_F624_CONTEXT_REPAIR_FAILURE_65'


def metrics(pnls):
    p=np.asarray(pnls,dtype=float); wins=int((p>0).sum())
    gp=float(p[p>0].sum()); gl=float(-p[p<=0].sum())
    eq=np.cumsum(p); peak=np.maximum.accumulate(np.r_[0.0,eq])
    dd=float((peak[1:]-eq).max()) if len(eq) else 0.0
    ls=cur=0
    for x in p:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':int(len(p)),'wins':wins,'losses':int(len(p)-wins),
            'wr':float(wins/len(p)) if len(p) else np.nan,
            'pnl':float(p.sum()),'pf':float(gp/gl) if gl>0 else math.inf,
            'dd':dd,'ls':int(ls)}


def cross_up(a):
    a=np.asarray(a,dtype=bool)
    return int(np.sum((~a[:-1]) & a[1:])) if len(a)>1 else 0


def first_half_r_hit(k,t,tr):
    ex=pd.Timestamp(tr.exit_t)
    bars=k[(k.index>=t)&(k.index<ex)]
    px=float(tr.entry)*(1.0+HALF_R)
    z=bars[bars.high.astype(float)>=px]
    return None if z.empty else pd.Timestamp(z.iloc[0].ts)


def f624_state(k,t,tr):
    ht=first_half_r_hit(k,t,tr)
    if ht is None:return None
    dt=ht+pd.Timedelta(minutes=65)
    ex=pd.Timestamp(tr.exit_t)
    if dt not in k.index or ex<=dt:return None

    w=k[(k.index>=ht)&(k.index<dt)]
    if len(w)!=13:return None
    tail4=w.iloc[-4:]; tail2=w.iloc[-2:]
    bearish_persist=bool((tail4.close.astype(float)<tail4.ema7.astype(float)).all())
    flow2=float(tail2.taker_imb.astype(float).mean())
    flow_weak=bool(flow2<0)

    pre=k[(k.index<t)&(k.index>=t-pd.Timedelta(minutes=120))]
    if len(pre)!=24:return None
    hi=float(pre.high.max()); lo=float(pre.low.min()); rng=hi-lo
    if not np.isfinite(rng) or rng<=0:return None
    entry_pos=float((float(tr.entry)-lo)/rng)
    upper_half=bool(entry_pos>0.5)

    above20=(w.close.astype(float).to_numpy()>=w.ema20.astype(float).to_numpy())
    reclaims=cross_up(above20)
    no_repair=bool(reclaims==0)
    signal=bool(bearish_persist and flow_weak and upper_half and no_repair)
    return {'hit_t':ht,'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
            'tail4_below_ema7':bearish_persist,'tail2_taker_mean':flow2,
            'pre120_entry_range_pos':entry_pos,'upper_half_2h':upper_half,
            'ema20_reclaims':int(reclaims),'no_ema20_reclaim':no_repair,
            RULE:signal}


def exit_open_pnl(k,f,t,tr,dt):
    px=float(k.loc[dt,'open'])
    fund,_=s50.funding_cost(k,f,t,dt,float(tr.entry))
    pnl=s50.NOTIONAL*(px/float(tr.entry)-1.0)-s50.FEE-fund
    return float(pnl),px,float(fund)


def friday_fib5(k,t,tr):
    fib=s63.fib2h(k,t,float(tr.entry))
    if fib is None:return False,float(tr.pnl),np.nan,np.nan,np.nan
    baseline=s63.rolling_2h_range_baseline(k,t)
    first=k.loc[t]
    first5_red=bool(float(first.close)<float(tr.entry))
    alive5=bool(pd.Timestamp(tr.exit_t)>t+pd.Timedelta(minutes=5))
    shallow=bool(fib['retr']<=0.382)
    expansion=bool(np.isfinite(baseline) and fib['range_pct']>baseline)
    action=bool(first5_red and alive5 and shallow and expansion)
    if not action:return False,float(tr.pnl),fib['retr'],fib['range_pct'],baseline
    dt=t+pd.Timedelta(minutes=5); px=float(k.loc[dt,'open'])
    pnl=s50.NOTIONAL*(px/float(tr.entry)-1.0)-s50.FEE
    return True,float(pnl),fib['retr'],fib['range_pct'],baseline


def saturday_champion(k,f,t,tr):
    """Exact frozen S5.7G NO_BULL_TOP_Q_30 chronology on top of A7.19."""
    s240=a50.state240(k,t,tr)
    base=float(a50.a719_pnl(k,f,t,tr,s240))
    base_exit=pd.Timestamp(f57.a719_exit_time(t,tr,s240))
    h05,_=a52.first_hinges(k,t,tr)  # Saturday frozen +0.50% hinge, only for S5.7G chronology.
    action=False; action_dt=None; strategy=base
    if h05 is not None:
        hinge_ts=h05-pd.Timedelta(minutes=5)
        hinge=k.loc[hinge_ts]
        cm=c57.morph(hinge)
        rejected=bool(np.isfinite(cm['upper_wick_ratio']) and cm['upper_wick_ratio']>=0.50)
        if rejected:
            feat=e57.snapshot_features(k,tr,h05,hinge,30)
            unresolved=bool(feat.get('unresolved',False))
            if unresolved:
                signal_present=bool(feat['last_bull_top_q'])
                d=h05+pd.Timedelta(minutes=30)
                if (not signal_present) and d<=base_exit and d in k.index:
                    strategy,_=f57.exit_open_pnl(k,f,t,tr,d)
                    action=True; action_dt=d
    return float(strategy),(action_dt if action else base_exit),('S57G' if action else 'A719'),bool(action),float(base)


def main():
    k=s50.load_klines()
    k['ema7']=k['close'].ewm(span=7,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k)
    trades=[s50.simulate(k,f,t) for t in entries]
    if len(trades)!=139 or abs(sum(x.pnl for x in trades)-87.199692)>0.02:
        raise RuntimeError('Saturday parent parity fail')

    rows=[]; champ_sum=0.0
    for i,(t,tr) in enumerate(zip(entries,trades)):
        champ_pnl,champ_dt,champ_layer,champ_action,a719_pnl=saturday_champion(k,f,t,tr)
        champ_sum+=champ_pnl
        fib_action,fib_pnl,retr2h,range2h,rangebase=friday_fib5(k,t,tr)
        if fib_action:
            base_pnl=fib_pnl; base_dt=t+pd.Timedelta(minutes=5); base_layer='FIB5'
        else:
            base_pnl=champ_pnl; base_dt=champ_dt; base_layer=champ_layer

        st=f624_state(k,t,tr)
        static_pnl=float(tr.pnl); static_layer='PARENT'
        managed=float(base_pnl); managed_layer=base_layer; active=False
        if st is not None and st[RULE]:
            cut,cutpx,cutfund=exit_open_pnl(k,f,t,tr,st['decision_t'])
            static_pnl=cut; static_layer=RULE
            # Exact event chronology: only preempt if F6.24 happens strictly before frozen baseline exit/action.
            if st['decision_t'] < pd.Timestamp(base_dt):
                managed=cut; managed_layer=RULE; active=True
        else:
            cutpx=cutfund=np.nan

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),
             'a719_pnl':a719_pnl,'champion_pnl':champ_pnl,'champion_action':champ_action,'champion_layer':champ_layer,'champion_exit_t':str(champ_dt),
             'fib5_action':fib_action,'fib5_pnl':fib_pnl,'retr2h_fib5':retr2h,'range2h_pct_fib5':range2h,'range2h_baseline24h':rangebase,
             'baseline_pnl':float(base_pnl),'baseline_layer':base_layer,'baseline_exit_t':str(base_dt),
             'static_f624_pnl':float(static_pnl),'static_f624_layer':static_layer,
             'managed_pnl':float(managed),'managed_layer':managed_layer,'active_action':bool(active),
             'incremental_vs_baseline':float(managed-base_pnl)}
        if st is not None:
            row.update({'raw_signal':bool(st[RULE]),'halfR_hit_t':str(st['hit_t']),'decision_t':str(st['decision_t']),
                        'tail4_below_ema7':bool(st['tail4_below_ema7']),'tail2_taker_mean':float(st['tail2_taker_mean']),
                        'pre120_entry_range_pos':float(st['pre120_entry_range_pos']),'upper_half_2h':bool(st['upper_half_2h']),
                        'ema20_reclaims':int(st['ema20_reclaims']),'no_ema20_reclaim':bool(st['no_ema20_reclaim'])})
        rows.append(row)
    df=pd.DataFrame(rows)
    if abs(champ_sum-111.239827)>0.05:
        raise RuntimeError(f'S5.7G champion parity fail {champ_sum}')

    parent_m=metrics(df.parent_pnl)
    champ_m=metrics(df.champion_pnl)
    base_m=metrics(df.baseline_pnl)
    static_m=metrics(df.static_f624_pnl)
    managed_m=metrics(df.managed_pnl)
    if abs(base_m['pnl']-119.738317)>0.06 or abs(base_m['wr']*100-54.676)>0.08:
        raise RuntimeError(f'S6.3 integrated parity fail {base_m}')

    raw=df[df.raw_signal==True].copy() if 'raw_signal' in df.columns else df.iloc[0:0]
    acts=df[df.active_action].copy()
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    static_delta=float(static_m['pnl']-parent_m['pnl'])
    static_d=float((d.static_f624_pnl-d.parent_pnl).sum()); static_v=float((v.static_f624_pnl-v.parent_pnl).sum())
    inc=float(managed_m['pnl']-base_m['pnl']); incD=float(d.incremental_vs_baseline.sum()); incV=float(v.incremental_vs_baseline.sum())
    parent_win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_pnl<=0)).sum())
    baseline_pos_nonpos=int(((acts.baseline_pnl>0)&(acts.managed_pnl<=0)).sum())
    loss_to_positive=int(((acts.parent_pnl<=0)&(acts.managed_pnl>0)).sum())

    jack=[]
    for _,r in acts.iterrows():
        jack.append(float(inc-r.incremental_vs_baseline))
    jack_min=float(min(jack)) if jack else np.nan

    # Four equal chronology blocks for transfer stability; no threshold fitting.
    edges=np.linspace(0,len(df),5,dtype=int); blocks=[]
    for j in range(4):
        g=df.iloc[edges[j]:edges[j+1]]
        blocks.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),
                       'actions':int(g.active_action.sum()),'incremental':float(g.incremental_vs_baseline.sum())})

    transfer_pass=bool(inc>0 and incD>=0 and incV>=0 and len(acts)>0 and baseline_pos_nonpos==0 and
                       managed_m['wr']>=base_m['wr'] and managed_m['dd']<=base_m['dd']+1e-9)
    static_pass=bool(static_delta>0 and static_d>=0 and static_v>=0)

    out={
      'transfer_definition':{
        'milestone':f'+0.5R normalized to Saturday frozen R={R:.4f} => +{HALF_R:.4f}',
        'decision':'+65m from first hit-bar timestamp, exact Friday implementation',
        'bearish_persistence':'final 4 completed 5m closes below EMA7',
        'flow':'final-2 taker imbalance mean < 0',
        'context':'pre-entry 2h entry range position > 0.50',
        'repair':'zero close<EMA20 -> close>=EMA20 transitions from milestone to decision',
        'exit':'actual decision-time open; no Saturday tuning'},
      'parent':parent_m,'s57g_champion':champ_m,'s63_fib5_plus_champion':base_m,
      'f624_on_static':static_m,'f624_on_integrated':managed_m,
      'static_delta':static_delta,'static_D':static_d,'static_V':static_v,'static_transfer_pass':static_pass,
      'raw_signals':int(len(raw)),'active_actions':int(len(acts)),'actions_D':int((acts.i<SPLIT).sum()),'actions_V':int((acts.i>=SPLIT).sum()),
      'preempted_by_frozen_baseline':int(len(raw)-len(acts)),
      'parent_winners_acted':int((acts.parent_pnl>0).sum()),'parent_losses_acted':int((acts.parent_pnl<=0).sum()),
      'loss_to_positive':loss_to_positive,'parent_winner_to_nonpositive':parent_win_nonpos,'baseline_positive_to_nonpositive':baseline_pos_nonpos,
      'positive_increment_actions':int((acts.incremental_vs_baseline>0).sum()),'negative_increment_actions':int((acts.incremental_vs_baseline<0).sum()),
      'incremental_vs_integrated':inc,'incremental_D':incD,'incremental_V':incV,
      'wr_gain_pp':float((managed_m['wr']-base_m['wr'])*100),'dd_improvement':float(base_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental':jack_min,'blocks4':blocks,'transfer_pass':transfer_pass,
      'actions_detail':acts[['date','period','parent_pnl','baseline_pnl','managed_pnl','incremental_vs_baseline','parent_mfe_r','baseline_layer','pre120_entry_range_pos','ema20_reclaims','tail2_taker_mean']].to_dict('records') if len(acts) else []}
    df.to_csv(OUT/'s64_rows.csv',index=False)
    (OUT/'s64_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Saturday S6.4 — Exact Friday F6.24 Transfer','',
        f"**Integrated transfer:** {'PASS' if transfer_pass else 'FAIL'}",
        f"**Static-parent transfer:** {'PASS' if static_pass else 'FAIL'}",
        '**Research only; live BBC untouched. No Saturday retuning.**','',
        '## Exact transferred mechanism',
        f'- +0.5R milestone; Saturday frozen R=1.2%, therefore +0.5R=+0.6%',
        '- decision +65m using Friday implementation timing',
        '- final 4 completed 5m closes below EMA7',
        '- final-2 taker mean < 0',
        '- pre-entry 2h entry position >50%',
        '- zero EMA20 reclaims from milestone to decision',
        '- exit actual decision open','',
        '## Frozen Saturday parity',
        f"- parent **{parent_m['pnl']:+.3f}**, WR **{parent_m['wr']*100:.2f}%**",
        f"- S5.7G champion **{champ_m['pnl']:+.3f}**",
        f"- S6.3 FIB5 + S5.7G **{base_m['pnl']:+.3f}**, WR **{base_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f}**, DD **{base_m['dd']:.3f}**",'',
        '## Transfer result on integrated baseline',
        f"- raw signals **{len(raw)}**, active after chronology **{len(acts)}**, preempted **{len(raw)-len(acts)}**",
        f"- actions D/V **{(acts.i<SPLIT).sum()} / {(acts.i>=SPLIT).sum()}**",
        f"- parent winners/losses acted **{(acts.parent_pnl>0).sum()} / {(acts.parent_pnl<=0).sum()}**",
        f"- loss→positive **{loss_to_positive}**, baseline positive→nonpositive **{baseline_pos_nonpos}**",
        f"- PnL **{base_m['pnl']:+.3f} -> {managed_m['pnl']:+.3f}**, incremental **{inc:+.3f}**",
        f"- D/V incremental **{incD:+.3f} / {incV:+.3f}**",
        f"- WR **{base_m['wr']*100:.2f}% -> {managed_m['wr']*100:.2f}%**, PF **{base_m['pf']:.3f} -> {managed_m['pf']:.3f}**, DD **{base_m['dd']:.3f} -> {managed_m['dd']:.3f}**",
        f"- action jackknife min remaining incremental **{jack_min:+.3f}**" if np.isfinite(jack_min) else '- no active-action jackknife', '',
        '## Cross-context interpretation guardrail',
        'This is a genuine transfer test because Friday F6.24 is ported without Saturday threshold/timing tuning. +0.5R is normalized to the frozen Saturday risk unit rather than copied as Friday absolute price distance. Do not retune based on this Saturday run.']
    (OUT/'S6.4_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
