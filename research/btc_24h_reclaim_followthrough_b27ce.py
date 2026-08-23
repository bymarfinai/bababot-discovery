#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Events.csv'
OUT_MD = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_SUM = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
REGIMES = ('BULL','BEAR','SIDEWAYS')
LADDERS = (.05,.10,.15,.25,.50)


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','retest_complete_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    q=d[d.partition.isin(MAJOR)&d.retest_class.eq('RETEST_RECLAIMED')].copy()
    exp={'external':202,'development':336,'reference_validation':196}
    assert len(q)==734
    for p,n in exp.items(): assert len(q[q.partition==p])==n,(p,len(q[q.partition==p]),n)
    assert int(q.partition.isin(OOS).sum())==398
    assert q.retest_complete_ts.notna().all()
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_one(x5,r):
    start=pd.Timestamp(r.retest_complete_ts); end=pd.Timestamp(r.obs_end)
    L=float(r.L); H=float(r.H); R4=H-L
    assert R4>0 and start<=end
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4}
    if start>=end:
        return {**base,'eligible':False,'terminal_type':'NO_FOLLOWTHROUGH_WINDOW','terminal_ts':pd.NaT,
                'minutes_to_terminal':np.nan,'max_high_ext_r4':np.nan,'max_close_ext_r4':np.nan,
                'final_close_above_L':np.nan,**{f'close_ext_{int(f*100):02d}':np.nan for f in LADDERS}}
    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start
    term_idx=None; typ='NO_BOUNDARY_BY_BLOCK_END'
    for i,b in enumerate(q.itertuples()):
        c=float(b.close)
        if c<L: term_idx=i; typ='REBREAK_LOW'; break
        if c>H: term_idx=i; typ='HIGH_BREAK'; break
    if term_idx is None:
        z=q; terminal_ts=end; mins=float((end-start)/pd.Timedelta(minutes=1))
    else:
        z=q.iloc[:term_idx+1]; terminal_ts=q.index[term_idx]+BAR5
        mins=float((terminal_ts-start)/pd.Timedelta(minutes=1))
    max_hi=max(0.0,(float(z.high.max())-L)/R4)
    max_cl=max(0.0,(float(z.close.max())-L)/R4)
    final_above=bool(float(q.iloc[-1].close)>L)
    out={**base,'eligible':True,'terminal_type':typ,'terminal_ts':terminal_ts,
         'minutes_to_terminal':mins,'max_high_ext_r4':max_hi,'max_close_ext_r4':max_cl,
         'final_close_above_L':final_above}
    for f in LADDERS: out[f'close_ext_{int(f*100):02d}']=bool(max_cl>=f)
    return out


def metrics(g):
    elig=g[g.eligible].copy(); n=len(g); ne=len(elig)
    re=int((elig.terminal_type=='REBREAK_LOW').sum()); hi=int((elig.terminal_type=='HIGH_BREAK').sum()); nb=int((elig.terminal_type=='NO_BOUNDARY_BY_BLOCK_END').sum())
    nw=n-ne
    rb=elig[elig.terminal_type=='REBREAK_LOW']
    out={'n':int(n),'eligible_n':int(ne),'no_window_n':int(nw),'rebreak_n':re,'rebreak_rate':re/ne if ne else np.nan,
         'high_break_n':hi,'high_break_rate':hi/ne if ne else np.nan,'no_boundary_n':nb,'no_boundary_rate':nb/ne if ne else np.nan,
         'persistent_rate':(hi+nb)/ne if ne else np.nan,
         'median_rebreak_min':float(rb.minutes_to_terminal.median()) if len(rb) else np.nan,
         'max_close_p50':float(elig.max_close_ext_r4.quantile(.5)) if ne else np.nan,
         'max_close_p75':float(elig.max_close_ext_r4.quantile(.75)) if ne else np.nan}
    for f in LADDERS:
        c=f'close_ext_{int(f*100):02d}'
        out[f'{c}_rate']=float(elig[c].astype(float).mean()) if ne else np.nan
    return out


def summarize(d):
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**metrics(d[d.partition==p])})
    rows += [{'scope':'POOL','name':'POOLED_OOS',**metrics(d[d.partition.isin(OOS)])},
             {'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)}]
    for cb in CLOCKS: rows.append({'scope':'CLOCK','name':cb,**metrics(d[d.clock_block==cb])})
    for rg in REGIMES: rows.append({'scope':'REGIME','name':rg,**metrics(d[d.regime==rg])})
    return pd.DataFrame(rows)


def row(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]; assert len(z)==1; return z.iloc[0]

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.1f}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==734 and int(d.partition.isin(OOS).sum())==398
    d.to_csv(OUT_DETAIL,index=False); s=summarize(d); s.to_csv(OUT_SUM,index=False)

    ext=row(s,'PARTITION','external'); val=row(s,'PARTITION','reference_validation'); oos=row(s,'POOL','POOLED_OOS')
    temporary=(oos.rebreak_rate>=.60 and ext.rebreak_rate>=.55 and val.rebreak_rate>=.55)
    persistent=(oos.persistent_rate>=.60 and ext.persistent_rate>=.55 and val.persistent_rate>=.55)
    verdict='B27CE_RECLAIM_MOSTLY_TEMPORARY' if temporary else ('B27CE_RECLAIM_MOSTLY_PERSISTENT' if persistent else 'B27CE_RECLAIM_FOLLOWTHROUGH_MIXED')
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CE — BTC 24H Direct-Break Reclaim Followthrough Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27BZ first-retest reclaim cohort reproduced: external 202 / development 336 / validation 196 / pooled major 734 / pooled OOS 398. Anatomy only; trading WR/PF/PnL/expectancy are N/A.','',
           '## Primary readout','',
           '| Scope | N / eligible | Rebreak Low | High break | No boundary | Persistent-like | No window | Median reclaim→rebreak | Max close ext P50/P75 | +5/+10/+15/+25/+50% R4 |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=row(s,scope,name)
        ladd=' / '.join(pct(r[f'close_ext_{int(f*100):02d}_rate']) for f in LADDERS)
        lines.append(f'| {name} | {int(r.n)} / {int(r.eligible_n)} | {int(r.rebreak_n)} ({pct(r.rebreak_rate)}) | {int(r.high_break_n)} ({pct(r.high_break_rate)}) | {int(r.no_boundary_n)} ({pct(r.no_boundary_rate)}) | {pct(r.persistent_rate)} | {int(r.no_window_n)} | {num(r.median_rebreak_min)}m | {pct(r.max_close_p50)} / {pct(r.max_close_p75)} | {ladd} |')
    lines += ['', '## By 4H clock — pooled major','',
              '| UTC block | N / eligible | Rebreak Low | Persistent-like | Median rebreak | Max close P75 | +15% R4 | +25% R4 |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=row(s,'CLOCK',cb)
        lines.append(f'| {cb} | {int(r.n)} / {int(r.eligible_n)} | {pct(r.rebreak_rate)} | {pct(r.persistent_rate)} | {num(r.median_rebreak_min)}m | {pct(r.max_close_p75)} | {pct(r.close_ext_15_rate)} | {pct(r.close_ext_25_rate)} |')
    lines += ['',f'**Frozen verdict: `{verdict}`.**','',
              'Rebreak/persistence rates describe only the remainder of the same 4H block after first-retest reclaim. They are not trade win rates and do not imply a live rule.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
