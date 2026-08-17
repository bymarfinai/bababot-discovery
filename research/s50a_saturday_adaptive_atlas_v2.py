#!/usr/bin/env python3
"""Saturday T-Method S5.0A v2 — parity-corrected adaptive state atlas.

Research only. No entry/exit rule is changed.
Frozen benchmarks remain A7.19 full-coverage and A7.26 selective.
"""
from __future__ import annotations
import json, os
from pathlib import Path
import numpy as np
import pandas as pd
import s50_saturday_parent_forensics as s50

OUT=Path(os.getenv('S50A_OUT','s50a_out')); OUT.mkdir(parents=True,exist_ok=True)
SPLIT=83

def row(k,t):
    x=k[k.index<=t]
    return None if x.empty else x.iloc[-1]

def pre_context(k,t):
    """Exact A7.24+ convention: pre-returns/slopes end on completed bar i-1."""
    op=float(k.loc[t,'open']); done=t-pd.Timedelta(minutes=5); r=k.loc[done]
    r1=row(k,done-pd.Timedelta(minutes=60)); r4=row(k,done-pd.Timedelta(minutes=240)); rs=row(k,done-pd.Timedelta(minutes=60))
    w=k[(k.index>=t-pd.Timedelta(minutes=60))&(k.index<t)]
    if r1 is None or r4 is None or rs is None or len(w)!=12: raise RuntimeError(f'bad pre {t}')
    c=float(r.close); ema=float(r.ema20)
    pre1=c/float(r1.close)-1; pre4=c/float(r4.close)-1; slope=ema/float(rs.ema20)-1
    ph=float(w.high.max()); dist=ph/op-1
    conds=[pre1>0,pre4>0,op>ema,slope>0,dist<=.001]
    score=int(sum(conds)); stretched=all(conds)
    state='STRETCHED' if stretched else ('PULLBACK' if score<=1 else 'NORMAL')
    return {'pre1':pre1,'pre4':pre4,'pre_above_ema20':op>ema,'pre_ema20_slope60':slope,
            'pre_dist_below_prior1h_high':dist,'pre_stretch_score':score,'pre_state':state}

def rv24(k,t):
    w=k[(k.index>=t-pd.Timedelta(hours=24))&(k.index<t)]
    if len(w)!=288:return np.nan
    lr=np.diff(np.log(w.close.astype(float).to_numpy())); return float(np.sqrt(np.sum(lr*lr)))

def thesis60(k,t,tr):
    d=t+pd.Timedelta(minutes=60)
    if pd.Timestamp(tr.exit_t)<=d:
        return {'state60':'NOT_ALIVE','progress60':np.nan,'taker60':np.nan,'mfe60':np.nan,'mae60':np.nan,
                'ema20_dist60':np.nan,'rv24':rv24(k,t),'progress60_rv':np.nan,'mfe60_rv':np.nan,'mae60_rv':np.nan}
    bars=k[(k.index>=t)&(k.index<d)]
    if len(bars)!=12:raise RuntimeError(f'bad60 {t}')
    px=float(k.loc[d,'open']); prog=px/tr.entry-1; tak=float(np.nanmean(bars.taker_imb.to_numpy()))
    mfe=float(bars.high.max())/tr.entry-1; mae=1-float(bars.low.min())/tr.entry
    last=bars.iloc[-1]; ed=float(last.close)/float(last.ema20)-1
    if prog<=-.001 and tak<0: state='FAILURE_CANDIDATE'
    elif prog>=.001 and tak>0: state='HEALTHY'
    else: state='MIXED'
    r=rv24(k,t)
    return {'state60':state,'progress60':prog,'taker60':tak,'mfe60':mfe,'mae60':mae,'ema20_dist60':ed,'rv24':r,
            'progress60_rv':prog/r if np.isfinite(r) and r>0 else np.nan,
            'mfe60_rv':mfe/r if np.isfinite(r) and r>0 else np.nan,
            'mae60_rv':mae/r if np.isfinite(r) and r>0 else np.nan}

def runner_path(k,t,tr):
    ex=pd.Timestamp(tr.exit_t); bars=k[(k.index>=t)&(k.index<ex)]
    h05=h08=None
    for b in bars.itertuples(index=False):
        if h05 is None and float(b.high)/tr.entry-1>=.005:h05=b.ts+pd.Timedelta(minutes=5)
        if h08 is None and float(b.high)/tr.entry-1>=.008:h08=b.ts+pd.Timedelta(minutes=5)
    if h05 is None:return {'runner_state':'NO_0.5_IMPULSE','first05_min':np.nan,'first08_min':np.nan,'giveback_state':'NO_HINGE','giveback40_min':np.nan}
    aft=k[(k.index>=h05)&(k.index<ex)]; gb=None
    for b in aft.itertuples(index=False):
        if float(b.close)/tr.entry-1<=.004:gb=b.ts+pd.Timedelta(minutes=5);break
    m05=(h05-t).total_seconds()/60; m08=(h08-t).total_seconds()/60 if h08 is not None else np.nan
    gm=(gb-h05).total_seconds()/60 if gb is not None else np.nan
    runner='DEEP_RUNNER' if h08 is not None else 'SHALLOW_RUNNER'
    if gb is not None and gm<=5: path='FAST_GIVEBACK'
    elif h08 is not None and (gb is None or h08<=gb):path='CONTINUATION_FIRST'
    else:path='NORMAL_PULLBACK'
    return {'runner_state':runner,'first05_min':m05,'first08_min':m08,'giveback_state':path,'giveback40_min':gm}

def state240(k,t,tr):
    d=t+pd.Timedelta(minutes=240)
    if pd.Timestamp(tr.exit_t)<=d:return {'state240':'NOT_ALIVE','progress240_open':np.nan,'mfe240':np.nan,'taker240':np.nan}
    bars=k[(k.index>=t)&(k.index<d)]; op=float(k.loc[d,'open']); prog=op/tr.entry-1
    mfe=float(bars.high.max())/tr.entry-1; tak=float(np.nanmean(bars.taker_imb.to_numpy()))
    fail=mfe>=.005 and mfe<.008 and prog>=.002 and prog<=.004 and tak<0
    return {'state240':'SHALLOW_FAILURE' if fail else 'PRESERVE','progress240_open':prog,'mfe240':mfe,'taker240':tak}

def timeout18(k,t,tr):
    if tr.reason!='TIMEOUT':return {'state18h':'NOT_TIMEOUT','post18_ret6h':np.nan,'post18_mfe6h':np.nan,'post18_mae6h':np.nan}
    d=t+pd.Timedelta(hours=18); dt=d-pd.Timedelta(minutes=5); r=k.loc[dt]; old=row(k,dt-pd.Timedelta(minutes=60))
    w=k[(k.index>=d-pd.Timedelta(minutes=60))&(k.index<d)]
    above=float(r.close)>float(r.ema20); slope=float(r.ema20)/float(old.ema20)-1; tak=float(np.nanmean(w.taker_imb.to_numpy()))
    state='STILL_ALIVE' if above and slope>0 and tak>0 else ('DEAD' if (not above) and slope<0 and tak<0 else 'MIXED')
    px=float(r.close); fw=k[(k.index>=d)&(k.index<d+pd.Timedelta(hours=6))]
    if len(fw)==72:
        ret=float(fw.iloc[-1].close)/px-1;mfe=float(fw.high.max())/px-1;mae=1-float(fw.low.min())/px
    else:ret=mfe=mae=np.nan
    return {'state18h':state,'post18_ret6h':ret,'post18_mfe6h':mfe,'post18_mae6h':mae}

def a719_pnl(k,f,t,tr,s240):
    if s240['state240']!='SHALLOW_FAILURE':return tr.pnl
    d=t+pd.Timedelta(minutes=240);fund,_=s50.funding_cost(k,f,t,d,tr.entry)
    return s50.NOTIONAL*s240['progress240_open']-s50.FEE-fund

def auc(y,s):
    y=np.asarray(y,dtype=int);s=np.asarray(s,dtype=float);m=np.isfinite(s);y=y[m];s=s[m];n1=int(y.sum());n0=len(y)-n1
    if not n1 or not n0:return np.nan
    ranks=pd.Series(s).rank(method='average').to_numpy();return float((ranks[y==1].sum()-n1*(n1+1)/2)/(n1*n0))

def met(g):
    if len(g)==0:return {'n':0,'wins':0,'wr':np.nan,'pnl':0.0,'avg':np.nan}
    w=int((g.pnl>0).sum());return {'n':len(g),'wins':w,'wr':w/len(g),'pnl':float(g.pnl.sum()),'avg':float(g.pnl.mean())}

def stab(df,col):
    out=[]
    for st,g in df.groupby(col,dropna=False):
        r={'state':str(st),**met(g)};dm=met(g[g.idx<SPLIT]);vm=met(g[g.idx>=SPLIT]);r.update({f'disc_{k}':v for k,v in dm.items()});r.update({f'val_{k}':v for k,v in vm.items()});out.append(r)
    return sorted(out,key=lambda x:(-x['n'],x['state']))

def pct(x):return 'NA' if not np.isfinite(x) else f'{100*x:.2f}%'
def money(x):return 'NA' if not np.isfinite(x) else f'${x:+.3f}'
def tab(rows):
    z=['| State | N | WR | PnL | Discovery | Validation |','|---|---:|---:|---:|---:|---:|']
    for r in rows:z.append(f"| {r['state']} | {r['n']} | {pct(r['wr'])} | {money(r['pnl'])} | {r['disc_n']} / {pct(r['disc_wr'])} / {money(r['disc_pnl'])} | {r['val_n']} / {pct(r['val_wr'])} / {money(r['val_pnl'])} |")
    return '\n'.join(z)

def main():
    k=s50.load_klines();f=s50.load_funding();ents=s50.saturday_entries(k);trs=[s50.simulate(k,f,t) for t in ents]
    if len(trs)!=139 or sum(x.pnl>0 for x in trs)!=65 or abs(sum(x.pnl for x in trs)-87.20)>.20:raise RuntimeError('parent parity fail')
    rec=[];a719=[]
    for i,(t,tr) in enumerate(zip(ents,trs)):
        r={'idx':i,'date':tr.date,'pnl':tr.pnl,'win':tr.pnl>0,'reason':tr.reason,'mfe_parent':tr.mfe,'mae_parent':tr.mae}
        r.update(pre_context(k,t));r.update(thesis60(k,t,tr));r.update(runner_path(k,t,tr));s=state240(k,t,tr);r.update(s);r.update(timeout18(k,t,tr));rec.append(r);a719.append(a719_pnl(k,f,t,tr,s))
    df=pd.DataFrame(rec);df['a719_pnl']=a719
    # Hard parity gates for frozen prior research.
    stretched=df.pre_state.eq('STRETCHED')
    f60=df.state60.eq('FAILURE_CANDIDATE')
    if (stretched.sum(),stretched.iloc[:83].sum(),stretched.iloc[83:].sum())!=(16,8,8):raise RuntimeError('A7.26 state parity fail')
    if abs(df.a719_pnl.sum()-103.3830997612)>.01:raise RuntimeError('A7.19 econ parity fail')
    kept=df.loc[~stretched,'a719_pnl']
    if len(kept)!=123 or abs(kept.sum()-109.58688181)>.01:raise RuntimeError('A7.26 econ parity fail')
    if (f60.sum(),int(((df.pnl<=0)&f60).sum()),f60.iloc[:83].sum(),f60.iloc[83:].sum())!=(30,23,17,13):raise RuntimeError('A7.13 parity fail')
    if int((df.giveback_state=='FAST_GIVEBACK').sum())!=30 or int((df.state240=='SHALLOW_FAILURE').sum())!=8:raise RuntimeError('path parity fail')
    df.to_csv(OUT/'s50a_atlas_rows.csv',index=False)
    cols=['pre_state','pre_stretch_score','state60','runner_state','giveback_state','state240','state18h'];tables={c:stab(df,c) for c in cols}
    alive=df[df.state60!='NOT_ALIVE']
    aucs={}
    for name,g in [('full',alive),('discovery',alive[alive.idx<SPLIT]),('validation',alive[alive.idx>=SPLIT])]:
        y=g.win.astype(int).to_numpy();aucs[name]={'progress_raw':auc(y,g.progress60),'progress_rv':auc(y,g.progress60_rv),'mfe_raw':auc(y,g.mfe60),'mfe_rv':auc(y,g.mfe60_rv),'mae_loss_raw':auc(1-y,g.mae60),'mae_loss_rv':auc(1-y,g.mae60_rv)}
    df['route']=df.pre_state+'>'+df.state60+'>'+df.runner_state+'>'+df.giveback_state+'>'+df.state240
    routes=[]
    for rt,g in df.groupby('route'):
        if len(g)>=4:routes.append({'route':rt,**met(g),'disc_n':int((g.idx<SPLIT).sum()),'val_n':int((g.idx>=SPLIT).sum())})
    routes=sorted(routes,key=lambda x:(-x['n'],x['route']))
    tf=[]
    for st,g in df[df.state18h!='NOT_TIMEOUT'].groupby('state18h'):
        tf.append({'state':st,'n':len(g),'parent_wr':float(g.win.mean()),'parent_pnl':float(g.pnl.sum()),'post18_ret6h_mean':float(g.post18_ret6h.mean()),'post18_mfe6h_median':float(g.post18_mfe6h.median()),'post18_mae6h_median':float(g.post18_mae6h.median())})
    summary={'parent':met(df),'parity':{'a719_pnl':float(df.a719_pnl.sum()),'a726_kept_n':int((~stretched).sum()),'a726_pnl':float(df.loc[~stretched,'a719_pnl'].sum()),'failure60_n':int(f60.sum()),'failure60_losses':int(((df.pnl<=0)&f60).sum())},'tables':tables,'aucs':aucs,'routes':routes,'timeout_follow':tf}
    (OUT/'s50a_summary.json').write_text(json.dumps(summary,indent=2,default=float))
    md=['# BTC Temporal Saturday T-Method S5.0A — Adaptive State Atlas (Parity-Corrected)','',
        '**Status:** COMPLETE — STRONG SATURDAY-NATIVE STATE STRUCTURE FOUND; NO NEW TRADE RULE PROMOTED',
        '**Parent:** Saturday 18:00 WIB BUY / TP2.6 / SL1.2 / max18h','**Sample:** 139; discovery83 / validation56',
        '**Frozen benchmarks preserved:** A7.19 full-coverage and A7.26 selective.','',
        '## Reproduction/parity gates',f"- Parent: 139 / 65W / 74L / WR {pct(df.win.mean())} / {money(df.pnl.sum())}",f"- A7.19 reproduced: {money(df.a719_pnl.sum())}",f"- A7.26 exact state: 16 signals (8 discovery / 8 validation); frozen A7.19+skip economics {money(df.loc[~stretched,'a719_pnl'].sum())}",f"- A7.13 +60m failure: 30 live-position signals / 23 eventual losses = {23/30:.2%}",'',
        '## 1. Pre-entry state',tab(tables['pre_state']),'','### Stretch score',tab(tables['pre_stretch_score']),'',
        '## 2. +60m thesis health',tab(tables['state60']),'',
        '## 3. Runner maturity',tab(tables['runner_state']),'',
        '## 4. Post-0.5 path',tab(tables['giveback_state']),'',
        '## 5. +240m A7.19 state (classification only)',tab(tables['state240']),'',
        '## 6. +18h timeout health (descriptive only)',tab(tables['state18h']),'','### Next 6h after frozen timeout']
    for r in tf:md.append(f"- {r['state']}: N{r['n']}; next6h mean {pct(r['post18_ret6h_mean'])}; median MFE {pct(r['post18_mfe6h_median'])}; median MAE {pct(r['post18_mae6h_median'])}")
    md+=['','## 7. Fixed % vs volatility-normalized information (+60m, live positions only)']
    for n,v in aucs.items():md.append(f"- {n}: progress {v['progress_raw']:.3f} vs RV {v['progress_rv']:.3f}; MFE {v['mfe_raw']:.3f} vs RV {v['mfe_rv']:.3f}; MAE-for-loss {v['mae_loss_raw']:.3f} vs RV {v['mae_loss_rv']:.3f}")
    md+=['','## 8. Most common routes (N>=4, descriptive only)']
    for r in routes[:20]:md.append(f"- N{r['n']} / WR {100*r['wr']:.1f}% / {money(r['pnl'])} / D{r['disc_n']} V{r['val_n']}: `{r['route']}`")
    md+=['','## Guardrail','S5.0A maps causal states only. It does not authorize a new skip, cut, lock, flip, or hold-extension rule. S5.1 should test actions against this fixed state map while always benchmarking against preserved A7.19/A7.26.']
    (OUT/'S5.0A_CHECKPOINT.md').write_text('\n'.join(md)+'\n');print('\n'.join(md))

if __name__=='__main__':main()
