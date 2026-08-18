#!/usr/bin/env python3
"""Sunday Friday-method SF6-SF8 — confirmed failure-to-develop management.

Motivated by SF5 forensic, with one predeclared natural state at +6h:
- trade still alive;
- MFE so far <0.5R (R=1.4%, so <0.70% favorable);
- close-progress <=0 (SELL has not developed);
- last completed close >= EMA20;
- >50% of completed 5m candles since entry are green (bullish majority).

SF6 comparator: immediate exit at actual +6h open.
SF7/SF8 Friday-style recovery confirmation: wait to +7h; HOLD original parent if either
  (a) +7h last completed close is lower than +6h last completed close, or
  (b) +6h->+7h taker imbalance <0 (seller flow).
Otherwise exit actual +7h open.

No timing, EMA period, MFE threshold, progress threshold, candle-majority threshold, or flow threshold sweep.
Live BBC untouched. D/V are robustness slices only because Sunday history was previously inspected.
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
OUT=Path(os.getenv('SUNFM68_OUT','sunfm68_out')); OUT.mkdir(parents=True,exist_ok=True)
DISC_N=83; R=0.014


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'pf':None,'dd':0.0,'ls':0}
    wins=int((a>0).sum());gp=float(a[a>0].sum());gl=float(-a[a<=0].sum())
    eq=np.cumsum(a);peak=np.maximum.accumulate(np.r_[0.,eq]);dd=float(np.max(peak[1:]-eq));cur=ls=0
    for x in a:
        if x<=0:cur+=1;ls=max(ls,cur)
        else:cur=0
    return {'n':len(a),'wins':wins,'wr':wins/len(a),'pnl':float(a.sum()),'pf':gp/gl if gl>0 else 999.0,'dd':dd,'ls':ls}


def funding_pnl(k,f,tr,dt,px):
    ep=float(tr['entry']);fc,_=sun17.funding_short(k,f,tr['entry_t'],dt+pd.Timedelta(minutes=5),ep)
    return float(sun17.NOTIONAL*(1-px/ep)-sun17.FEE-fc)


def state(k,tr,m):
    t=tr['entry_t'];dt=t+pd.Timedelta(minutes=m)
    if tr['exit_t']<=dt or dt not in k.index:return None
    x=k[(k.index>=t)&(k.index<dt)]
    if len(x)!=m//5:return None
    last=x.iloc[-1];ep=float(tr['entry']);cl=x.close.astype(float).to_numpy();op=x.open.astype(float).to_numpy()
    return {'dt':dt,'open':float(k.loc[dt,'open']),'last_close':float(last.close),
            'progress':1-float(last.close)/ep,'mfe_r':(1-float(x.low.min())/ep)/R,
            'above20':bool(float(last.close)>=float(last.ema20)),'above7':bool(float(last.close)>=float(last.ema7)),
            'green_frac':float(np.mean(cl>op))}


def candidate6(s):
    return bool(s is not None and s['mfe_r']<0.5 and s['progress']<=0 and s['above20'] and s['green_frac']>0.5)


def flow67(k,tr):
    t=tr['entry_t'];x=k[(k.index>=t+pd.Timedelta(hours=6))&(k.index<t+pd.Timedelta(hours=7))]
    if len(x)!=12:return np.nan
    q=float(x.quote_volume.sum());b=float(x.taker_buy_quote.sum());return 2*b/q-1 if q>0 else np.nan


def main():
    k=f517.load_klines();f=s50.load_funding();trs=[sun17.simulate_parent(k,f,t) for t in sun17.entries(k)]
    parent=np.array([tr['pnl'] for tr in trs],float)
    if len(parent)!=139 or int((parent>0).sum())!=66 or abs(parent.sum()-63.599379132074105)>0.25:raise RuntimeError('parent parity')
    cut6=[];confirm7=[];rows=[]
    for i,tr in enumerate(trs):
        s6=state(k,tr,360);cand=candidate6(s6)
        if cand:
            p6=funding_pnl(k,f,tr,s6['dt'],s6['open'])
        else:p6=float(tr['pnl'])
        cut6.append(p6)

        layer='PARENT';p7=float(tr['pnl']);s7=None;fl=np.nan;pr=False;fr=False
        if cand:
            s7=state(k,tr,420)
            if s7 is not None:
                fl=flow67(k,tr);pr=bool(s7['last_close']<s6['last_close']);fr=bool(np.isfinite(fl) and fl<0)
                if pr or fr:layer='RECOVERY7_HOLD'
                else:
                    p7=funding_pnl(k,f,tr,s7['dt'],s7['open']);layer='CUT7'
            else:layer='PARENT_EXIT_BEFORE7'
        confirm7.append(p7)
        rows.append({'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),'parent_pnl':float(tr['pnl']),
                     'parent_reason':tr['reason'],'parent_win':bool(tr['pnl']>0),'candidate6':cand,
                     'cp6_progress':None if s6 is None else s6['progress'],'cp6_mfe_r':None if s6 is None else s6['mfe_r'],
                     'cp6_above20':None if s6 is None else s6['above20'],'cp6_green_frac':None if s6 is None else s6['green_frac'],
                     'cut6_pnl':p6,'confirm7_pnl':p7,'layer':layer,'flow67':None if not np.isfinite(fl) else fl,
                     'price_repair7':pr,'flow_repair7':fr})
    cut6=np.asarray(cut6);confirm7=np.asarray(confirm7);df=pd.DataFrame(rows);df.to_csv(OUT/'sunfm68_rows.csv',index=False)
    def pack(a):return {'full':metrics(a),'D':metrics(a[:DISC_N]),'V':metrics(a[DISC_N:])}
    P=pack(parent);C6=pack(cut6);C7=pack(confirm7);cand=df[df.candidate6];cuts=df[df.layer=='CUT7'];holds=df[df.layer=='RECOVERY7_HOLD']
    d7=confirm7-parent;blocks=[metrics(confirm7[z]) for z in np.array_split(np.arange(139),8)]
    out={'status':'COMPLETE_SUNDAY_FRIDAY_METHOD_SF6_SF8','parent':P,'cut6':C6,'confirm7':C7,
         'rule':'+6h MFE<0.5R + progress<=0 + close>=EMA20 + green_frac>50%; +7h HOLD on lower-close or seller-flow else CUT',
         'funnel':{'candidate6':len(cand),'D':int((cand.i<DISC_N).sum()),'V':int((cand.i>=DISC_N).sum()),'recovery7_hold':len(holds),'cut7':len(cuts)},
         'delta_full':float(d7.sum()),'delta_D':float(d7[:DISC_N].sum()),'delta_V':float(d7[DISC_N:].sum()),
         'cut7_parent_W':int((cuts.parent_pnl>0).sum()),'cut7_parent_L':int((cuts.parent_pnl<=0).sum()),
         'cut7_loss_to_positive':int(((cuts.parent_pnl<=0)&(cuts.confirm7_pnl>0)).sum()),
         'cut7_winner_to_nonpositive':int(((cuts.parent_pnl>0)&(cuts.confirm7_pnl<=0)).sum()),
         'positive_blocks':int(sum(x['pnl']>0 for x in blocks)),
         'guardrail':'Single natural state from SF5 forensic; no parameter sweep. Same-sample research; requires true-OOS trigger evidence before live.'}
    (OUT/'sunfm68_summary.json').write_text(json.dumps(out,indent=2,default=str))
    def wr(m):return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday Friday-Method SF6-SF8 — Confirmed Failure','', '**Status: COMPLETE — single natural failure state + Friday-style recovery confirmation.**','',
        '## Rule','- +6h candidate: MFE<0.5R, progress<=0, close>=EMA20, bullish candle majority >50%.',
        '- +7h: if close improves downward vs +6h OR +6→7h taker flow is seller-dominant, HOLD original runner.',
        '- Otherwise CUT at actual +7h open.','',
        '## Funnel',f"- candidates +6h **{len(cand)}** (D/V {(cand.i<DISC_N).sum()}/{(cand.i>=DISC_N).sum()})",f"- recovery HOLD +7h **{len(holds)}**",f"- CUT7 **{len(cuts)}**",'',
        '## Result',f"- Parent: WR **{wr(P['full'])}**, PnL **${P['full']['pnl']:+.2f}**, PF **{P['full']['pf']:.2f}**, DD **${P['full']['dd']:.2f}**.",
        f"- Immediate CUT6: WR **{wr(C6['full'])}**, PnL **${C6['full']['pnl']:+.2f}**, D/V **${C6['D']['pnl']:+.2f} / ${C6['V']['pnl']:+.2f}**.",
        f"- CONFIRM7: WR **{wr(C7['full'])}**, PnL **${C7['full']['pnl']:+.2f}**, PF **{C7['full']['pf']:.2f}**, DD **${C7['full']['dd']:.2f}**.",
        f"- delta vs parent **${d7.sum():+.2f}**; D/V **${d7[:DISC_N].sum():+.2f} / ${d7[DISC_N:].sum():+.2f}**.",
        f"- CUT7 parent W/L **{(cuts.parent_pnl>0).sum()}/{(cuts.parent_pnl<=0).sum()}**; loss→positive **{((cuts.parent_pnl<=0)&(cuts.confirm7_pnl>0)).sum()}**; winner→nonpositive **{((cuts.parent_pnl>0)&(cuts.confirm7_pnl<=0)).sum()}**.",
        f"- positive blocks **{sum(x['pnl']>0 for x in blocks)}/8**.",'', '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF6_SF8_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)
if __name__=='__main__':main()
