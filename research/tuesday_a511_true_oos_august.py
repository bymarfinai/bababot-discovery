#!/usr/bin/env python3
"""Frozen Tuesday A5.11 post-cutoff August replay.

Research only; live BBC untouched.

Frozen strategy (defined on history ending 2026-07-30):
- BTCUSDT Tuesday 06:00 WIB SELL
- TP 1.35%, SL 0.80%, max hold 6h
- A5.2 conditional +0.20% protection after first +0.50% MFE
- A5.9 FastMR: hinge >=0.40% below EMA20 + giveback <=+0.30% within 60m => +0.20% lock
- A5.11 recovery: before FastMR lock touch, EMA7 bearish rejection with progress >=+0.30% cancels lock

This script first reproduces the frozen 139-trade historical stack. It refuses to
score August unless static/A5.2/A5.9/A5.11 parity passes.

August dates scored unchanged: 2026-08-04, 2026-08-11, 2026-08-18.
Aug 4/11 are retrospective post-cutoff observations; Aug 18 is post-freeze.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s57h_true_oos_extension as h57

OUT=Path(os.getenv('TUEA511_OUT','tuea511_out')); OUT.mkdir(parents=True,exist_ok=True)

NOTIONAL=500.0
FEE=0.0015*NOTIONAL
TP=0.0135
SL=0.0080
HOLD_MIN=360
HINGE=0.0050
LOCK=0.0020
A52_WEAK=0.0035
A52_MAE=0.0020
FAST_D20=0.0040
FAST_GIVEBACK=0.0030
FAST_LATENCY=60
RECOVERY_PROGRESS=0.0030
START=pd.Timestamp('2023-12-02',tz='UTC')
END=pd.Timestamp('2026-07-30',tz='UTC')
DAILY_START=pd.Timestamp('2026-08-01',tz='UTC')
DAILY_END=pd.Timestamp('2026-08-18',tz='UTC')
OOS_END=pd.Timestamp('2026-08-19',tz='UTC')
EXPECTED=['2026-08-04','2026-08-11','2026-08-18']


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'pf':None,'exp':None}
    w=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    return {'n':int(len(a)),'wins':w,'losses':int(len(a)-w),'wr':float(w/len(a)),
            'pnl':float(a.sum()),'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean())}


def pnl_at(ep,px):
    return float(NOTIONAL*(1.0-float(px)/float(ep))-FEE)


def load_extended():
    hist=f517.load_klines().reset_index(drop=True)[['ts','open','high','low','close','quote_volume','taker_buy_quote']]
    daily=[h57.parse_kline_zip(d) for d in h57.days(DAILY_START,DAILY_END)]
    k=pd.concat([hist,*daily],ignore_index=True)
    k=k.dropna(subset=['ts','open','high','low','close']).drop_duplicates('ts').sort_values('ts').reset_index(drop=True)
    k['ema7']=k['close'].ewm(span=7,adjust=False).mean()
    k['ema20']=k['close'].ewm(span=20,adjust=False).mean()
    k['taker_imb']=np.where(k['quote_volume']>0,2*k['taker_buy_quote']/k['quote_volume']-1.0,np.nan)
    return k.set_index('ts',drop=False)


def entries(k,start=START,end=END):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    m=(idx>=start)&(idx<end)&(local.dayofweek==1)&(local.hour==6)&(local.minute==0)
    return list(idx[m])


def simulate_parent(k,t):
    ep=float(k.loc[t,'open']); tpp=ep*(1-TP); slp=ep*(1+SL)
    bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(minutes=HOLD_MIN))]
    if len(bars)!=HOLD_MIN//5: raise RuntimeError(f'incomplete parent {t}: {len(bars)}')
    reason='TIMEOUT'; exit_t=t+pd.Timedelta(minutes=HOLD_MIN); exit_px=float(bars.iloc[-1].close)
    mfe=mae=0.0
    for b in bars.itertuples(index=False):
        mfe=max(mfe,1.0-float(b.low)/ep); mae=max(mae,float(b.high)/ep-1.0)
        hit_sl=float(b.high)>=slp; hit_tp=float(b.low)<=tpp
        if hit_sl: # adverse-first same 5m
            reason='SL'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=slp; break
        if hit_tp:
            reason='TP'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=tpp; break
    return {'entry_t':t,'entry':ep,'exit_t':exit_t,'exit_px':exit_px,'reason':reason,
            'pnl':pnl_at(ep,exit_px),'mfe':float(mfe),'mae':float(mae)}


def first_hinge(k,tr):
    t=tr['entry_t']; ep=tr['entry']; bars=k[(k.index>=t)&(k.index<tr['exit_t'])]
    for b in bars.itertuples(index=False):
        if 1.0-float(b.low)/ep>=HINGE:
            d=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=d:return None
            hist=k[(k.index>=t)&(k.index<d)]
            return {'bar_t':b.ts,'decision_t':d,'close_progress':1.0-float(b.close)/ep,
                    'cum_mae':float(hist.high.max())/ep-1.0,
                    'd20':float(b.ema20)/float(b.close)-1.0}
    return None


def run_protect(k,tr,h):
    """A5.2 exact corrected-execution protection."""
    if h is None:return float(tr['pnl']),False,None
    act=bool(h['close_progress']<=A52_WEAK and h['cum_mae']>=A52_MAE)
    if not act:return float(tr['pnl']),False,None
    ep=tr['entry']; lp=ep*(1-LOCK); d=h['decision_t']
    op=float(k.loc[d,'open'])
    if op>=lp:return pnl_at(ep,op),True,'A5.2_MARKET'
    for b in k[(k.index>=d)&(k.index<tr['exit_t'])].itertuples(index=False):
        if float(b.high)>=lp:return pnl_at(ep,lp),True,'A5.2_LOCK'
        if float(b.low)<=ep*(1-TP):return float(tr['pnl']),True,'PARENT_TP'
    return float(tr['pnl']),True,'PARENT'


def fastmr_arm(k,tr,h):
    if h is None or h['d20']<FAST_D20:return None
    start=h['decision_t']; end=min(tr['exit_t'],start+pd.Timedelta(minutes=FAST_LATENCY)); ep=tr['entry']
    for b in k[(k.index>=start)&(k.index<end)].itertuples(index=False):
        prog=1.0-float(b.close)/ep
        if prog<=FAST_GIVEBACK:
            d=b.ts+pd.Timedelta(minutes=5)
            if tr['exit_t']<=d:return None
            return {'signal_bar':b.ts,'decision_t':d,'progress':prog,'d20':h['d20']}
    return None


def run_fastmr(k,tr,arm,recovery=False):
    if arm is None:return float(tr['pnl']),False,False,'PARENT',None
    ep=tr['entry']; lp=ep*(1-LOCK); d=arm['decision_t']; op=float(k.loc[d,'open'])
    if op>=lp:return pnl_at(ep,op),True,False,'FASTMR_MARKET',None
    for b in k[(k.index>=d)&(k.index<tr['exit_t'])].itertuples(index=False):
        # The live lock has priority over any recovery signal forming on this bar.
        if float(b.high)>=lp:
            return pnl_at(ep,lp),True,False,'FASTMR_LOCK',None
        if recovery:
            prog=1.0-float(b.close)/ep
            reject=bool(float(b.high)>=float(b.ema7) and float(b.close)<float(b.ema7) and prog>=RECOVERY_PROGRESS)
            if reject:
                cancel=b.ts+pd.Timedelta(minutes=5)
                if tr['exit_t']>cancel:
                    return float(tr['pnl']),True,True,'A5.11_RUNNER_RECOVERY',cancel
    return float(tr['pnl']),True,False,'PARENT',None


def layered(k,tr):
    h=first_hinge(k,tr)
    a52_p,a52_act,a52_layer=run_protect(k,tr,h)
    if a52_act:
        return {'parent_pnl':float(tr['pnl']),'a52_pnl':a52_p,'a59_pnl':a52_p,'a511_pnl':a52_p,
                'hinge':h,'a52_act':True,'fastmr_arm':False,'recovery':False,
                'final_layer':a52_layer,'recovery_t':None}
    arm=fastmr_arm(k,tr,h)
    a59,fast_act,_,fast_layer,_=run_fastmr(k,tr,arm,False)
    a511,_,rec,layer,rt=run_fastmr(k,tr,arm,True)
    return {'parent_pnl':float(tr['pnl']),'a52_pnl':float(tr['pnl']),'a59_pnl':a59,'a511_pnl':a511,
            'hinge':h,'a52_act':False,'fastmr_arm':fast_act,'recovery':rec,
            'final_layer':layer if fast_act else 'PARENT','recovery_t':rt,'fast_arm':arm}


def historical_parity(k):
    es=entries(k); trs=[simulate_parent(k,t) for t in es]
    rows=[layered(k,tr) for tr in trs]
    p=np.asarray([r['parent_pnl'] for r in rows]); a52=np.asarray([r['a52_pnl'] for r in rows]);
    a59=np.asarray([r['a59_pnl'] for r in rows]); a511=np.asarray([r['a511_pnl'] for r in rows])
    out={'parent':metrics(p),'a52':metrics(a52),'a59':metrics(a59),'a511':metrics(a511),
         'a52_actions':int(sum(r['a52_act'] for r in rows)),
         'fastmr_actions':int(sum(r['fastmr_arm'] for r in rows)),
         'recoveries':int(sum(r['recovery'] for r in rows))}
    checks={
      'n139':out['parent']['n']==139,
      'parent_w79':out['parent']['wins']==79,
      'parent_pnl':abs(out['parent']['pnl']-95.73)<0.15,
      'a52_w83':out['a52']['wins']==83,
      'a52_pnl':abs(out['a52']['pnl']-105.90)<0.15,
      'a52_actions7':out['a52_actions']==7,
      'a59_w89':out['a59']['wins']==89,
      'a59_pnl':abs(out['a59']['pnl']-120.27)<0.15,
      'fast_actions12':out['fastmr_actions']==12,
      'a511_w89':out['a511']['wins']==89,
      'a511_pnl':abs(out['a511']['pnl']-130.33)<0.15,
      'recoveries4':out['recoveries']==4,
    }
    out['checks']=checks; out['pass']=bool(all(checks.values()))
    return out


def main():
    k=load_extended()
    parity=historical_parity(k)
    if not parity['pass']:
        (OUT/'tuesday_a511_parity_failure.json').write_text(json.dumps(parity,indent=2,default=str))
        raise RuntimeError('historical parity failed: '+json.dumps(parity,default=str))

    es=entries(k,pd.Timestamp('2026-08-01',tz='UTC'),OOS_END)
    dates=[(t+pd.Timedelta(hours=7)).strftime('%Y-%m-%d') for t in es]
    if dates!=EXPECTED:raise RuntimeError(f'unexpected August Tuesday entries {dates}')
    rows=[]
    for t,d in zip(es,dates):
        tr=simulate_parent(k,t); r=layered(k,tr); h=r.get('hinge'); arm=r.get('fast_arm')
        rows.append({'date':d,'entry_t_utc':str(t),'entry':tr['entry'],'parent_reason':tr['reason'],
                     'parent_pnl':tr['pnl'],'parent_mfe_pct':100*tr['mfe'],'parent_mae_pct':100*tr['mae'],
                     'hinge_reached':bool(h is not None),'hinge_close_progress_pct':None if h is None else 100*h['close_progress'],
                     'hinge_cum_mae_pct':None if h is None else 100*h['cum_mae'],
                     'hinge_d20_pct':None if h is None else 100*h['d20'],
                     'a52_act':r['a52_act'],'a52_pnl':r['a52_pnl'],
                     'fastmr_arm':r['fastmr_arm'],'fastmr_decision_t':None if arm is None else str(arm['decision_t']),
                     'recovery':r['recovery'],'recovery_t':None if r['recovery_t'] is None else str(r['recovery_t']),
                     'final_layer':r['final_layer'],'a511_pnl':r['a511_pnl'],
                     'delta_champion_vs_parent':r['a511_pnl']-tr['pnl'],
                     'calendar_status':'POST_FREEZE_FORWARD' if d=='2026-08-18' else 'POST_CUTOFF_RETROSPECTIVE'})
    df=pd.DataFrame(rows)
    pm=metrics(df.parent_pnl); cm=metrics(df.a511_pnl)
    summary={'status':'COMPLETE_FROZEN_TUESDAY_A511_AUGUST_REPLAY','research_cutoff':'2026-07-30 UTC',
             'freeze_date':'2026-08-16 WIB','historical_parity':parity,'dates':dates,
             'parent_august':pm,'champion_august':cm,'delta_champion_vs_parent':float(df.delta_champion_vs_parent.sum()),
             'a52_actions':int(df.a52_act.sum()),'fastmr_actions':int(df.fastmr_arm.sum()),'runner_recoveries':int(df.recovery.sum()),
             'forward_post_freeze_n':1,
             'guardrail':'Frozen rules unchanged. Aug4/11 are data-level post-cutoff retrospective observations; Aug18 is post-freeze forward. N=3 is too small to prove or reject the edge.'}
    df.to_csv(OUT/'tuesday_a511_true_oos_august_rows.csv',index=False)
    (OUT/'tuesday_a511_true_oos_august_summary.json').write_text(json.dumps(summary,indent=2,default=str))
    def wr(m):return '-' if m['wr'] is None else f"{100*m['wr']:.1f}%"
    md=['# Frozen Tuesday A5.11 — August Post-Cutoff Replay','',
        '**Status: COMPLETE — frozen rules unchanged; live BBC untouched.**','',
        '## Historical parity',
        f"- Parent: {parity['parent']['wins']}/{parity['parent']['n']}, PnL **${parity['parent']['pnl']:+.2f}**.",
        f"- A5.2: {parity['a52']['wins']}/{parity['a52']['n']}, PnL **${parity['a52']['pnl']:+.2f}**, actions {parity['a52_actions']}.",
        f"- A5.9: {parity['a59']['wins']}/{parity['a59']['n']}, PnL **${parity['a59']['pnl']:+.2f}**, FastMR actions {parity['fastmr_actions']}.",
        f"- A5.11: {parity['a511']['wins']}/{parity['a511']['n']}, PnL **${parity['a511']['pnl']:+.2f}**, recoveries {parity['recoveries']}.",
        '- parity gate **PASS**.','',
        '## August 2026',
        f"- Static parent: {pm['wins']}/{pm['n']} wins, WR **{wr(pm)}**, PnL **${pm['pnl']:+.2f}**.",
        f"- Frozen A5.11 champion: {cm['wins']}/{cm['n']} wins, WR **{wr(cm)}**, PnL **${cm['pnl']:+.2f}**.",
        f"- adaptive delta vs parent **${summary['delta_champion_vs_parent']:+.2f}**.",
        f"- A5.2 / FastMR / recovery activations: **{summary['a52_actions']} / {summary['fastmr_actions']} / {summary['runner_recoveries']}**.",'',
        '| Date | Parent | MFE | A5.2 | FastMR | Recovery | Final | Champion |','|---|---:|---:|---:|---:|---:|---|---:|']
    for x in rows:
        md.append(f"| {x['date']} | ${x['parent_pnl']:+.2f} | {x['parent_mfe_pct']:.3f}% | {x['a52_act']} | {x['fastmr_arm']} | {x['recovery']} | {x['final_layer']} | ${x['a511_pnl']:+.2f} |")
    md += ['', '## OOS interpretation',
           '- Aug 4 and Aug 11 occur after the Jul-30 research-data cutoff, but before the Aug-16 freeze date: treat them as retrospective unseen extension, not forward-live observations.',
           '- Aug 18 is the first observation after the freeze date and is the cleanest forward datapoint.',
           '- N=3 is only an early warning/encouragement signal, never proof of non-overfit or overfit.','',
           '## Guardrail',summary['guardrail']]
    (OUT/'TUESDAY_A511_TRUE_OOS_AUGUST.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=str),flush=True)

if __name__=='__main__':main()
