#!/usr/bin/env python3
"""S6.5 — Exact Friday F6.18 D3 transfer to Saturday18 BUY.

Research only; live BBC untouched.

Transfer the Friday D3 mechanism without Saturday retuning:
- first +1R milestone, normalized to frozen Saturday R=1.2% => +1.2%;
- first hit is known only when its 5m bar completes;
- decision at hit-bar open +20m, after exactly four completed bars: hit, +5, +10, +15;
- P1 alert: median taker over those four bars < 0 AND latest completed close < EMA7;
- D3 confirmation: latest bar bearish, real body > 2*(upper wick + lower wick),
  AND latest close < previous completed 5m low;
- exit at actual decision-time open.

No body/timing/EMA/taker/threshold retuning.

Evaluate against the latest frozen Saturday stack:
S5.7G/A7.19 + transferred FIB5 + transferred F6.24, with exact chronology.
Also report transfer against S6.3 baseline before F6.24 for transparency.
"""
from __future__ import annotations

import json, math, os
from pathlib import Path
import numpy as np
import pandas as pd

import s50_saturday_parent_forensics as s50
import s64_saturday_friday_f624_transfer as s64

OUT=Path(os.getenv('S65_OUT','s65_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83
R=s50.SL
RULE='FRIDAY_D3_STRONG_BODY_BREAK_PRIOR_LOW'


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


def first_1r_hit(k,t,tr):
    ex=pd.Timestamp(tr.exit_t)
    bars=k[(k.index>=t)&(k.index<ex)]
    px=float(tr.entry)*(1.0+R)
    z=bars[bars.high.astype(float)>=px]
    return None if z.empty else pd.Timestamp(z.iloc[0].ts)


def d3_state(k,t,tr):
    ht=first_1r_hit(k,t,tr)
    if ht is None:return None
    dt=ht+pd.Timedelta(minutes=20)
    ex=pd.Timestamp(tr.exit_t)
    if dt not in k.index or ex<=dt:return None
    w=k[(k.index>=ht)&(k.index<dt)].copy()
    if len(w)!=4:return None
    last=w.iloc[-1]; prev=w.iloc[-2]
    taker_med=float(w.taker_imb.astype(float).median())
    below7=bool(float(last.close)<float(last.ema7))
    p1=bool(taker_med<0 and below7)

    rng=max(float(last.high-last.low),1e-12)
    body=abs(float(last.close-last.open))
    uw=float(last.high-max(last.open,last.close))
    lw=float(min(last.open,last.close)-last.low)
    strong=bool(float(last.close)<float(last.open) and body>2.0*(uw+lw))
    break_prior=bool(float(last.close)<float(prev.low))
    signal=bool(p1 and strong and break_prior)
    return {'hit_t':ht,'decision_t':dt,'decision_open':float(k.loc[dt,'open']),
            'taker_med':taker_med,'below_ema7':below7,'p1_alert':p1,
            'last_body_ratio':float(body/rng),'last_upper_wick_ratio':float(uw/rng),
            'last_lower_wick_ratio':float(lw/rng),'strong_body':strong,
            'break_prior_low':break_prior,RULE:signal}


def latest_saturday_baseline(k,f,t,tr):
    """Reproduce S6.4 latest baseline: FIB5 > S5.7G/A7.19, then F6.24 if earlier."""
    champ_pnl,champ_dt,champ_layer,champ_action,a719_pnl=s64.saturday_champion(k,f,t,tr)
    fib_action,fib_pnl,retr2h,range2h,rangebase=s64.friday_fib5(k,t,tr)
    if fib_action:
        s63_pnl=float(fib_pnl); s63_dt=t+pd.Timedelta(minutes=5); s63_layer='FIB5'
    else:
        s63_pnl=float(champ_pnl); s63_dt=pd.Timestamp(champ_dt); s63_layer=champ_layer

    latest_pnl=s63_pnl; latest_dt=s63_dt; latest_layer=s63_layer
    f624=s64.f624_state(k,t,tr)
    f624_active=False
    if f624 is not None and f624[s64.RULE] and f624['decision_t']<latest_dt:
        latest_pnl,_,_=s64.exit_open_pnl(k,f,t,tr,f624['decision_t'])
        latest_dt=f624['decision_t']; latest_layer=s64.RULE; f624_active=True
    return {'s63_pnl':s63_pnl,'s63_dt':s63_dt,'s63_layer':s63_layer,
            'latest_pnl':float(latest_pnl),'latest_dt':pd.Timestamp(latest_dt),'latest_layer':latest_layer,
            'f624_active':f624_active,'champion_pnl':float(champ_pnl),'a719_pnl':float(a719_pnl)}


def main():
    k=s50.load_klines(); k['ema7']=k['close'].ewm(span=7,adjust=False).mean()
    f=s50.load_funding(); entries=s50.saturday_entries(k)
    trades=[s50.simulate(k,f,t) for t in entries]
    if len(trades)!=139 or abs(sum(x.pnl for x in trades)-87.199692)>0.02:
        raise RuntimeError('Saturday parent parity fail')

    rows=[]
    for i,(t,tr) in enumerate(zip(entries,trades)):
        b=latest_saturday_baseline(k,f,t,tr)
        st=d3_state(k,t,tr)
        managed_latest=float(b['latest_pnl']); layer_latest=b['latest_layer']; active_latest=False
        managed_s63=float(b['s63_pnl']); layer_s63=b['s63_layer']; active_s63=False
        cut=np.nan
        if st is not None and st[RULE]:
            cut,_,_=s64.exit_open_pnl(k,f,t,tr,st['decision_t'])
            if st['decision_t']<b['s63_dt']:
                managed_s63=float(cut); layer_s63=RULE; active_s63=True
            if st['decision_t']<b['latest_dt']:
                managed_latest=float(cut); layer_latest=RULE; active_latest=True

        row={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
             'parent_pnl':float(tr.pnl),'parent_win':bool(tr.pnl>0),'parent_mfe_r':float(tr.mfe/R),
             's63_pnl':float(b['s63_pnl']),'s63_layer':b['s63_layer'],'s63_exit_t':str(b['s63_dt']),
             's64_latest_pnl':float(b['latest_pnl']),'s64_latest_layer':b['latest_layer'],'s64_latest_exit_t':str(b['latest_dt']),
             'f624_active':bool(b['f624_active']),
             'managed_vs_s63':managed_s63,'managed_vs_s63_layer':layer_s63,'active_vs_s63':active_s63,
             'managed_latest':managed_latest,'managed_latest_layer':layer_latest,'active_latest':active_latest,
             'inc_vs_s63':float(managed_s63-b['s63_pnl']),
             'inc_vs_latest':float(managed_latest-b['latest_pnl'])}
        if st is not None:
            row.update({'raw_signal':bool(st[RULE]),'hit_1r_t':str(st['hit_t']),'decision_t':str(st['decision_t']),
                        'taker_med':float(st['taker_med']),'below_ema7':bool(st['below_ema7']),
                        'p1_alert':bool(st['p1_alert']),'last_body_ratio':float(st['last_body_ratio']),
                        'last_upper_wick_ratio':float(st['last_upper_wick_ratio']),
                        'strong_body':bool(st['strong_body']),'break_prior_low':bool(st['break_prior_low'])})
        rows.append(row)

    df=pd.DataFrame(rows); df.to_csv(OUT/'s65_rows.csv',index=False)
    parent_m=metrics(df.parent_pnl); s63_m=metrics(df.s63_pnl); latest_m=metrics(df.s64_latest_pnl)
    managed63_m=metrics(df.managed_vs_s63); managed_m=metrics(df.managed_latest)
    if abs(s63_m['pnl']-119.738317)>0.06 or abs(s63_m['wr']*100-54.676)>0.08:
        raise RuntimeError(f'S6.3 parity fail {s63_m}')
    if abs(latest_m['pnl']-119.766311)>0.06:
        raise RuntimeError(f'S6.4 latest parity fail {latest_m}')

    raw=df[df.raw_signal==True].copy() if 'raw_signal' in df.columns else df.iloc[0:0]
    acts=df[df.active_latest].copy(); acts63=df[df.active_vs_s63].copy()
    d=df[df.i<SPLIT]; v=df[df.i>=SPLIT]
    inc=float(managed_m['pnl']-latest_m['pnl']); incD=float(d.inc_vs_latest.sum()); incV=float(v.inc_vs_latest.sum())
    inc63=float(managed63_m['pnl']-s63_m['pnl']); inc63D=float(d.inc_vs_s63.sum()); inc63V=float(v.inc_vs_s63.sum())
    win_nonpos=int(((acts.s64_latest_pnl>0)&(acts.managed_latest<=0)).sum())
    parent_win_nonpos=int(((acts.parent_pnl>0)&(acts.managed_latest<=0)).sum())
    loss_pos=int(((acts.parent_pnl<=0)&(acts.managed_latest>0)).sum())

    jack=[float(inc-r.inc_vs_latest) for _,r in acts.iterrows()]
    jack_min=float(min(jack)) if jack else np.nan
    edges=np.linspace(0,len(df),5,dtype=int); blocks=[]
    for j in range(4):
        g=df.iloc[edges[j]:edges[j+1]]
        blocks.append({'block':j+1,'start':str(g.date.iloc[0]),'end':str(g.date.iloc[-1]),
                       'actions':int(g.active_latest.sum()),'incremental':float(g.inc_vs_latest.sum())})

    transfer_pass=bool(inc>0 and incD>=0 and incV>=0 and len(acts)>0 and win_nonpos==0 and
                       managed_m['wr']>=latest_m['wr'] and managed_m['dd']<=latest_m['dd']+1e-9)
    out={
      'transfer_definition':{
        'milestone':f'+1R normalized to Saturday frozen R={R:.4f}',
        'decision':'first +1R hit-bar open +20m; four completed bars known',
        'p1':'median taker over 4 bars <0 AND latest close <EMA7',
        'strong_body':'latest bearish real body > 2x total wicks',
        'break':'latest close < previous completed 5m low',
        'exit':'actual decision open; no Saturday retuning'},
      'parent':parent_m,'s63_baseline':s63_m,'s64_latest_baseline':latest_m,
      'd3_on_s63':managed63_m,'d3_on_latest':managed_m,
      'raw_signals':int(len(raw)),'active_vs_s63':int(len(acts63)),'active_latest':int(len(acts)),
      'preempted_vs_latest':int(len(raw)-len(acts)),
      'actions_D':int((acts.i<SPLIT).sum()),'actions_V':int((acts.i>=SPLIT).sum()),
      'parent_winners_acted':int((acts.parent_pnl>0).sum()),'parent_losses_acted':int((acts.parent_pnl<=0).sum()),
      'loss_to_positive':loss_pos,'parent_winner_to_nonpositive':parent_win_nonpos,
      'baseline_positive_to_nonpositive':win_nonpos,
      'positive_increment_actions':int((acts.inc_vs_latest>0).sum()),'negative_increment_actions':int((acts.inc_vs_latest<0).sum()),
      'incremental_vs_s63':inc63,'incremental_s63_D':inc63D,'incremental_s63_V':inc63V,
      'incremental_vs_latest':inc,'incremental_D':incD,'incremental_V':incV,
      'wr_gain_pp':float((managed_m['wr']-latest_m['wr'])*100),'dd_improvement':float(latest_m['dd']-managed_m['dd']),
      'jackknife_min_remaining_incremental':jack_min,'blocks4':blocks,'transfer_pass':transfer_pass,
      'actions_detail':acts[['date','period','parent_pnl','parent_mfe_r','s64_latest_pnl','managed_latest','inc_vs_latest','s64_latest_layer','taker_med','last_body_ratio','last_upper_wick_ratio']].to_dict('records') if len(acts) else []}
    (OUT/'s65_summary.json').write_text(json.dumps(out,indent=2,default=str))

    md=['# Saturday S6.5 — Exact Friday D3 Transfer','',
        f"**Integrated latest-stack transfer:** {'PASS' if transfer_pass else 'FAIL'}",
        '**Research only; live BBC untouched. No Saturday retuning.**','',
        '## Exact transferred mechanism',
        f'- +1R milestone normalized to Saturday R={R*100:.2f}% => +{R*100:.2f}%',
        '- decision at hit-bar open +20m after four completed 5m bars',
        '- median taker over four bars <0 + latest close below EMA7',
        '- latest bearish real body >2x total wicks',
        '- latest close breaks previous completed 5m low',
        '- exit actual decision open','',
        '## Frozen Saturday parity',
        f"- parent **{parent_m['pnl']:+.3f}**, WR **{parent_m['wr']*100:.2f}%**",
        f"- S6.3 FIB5+S5.7G **{s63_m['pnl']:+.3f}**, WR **{s63_m['wr']*100:.2f}%**",
        f"- latest S6.4 stack **{latest_m['pnl']:+.3f}**, WR **{latest_m['wr']*100:.2f}%**, PF **{latest_m['pf']:.3f}**, DD **{latest_m['dd']:.3f}**",'',
        '## Transfer result',
        f"- raw D3 signals **{len(raw)}**, active after latest chronology **{len(acts)}**, preempted **{len(raw)-len(acts)}**",
        f"- actions D/V **{(acts.i<SPLIT).sum()} / {(acts.i>=SPLIT).sum()}**",
        f"- parent winners/losses acted **{(acts.parent_pnl>0).sum()} / {(acts.parent_pnl<=0).sum()}**",
        f"- loss→positive **{loss_pos}**, baseline positive→nonpositive **{win_nonpos}**",
        f"- vs S6.3 incremental **{inc63:+.3f}**, D/V **{inc63D:+.3f} / {inc63V:+.3f}**",
        f"- latest-stack PnL **{latest_m['pnl']:+.3f} -> {managed_m['pnl']:+.3f}**, incremental **{inc:+.3f}**",
        f"- D/V incremental **{incD:+.3f} / {incV:+.3f}**",
        f"- WR **{latest_m['wr']*100:.2f}% -> {managed_m['wr']*100:.2f}%**, PF **{latest_m['pf']:.3f} -> {managed_m['pf']:.3f}**, DD **{latest_m['dd']:.3f} -> {managed_m['dd']:.3f}**",'',
        '## Guardrail','This is a genuine cross-context test: the Friday D3 morphology and +20m timing are transferred without Saturday fitting. +1R is normalized to Saturday frozen risk. Do not retune on this Saturday sample.']
    (OUT/'S6.5_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
