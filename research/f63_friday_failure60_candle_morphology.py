#!/usr/bin/env python3
"""F6.3 — Friday15 FAILURE_60 candle morphology forensic.
Research only; live BBC untouched.

Frozen cohort: F6.1 FAILURE_60.
Purpose: test whether fixed, causal 5m candle morphology at +60m separates
recoverable parent winners from true failures. No action/rule is applied.

Fixed taxonomy copied in spirit from Saturday S5.7B (no threshold sweep):
- DOJI_LIKE body/range <= 0.20
- STRONG_BODY body/range >= 0.70
- CLOSE_TOP_Q >= 0.75, CLOSE_BOTTOM_Q <= 0.25
- LOWER/UPPER_WICK_DOM wick/range >= 0.50
- BULL/BEAR, ENGULF/INSIDE/OUTSIDE
Sequence flags use only the final three completed 5m candles before +60m.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60
import f62_friday_false_failure_recovery_forensic as f62

OUT=Path(os.getenv('F63_OUT','f63_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N
FLAGS=['BULL','BEAR','DOJI_LIKE','STRONG_BODY','CLOSE_TOP_Q','CLOSE_BOTTOM_Q','LOWER_WICK_DOM','UPPER_WICK_DOM','ENGULF','INSIDE','OUTSIDE',
       'BULL_TOP_Q','BULL_ENGULF','HIGHER_LOW','HIGHER_CLOSE','TWO_BULL_LAST3','TWO_HIGHER_CLOSE_LAST3','LOWER_WICK_RISING','BULL_REVERSAL_SEQ']
CONT=['body_ratio','upper_wick_ratio','lower_wick_ratio','close_loc','range_pct_entry','signed_body_pct_entry','range_vs_prev','body_vs_prev',
      'bull_count3','close_change_prev','low_change_prev','lower_wick_change_prev','close_loc_change_prev']


def auc(y, score):
    y=np.asarray(y,dtype=int); s=np.asarray(score,dtype=float)
    m=np.isfinite(s); y=y[m]; s=s[m]
    n1=int(y.sum()); n0=len(y)-n1
    if n1==0 or n0==0:return np.nan
    r=pd.Series(s).rank(method='average').to_numpy()
    return float((r[y==1].sum()-n1*(n1+1)/2)/(n1*n0))


def candle(k, decision_t, entry):
    bt=decision_t-pd.Timedelta(minutes=5)
    if bt not in k.index:return None
    b=k.loc[bt]; pt=bt-pd.Timedelta(minutes=5); prev=k.loc[pt] if pt in k.index else None
    o,h,l,c=map(float,[b.open,b.high,b.low,b.close]); rg=max(h-l,1e-12); body=abs(c-o)
    uw=(h-max(o,c))/rg; lw=(min(o,c)-l)/rg; cl=(c-l)/rg
    bull=c>o; bear=c<o
    engulf=inside=outside=False; range_vs_prev=body_vs_prev=np.nan
    prev_cl=np.nan; prev_lw=np.nan; prev_close=np.nan; prev_low=np.nan
    if prev is not None:
        po,ph,pl,pc=map(float,[prev.open,prev.high,prev.low,prev.close]); pr=max(ph-pl,1e-12); pb=abs(pc-po)
        engulf=(max(o,c)>=max(po,pc) and min(o,c)<=min(po,pc) and body>pb)
        inside=(h<=ph and l>=pl); outside=(h>=ph and l<=pl)
        range_vs_prev=rg/pr; body_vs_prev=body/pb if pb>0 else np.nan
        prev_cl=(pc-pl)/pr; prev_lw=(min(po,pc)-pl)/pr; prev_close=pc; prev_low=pl
    return {
      'body_ratio':body/rg,'upper_wick_ratio':uw,'lower_wick_ratio':lw,'close_loc':cl,
      'range_pct_entry':rg/entry,'signed_body_pct_entry':(c-o)/entry,
      'range_vs_prev':range_vs_prev,'body_vs_prev':body_vs_prev,
      'BULL':bull,'BEAR':bear,'DOJI_LIKE':body/rg<=.20,'STRONG_BODY':body/rg>=.70,
      'CLOSE_TOP_Q':cl>=.75,'CLOSE_BOTTOM_Q':cl<=.25,'LOWER_WICK_DOM':lw>=.50,'UPPER_WICK_DOM':uw>=.50,
      'ENGULF':engulf,'INSIDE':inside,'OUTSIDE':outside,
      'BULL_TOP_Q':bool(bull and cl>=.75),'BULL_ENGULF':bool(bull and engulf),
      'HIGHER_LOW':bool(np.isfinite(prev_low) and l>prev_low),'HIGHER_CLOSE':bool(np.isfinite(prev_close) and c>prev_close),
      'close_change_prev':(c-prev_close)/entry if np.isfinite(prev_close) else np.nan,
      'low_change_prev':(l-prev_low)/entry if np.isfinite(prev_low) else np.nan,
      'lower_wick_change_prev':lw-prev_lw if np.isfinite(prev_lw) else np.nan,
      'close_loc_change_prev':cl-prev_cl if np.isfinite(prev_cl) else np.nan,
    }


def sequence3(k, decision_t):
    w=k[(k.index>=decision_t-pd.Timedelta(minutes=15))&(k.index<decision_t)]
    if len(w)!=3:raise RuntimeError(f'bad last3 at {decision_t}: {len(w)}')
    bull=(w.close>w.open).to_numpy(bool)
    closes=w.close.to_numpy(float); lows=w.low.to_numpy(float)
    # last candle lower-wick ratio vs previous candle, calculated independently
    def lw_ratio(r):
        rg=max(float(r.high-r.low),1e-12); return (min(float(r.open),float(r.close))-float(r.low))/rg
    lws=[lw_ratio(x) for _,x in w.iterrows()]
    return {
      'bull_count3':int(bull.sum()),
      'TWO_BULL_LAST3':bool(bull.sum()>=2),
      'TWO_HIGHER_CLOSE_LAST3':bool(closes[1]>closes[0] and closes[2]>closes[1]),
      'LOWER_WICK_RISING':bool(lws[2]>lws[1]),
      'BULL_REVERSAL_SEQ':bool((not bull[0]) and bull[2] and closes[2]>closes[1] and lows[2]>=lows[1]),
    }


def groups(df):return [('full',df),('discovery',df[df.i<SPLIT]),('validation',df[df.i>=SPLIT])]


def main():
    k=f517.load_klines(); days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rec=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8); tr=f517.simulate_parent(k,t); parents.append(tr)
        pf=f60.path_features(k,t,tr)
        failure=bool(pf['alive60'] and pf['progress60']<=0 and pf['taker60']<0 and pf['ema20_dist60']<=0)
        if not failure:continue
        dt=t+pd.Timedelta(minutes=60); cf=candle(k,dt,tr.entry); sq=sequence3(k,dt); fut=f62.future_taxonomy(k,t,tr)
        rec.append({'i':i,'date':tr.date,'period':'discovery' if i<SPLIT else 'validation','parent_win':tr.pnl>0,'parent_pnl':tr.pnl,
                    'future_reclaim_entry':fut['future_reclaim_entry'],'future_reach05r':fut['future_reach05r'],**cf,**sq})
    f517.assert_parent(parents); df=pd.DataFrame(rec)
    if len(df)!=28:raise RuntimeError(f'failure60 parity {len(df)}')
    df.to_csv(OUT/'f63_failure60_morphology_rows.csv',index=False)

    cont=[]
    for feat in CONT:
      for p,g in groups(df):
        cont.append({'feature':feat,'period':p,'n':len(g),'auc_win_high':auc(g.parent_win,g[feat]),
                     'winner_median':float(g[g.parent_win][feat].median()),'loser_median':float(g[~g.parent_win][feat].median())})
    cdf=pd.DataFrame(cont); cdf.to_csv(OUT/'f63_continuous.csv',index=False)

    flags=[]
    for flag in FLAGS:
      for p,g in groups(df):
        yes=g[g[flag].astype(bool)]; no=g[~g[flag].astype(bool)]
        yw=float(yes.parent_win.mean()) if len(yes) else np.nan; nw=float(no.parent_win.mean()) if len(no) else np.nan
        yr=float(yes.future_reclaim_entry.mean()) if len(yes) else np.nan; nr=float(no.future_reclaim_entry.mean()) if len(no) else np.nan
        flags.append({'flag':flag,'period':p,'yes_n':len(yes),'no_n':len(no),'yes_wr':yw,'no_wr':nw,'winner_effect_pp':100*(yw-nw) if np.isfinite(yw) and np.isfinite(nw) else np.nan,
                      'yes_reclaim':yr,'no_reclaim':nr,'reclaim_effect_pp':100*(yr-nr) if np.isfinite(yr) and np.isfinite(nr) else np.nan})
    fdf=pd.DataFrame(flags); fdf.to_csv(OUT/'f63_flags.csv',index=False)

    candidates=[]
    for flag in FLAGS:
      z=fdf[fdf.flag==flag].set_index('period'); d=z.loc['discovery']; v=z.loc['validation']; full=z.loc['full']
      if d.yes_n<2 or d.no_n<2 or v.yes_n<2 or v.no_n<2:continue
      same=np.isfinite(d.winner_effect_pp) and np.isfinite(v.winner_effect_pp) and np.sign(d.winner_effect_pp)==np.sign(v.winner_effect_pp) and np.sign(d.winner_effect_pp)!=0
      if same and abs(full.winner_effect_pp)>=20:
        candidates.append({'flag':flag,'full_effect_pp':float(full.winner_effect_pp),'d_effect_pp':float(d.winner_effect_pp),'v_effect_pp':float(v.winner_effect_pp),
                           'full_yes_n':int(full.yes_n),'full_yes_wr':float(full.yes_wr),'full_no_wr':float(full.no_wr)})

    stable_cont=[]
    for feat in CONT:
      z=cdf[cdf.feature==feat].set_index('period'); af=float(z.loc['full','auc_win_high']); ad=float(z.loc['discovery','auc_win_high']); av=float(z.loc['validation','auc_win_high'])
      if np.isfinite(ad) and np.isfinite(av) and (ad-.5)*(av-.5)>0 and abs(af-.5)>=.10:
        stable_cont.append({'feature':feat,'auc_full':af,'auc_disc':ad,'auc_val':av})

    summary={'n':len(df),'wins':int(df.parent_win.sum()),'losses':int((~df.parent_win).sum()),'candidates':candidates,'stable_continuous':stable_cont,
             'verdict':'MORPHOLOGY_PASS' if (candidates or stable_cont) else 'MORPHOLOGY_FAIL'}
    (OUT/'f63_summary.json').write_text(json.dumps(summary,indent=2))
    md=['# Friday15 F6.3 — FAILURE_60 Candle Morphology','',f"**Status:** COMPLETE — {summary['verdict']}",'**Forensic only; no action promoted. Live BBC untouched.**','',
        f"- Cohort: {summary['n']} FAILURE_60 = {summary['wins']} winners / {summary['losses']} losers",'', '## Fixed morphology candidates']
    if candidates:
      for x in candidates:md.append(f"- `{x['flag']}`: full/D/V winner separation {x['full_effect_pp']:+.1f}/{x['d_effect_pp']:+.1f}/{x['v_effect_pp']:+.1f}pp; yes N={x['full_yes_n']}, WR={100*x['full_yes_wr']:.1f}% vs {100*x['full_no_wr']:.1f}%")
    else:md.append('- none')
    md+=['','## Stable continuous morphology']
    if stable_cont:
      for x in stable_cont:md.append(f"- `{x['feature']}` AUC full/D/V {x['auc_full']:.3f}/{x['auc_disc']:.3f}/{x['auc_val']:.3f}")
    else:md.append('- none')
    md+=['','## Guardrail','No wick/body threshold was tuned; all definitions were frozen before seeing F6.3 results.']
    (OUT/'F6.3_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
