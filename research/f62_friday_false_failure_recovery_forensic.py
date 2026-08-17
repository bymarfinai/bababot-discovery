#!/usr/bin/env python3
"""F6.2 — Friday15 false-failure recovery forensic.

Research only; live BBC untouched.

Frozen cohort from F6.1:
FAILURE_60 iff alive at +60m AND progress60 <= 0 AND taker60 < 0 AND ema20_dist60 <= 0.

Purpose:
Separate eventual parent winners/recoverable dips from true failures using only
information causally available at the +60m decision point. No management action,
no cutoff fitting, no classifier.
"""
from __future__ import annotations

import json, os
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f60_friday_adaptive_restart_atlas as f60

OUT=Path(os.getenv('F62_OUT','f62_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=f517.SPLIT_N

CONT=[
    'progress60','mfe60','mae60','ema7_dist60','ema20_dist60','ema_spread60','taker60',
    'recent_taker15','recent_taker30','progress_chg15','progress_chg30',
    'last_body_ratio','last_upper_wick_ratio','last_lower_wick_ratio','last_close_location',
    'pre_ret60','pre_taker60','pre_volume_ratio60','pre_range_ratio60','pre_ema_spread',
]
BIN=[
    'recent_taker15_pos','recent_taker30_pos','progress_rising15','progress_rising30',
    'above_ema7_60','ema_spread_rising15','last_bull','last_top_quartile','last_lower_wick_dom',
]


def auc(y, score):
    y=np.asarray(y,dtype=int); s=np.asarray(score,dtype=float)
    m=np.isfinite(s); y=y[m]; s=s[m]
    n1=int(y.sum()); n0=len(y)-n1
    if n1==0 or n0==0: return np.nan
    r=pd.Series(s).rank(method='average').to_numpy()
    return float((r[y==1].sum()-n1*(n1+1)/2)/(n1*n0))


def morph(row):
    o,h,l,c=map(float,[row.open,row.high,row.low,row.close]); rg=h-l
    if rg<=0: return 0.,0.,0.,.5
    body=abs(c-o)/rg; uw=(h-max(o,c))/rg; lw=(min(o,c)-l)/rg; cl=(c-l)/rg
    return body,uw,lw,cl


def feature60(k,t,tr,pf):
    d=t+pd.Timedelta(minutes=60)
    w60=k[(k.index>=t)&(k.index<d)]
    if len(w60)!=12: raise RuntimeError(f'bad 60m window {t}: {len(w60)}')
    w15=w60.iloc[-3:]; w30=w60.iloc[-6:]
    last=w60.iloc[-1]
    body,uw,lw,cl=morph(last)
    pre=f60.basic_pre(k,t)

    # progress at earlier actual decision opens, all known by +60m.
    p45=float(k.loc[t+pd.Timedelta(minutes=45),'open'])/tr.entry-1.0
    p30=float(k.loc[t+pd.Timedelta(minutes=30),'open'])/tr.entry-1.0
    ema_spread45=float(k.loc[t+pd.Timedelta(minutes=40),'ema7'])/float(k.loc[t+pd.Timedelta(minutes=40),'ema20'])-1.0

    q15=float(w15.quote_volume.sum()); tb15=float(w15.taker_buy_quote.sum())
    q30=float(w30.quote_volume.sum()); tb30=float(w30.taker_buy_quote.sum())
    tk15=(2*tb15/q15-1.0) if q15>0 else np.nan
    tk30=(2*tb30/q30-1.0) if q30>0 else np.nan

    return {
        'progress60':pf['progress60'],'mfe60':pf['mfe60'],'mae60':pf['mae60'],
        'ema7_dist60':pf['ema7_dist60'],'ema20_dist60':pf['ema20_dist60'],'ema_spread60':pf['ema_spread60'],'taker60':pf['taker60'],
        'recent_taker15':tk15,'recent_taker30':tk30,
        'progress_chg15':pf['progress60']-p45,'progress_chg30':pf['progress60']-p30,
        'last_body_ratio':body,'last_upper_wick_ratio':uw,'last_lower_wick_ratio':lw,'last_close_location':cl,
        'pre_ret60':pre.get('ret60',np.nan),'pre_taker60':pre.get('taker_imb60',np.nan),
        'pre_volume_ratio60':pre.get('volume_ratio60',np.nan),'pre_range_ratio60':pre.get('range_ratio60',np.nan),
        'pre_ema_spread':pre.get('entry_ema_spread',np.nan),
        'recent_taker15_pos':tk15>0,'recent_taker30_pos':tk30>0,
        'progress_rising15':pf['progress60']>p45,'progress_rising30':pf['progress60']>p30,
        'above_ema7_60':float(last.close)>float(last.ema7),
        'ema_spread_rising15':pf['ema_spread60']>ema_spread45,
        'last_bull':float(last.close)>float(last.open),'last_top_quartile':cl>=.75,'last_lower_wick_dom':lw>=.50,
    }


def future_taxonomy(k,t,tr):
    d=t+pd.Timedelta(minutes=60)
    aft=k[(k.index>=d)&(k.index<tr.exit_t)]
    reclaim_entry=False; reach05=False; reach10=False
    first_reclaim=None
    for b in aft.itertuples(index=False):
        if not reclaim_entry and float(b.close)>=tr.entry:
            reclaim_entry=True; first_reclaim=b.ts+pd.Timedelta(minutes=5)
        if float(b.high)/tr.entry-1.0>=0.0035: reach05=True
        if float(b.high)/tr.entry-1.0>=0.0070: reach10=True
    return {
        'future_reclaim_entry':reclaim_entry,'future_reach05r':reach05,'future_reach10r':reach10,
        'reclaim_entry_min':((first_reclaim-d).total_seconds()/60) if first_reclaim is not None else np.nan,
    }


def period_groups(df):
    return [('full',df),('discovery',df[df.i<SPLIT]),('validation',df[df.i>=SPLIT])]


def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[]; rec=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t); parents.append(tr)
        pf=f60.path_features(k,t,tr)
        failure=bool(pf['alive60'] and pf['progress60']<=0 and pf['taker60']<0 and pf['ema20_dist60']<=0)
        if not failure: continue
        r={'i':i,'period':'discovery' if i<SPLIT else 'validation','date':tr.date,
           'parent_pnl':tr.pnl,'parent_win':tr.pnl>0,'parent_reason':tr.reason}
        r.update(feature60(k,t,tr,pf)); r.update(future_taxonomy(k,t,tr)); rec.append(r)
    f517.assert_parent(parents)
    df=pd.DataFrame(rec); df.to_csv(OUT/'f62_failure60_rows.csv',index=False)
    if len(df)!=28: raise RuntimeError(f'FAILURE60 parity expected 28 got {len(df)}')

    outcome=[]
    for name,g in period_groups(df):
        outcome.append({'period':name,'n':len(g),'wins':int(g.parent_win.sum()),'wr':float(g.parent_win.mean()),'pnl':float(g.parent_pnl.sum()),
                        'reclaim_entry_n':int(g.future_reclaim_entry.sum()),'reach05r_n':int(g.future_reach05r.sum()),'reach10r_n':int(g.future_reach10r.sum())})
    pd.DataFrame(outcome).to_csv(OUT/'f62_outcomes.csv',index=False)

    cr=[]
    for feat in CONT:
        for name,g in period_groups(df):
            cr.append({'feature':feat,'period':name,'n':len(g),'auc_win_high':auc(g.parent_win,g[feat]),
                       'winner_median':float(g[g.parent_win][feat].median()) if g.parent_win.any() else np.nan,
                       'loser_median':float(g[~g.parent_win][feat].median()) if (~g.parent_win).any() else np.nan})
    cdf=pd.DataFrame(cr); cdf.to_csv(OUT/'f62_continuous_auc.csv',index=False)

    br=[]
    for sig in BIN:
        for name,g in period_groups(df):
            yes=g[g[sig].astype(bool)]; no=g[~g[sig].astype(bool)]
            br.append({'signal':sig,'period':name,'n':len(g),'yes_n':len(yes),'no_n':len(no),
                       'yes_wr':float(yes.parent_win.mean()) if len(yes) else np.nan,
                       'no_wr':float(no.parent_win.mean()) if len(no) else np.nan,
                       'effect_pp':100*((float(yes.parent_win.mean()) if len(yes) else np.nan)-(float(no.parent_win.mean()) if len(no) else np.nan))})
    bdf=pd.DataFrame(br); bdf.to_csv(OUT/'f62_binary_atlas.csv',index=False)

    stable=[]
    for feat in CONT:
        z=cdf[cdf.feature==feat].set_index('period')
        af=float(z.loc['full','auc_win_high']); ad=float(z.loc['discovery','auc_win_high']); av=float(z.loc['validation','auc_win_high'])
        same=bool(np.isfinite(ad) and np.isfinite(av) and (ad-.5)*(av-.5)>0)
        stable.append({'feature':feat,'auc_full':af,'auc_disc':ad,'auc_val':av,'same_side_dv':same,'screen':bool(same and abs(af-.5)>=.10)})
    sdf=pd.DataFrame(stable).sort_values(['screen','auc_full'],ascending=[False,False]); sdf.to_csv(OUT/'f62_stability.csv',index=False)

    summary={'outcomes':outcome,'stable_continuous':sdf[sdf.screen].to_dict('records')}
    # Fixed natural binary transfer screen: expected recovery signal if yes-WR > no-WR in both halves, each side represented.
    candidates=[]
    for sig in BIN:
        z=bdf[bdf.signal==sig].set_index('period'); d=z.loc['discovery']; v=z.loc['validation']; f=z.loc['full']
        ok=bool(d.yes_n>0 and d.no_n>0 and v.yes_n>0 and v.no_n>0 and d.yes_wr>d.no_wr and v.yes_wr>v.no_wr and f.effect_pp>=20)
        if ok: candidates.append({'signal':sig,'full_effect_pp':float(f.effect_pp),'d_effect_pp':float(d.effect_pp),'v_effect_pp':float(v.effect_pp),'full_yes_n':int(f.yes_n)})
    summary['binary_recovery_candidates']=candidates
    summary['verdict']='FORENSIC_PASS' if (len(summary['stable_continuous']) or len(candidates)) else 'FORENSIC_FAIL'
    (OUT/'f62_summary.json').write_text(json.dumps(summary,indent=2,default=float))

    md=['# Friday15 F6.2 — False Failure Recovery Forensic','',f"**Status:** COMPLETE — {summary['verdict']}",'**No action/rule promoted. Live BBC untouched.**','',
        '## FAILURE_60 cohort']
    for x in outcome:
        md.append(f"- {x['period']}: N={x['n']}, wins={x['wins']} ({100*x['wr']:.2f}%), PnL={x['pnl']:+.3f}, reclaim-entry={x['reclaim_entry_n']}, later +0.5R={x['reach05r_n']}, later +1R={x['reach10r_n']}")
    md+=['','## Stable continuous clues']
    for x in summary['stable_continuous']:
        md.append(f"- `{x['feature']}` AUC full/D/V = {x['auc_full']:.3f}/{x['auc_disc']:.3f}/{x['auc_val']:.3f}")
    md+=['','## Fixed natural binary recovery candidates']
    if candidates:
        for x in candidates: md.append(f"- `{x['signal']}` effect full/D/V = {x['full_effect_pp']:+.1f}/{x['d_effect_pp']:+.1f}/{x['v_effect_pp']:+.1f}pp; yes N={x['full_yes_n']}")
    else: md.append('- none passed the predeclared transfer screen')
    md+=['','## Guardrail','These are forensic recovery clues only. No threshold tuning, classifier, cut, protect, or flip was tested.']
    (OUT/'F6.2_CHECKPOINT.md').write_text('\n'.join(md)+'\n')
    print(json.dumps(summary,indent=2,default=float),flush=True)

if __name__=='__main__': main()
