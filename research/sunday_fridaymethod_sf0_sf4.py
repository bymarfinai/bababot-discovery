#!/usr/bin/env python3
"""Sunday Friday-method SF0-SF4.

Research only; live BBC untouched.
Reset parent: Sunday 16:00 WIB SELL, TP2.5%, SL1.4%, max hold18h.

Purpose: adapt the *process* of Friday F6 failure->repair->confirmation to Sunday,
without copying Friday numeric thresholds.

Predeclared Sunday causal milestones from prior Sunday path anatomy:
- +2h: WATCH only if all three directional failure signs agree:
    close progress <= 0 (SELL has not developed), close >= EMA20, last-30m taker imbalance > 0.
- +4h: release WATCH back to parent if ANY repair appears:
    progress > 0 OR close < EMA20 OR last-30m taker imbalance < 0.
  Otherwise mark PERSISTENT4.
- +6h: candidate failure only if still alive and all three failure signs again agree.
- +7h confirmation: preserve runner if either bearish price repair or seller-flow repair appears
    versus +6h: last completed close at +7h < last completed close at +6h OR +6->7h taker mean < 0.
  Otherwise exit at actual +7h open.

Comparators (diagnostic only):
A) immediate +6h cut of persistent failures;
B) Friday-style +7h confirmation above.
No timing, EMA period, taker threshold, or price threshold sweep.
Discovery first 83 / validation last 56 are report slices only because Sunday history was previously inspected.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import s50_saturday_parent_forensics as s50
import sun17b_sunday16_loss_prevday_forensics_exactfunding as sun17b

sun17 = sun17b.base
sun17.funding_short = sun17b.exact_sun16_funding
OUT = Path(os.getenv('SUNFM_OUT','sunfm_out')); OUT.mkdir(parents=True, exist_ok=True)
DISC_N = 83


def metrics(a):
    a=np.asarray(a,float)
    if len(a)==0:return {'n':0,'wins':0,'losses':0,'wr':None,'pnl':0.0,'pf':None,'dd':0.0,'ls':0,'exp':None}
    wins=int((a>0).sum()); gp=float(a[a>0].sum()); gl=float(-a[a<=0].sum())
    eq=np.cumsum(a); peak=np.maximum.accumulate(np.r_[0.0,eq]); dd=float(np.max(peak[1:]-eq))
    cur=ls=0
    for x in a:
        if x<=0: cur+=1; ls=max(ls,cur)
        else: cur=0
    return {'n':len(a),'wins':wins,'losses':len(a)-wins,'wr':wins/len(a),'pnl':float(a.sum()),
            'pf':gp/gl if gl>0 else 999.0,'dd':dd,'ls':ls,'exp':float(a.mean())}


def funding_pnl(k,f,tr,decision_t,exit_px):
    # Exit executes at actual decision open; exact SUN1.6 funding convention.
    ep=float(tr['entry'])
    fc,_=sun17.funding_short(k,f,tr['entry_t'],decision_t+pd.Timedelta(minutes=5),ep)
    return float(sun17.NOTIONAL*(1.0-exit_px/ep)-sun17.FEE-fc)


def cp(k,tr,minutes):
    t=tr['entry_t']; dt=t+pd.Timedelta(minutes=minutes)
    if tr['exit_t']<=dt or dt not in k.index:return None
    x=k[(k.index>=t)&(k.index<dt)]
    if len(x)!=minutes//5:return None
    last=x.iloc[-1]; tail=x.iloc[-6:]  # 30m
    q=float(tail.quote_volume.sum()); b=float(tail.taker_buy_quote.sum())
    tak=2*b/q-1 if q>0 else np.nan
    ep=float(tr['entry'])
    return {'dt':dt,'decision_open':float(k.loc[dt,'open']),'last_close':float(last.close),
            'progress':1.0-float(last.close)/ep,
            'mfe':1.0-float(x.low.min())/ep,'mae':float(x.high.max())/ep-1.0,
            'close_ge_ema20':bool(float(last.close)>=float(last.ema20)),
            'close_ge_ema7':bool(float(last.close)>=float(last.ema7)),
            'tail30_taker':float(tak)}


def hour_flow(k,tr,a_min,b_min):
    t=tr['entry_t']; a=t+pd.Timedelta(minutes=a_min); b=t+pd.Timedelta(minutes=b_min)
    x=k[(k.index>=a)&(k.index<b)]
    if len(x)!=(b_min-a_min)//5:return np.nan
    q=float(x.quote_volume.sum()); buy=float(x.taker_buy_quote.sum())
    return 2*buy/q-1 if q>0 else np.nan


def failure3(st):
    return bool(st is not None and st['progress']<=0 and st['close_ge_ema20'] and st['tail30_taker']>0)


def apply_cut6(k,f,tr):
    c2=cp(k,tr,120)
    watch=failure3(c2)
    if not watch:return float(tr['pnl']), 'PARENT', c2, None, None, None
    c4=cp(k,tr,240)
    if c4 is None:return float(tr['pnl']), 'PARENT', c2, c4, None, None
    repair4=bool(c4['progress']>0 or (not c4['close_ge_ema20']) or c4['tail30_taker']<0)
    if repair4:return float(tr['pnl']), 'REPAIRED4_HOLD', c2, c4, None, {'repair4':True}
    c6=cp(k,tr,360)
    if not failure3(c6):return float(tr['pnl']), 'REPAIRED6_HOLD', c2, c4, c6, {'repair4':False}
    p=funding_pnl(k,f,tr,c6['dt'],c6['decision_open'])
    return p,'CUT6',c2,c4,c6,{'repair4':False}


def apply_confirm7(k,f,tr):
    p6,layer6,c2,c4,c6,extra=apply_cut6(k,f,tr)
    if layer6!='CUT6':return p6,layer6,c2,c4,c6,None,extra
    c7=cp(k,tr,420)
    if c7 is None:return float(tr['pnl']),'PARENT_EXIT_BEFORE7',c2,c4,c6,c7,extra
    flow67=hour_flow(k,tr,360,420)
    bearish_price=bool(c7['last_close']<c6['last_close'])
    seller_flow=bool(np.isfinite(flow67) and flow67<0)
    if bearish_price or seller_flow:
        ex={**(extra or {}),'bearish_price_repair7':bearish_price,'seller_flow_repair7':seller_flow,'flow67':flow67}
        return float(tr['pnl']),'RECOVERY7_HOLD',c2,c4,c6,c7,ex
    p=funding_pnl(k,f,tr,c7['dt'],c7['decision_open'])
    ex={**(extra or {}),'bearish_price_repair7':False,'seller_flow_repair7':False,'flow67':flow67}
    return p,'CUT7',c2,c4,c6,c7,ex


def main():
    k=f517.load_klines(); f=s50.load_funding(); es=sun17.entries(k)
    trades=[sun17.simulate_parent(k,f,t) for t in es]
    parent=np.array([tr['pnl'] for tr in trades],float)
    pm=metrics(parent)
    if pm['n']!=139 or pm['wins']!=66 or abs(pm['pnl']-63.599379132074105)>0.25:
        raise RuntimeError(f'parent parity fail {pm}')

    cut6=[]; conf7=[]; rows=[]
    for i,tr in enumerate(trades):
        p6,l6,c2,c4,c6,e6=apply_cut6(k,f,tr); cut6.append(p6)
        p7,l7,d2,d4,d6,d7,e7=apply_confirm7(k,f,tr); conf7.append(p7)
        rows.append({
            'i':i,'period':'D' if i<DISC_N else 'V','date':str(tr['entry_t'].date()),
            'parent_pnl':float(tr['pnl']),'parent_win':bool(tr['pnl']>0),'parent_reason':tr['reason'],
            'parent_mfe':float(tr['mfe']),'parent_mae':float(tr['mae']),
            'watch2':failure3(c2),'cp2_progress':None if c2 is None else c2['progress'],'cp2_taker':None if c2 is None else c2['tail30_taker'],
            'persistent4':bool(c2 is not None and failure3(c2) and c4 is not None and not (c4['progress']>0 or (not c4['close_ge_ema20']) or c4['tail30_taker']<0)),
            'cp4_progress':None if c4 is None else c4['progress'],'cp4_taker':None if c4 is None else c4['tail30_taker'],
            'candidate6':l6=='CUT6','cp6_progress':None if c6 is None else c6['progress'],'cp6_taker':None if c6 is None else c6['tail30_taker'],
            'cut6_pnl':float(p6),'cut6_layer':l6,
            'confirm7_pnl':float(p7),'confirm7_layer':l7,
            'cp7_progress':None if d7 is None else d7['progress'],
            'flow67':None if e7 is None else e7.get('flow67'),
            'bearish_price_repair7':None if e7 is None else e7.get('bearish_price_repair7'),
            'seller_flow_repair7':None if e7 is None else e7.get('seller_flow_repair7'),
        })
    cut6=np.asarray(cut6,float); conf7=np.asarray(conf7,float); df=pd.DataFrame(rows)
    df.to_csv(OUT/'sunfm_rows.csv',index=False)

    def pack(a):
        return {'full':metrics(a),'D':metrics(a[:DISC_N]),'V':metrics(a[DISC_N:])}
    P=pack(parent); C6=pack(cut6); C7=pack(conf7)
    w2=df[df.watch2==True]; p4=df[df.persistent4==True]; c6=df[df.candidate6==True]
    cut7=df[df.confirm7_layer=='CUT7']; rec7=df[df.confirm7_layer=='RECOVERY7_HOLD']
    # Parent winners/losses affected by actual final CUT7.
    affected=cut7
    winner_damage=int(((affected.parent_pnl>0)&(affected.confirm7_pnl<=0)).sum())
    loss_rescue=int(((affected.parent_pnl<=0)&(affected.confirm7_pnl>0)).sum())
    delta7=conf7-parent
    blocks=[metrics(conf7[z]) for z in np.array_split(np.arange(139),8)]
    out={
      'status':'COMPLETE_SUNDAY_FRIDAY_METHOD_SF0_SF4',
      'architecture':{
        'parent':'Sunday16 SELL TP2.5 SL1.4 max18h',
        'watch2':'+2h progress<=0 AND close>=EMA20 AND last30m taker>0',
        'repair4':'release if progress>0 OR close<EMA20 OR last30m taker<0',
        'failure6':'same 3-way failure persists at +6h',
        'confirm7':'HOLD if +7h close lower than +6h close OR +6->7h taker<0; otherwise CUT at actual +7h open',
        'tuning':'none; directional zero-cross logic only'},
      'parent':P,'immediate_cut6':C6,'confirm7':C7,
      'funnel':{'watch2':len(w2),'watch2_D':int((w2.i<DISC_N).sum()),'watch2_V':int((w2.i>=DISC_N).sum()),
                'persistent4':len(p4),'candidate6':len(c6),'recovery7_hold':len(rec7),'cut7':len(cut7)},
      'confirm7_delta_full':float(delta7.sum()),'confirm7_delta_D':float(delta7[:DISC_N].sum()),'confirm7_delta_V':float(delta7[DISC_N:].sum()),
      'cut7_parent_winners':int((affected.parent_pnl>0).sum()),'cut7_parent_losses':int((affected.parent_pnl<=0).sum()),
      'cut7_loss_to_positive':loss_rescue,'cut7_winner_to_nonpositive':winner_damage,
      'positive_blocks':int(sum(x['pnl']>0 for x in blocks)),
      'guardrail':'Friday-style methodology adaptation only. Sunday history has prior research exposure, so D/V are robustness slices, not untouched OOS. Do not retune from August N=3.'}
    (OUT/'sunfm_summary.json').write_text(json.dumps(out,indent=2,default=str))

    def wr(m):return '-' if m['wr'] is None else f"{100*m['wr']:.2f}%"
    md=['# Sunday Friday-Method — SF0 to SF4','',
        '**Status: COMPLETE — staged failure/repair/confirmation test; live BBC untouched.**','',
        '## Architecture','- Parent Sunday16 SELL / TP2.5 / SL1.4 / 18h.',
        '- +2h WATCH: progress<=0 + close>=EMA20 + buyer taker-flow.',
        '- +4h REPAIR: any favorable progress, close<EMA20, or seller-flow releases back to runner.',
        '- +6h FAILURE: same 3 failure signs still agree.',
        '- +7h CONFIRM: lower close vs +6h OR seller-flow => HOLD; otherwise CUT actual +7h open.','',
        '## Funnel',f"- WATCH +2h **{len(w2)}** (D/V {(w2.i<DISC_N).sum()}/{(w2.i>=DISC_N).sum()})",
        f"- persistent +4h **{len(p4)}**",f"- candidate +6h **{len(c6)}**",f"- +7h recovery HOLD **{len(rec7)}**",f"- final CUT7 **{len(cut7)}**",'',
        '## Economics',
        f"- Parent: WR **{wr(P['full'])}**, PnL **${P['full']['pnl']:+.2f}**, PF **{P['full']['pf']:.2f}**, DD **${P['full']['dd']:.2f}**.",
        f"- Immediate CUT6: WR **{wr(C6['full'])}**, PnL **${C6['full']['pnl']:+.2f}**, D/V **${C6['D']['pnl']:+.2f} / ${C6['V']['pnl']:+.2f}**.",
        f"- Friday-style CONFIRM7: WR **{wr(C7['full'])}**, PnL **${C7['full']['pnl']:+.2f}**, PF **{C7['full']['pf']:.2f}**, DD **${C7['full']['dd']:.2f}**.",
        f"- CONFIRM7 delta vs parent **${delta7.sum():+.2f}**; D/V **${delta7[:DISC_N].sum():+.2f} / ${delta7[DISC_N:].sum():+.2f}**.",
        f"- final CUT7 parent W/L **{(affected.parent_pnl>0).sum()}/{(affected.parent_pnl<=0).sum()}**; loss->positive **{loss_rescue}**; winner->nonpositive **{winner_damage}**.",
        f"- positive chrono blocks **{sum(x['pnl']>0 for x in blocks)}/8**.",'',
        '## Guardrail',out['guardrail']]
    (OUT/'SUNDAY_FRIDAY_METHOD_SF0_SF4_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str),flush=True)

if __name__=='__main__':main()
