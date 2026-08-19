#!/usr/bin/env python3
"""P2 shallow decision-tree BTC Friday pre-entry price/candle fingerprint."""
from __future__ import annotations
import json,math
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
import f517_regime_attribution as f517
import f637_friday_relative_upper_rejection_forensic as f637

ROOT=Path(__file__).resolve().parent.parent
OUT_MD=ROOT/'BTC_Friday_Preentry_Fingerprint_P2_Result.md'
OUT_JSON=ROOT/'BTC_Friday_Preentry_Fingerprint_P2_Result.json'
OUT_ROWS=ROOT/'BTC_Friday_Preentry_Fingerprint_P2_Rows.csv'
SPLIT=f517.SPLIT_N
FEATURES=[
 'f5_body','f5_upper','f5_lower','f5_upper_minus_lower','f5_upper_delta_prev3median','f5_body_delta_prev3median','f5_upper_share_delta_prev3median',
 'm15_ret','m15_body','m15_upper','m15_lower','m15_close_pos','m15_range_open',
 'h1_ret','h1_body','h1_upper','h1_lower','h1_close_pos','h1_range_open',
 'h4_ret','entry_dist_ema7','entry_dist_ema20','ema7_slope15','ema20_slope15']

def agg_geom(x,prefix):
    o=float(x.iloc[0].open);c=float(x.iloc[-1].close);h=float(x.high.max());l=float(x.low.min());rg=max(h-l,1e-12)
    return {f'{prefix}_ret':c/o-1.0,f'{prefix}_body':abs(c-o)/rg,f'{prefix}_upper':(h-max(o,c))/rg,
            f'{prefix}_lower':(min(o,c)-l)/rg,f'{prefix}_close_pos':(c-l)/rg,f'{prefix}_range_open':(h-l)/o}
def features(k,t):
    lf=f637.local_features(k,t)
    if lf is None:return None
    m15=k[(k.index>=t-pd.Timedelta(minutes=15))&(k.index<t)]
    h1=k[(k.index>=t-pd.Timedelta(hours=1))&(k.index<t)]
    h4=k[(k.index>=t-pd.Timedelta(hours=4))&(k.index<t)]
    if len(m15)!=3 or len(h1)!=12 or len(h4)!=48 or t not in k.index:return None
    cur=k.loc[t-pd.Timedelta(minutes=5)];prev=k.loc[t-pd.Timedelta(minutes=20)];entry=float(k.loc[t].open)
    out={
      'f5_body':float(lf['rel_last_body']),'f5_upper':float(lf['rel_last_upper']),'f5_lower':float(lf['rel_last_lower']),
      'f5_upper_minus_lower':float(lf['rel_upper_minus_lower']),'f5_upper_delta_prev3median':float(lf['rel_upper_delta_prev3median']),
      'f5_body_delta_prev3median':float(lf['rel_body_delta_prev3median']),'f5_upper_share_delta_prev3median':float(lf['rel_upper_share_delta_prev3median']),
      'h4_ret':float(h4.iloc[-1].close)/float(h4.iloc[0].open)-1.0,
      'entry_dist_ema7':entry/float(cur.ema7)-1.0,'entry_dist_ema20':entry/float(cur.ema20)-1.0,
      'ema7_slope15':float(cur.ema7)/float(prev.ema7)-1.0,'ema20_slope15':float(cur.ema20)/float(prev.ema20)-1.0}
    out.update(agg_geom(m15,'m15'));out.update(agg_geom(h1,'h1'))
    return out

def pf(vals):
    gp=sum(v for v in vals if v>0);gl=-sum(v for v in vals if v<=0)
    return gp/gl if gl>0 else (999.0 if gp>0 else None)
def stats(df):
    a=df.parent_pnl.astype(float).tolist()
    if not a:return {'n':0,'wins':0,'wr':None,'pnl':0.0,'exp':None,'pf':None}
    w=sum(v>0 for v in a);return {'n':len(a),'wins':w,'wr':w/len(a),'pnl':sum(a),'exp':sum(a)/len(a),'pf':pf(a)}
def path_to_leaf(clf,leaf_id):
    tr=clf.tree_;path=[]
    def rec(node,conds):
        if node==leaf_id:
            path.extend(conds);return True
        if tr.children_left[node]==tr.children_right[node]:return False
        feat=FEATURES[tr.feature[node]];thr=float(tr.threshold[node])
        if rec(tr.children_left[node],conds+[(feat,'<=',thr)]):return True
        if rec(tr.children_right[node],conds+[(feat,'>',thr)]):return True
        return False
    rec(0,[]);return path
def rule_text(path):
    return ' AND '.join(f'{f} {op} {v:.8g}' for f,op,v in path)
def blocks(df,leaf):
    edges=np.linspace(0,len(df),5,dtype=int);out={}
    for i in range(4):out[f'B{i+1}']=stats(df.iloc[edges[i]:edges[i+1]][lambda z:z.leaf==leaf])
    return out

def main():
    k=f517.load_klines();days=[d for d in pd.date_range(f517.START,f517.END,inclusive='left',freq='D') if d.weekday()==4]
    parents=[];rows=[]
    for i,d0 in enumerate(days):
        t=pd.Timestamp(d0.date(),tz='UTC')+pd.Timedelta(hours=8);tr=f517.simulate_parent(k,t);parents.append(tr);ft=features(k,t)
        if ft is None:raise RuntimeError(f'missing features {t}')
        rows.append({'i':i,'date':str(tr.date),'period':'discovery' if i<SPLIT else 'validation','parent_pnl':float(tr.pnl),'win':int(tr.pnl>0),**ft})
    f517.assert_parent(parents);df=pd.DataFrame(rows)
    if len(df)!=138:raise RuntimeError(f'expected 138, got {len(df)}')
    disc0=df[df.i<SPLIT].copy();val0=df[df.i>=SPLIT].copy()
    med={f:float(pd.to_numeric(disc0[f],errors='coerce').replace([np.inf,-np.inf],np.nan).median()) for f in FEATURES}
    X=df[FEATURES].copy()
    for f in FEATURES:X[f]=pd.to_numeric(X[f],errors='coerce').replace([np.inf,-np.inf],np.nan).fillna(med[f])
    Xd=X.loc[disc0.index];yd=disc0.win.astype(int)
    clf=DecisionTreeClassifier(criterion='gini',max_depth=2,min_samples_leaf=12,random_state=20260819)
    clf.fit(Xd,yd);df['leaf']=clf.apply(X)
    # Refresh chronology slices after leaf assignment; this is the only fix vs the failed implementation run.
    disc=df[df.i<SPLIT].copy();val=df[df.i>=SPLIT].copy()
    leaves=[]
    pred_by_leaf={int(l):int(np.argmax(clf.tree_.value[int(l)][0])) for l in set(clf.apply(Xd))}
    for leaf in sorted(set(clf.apply(Xd))):
        z=disc[disc.leaf==leaf];s=stats(z);path=path_to_leaf(clf,int(leaf))
        leaves.append({'leaf':int(leaf),'predicted_class':pred_by_leaf[int(leaf)],'rule':rule_text(path),'path':path,**s})
    eligible=[x for x in leaves if x['predicted_class']==1 and x['n']>=12 and x['wr'] is not None and x['wr']>=.80]
    eligible.sort(key=lambda x:(-x['wr'],-x['n'],x['leaf']))
    baseline={'full':stats(df),'discovery':stats(disc),'validation':stats(val)}
    out={'protocol':'P2','model':{'max_depth':2,'min_samples_leaf':12,'criterion':'gini','features':FEATURES,'discovery_medians':med},
         'discovery_leaves':leaves,'baseline':baseline}
    if not eligible:
        out.update({'selected_leaf':None,'verdict':'REJECT_P2_80_CANDLE_IDENTIFIER','reason':'No positive discovery leaf with N>=12 and WR>=80%.'})
    else:
        ch=eligible[0];leaf=ch['leaf'];sd=stats(disc[disc.leaf==leaf]);sv=stats(val[val.leaf==leaf]);sf=stats(df[df.leaf==leaf]);bl=blocks(df,leaf)
        pos=sum(x['n']>0 and x['pnl']>0 for x in bl.values())
        qualify=bool(sd['n']>=12 and sd['wr']>=.80 and sv['n']>=8 and sv['wr'] is not None and sv['wr']>=.80 and
                     sf['n']>=20 and sf['wr'] is not None and sf['wr']>=.80 and sv['exp'] is not None and sv['exp']>0 and
                     sv['pf'] is not None and sv['pf']>1 and baseline['validation']['wr'] is not None and sv['wr']>baseline['validation']['wr'] and pos>=3)
        out.update({'selected_leaf':leaf,'selected_rule':ch['rule'],'selected_path':ch['path'],'selected':{'discovery':sd,'validation':sv,'full':sf,'blocks':bl,'positive_blocks':pos},
                    'selected_dates':df[df.leaf==leaf][['date','period','parent_pnl','win']].to_dict('records'),
                    'verdict':'BTC_FRIDAY_80_CANDIDATE' if qualify else 'REJECT_P2_80_CANDLE_IDENTIFIER',
                    'guardrail':'Exact depth-2 discovery tree and selected leaf only; no deeper-tree retry.'})
    df.to_csv(OUT_ROWS,index=False);OUT_JSON.write_text(json.dumps(out,indent=2,default=str)+'\n')
    def F(x,d=2):return '-' if x is None else f'{x:.{d}f}'
    md=['# BTC Friday Pre-entry Fingerprint P2 — Shallow Tree Result','',f"Discovery leaves: **{len(leaves)}**",'']
    md += ['## Discovery leaves','','| Leaf | Pred | N | Wins | WR | Rule |','|---:|---:|---:|---:|---:|---|']
    for x in leaves:md.append(f"| {x['leaf']} | {x['predicted_class']} | {x['n']} | {x['wins']} | {F(100*x['wr'])}% | `{x['rule']}` |")
    if out.get('selected_leaf') is None:
        md += ['','## Verdict','',f"**{out['verdict']}**",'',out['reason']]
    else:
        md += ['','## Selected human-readable fingerprint','',f"`{out['selected_rule']}`",'',
               '| Cohort | N | Wins | WR | PnL | Exp | PF |','|---|---:|---:|---:|---:|---:|---:|']
        for name,x in [('Discovery',out['selected']['discovery']),('Validation',out['selected']['validation']),('Full',out['selected']['full'])]:
            md.append(f"| {name} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | ${F(x['exp'],3)} | {F(x['pf'],3)} |")
        md += ['','### Chronological blocks','','| Block | N | Wins | WR | PnL | PF |','|---|---:|---:|---:|---:|---:|']
        for b,x in out['selected']['blocks'].items():md.append(f"| {b} | {x['n']} | {x['wins']} | {F(100*x['wr'] if x['wr'] is not None else None)}% | ${F(x['pnl'],3)} | {F(x['pf'],3)} |")
        md += ['','## Verdict','',f"**{out['verdict']}**"]
    md += ['','Observed historical WR is not a guaranteed future win probability.']
    OUT_MD.write_text('\n'.join(md)+'\n');print(json.dumps(out,indent=2,default=str))
if __name__=='__main__':main()
