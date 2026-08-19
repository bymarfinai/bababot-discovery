#!/usr/bin/env python3
"""P1 frozen BTC Friday pre-entry morphology discovery over F6.37 atoms."""
from __future__ import annotations
import itertools,json,math
from pathlib import Path
import numpy as np
import pandas as pd
import f517_regime_attribution as f517
import f637_friday_relative_upper_rejection_forensic as f637

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_Preentry_Fingerprint_P1_Result.md'
OUT_JSON=ROOT/'BTC_Friday_Preentry_Fingerprint_P1_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_Preentry_Fingerprint_P1_Rows.csv'
OUT_DISC=ROOT/'BTC_Friday_Preentry_Fingerprint_P1_Discovery_Leaderboard.csv'
SPLIT=f517.SPLIT_N
ATOMS=[
 ('last_red','rel_last_red'),('last_upper_gt_lower','rel_last_upper_gt_lower'),
 ('upper_gt_prev1','rel_upper_gt_prev1'),('upper_gt_prev2max','rel_upper_gt_prev2max'),
 ('upper_localmax4','rel_upper_localmax4'),('body_lt_prev1','rel_body_lt_prev1'),
 ('body_contract3median','rel_body_contract3median'),('upper_share_gt_prev3median','rel_upper_share_gt_prev3median'),
 ('rejection_expansion_composite','rel_rejection_expansion_composite'),('wick_dominant','rel_wick_dominant'),
 ('f636_morphology','rel_f636_morphology'),('balance_gate','balance_gate')]

def pf(vals):
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else None)
def stats(df):
    a=df.parent_pnl.astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    w=sum(v>0 for v in a)
    return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}
def expr(lits):
    return ' AND '.join(f'{name}={str(bool(val))}' for name,val,_ in lits)
def mask_for(df,lits):
    m=pd.Series(True,index=df.index)
    for _,val,col in lits:m &= df[col].astype(bool).eq(bool(val))
    return m
def block_stats(df,lits):
    edges=np.linspace(0,len(df),5,dtype=int);out={}
    for i in range(4):
        z=df.iloc[edges[i]:edges[i+1]];q=z[mask_for(z,lits)]
        out[f'B{i+1}']=stats(q)
    return out

def main():
    k=f517.load_klines();days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8)
        tr=f517.simulate_parent(k,t);parents.append(tr);lf=f637.local_features(k,t)
        if lf is None:raise RuntimeError(f'missing local features {t}')
        row={'i':i,'date':str(tr.date),'period':'discovery' if i<SPLIT else 'validation','parent_pnl':float(tr.pnl),'win':bool(tr.pnl>0)}
        for name,col in ATOMS:
            if name=='balance_gate':continue
            row[col]=bool(lf[col])
        row['balance_gate']=bool(float(lf['rel_last_upper'])>float(lf['rel_body_delta_prev3median']))
        rows.append(row)
    f517.assert_parent(parents)
    df=pd.DataFrame(rows);df.to_csv(OUT_ROWS,index=False)
    if len(df)!=138:raise RuntimeError(f'expected 138 got {len(df)}')
    disc=df[df.i<SPLIT];val=df[df.i>=SPLIT]
    candidates=[]
    # singles
    for name,col in ATOMS:
        for v in (False,True):candidates.append([(name,v,col)])
    # exactly two different atoms, all polarity combinations
    for (n1,c1),(n2,c2) in itertools.combinations(ATOMS,2):
        for v1 in (False,True):
            for v2 in (False,True):candidates.append([(n1,v1,c1),(n2,v2,c2)])
    if len(candidates)!=288:raise RuntimeError(f'candidate grammar mismatch {len(candidates)}')
    lead=[]
    for lits in candidates:
        s=stats(disc[mask_for(disc,lits)])
        lead.append({'rule':expr(lits),**s,'lits':lits})
    eligible=[x for x in lead if x['n']>=12 and x['wr'] is not None and x['wr']>=.80 and x['pnl']>0 and x['pf'] is not None and x['pf']>1]
    eligible.sort(key=lambda x:(-x['wr'],-x['n'],-x['pf'],x['rule']))
    # Discovery leaderboard only; no validation peeking for alternative selection.
    pd.DataFrame([{k:v for k,v in x.items() if k!='lits'} for x in sorted(lead,key=lambda x:(-x['wr'] if x['wr'] is not None else 1,-x['n'],x['rule']))]).to_csv(OUT_DISC,index=False)
    baseline_d=stats(disc);baseline_v=stats(val);baseline=stats(df)
    if not eligible:
        out={'protocol':'P1','candidate_rules_evaluated':len(candidates),'discovery_eligible_80_rules':0,'selected_rule':None,
             'baseline':{'full':baseline,'discovery':baseline_d,'validation':baseline_v},'verdict':'REJECT_P1_80_CANDLE_IDENTIFIER',
             'reason':'No frozen-grammar rule achieved discovery N>=12, WR>=80%, positive PnL and PF>1. Validation was not used to select an alternative.'}
    else:
        chosen=eligible[0];lits=chosen['lits'];rule=chosen['rule']
        sd=stats(disc[mask_for(disc,lits)]);sv=stats(val[mask_for(val,lits)]);sf=stats(df[mask_for(df,lits)])
        blocks=block_stats(df,lits);pos=sum(x['n']>0 and x['pnl']>0 for x in blocks.values())
        qualify=bool(sd['n']>=12 and sd['wr']>=.80 and sv['n']>=8 and sv['wr'] is not None and sv['wr']>=.80 and
                     sv['exp'] is not None and sv['exp']>0 and sv['pf'] is not None and sv['pf']>1 and
                     sf['n']>=20 and sf['wr'] is not None and sf['wr']>=.80 and pos>=3 and
                     baseline_v['wr'] is not None and sv['wr']>baseline_v['wr'])
        selected_rows=df[mask_for(df,lits)]
        out={'protocol':'P1','candidate_rules_evaluated':len(candidates),'discovery_eligible_80_rules':len(eligible),
             'selected_rule':rule,'selected_literals':[(a,bool(b),c) for a,b,c in lits],
             'selected':{'full':sf,'discovery':sd,'validation':sv,'blocks':blocks,'positive_blocks':pos},
             'baseline':{'full':baseline,'discovery':baseline_d,'validation':baseline_v},
             'selected_dates':selected_rows[['date','period','parent_pnl','win']].to_dict('records'),
             'verdict':'BTC_FRIDAY_80_CANDIDATE' if qualify else 'REJECT_P1_80_CANDLE_IDENTIFIER',
             'guardrail':'Only the discovery-selected top rule was evaluated for validation promotion. Do not try runner-up rules on the same validation.'}
    OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2):return '-' if x is None else f'{x:.{d}f}'
    md=['# BTC Friday Pre-entry Fingerprint P1 — Result','',f"Candidate rules evaluated on discovery only: **{out['candidate_rules_evaluated']}**",f"Discovery rules meeting frozen 80% screen: **{out['discovery_eligible_80_rules']}**",'']
    if out.get('selected_rule') is None:
        md += ['## Result','','**No discovery candidate qualified.**','',f"Verdict: **{out['verdict']}**",'',out['reason']]
    else:
        md += ['## Discovery-selected fingerprint','',f"`{out['selected_rule']}`",'',
               '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,x in [('Discovery',out['selected']['discovery']),('Validation',out['selected']['validation']),('Full',out['selected']['full'])]:
            md.append(f"| {name} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | ${F(x['exp'],3)} | {F(x['pf'],3)} |")
        md += ['','### Chronological blocks','','| Block | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for b,x in out['selected']['blocks'].items():md.append(f"| {b} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | {F(x['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**",'',out['guardrail']]
    md += ['','Observed WR is historical identification, not a guaranteed future win probability.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
