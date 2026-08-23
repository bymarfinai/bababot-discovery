#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Result.md'
OUT_DETAIL=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Detail.csv'
OUT_SUM=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Summary.csv'
OUT_MAP=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Map.csv'
OUT_STATUS=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CLOCK_SPECIFIC_ENTRY_B27CP_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
REUSED=('external','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
LEVELS=(0.05,0.10,0.15,0.25,0.50)


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x,start,end):
    a=int(x.index.searchsorted(start,'left')); b=int(x.index.searchsorted(end,'left'))
    return x.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d['eligible'])
    q=d[d.partition.isin(MAJOR)&d.eligible].copy()
    exp={'external':202,'development':333,'reference_validation':194}
    assert len(q)==729
    for p,n in exp.items(): assert len(q[q.partition.eq(p)])==n,(p,len(q[q.partition.eq(p)]),n)
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_one(x5,r,f):
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); horizon=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=H-L; entry=L+f*R4; T10=L-.10*R4
    assert R4>0 and start<obs_end
    q0=fast_slice(x5,start,obs_end)
    qall=fast_slice(x5,start,horizon)
    assert len(q0)>=1 and q0.index[0]==start
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4,'entry_fraction':f,'entry_level':entry,'T10':T10}

    fill_idx=None; fill_ts=pd.NaT; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q0.itertuples()):
        fills=float(b.high)>=entry
        lowbreak=float(b.close)<L
        highbreak=float(b.close)>H
        if fills:
            fill_idx=i; fill_ts=q0.index[i]; cancel=''
            break
        if lowbreak:
            cancel='LOW_BREAK_BEFORE_FILL'; break
        if highbreak:
            cancel='HIGH_BREAK_BEFORE_FILL'; break
    if fill_idx is None:
        return {**base,'filled':False,'fill_ts':pd.NaT,'cancel_reason':cancel,'rebreak_confirmed':False,
                'rebreak_complete_ts':pd.NaT,'t10_reached':False,'t10_ts':pd.NaT,'high_failure':False,
                'high_failure_ts':pd.NaT,'unresolved':False,'minutes_reclaim_to_fill':np.nan,
                'minutes_fill_to_rebreak':np.nan,'minutes_fill_to_t10':np.nan}

    rebreak=False; rb_complete=pd.NaT; t10=False; t10_ts=pd.NaT; high_fail=False; high_ts=pd.NaT
    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; fb_c=float(fb.close)
    if fb_c<L:
        rebreak=True; rb_complete=fb_ts+BAR5
    elif fb_c>H:
        high_fail=True; high_ts=fb_ts+BAR5

    if not high_fail:
        for i in range(fill_idx+1,len(qall)):
            ts=qall.index[i]; b=qall.iloc[i]; c=float(b.close); lo=float(b.low)
            if not rebreak:
                if c<L:
                    rebreak=True; rb_complete=ts+BAR5
                    continue
                if c>H:
                    high_fail=True; high_ts=ts+BAR5; break
                continue
            if ts<rb_complete:
                continue
            # Favorable intrabar T10 is observable before this bar's completed-close invalidation.
            if lo<=T10:
                t10=True; t10_ts=ts+BAR5; break
            if c>H:
                high_fail=True; high_ts=ts+BAR5; break

    unresolved=bool((not t10) and (not high_fail))
    return {**base,'filled':True,'fill_ts':fill_ts,'cancel_reason':'','rebreak_confirmed':bool(rebreak),
            'rebreak_complete_ts':rb_complete,'t10_reached':bool(t10),'t10_ts':t10_ts,
            'high_failure':bool(high_fail),'high_failure_ts':high_ts,'unresolved':unresolved,
            'minutes_reclaim_to_fill':float((fill_ts-start)/pd.Timedelta(minutes=1)),
            'minutes_fill_to_rebreak':float((rb_complete-fill_ts)/pd.Timedelta(minutes=1)) if rebreak else np.nan,
            'minutes_fill_to_t10':float((t10_ts-fill_ts)/pd.Timedelta(minutes=1)) if t10 else np.nan}


def metrics(g):
    source_n=len(g); z=g[g.filled].copy(); fills=len(z)
    rb=int(z.rebreak_confirmed.sum()) if fills else 0
    t10=int(z.t10_reached.sum()) if fills else 0
    hf=int(z.high_failure.sum()) if fills else 0
    un=int(z.unresolved.sum()) if fills else 0
    return {'source_n':int(source_n),'fills_n':int(fills),'fill_rate':fills/source_n if source_n else np.nan,
            'rebreak_n':rb,'rebreak_rate_fill':rb/fills if fills else np.nan,
            't10_n':t10,'t10_rate_fill':t10/fills if fills else np.nan,'t10_yield_source':t10/source_n if source_n else np.nan,
            'high_failure_n':hf,'high_failure_rate_fill':hf/fills if fills else np.nan,
            'unresolved_n':un,'unresolved_rate_fill':un/fills if fills else np.nan,
            'median_reclaim_fill_min':float(z.minutes_reclaim_to_fill.median()) if fills else np.nan,
            'median_fill_rebreak_min':float(z.loc[z.rebreak_confirmed,'minutes_fill_to_rebreak'].median()) if rb else np.nan,
            'median_fill_t10_min':float(z.loc[z.t10_reached,'minutes_fill_to_t10'].median()) if t10 else np.nan}


def summarize(d):
    rows=[]
    for f in LEVELS:
        z=d[d.entry_fraction.eq(f)]
        for p in MAJOR: rows.append({'entry_fraction':f,'scope':'PARTITION','name':p,**metrics(z[z.partition.eq(p)])})
        rows.append({'entry_fraction':f,'scope':'POOL','name':'POOLED_REUSED_EXTVAL',**metrics(z[z.partition.isin(REUSED)])})
        rows.append({'entry_fraction':f,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for p in MAJOR:
            for cb in CLOCKS:
                rows.append({'entry_fraction':f,'scope':'CLOCK_'+p.upper(),'name':cb,**metrics(z[z.partition.eq(p)&z.clock_block.eq(cb)])})
        for cb in CLOCKS:
            rows.append({'entry_fraction':f,'scope':'CLOCK_REUSED','name':cb,**metrics(z[z.partition.isin(REUSED)&z.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def row(s,f,scope,name):
    q=s[(s.entry_fraction.eq(f))&(s.scope.eq(scope))&(s.name.eq(name))]
    assert len(q)==1,(f,scope,name,len(q))
    return q.iloc[0]


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def mins(v): return '-' if pd.isna(v) else f'{float(v):.1f}m'


def select_map(s):
    rows=[]
    for cb in CLOCKS:
        b=row(s,.05,'CLOCK_DEVELOPMENT',cb); by=float(b.t10_yield_source)
        candidates=[]
        for f in LEVELS[1:]:
            r=row(s,f,'CLOCK_DEVELOPMENT',cb)
            elig=bool(int(r.fills_n)>=20 and float(r.t10_yield_source)>=by+.02-1e-12)
            if elig:
                candidates.append((float(r.t10_yield_source),float(r.t10_rate_fill),float(r.fill_rate),-f,f))
        sel=max(candidates)[-1] if candidates else .05
        ext=row(s,sel,'CLOCK_EXTERNAL',cb); val=row(s,sel,'CLOCK_REFERENCE_VALIDATION',cb)
        extb=row(s,.05,'CLOCK_EXTERNAL',cb); valb=row(s,.05,'CLOCK_REFERENCE_VALIDATION',cb)
        alt=sel!=.05
        confirmed=bool(alt and int(ext.fills_n)>=10 and int(val.fills_n)>=10 and
                       float(ext.t10_yield_source)>=float(extb.t10_yield_source)-1e-12 and
                       float(val.t10_yield_source)>=float(valb.t10_yield_source)-1e-12)
        rows.append({'clock_block':cb,'wib':WIB[cb],'selected_fraction':sel,'alternate':alt,'reused_confirmed':confirmed,
                     'dev_f05_yield':float(b.t10_yield_source),'dev_selected_yield':float(row(s,sel,'CLOCK_DEVELOPMENT',cb).t10_yield_source),
                     'ext_f05_yield':float(extb.t10_yield_source),'ext_selected_yield':float(ext.t10_yield_source),
                     'val_f05_yield':float(valb.t10_yield_source),'val_selected_yield':float(val.t10_yield_source)})
    return pd.DataFrame(rows)


def selected_data(d,m):
    pieces=[]
    for rr in m.itertuples(index=False):
        pieces.append(d[d.clock_block.eq(rr.clock_block)&d.entry_fraction.eq(rr.selected_fraction)].copy())
    q=pd.concat(pieces,ignore_index=True)
    # exactly one candidate row per source event after map selection
    assert len(q)==729
    return q


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    out=[]
    for r in src.itertuples(index=False):
        for f in LEVELS: out.append(eval_one(x5,r,f))
    d=pd.DataFrame(out); assert len(d)==729*len(LEVELS)
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    m=select_map(s); m.to_csv(OUT_MAP,index=False)
    sd=selected_data(d,m)

    base=d[d.entry_fraction.eq(.05)].copy(); assert len(base)==729
    map_metrics={p:metrics(sd[sd.partition.eq(p)]) for p in MAJOR}
    map_metrics['POOLED_MAJOR']=metrics(sd)
    base_metrics={p:metrics(base[base.partition.eq(p)]) for p in MAJOR}
    base_metrics['POOLED_MAJOR']=metrics(base)

    alt_n=int(m.alternate.sum()); conf_n=int(m.reused_confirmed.sum())
    improved=float(map_metrics['POOLED_MAJOR']['t10_yield_source'])>float(base_metrics['POOLED_MAJOR']['t10_yield_source'])+1e-12
    verdict='B27CP_CLOCK_ENTRY_REUSED_CANDIDATE' if (alt_n>=2 and conf_n>=int(np.ceil(alt_n/2)) and improved) else 'B27CP_CLOCK_ENTRY_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\nlevels={len(LEVELS)}\nrows={len(d)}\nuntouched_holdout=NONE\n')

    lines=['# B27CP — BTC 24H Clock-Specific SHORT Entry Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Structural/anatomy only: trading WR/PF/expectancy/PnL are **N/A**. External/reference_validation are reused-data confirmation, not untouched OOS.','',
           'Frozen candidates: F05/F10/F15/F25/F50. Structural objective: causal T10 before completed High failure, with the frozen +4h unresolved horizon.','',
           '## Six clocks — development first','',
           '| UTC / WIB | Entry | Source | Fills | Fill | Rebreak/fill | T10/fill | T10 yield/source | High fail/fill | Unresolved/fill | Reclaim→fill | Fill→T10 | Selected |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for cb in CLOCKS:
        sel=float(m.loc[m.clock_block.eq(cb),'selected_fraction'].iloc[0])
        for f in LEVELS:
            r=row(s,f,'CLOCK_DEVELOPMENT',cb)
            lines.append(f'| {cb} / {WIB[cb]} | F{int(f*100):02d} | {int(r.source_n)} | {int(r.fills_n)} | {pct(r.fill_rate)} | {pct(r.rebreak_rate_fill)} | {pct(r.t10_rate_fill)} | **{pct(r.t10_yield_source)}** | {pct(r.high_failure_rate_fill)} | {pct(r.unresolved_rate_fill)} | {mins(r.median_reclaim_fill_min)} | {mins(r.median_fill_t10_min)} | {"**YES**" if abs(f-sel)<1e-12 else ""} |')

    lines += ['', '## Frozen clock map + reused-data confirmation','',
              '| UTC / WIB | Selected | Dev F05→selected T10 yield | External F05→selected | Validation F05→selected | Reused confirmed |',
              '|---|---|---:|---:|---:|---|']
    for rr in m.itertuples(index=False):
        lines.append(f'| {rr.clock_block} / {rr.wib} | **F{int(rr.selected_fraction*100):02d}** | {pct(rr.dev_f05_yield)} → **{pct(rr.dev_selected_yield)}** | {pct(rr.ext_f05_yield)} → **{pct(rr.ext_selected_yield)}** | {pct(rr.val_f05_yield)} → **{pct(rr.val_selected_yield)}** | {"YES" if rr.reused_confirmed else "NO"} |')

    lines += ['', '## Selected clock map vs universal F05','',
              '| Scope | Source | F05 fills | Map fills | F05 T10/fill | Map T10/fill | F05 T10 yield/source | Map T10 yield/source | Map High fail/fill | Map unresolved/fill |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*MAJOR,'POOLED_MAJOR'):
        b=base_metrics[p]; a=map_metrics[p]
        lines.append(f'| {p} | {a["source_n"]} | {b["fills_n"]} | {a["fills_n"]} | {pct(b["t10_rate_fill"])} | {pct(a["t10_rate_fill"])} | {pct(b["t10_yield_source"])} | **{pct(a["t10_yield_source"])}** | {pct(a["high_failure_rate_fill"])} | {pct(a["unresolved_rate_fill"])} |')

    lines += ['', f'Alternate entry selected in **{alt_n}/6** clocks; reused-confirmed alternates **{conf_n}/{alt_n if alt_n else 0}**.',
              '', f'**Frozen verdict: `{verdict}`.**','',
              'This is not a trading-WR result. No SL economics were optimized here. Any economic follow-up must be separately preregistered with nominal RR >=1:1; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
