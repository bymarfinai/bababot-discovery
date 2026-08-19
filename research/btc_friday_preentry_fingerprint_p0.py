#!/usr/bin/env python3
"""BTC Friday P0: exact F6.38 balance relationship as a pure pre-entry filter over ALL Fridays."""
from __future__ import annotations
import json, math
from pathlib import Path
import numpy as np
import pandas as pd

import f517_regime_attribution as f517
import f637_friday_relative_upper_rejection_forensic as f637

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_Preentry_Fingerprint_P0_Result.md'
OUT_JSON=ROOT/'BTC_Friday_Preentry_Fingerprint_P0_Result.json'
OUT_CSV=ROOT/'BTC_Friday_Preentry_Fingerprint_P0_Rows.csv'
SPLIT=f517.SPLIT_N


def pf(vals):
    gp=sum(x for x in vals if x>0);gl=-sum(x for x in vals if x<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else None)

def stats(df):
    a=df.parent_pnl.astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    return {'n':len(a),'wins':sum(x>0 for x in a),'wr':sum(x>0 for x in a)/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}

def block_stats(df,n=4):
    out={}
    edges=np.linspace(0,len(df),n+1,dtype=int)
    for j in range(n):
        z=df.iloc[edges[j]:edges[j+1]]
        g=z[z.balance_gate]
        out[f'B{j+1}']={'all_dates':[str(x) for x in z.date.tolist()],**stats(g)}
    return out

def main():
    k=f517.load_klines()
    days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr)
        lf=f637.local_features(k,t)
        if lf is None: raise RuntimeError(f'missing preentry geometry {t}')
        upper=float(lf['rel_last_upper']);body_exp=float(lf['rel_body_delta_prev3median'])
        gate=bool(upper>body_exp)
        rows.append({'i':i,'date':str(tr.date),'period':'discovery' if i<SPLIT else 'validation',
                     'entry_t':str(t),'parent_pnl':float(tr.pnl),'win':bool(tr.pnl>0),'reason':tr.reason,
                     'upper_wick_ratio':upper,'last_body_ratio':float(lf['rel_last_body']),
                     'body_delta_prev3median':body_exp,'balance_margin':upper-body_exp,'balance_gate':gate,
                     'last_red':bool(lf['rel_last_red']), 'wick_dominant':bool(lf['rel_wick_dominant']),
                     'upper_localmax4':bool(lf['rel_upper_localmax4']),
                     'body_contract3median':bool(lf['rel_body_contract3median'])})
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT_CSV,index=False)
    if len(df)!=138: raise RuntimeError(f'expected 138 Fridays, got {len(df)}')
    full=stats(df[df.balance_gate]);neg=stats(df[~df.balance_gate])
    disc=stats(df[(df.i<SPLIT)&df.balance_gate]);val=stats(df[(df.i>=SPLIT)&df.balance_gate])
    base=stats(df);blocks=block_stats(df,4)
    positive_blocks=sum(v['pnl']>0 for v in blocks.values() if v['n']>0)
    qualify=bool(full['n']>=20 and full['wr'] is not None and full['wr']>=.80 and
                 disc['n']>=10 and disc['wr'] is not None and disc['wr']>=.75 and
                 val['n']>=8 and val['wr'] is not None and val['wr']>=.75 and
                 val['exp'] is not None and val['exp']>0 and val['pf'] is not None and val['pf']>1 and positive_blocks>=3)
    verdict='BTC_FRIDAY_80_CANDIDATE' if qualify else 'REJECT_AS_80_CANDLE_IDENTIFIER'
    out={'protocol':'BTC_FRIDAY_PREENTRY_FINGERPRINT_P0','rule':'upper_wick_ratio > body_delta_vs_median_prior3',
         'baseline':base,'balance_true':{'full':full,'discovery':disc,'validation':val,'blocks':blocks},
         'balance_false':neg,'positive_blocks':positive_blocks,'verdict':verdict,
         'gate_rows':df[df.balance_gate].to_dict('records'),
         'guardrail':'Pure pre-entry application to all canonical BTC Fridays. No post-entry cohort information and no threshold tuning.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2): return '-' if x is None else f'{x:.{d}f}'
    md=['# BTC Friday Pre-entry Fingerprint P0 — Result','',
        '**Pure pre-entry test across every canonical BTC Friday; live BBC untouched.**','',
        'Rule: `upper_wick_ratio > body_ratio - median(prior 3 body ratios)`','',
        '## Headline','',
        '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
    for name,x in [('All Fridays',base),('BALANCE=True full',full),('Discovery',disc),('Validation',val),('BALANCE=False',neg)]:
        md.append(f"| {name} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | ${F(x['exp'],3)} | {F(x['pf'],3)} |")
    md += ['','## Chronological blocks — BALANCE=True','','| Block | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
    for b,x in blocks.items():
        md.append(f"| {b} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | {F(x['pf'],3)} |")
    md += ['','## 80% identification verdict','',f'**{verdict}**','',
           f"Positive BALANCE blocks: **{positive_blocks}/4**.",'',
           'This is observed historical performance, not a guarantee of future win probability. No post-result threshold/lookback inversion is allowed.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
