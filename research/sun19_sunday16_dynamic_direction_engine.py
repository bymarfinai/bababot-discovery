#!/usr/bin/env python3
"""SUN1.9 — Sunday16 dynamic BUY/SELL/WAIT engine from natural Fri/Sat/Sun signs.

Research only; live BBC untouched.

Purpose:
- Preserve the SUN1.8 RUNNER state: Saturday<0 AND Sunday-pre16<0 => SELL.
- Split the remaining WATCH population into the six natural F/S/U sign states.
- For each WATCH state, compare fixed mirrored BUY vs SELL parents using DISCOVERY only.
- Choose the more profitable direction only if its discovery PnL is positive; otherwise WAIT.
- Validation is report-only. No continuous thresholds, timing sweeps, or TP/SL retuning.

Execution geometry for both directions:
- Sunday 16:00 WIB actual 5m open
- TP 2.5%, SL 1.4%, max hold 18h
- $500 notional, 0.15% round-trip fee
- historical funding, exact SUN1.6 exit-bar-open convention
- adverse-first if TP and SL touch in same 5m bar
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17_sunday16_loss_prevday_forensics as sun17

OUT=Path(os.getenv('SUN19_OUT','sun19_out')); OUT.mkdir(parents=True,exist_ok=True)
NOTIONAL=500.0; FEE=0.0015*NOTIONAL
START=pd.Timestamp('2023-12-02',tz='UTC'); END=pd.Timestamp('2026-07-30',tz='UTC')
DISC_N=83; TP=0.025; SL=0.014; HOLD_MIN=18*60


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:
        return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'exp':None,'dd':0.0,'loss_streak':0}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peaks[1:]-eq))
    cur=best=0
    for x in a:
        if x<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return {'n':int(len(a)),'wins':wins,'wr':float(wins/len(a)),'pnl':float(a.sum()),
            'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean()),'dd':dd,'loss_streak':int(best)}


def entries(k):
    idx=k.index; local=idx+pd.Timedelta(hours=7)
    m=(idx>=START)&(idx<END)&(local.dayofweek==6)&(local.hour==16)&(local.minute==0)
    e=list(idx[m])
    if len(e)!=139: raise RuntimeError(f'entry parity {len(e)}')
    return e


def funding_cost_exact(k,f,entry_t,exit_t,entry_px,direction):
    # Exact SUN1.6 convention: settlements after entry and no later than EXIT BAR OPEN.
    exit_bar_t=exit_t-pd.Timedelta(minutes=5)
    rows=f[(f.ts>entry_t)&(f.ts<=exit_bar_t)]
    qty=NOTIONAL/entry_px; cost=0.0; n=0
    for r in rows.itertuples(index=False):
        if r.ts not in k.index: continue
        px=float(k.loc[r.ts,'open']); rate=float(r.rate)
        # BUY pays positive rate; SELL receives positive rate.
        cost += direction*qty*px*rate
        n += 1
    return float(cost),int(n)


def simulate(k,f,t,direction):
    ep=float(k.loc[t,'open'])
    if direction==1: # BUY
        tp_px=ep*(1+TP); sl_px=ep*(1-SL)
    else:            # SELL
        tp_px=ep*(1-TP); sl_px=ep*(1+SL)
    bars=k[(k.index>=t)&(k.index<t+pd.Timedelta(minutes=HOLD_MIN))]
    if len(bars)!=HOLD_MIN//5: raise RuntimeError(f'incomplete {t}: {len(bars)}')
    reason='TIMEOUT'; exit_t=t+pd.Timedelta(minutes=HOLD_MIN); exit_px=float(bars.iloc[-1].close)
    for b in bars.itertuples(index=False):
        if direction==1:
            hit_sl=float(b.low)<=sl_px; hit_tp=float(b.high)>=tp_px
        else:
            hit_sl=float(b.high)>=sl_px; hit_tp=float(b.low)<=tp_px
        if hit_sl: # adverse-first same bar
            reason='SL'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=sl_px; break
        if hit_tp:
            reason='TP'; exit_t=b.ts+pd.Timedelta(minutes=5); exit_px=tp_px; break
    gross=(exit_px/ep-1.0) if direction==1 else (1.0-exit_px/ep)
    fc,fn=funding_cost_exact(k,f,t,exit_t,ep,direction)
    pnl=NOTIONAL*gross-FEE-fc
    return {'pnl':float(pnl),'reason':reason,'entry':ep,'exit_t':exit_t,'funding':fc,'funding_events':fn}


def sign(x): return '+' if x>=0 else '-'


def state_key(ctx):
    return f"F{sign(ctx['fri_day_ret'])}|S{sign(ctx['sat_day_ret'])}|U{sign(ctx['sun_pre16_ret'])}"


def subset_metrics(arr,idx):
    return metrics(np.asarray(arr,float)[np.asarray(idx,int)])


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=entries(k)
    rows=[]
    sell=[]; buy=[]
    for i,t in enumerate(es):
        ctx=sun17.pre_context(k,t)
        s=simulate(k,f,t,-1); b=simulate(k,f,t,1)
        key=state_key(ctx); runner=(ctx['sat_day_ret']<0 and ctx['sun_pre16_ret']<0)
        sell.append(s['pnl']); buy.append(b['pnl'])
        rows.append({'i':i,'entry_t':str(t),'state':key,'runner':runner,
                     'fri_day_ret':ctx['fri_day_ret'],'sat_day_ret':ctx['sat_day_ret'],'sun_pre16_ret':ctx['sun_pre16_ret'],
                     'sell_pnl':s['pnl'],'buy_pnl':b['pnl'],'sell_reason':s['reason'],'buy_reason':b['reason']})
    df=pd.DataFrame(rows); sell=np.array(sell,float); buy=np.array(buy,float)

    # SELL parity to frozen Sunday16 parent.
    sm=metrics(sell)
    if not (sm['n']==139 and sm['wins']==66 and abs(sm['pnl']-63.599379132074105)<0.25):
        raise RuntimeError(f'SELL parent parity failed {sm}')

    states=sorted(df.state.unique())
    decisions={}; table=[]
    for st in states:
        idx=np.flatnonzero(df.state.to_numpy()==st)
        d_idx=idx[idx<DISC_N]; v_idx=idx[idx>=DISC_N]
        ds=subset_metrics(sell,d_idx); db=subset_metrics(buy,d_idx)
        vs=subset_metrics(sell,v_idx); vb=subset_metrics(buy,v_idx)
        fs=subset_metrics(sell,idx); fb=subset_metrics(buy,idx)
        is_runner=bool(df.loc[idx,'runner'].all()) if len(idx) else False
        if is_runner:
            decision='SELL'
            basis='LOCKED_RUNNER_S-_U-'
        else:
            # Discovery-only natural router: direction with higher D PnL if positive; else WAIT.
            best='SELL' if ds['pnl']>=db['pnl'] else 'BUY'
            best_pnl=max(ds['pnl'],db['pnl'])
            decision=best if best_pnl>0 else 'WAIT'
            basis='DISCOVERY_BEST_POSITIVE' if decision!='WAIT' else 'DISCOVERY_BOTH_NONPOSITIVE'
        decisions[st]=decision
        chosenD={'SELL':ds,'BUY':db}.get(decision,metrics([]))
        chosenV={'SELL':vs,'BUY':vb}.get(decision,metrics([]))
        chosenF={'SELL':fs,'BUY':fb}.get(decision,metrics([]))
        table.append({'state':st,'n':len(idx),'D_n':len(d_idx),'V_n':len(v_idx),'runner':is_runner,
                      'decision':decision,'basis':basis,
                      'D_SELL':ds,'D_BUY':db,'V_SELL':vs,'V_BUY':vb,
                      'chosen_D':chosenD,'chosen_V':chosenV,'chosen_full':chosenF})

    # Build the fixed discovery-selected engine; WAIT contributes no trade and zero PnL.
    engine_pnls=[]; engine_indices=[]; engine_dirs=[]
    D_pnls=[]; V_pnls=[]
    for i,r in df.iterrows():
        dec=decisions[r.state]
        if dec=='WAIT': continue
        p=float(sell[i] if dec=='SELL' else buy[i])
        engine_pnls.append(p); engine_indices.append(i); engine_dirs.append(dec)
        (D_pnls if i<DISC_N else V_pnls).append(p)

    em=metrics(engine_pnls); dmet=metrics(D_pnls); vmet=metrics(V_pnls)
    coverage=len(engine_pnls)/139.0
    D_cov=len(D_pnls)/DISC_N; V_cov=len(V_pnls)/(139-DISC_N)
    direction_counts={'SELL':int(sum(x=='SELL' for x in engine_dirs)),'BUY':int(sum(x=='BUY' for x in engine_dirs)),
                      'WAIT':int(sum(decisions[r.state]=='WAIT' for _,r in df.iterrows()))}

    # Validation-only aggregate of the already-frozen discovery router.
    out={'status':'COMPLETE_DISCOVERY_ROUTER_VALIDATION_REPORT_ONLY',
         'definition':{'entry':'Sunday 16:00 WIB','geometry':'TP2.5 SL1.4 hold18h mirrored BUY/SELL',
                       'states':'sign of Friday day, Saturday day, Sunday 00:00->16:00 returns',
                       'runner_lock':'S- and U- => SELL regardless Friday',
                       'watch_selection':'per exact F/S/U state, choose higher discovery PnL BUY or SELL only if >0, otherwise WAIT',
                       'validation':'report-only; never used to choose direction'},
         'sell_parent':sm,'state_table':table,'decisions':decisions,
         'engine':{'full':em,'D':dmet,'V':vmet,'coverage':coverage,'D_coverage':D_cov,'V_coverage':V_cov,
                   'direction_counts':direction_counts},
         'guardrail':'Same historical sample was already inspected in SUN1.7/SUN1.8. This is a diagnostic router, not untouched OOS validation.'}
    (OUT/'sun19_summary.json').write_text(json.dumps(out,indent=2,default=str))
    df.to_csv(OUT/'sun19_trades.csv',index=False)

    md=['# SUN1.9 — Sunday16 Dynamic BUY / SELL / WAIT','',
        '**Status: COMPLETE — discovery-selected natural-state router; validation report-only; live BBC untouched.**','',
        '## State decisions','',
        '| State | N | Decision | D chosen WR | D chosen PnL | V chosen WR | V chosen PnL |','|---|---:|---|---:|---:|---:|---:|']
    for x in table:
        def pct(m): return '-' if m['wr'] is None else f"{100*m['wr']:.1f}%"
        md.append(f"| {x['state']} | {x['n']} | **{x['decision']}** | {pct(x['chosen_D'])} | ${x['chosen_D']['pnl']:+.2f} | {pct(x['chosen_V'])} | ${x['chosen_V']['pnl']:+.2f} |")
    md += ['', '## Combined engine',
           f"- Trades **{em['n']}/139** ({100*coverage:.1f}% coverage); SELL {direction_counts['SELL']}, BUY {direction_counts['BUY']}, WAIT {direction_counts['WAIT']}.",
           f"- Full: WR **{100*em['wr']:.2f}%**, PnL **${em['pnl']:+.2f}**, PF **{em['pf']:.2f}**, DD ${em['dd']:.2f}.",
           f"- Discovery: trades {dmet['n']}/{DISC_N}, WR **{100*dmet['wr']:.2f}%**, PnL **${dmet['pnl']:+.2f}**, PF **{dmet['pf']:.2f}**.",
           f"- Validation: trades {vmet['n']}/{139-DISC_N}, WR **{100*vmet['wr']:.2f}%**, PnL **${vmet['pnl']:+.2f}**, PF **{vmet['pf']:.2f}**.",'',
           '## Guardrail',out['guardrail']]
    (OUT/'SUN1.9_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__': main()
