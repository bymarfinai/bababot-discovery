#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_POST_RECLAIM_ENTRY_LADDER_B27CF_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_POST_RECLAIM_ENTRY_LADDER_B27CF_Detail.csv'
OUT_SUM = ROOT / 'BTC_24H_POST_RECLAIM_ENTRY_LADDER_B27CF_Summary.csv'
OUT_SEL = ROOT / 'BTC_24H_POST_RECLAIM_ENTRY_LADDER_B27CF_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_POST_RECLAIM_ENTRY_LADDER_B27CF_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
LEVELS = (0.05,0.10,0.15,0.25,0.50)


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left')); b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d['eligible'])
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    assert len(q)==729, len(q)
    for p,n in exp.items(): assert len(q[q.partition==p])==n,(p,len(q[q.partition==p]),n)
    assert len(q[q.partition.isin(OOS)])==396
    assert q.reclaim_complete_ts.notna().all()
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_level(x5,r,f):
    start=pd.Timestamp(r.reclaim_complete_ts); end=pd.Timestamp(r.obs_end)
    L=float(r.L); H=float(r.H); R4=H-L; entry=L+f*R4
    assert R4>0 and start<end
    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4,'entry_fraction':f,'entry_px':entry}
    fill_idx=None; fill_ts=pd.NaT; terminal='NO_FILL_BEFORE_BLOCK_END'; terminal_ts=end
    for i,b in enumerate(q.itertuples()):
        fills=float(b.high)>=entry
        lowbreak=float(b.close)<L
        highbreak=float(b.close)>H
        if fill_idx is None:
            if fills:
                fill_idx=i; fill_ts=q.index[i]
                if lowbreak:
                    terminal='REBREAK_LOW_AFTER_FILL'; terminal_ts=q.index[i]+BAR5; break
                if highbreak:
                    terminal='HIGH_BREAK_AFTER_FILL'; terminal_ts=q.index[i]+BAR5; break
            else:
                if lowbreak:
                    terminal='LOW_BREAK_BEFORE_FILL'; terminal_ts=q.index[i]+BAR5; break
                if highbreak:
                    terminal='HIGH_BREAK_BEFORE_FILL'; terminal_ts=q.index[i]+BAR5; break
        else:
            if lowbreak:
                terminal='REBREAK_LOW_AFTER_FILL'; terminal_ts=q.index[i]+BAR5; break
            if highbreak:
                terminal='HIGH_BREAK_AFTER_FILL'; terminal_ts=q.index[i]+BAR5; break
    if fill_idx is not None and terminal=='NO_FILL_BEFORE_BLOCK_END':
        terminal='NO_BOUNDARY_AFTER_FILL'
    filled=fill_idx is not None
    mins_to_fill=float((fill_ts-start)/pd.Timedelta(minutes=1)) if filled else np.nan
    mins_fill_to_term=float((terminal_ts-fill_ts)/pd.Timedelta(minutes=1)) if filled and terminal=='REBREAK_LOW_AFTER_FILL' else np.nan
    return {**base,'filled':filled,'fill_ts':fill_ts,'terminal_type':terminal,'terminal_ts':terminal_ts,
            'minutes_reclaim_to_fill':mins_to_fill,'minutes_fill_to_rebreak':mins_fill_to_term}


def metrics(g):
    fills=g[g.filled].copy(); nf=len(g); n=len(fills)
    rb=int((fills.terminal_type=='REBREAK_LOW_AFTER_FILL').sum())
    hb=int((fills.terminal_type=='HIGH_BREAK_AFTER_FILL').sum())
    nb=int((fills.terminal_type=='NO_BOUNDARY_AFTER_FILL').sum())
    return {'source_n':int(nf),'fills_n':int(n),'fill_rate':n/nf if nf else np.nan,
            'rebreak_n':rb,'rebreak_rate':rb/n if n else np.nan,
            'high_break_n':hb,'high_break_rate':hb/n if n else np.nan,
            'no_boundary_n':nb,'no_boundary_rate':nb/n if n else np.nan,
            'median_reclaim_to_fill_min':float(fills.minutes_reclaim_to_fill.median()) if n else np.nan,
            'median_fill_to_rebreak_min':float(fills.loc[fills.terminal_type=='REBREAK_LOW_AFTER_FILL','minutes_fill_to_rebreak'].median()) if rb else np.nan}


def summarize(d):
    rows=[]
    for f in LEVELS:
        z=d[d.entry_fraction==f]
        for p in MAJOR: rows.append({'entry_fraction':f,'scope':'PARTITION','name':p,**metrics(z[z.partition==p])})
        rows.append({'entry_fraction':f,'scope':'POOL','name':'POOLED_OOS',**metrics(z[z.partition.isin(OOS)])})
        rows.append({'entry_fraction':f,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for cb in CLOCKS: rows.append({'entry_fraction':f,'scope':'CLOCK','name':cb,**metrics(z[z.clock_block==cb])})
    return pd.DataFrame(rows)


def getrow(s,f,scope,name):
    q=s[(s.entry_fraction==f)&(s.scope==scope)&(s.name==name)]; assert len(q)==1; return q.iloc[0]

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.1f}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    rows=[]
    for r in src.itertuples(index=False):
        for f in LEVELS: rows.append(eval_level(x5,r,f))
    d=pd.DataFrame(rows); assert len(d)==729*len(LEVELS)
    d.to_csv(OUT_DETAIL,index=False); s=summarize(d); s.to_csv(OUT_SUM,index=False)

    dev=[]
    for f in LEVELS:
        r=getrow(s,f,'PARTITION','development')
        eligible=bool(int(r.fills_n)>=50 and pd.notna(r.rebreak_rate) and float(r.rebreak_rate)>=.70)
        dev.append({'entry_fraction':f,'development_fills':int(r.fills_n),'development_rebreak_rate':float(r.rebreak_rate) if pd.notna(r.rebreak_rate) else np.nan,'development_eligible':eligible})
    sel=pd.DataFrame(dev)
    eligible_levels=sel.loc[sel.development_eligible,'entry_fraction'].tolist()
    selected=max(eligible_levels) if eligible_levels else None
    oos_supported=False
    if selected is not None:
        ext=getrow(s,selected,'PARTITION','external'); val=getrow(s,selected,'PARTITION','reference_validation'); oos=getrow(s,selected,'POOL','POOLED_OOS')
        oos_supported=bool(int(ext.fills_n)>=30 and float(ext.rebreak_rate)>=.60 and int(val.fills_n)>=30 and float(val.rebreak_rate)>=.60 and int(oos.fills_n)>=70 and float(oos.rebreak_rate)>=.65)
        sel['selected']=sel.entry_fraction.eq(selected)
        sel['oos_supported']=sel.entry_fraction.eq(selected)&oos_supported
    else:
        sel['selected']=False; sel['oos_supported']=False
    sel.to_csv(OUT_SEL,index=False)

    if selected is None: verdict='B27CF_POST_RECLAIM_ENTRY_NONE'
    elif oos_supported: verdict='B27CF_POST_RECLAIM_ENTRY_SUPPORTED'
    else: verdict='B27CF_POST_RECLAIM_ENTRY_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CF — BTC 24H Post-Reclaim SHORT Entry Ladder — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CE eligible reclaim cohort reproduced: external 202 / development 333 / validation 194 / pooled OOS 396 / pooled major 729. Structural entry anatomy only; trading WR/PF/PnL/expectancy are N/A.','',
           '## Entry ladder — major partitions','',
           '| Entry | Partition | Source N | Fills | Fill rate | Rebreak/fill | High break/fill | No boundary/fill | Reclaim→fill | Fill→rebreak |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for f in LEVELS:
        for p in MAJOR:
            r=getrow(s,f,'PARTITION',p)
            lines.append(f'| F{int(f*100):02d} | {p} | {int(r.source_n)} | {int(r.fills_n)} | {pct(r.fill_rate)} | {pct(r.rebreak_rate)} | {pct(r.high_break_rate)} | {pct(r.no_boundary_rate)} | {num(r.median_reclaim_to_fill_min)}m | {num(r.median_fill_to_rebreak_min)}m |')
    lines += ['', '## Pooled OOS','', '| Entry | Fills | Fill rate | Rebreak/fill | High break/fill | No boundary/fill | Reclaim→fill | Fill→rebreak |', '|---|---:|---:|---:|---:|---:|---:|---:|']
    for f in LEVELS:
        r=getrow(s,f,'POOL','POOLED_OOS')
        lines.append(f'| F{int(f*100):02d} | {int(r.fills_n)} | {pct(r.fill_rate)} | {pct(r.rebreak_rate)} | {pct(r.high_break_rate)} | {pct(r.no_boundary_rate)} | {num(r.median_reclaim_to_fill_min)}m | {num(r.median_fill_to_rebreak_min)}m |')
    lines += ['', '## Development selection','', '| Entry | Dev fills | Dev rebreak/fill | Eligible | Selected |', '|---|---:|---:|---|---|']
    for rr in sel.itertuples(index=False):
        lines.append(f'| F{int(rr.entry_fraction*100):02d} | {int(rr.development_fills)} | {pct(rr.development_rebreak_rate)} | {"YES" if rr.development_eligible else "NO"} | {"YES" if rr.selected else "NO"} |')
    if selected is not None:
        lines += ['', f'Frozen candidate: **F{int(selected*100):02d} = L + {100*selected:.0f}% R4**. Untouched OOS support: **{"PASS" if oos_supported else "FAIL"}**.']
    else:
        lines += ['', 'No development level met the frozen selection gate.']
    lines += ['', f'**Frozen verdict: `{verdict}`.**','', 'A structural pass does not define a trade. Any economic follow-up must preserve RR >= 1:1 and be separately preregistered.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
