#!/usr/bin/env python3
"""SUN2.0 — refine Sunday16 WAIT/unstable states with natural pre-entry context.

Research only; live BBC untouched.

Base: SUN1.9 F/S/U BUY-SELL-WAIT router, TP2.5 SL1.4 hold18h.
Refinement applies ONLY to coarse states that were WAIT in SUN1.9 plus the unstable
F-|S-|U+ state. Two natural, fully pre-entry views are used:
- Thursday calendar-day direction (T+/T-)
- Sunday 12:00->16:00 direction (L4+/L4-)

For each target coarse state, discovery independently chooses BUY/SELL/WAIT within
its Thursday-sign subgroup and within its last-4h-sign subgroup. A trade is taken
only when BOTH views independently agree on the same non-WAIT direction.
Otherwise WAIT. No TP/SL/hold/timing/continuous-threshold sweep.
Validation is report-only.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17_sunday16_loss_prevday_forensics as sun17
import sun19_sunday16_dynamic_direction_engine as sun19

OUT=Path(os.getenv('SUN20_OUT','sun20_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83
TARGET={'F+|S+|U-','F+|S-|U+','F-|S+|U+','F-|S-|U+'}


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0: return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'exp':None,'dd':0.0,'loss_streak':0}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peaks=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peaks[1:]-eq))
    cur=best=0
    for x in a:
        if x<=0: cur+=1; best=max(best,cur)
        else: cur=0
    return {'n':int(len(a)),'wins':wins,'wr':float(wins/len(a)),'pnl':float(a.sum()),
            'pf':float(gp/gl) if gl>0 else 999.0,'exp':float(a.mean()),'dd':dd,'loss_streak':int(best)}


def choose(d_sell,d_buy):
    ms=metrics(d_sell); mb=metrics(d_buy)
    best='SELL' if ms['pnl']>=mb['pnl'] else 'BUY'
    bp=max(ms['pnl'],mb['pnl'])
    return (best if bp>0 else 'WAIT'),ms,mb


def sign(x): return '+' if x>=0 else '-'


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun19.entries(k)
    rows=[]; sell=[]; buy=[]
    for i,t in enumerate(es):
        ctx=sun17.pre_context(k,t)
        s=sun19.simulate(k,f,t,-1); b=sun19.simulate(k,f,t,1)
        coarse=sun19.state_key(ctx)
        rows.append({'i':i,'entry_t':str(t),'coarse':coarse,
                     'thu_sign':sign(ctx['thu_day_ret']),'l4_sign':sign(ctx['sun12_to16_ret']),
                     'thu_day_ret':ctx['thu_day_ret'],'sun12_to16_ret':ctx['sun12_to16_ret'],
                     'sell_pnl':s['pnl'],'buy_pnl':b['pnl']})
        sell.append(s['pnl']); buy.append(b['pnl'])
    df=pd.DataFrame(rows); sell=np.array(sell,float); buy=np.array(buy,float)

    # Parent parity.
    sm=metrics(sell)
    if not (sm['n']==139 and sm['wins']==66 and abs(sm['pnl']-63.599379132074105)<0.25):
        raise RuntimeError(f'SELL parity failed {sm}')

    # Recreate SUN1.9 coarse decisions from discovery only.
    coarse_dec={}; coarse_detail={}
    for st in sorted(df.coarse.unique()):
        idx=np.flatnonzero(df.coarse.to_numpy()==st); d=idx[idx<DISC_N]
        # locked runner = S- and U-
        runner=('|S-|U-' in st)
        if runner:
            dec='SELL'; ms=metrics(sell[d]); mb=metrics(buy[d])
        else:
            dec,ms,mb=choose(sell[d],buy[d])
        coarse_dec[st]=dec; coarse_detail[st]={'decision':dec,'D_SELL':ms,'D_BUY':mb,'n':len(idx)}

    # Exact parity to SUN1.9 engine headline.
    p19=[]; p19_i=[]
    for i,r in df.iterrows():
        dec=coarse_dec[r.coarse]
        if dec=='WAIT': continue
        p19.append(float(sell[i] if dec=='SELL' else buy[i])); p19_i.append(i)
    m19=metrics(p19)
    if not (m19['n']==76 and abs(m19['pnl']-190.64)<0.35):
        raise RuntimeError(f'SUN1.9 engine parity failed {m19} decisions={coarse_dec}')

    # Discovery subgroup decisions for the two independent natural views.
    thu_dec={}; l4_dec={}; subgroup=[]
    for st in sorted(TARGET):
        for sg in ['+','-']:
            idx=np.flatnonzero((df.coarse.to_numpy()==st)&(df.thu_sign.to_numpy()==sg)&(df.i.to_numpy()<DISC_N))
            dec,ms,mb=choose(sell[idx],buy[idx])
            thu_dec[(st,sg)]=dec
            subgroup.append({'state':st,'view':'THU','sign':sg,'D_n':len(idx),'decision':dec,'D_SELL':ms,'D_BUY':mb})
            idx2=np.flatnonzero((df.coarse.to_numpy()==st)&(df.l4_sign.to_numpy()==sg)&(df.i.to_numpy()<DISC_N))
            dec2,ms2,mb2=choose(sell[idx2],buy[idx2])
            l4_dec[(st,sg)]=dec2
            subgroup.append({'state':st,'view':'L4','sign':sg,'D_n':len(idx2),'decision':dec2,'D_SELL':ms2,'D_BUY':mb2})

    # Build refined engine: untouched SUN1.9 decisions outside targets; inside targets require agreement.
    final=[]; final_i=[]; final_dir=[]; decisions=[]
    recovered=[]
    for i,r in df.iterrows():
        if r.coarse not in TARGET:
            dec=coarse_dec[r.coarse]; basis='SUN19_COARSE'
        else:
            a=thu_dec[(r.coarse,r.thu_sign)]; b=l4_dec[(r.coarse,r.l4_sign)]
            dec=a if (a==b and a!='WAIT') else 'WAIT'
            basis=f'AGREE_{a}_{b}'
        decisions.append(dec)
        if dec!='WAIT':
            p=float(sell[i] if dec=='SELL' else buy[i]); final.append(p); final_i.append(i); final_dir.append(dec)
            if r.coarse in TARGET: recovered.append(i)

    final=np.array(final,float); final_i=np.array(final_i,int)
    Dmask=final_i<DISC_N; Vmask=~Dmask
    outm={'full':metrics(final),'D':metrics(final[Dmask]),'V':metrics(final[Vmask])}
    recovered=np.array(recovered,int)
    recD=recovered[recovered<DISC_N]; recV=recovered[recovered>=DISC_N]
    # PnL for recovered target trades under their final decisions.
    decarr=np.array(decisions,object)
    def pnl_idx(idxs):
        return np.array([sell[i] if decarr[i]=='SELL' else buy[i] for i in idxs],float)
    rec={'full':metrics(pnl_idx(recovered)) if len(recovered) else metrics([]),
         'D':metrics(pnl_idx(recD)) if len(recD) else metrics([]),
         'V':metrics(pnl_idx(recV)) if len(recV) else metrics([])}

    # Per target coarse state final behavior.
    target_table=[]
    for st in sorted(TARGET):
        idx=np.flatnonzero(df.coarse.to_numpy()==st)
        ti=np.array([i for i in idx if decarr[i]!='WAIT'],int)
        di=ti[ti<DISC_N]; vi=ti[ti>=DISC_N]
        target_table.append({'state':st,'N':len(idx),'trade_n':len(ti),'D_trade_n':len(di),'V_trade_n':len(vi),
                             'D':metrics(pnl_idx(di)) if len(di) else metrics([]),
                             'V':metrics(pnl_idx(vi)) if len(vi) else metrics([]),
                             'full':metrics(pnl_idx(ti)) if len(ti) else metrics([])})

    result={'status':'COMPLETE_NATURAL_AGREEMENT_REFINEMENT',
            'definition':{'base':'SUN1.9 coarse F/S/U router','targets':sorted(TARGET),
                          'view1':'Thursday day sign','view2':'Sunday 12:00->16:00 sign',
                          'target_rule':'trade only if discovery subgroup decisions from both views agree on same BUY/SELL; otherwise WAIT',
                          'geometry':'mirrored BUY/SELL TP2.5 SL1.4 hold18h',
                          'validation':'report-only'},
            'sun19_parity':m19,'coarse_decisions':coarse_dec,'subgroups':subgroup,
            'target_table':target_table,'recovered_target':rec,'engine':outm,
            'counts':{'trades':len(final),'wait':139-len(final),'SELL':int(sum(x=='SELL' for x in final_dir)),'BUY':int(sum(x=='BUY' for x in final_dir))},
            'guardrail':'Diagnostic only. The overall historical sample has been inspected in prior Sunday research; validation is not untouched OOS.'}
    (OUT/'sun20_summary.json').write_text(json.dumps(result,indent=2,default=str))
    df.assign(final_decision=decisions).to_csv(OUT/'sun20_trades.csv',index=False)

    def wr(m): return '-' if m['wr'] is None else f"{100*m['wr']:.1f}%"
    md=['# SUN2.0 — Sunday16 WAIT / Unstable Natural Refinement','',
        '**Status: COMPLETE — diagnostic natural-state refinement; live BBC untouched.**','',
        '## Comparison',
        f"- SUN1.9: {m19['n']} trades, WR **{100*m19['wr']:.2f}%**, PnL **${m19['pnl']:+.2f}**, PF **{m19['pf']:.2f}**.",
        f"- SUN2.0: {outm['full']['n']} trades, WR **{100*outm['full']['wr']:.2f}%**, PnL **${outm['full']['pnl']:+.2f}**, PF **{outm['full']['pf']:.2f}**, DD ${outm['full']['dd']:.2f}.",
        f"- D: {outm['D']['n']} trades, WR {100*outm['D']['wr']:.2f}%, PnL ${outm['D']['pnl']:+.2f}.",
        f"- V: {outm['V']['n']} trades, WR {100*outm['V']['wr']:.2f}%, PnL ${outm['V']['pnl']:+.2f}.",'',
        '## Recovered target states','',
        '| Coarse state | Trades | D WR/PnL | V WR/PnL | Full WR/PnL |','|---|---:|---:|---:|---:|']
    for x in target_table:
        md.append(f"| {x['state']} | {x['trade_n']} | {wr(x['D'])} / ${x['D']['pnl']:+.2f} | {wr(x['V'])} / ${x['V']['pnl']:+.2f} | {wr(x['full'])} / ${x['full']['pnl']:+.2f} |")
    md += ['',f"Recovered target total: {rec['full']['n']} trades, WR **{wr(rec['full'])}**, PnL **${rec['full']['pnl']:+.2f}**; V {rec['V']['n']} trades, WR {wr(rec['V'])}, PnL ${rec['V']['pnl']:+.2f}.",'',
           '## Guardrail',result['guardrail']]
    (OUT/'SUN2.0_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(result,indent=2,default=str),flush=True)

if __name__=='__main__': main()
