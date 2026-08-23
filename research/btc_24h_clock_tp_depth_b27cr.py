#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Result.md'
OUT_DETAIL=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Detail.csv'
OUT_SUM=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Summary.csv'
OUT_MAP=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Map.csv'
OUT_STATUS=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Audit.txt'

BAR5=pd.Timedelta(minutes=5)
EXTRA=pd.Timedelta(hours=4)
MAJOR=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
TARGETS=(0.05,0.075,0.10,0.15)


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


def fill_event(x5,r):
    start=pd.Timestamp(r.reclaim_complete_ts); obs_end=pd.Timestamp(r.obs_end); horizon=obs_end+EXTRA
    H=float(r.H); L=float(r.L); R4=H-L; F05=L+.05*R4
    assert R4>0 and start<obs_end
    q0=fast_slice(x5,start,obs_end); qall=fast_slice(x5,start,horizon)
    assert len(q0)>=1 and q0.index[0]==start and len(qall)>=len(q0)
    fill_idx=None; fill_ts=pd.NaT; cancel='NO_FILL_BEFORE_BLOCK_END'
    for i,b in enumerate(q0.itertuples()):
        if float(b.high)>=F05:
            fill_idx=i; fill_ts=q0.index[i]; cancel=''; break
        if float(b.close)<L:
            cancel='LOW_BREAK_BEFORE_FILL'; break
        if float(b.close)>H:
            cancel='HIGH_BREAK_BEFORE_FILL'; break
    return {'start':start,'obs_end':obs_end,'horizon':horizon,'H':H,'L':L,'R4':R4,'F05':F05,
            'qall':qall,'fill_idx':fill_idx,'fill_ts':fill_ts,'cancel':cancel}


def eval_target(x5,r,tfrac,cache):
    start=cache['start']; obs_end=cache['obs_end']; horizon=cache['horizon']; H=cache['H']; L=cache['L']; R4=cache['R4']; F05=cache['F05']
    qall=cache['qall']; fill_idx=cache['fill_idx']; fill_ts=cache['fill_ts']; cancel=cache['cancel']
    target=L-tfrac*R4
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':obs_end,'reclaim_complete_ts':start,
          'H':H,'L':L,'R4':R4,'F05':F05,'target_fraction':tfrac,'target_px':target}
    if fill_idx is None:
        return {**base,'filled':False,'fill_ts':pd.NaT,'cancel_reason':cancel,'rebreak_confirmed':False,
                'rebreak_complete_ts':pd.NaT,'target_reached':False,'target_ts':pd.NaT,
                'high_failure':False,'high_failure_ts':pd.NaT,'unresolved':False,
                'minutes_reclaim_to_fill':np.nan,'minutes_fill_to_rebreak':np.nan,'minutes_fill_to_target':np.nan}
    rebreak=False; rb_complete=pd.NaT; hit=False; hit_ts=pd.NaT; high_fail=False; high_ts=pd.NaT
    fb=qall.iloc[fill_idx]; fb_ts=qall.index[fill_idx]; c=float(fb.close)
    if c<L:
        rebreak=True; rb_complete=fb_ts+BAR5
    elif c>H:
        high_fail=True; high_ts=fb_ts+BAR5
    if not high_fail:
        for i in range(fill_idx+1,len(qall)):
            ts=qall.index[i]; b=qall.iloc[i]; c=float(b.close); lo=float(b.low)
            if not rebreak:
                if c<L:
                    rebreak=True; rb_complete=ts+BAR5; continue
                if c>H:
                    high_fail=True; high_ts=ts+BAR5; break
                continue
            if ts<rb_complete: continue
            if lo<=target:
                hit=True; hit_ts=ts+BAR5; break
            if c>H:
                high_fail=True; high_ts=ts+BAR5; break
    unresolved=bool((not hit) and (not high_fail))
    return {**base,'filled':True,'fill_ts':fill_ts,'cancel_reason':'','rebreak_confirmed':bool(rebreak),
            'rebreak_complete_ts':rb_complete,'target_reached':bool(hit),'target_ts':hit_ts,
            'high_failure':bool(high_fail),'high_failure_ts':high_ts,'unresolved':unresolved,
            'minutes_reclaim_to_fill':float((fill_ts-start)/pd.Timedelta(minutes=1)),
            'minutes_fill_to_rebreak':float((rb_complete-fill_ts)/pd.Timedelta(minutes=1)) if rebreak else np.nan,
            'minutes_fill_to_target':float((hit_ts-fill_ts)/pd.Timedelta(minutes=1)) if hit else np.nan}


def metrics(g):
    source_n=len(g); z=g[g.filled].copy(); fills=len(z)
    rb=int(z.rebreak_confirmed.sum()) if fills else 0
    hit=int(z.target_reached.sum()) if fills else 0
    hf=int(z.high_failure.sum()) if fills else 0
    un=int(z.unresolved.sum()) if fills else 0
    return {'source_n':int(source_n),'fills_n':int(fills),'fill_rate':fills/source_n if source_n else np.nan,
            'rebreak_n':rb,'rebreak_rate_fill':rb/fills if fills else np.nan,
            'target_n':hit,'target_rate_fill':hit/fills if fills else np.nan,'target_yield_source':hit/source_n if source_n else np.nan,
            'high_failure_n':hf,'high_failure_rate_fill':hf/fills if fills else np.nan,
            'unresolved_n':un,'unresolved_rate_fill':un/fills if fills else np.nan,
            'median_reclaim_fill_min':float(z.minutes_reclaim_to_fill.median()) if fills else np.nan,
            'median_fill_rebreak_min':float(z.loc[z.rebreak_confirmed,'minutes_fill_to_rebreak'].median()) if rb else np.nan,
            'median_fill_target_min':float(z.loc[z.target_reached,'minutes_fill_to_target'].median()) if hit else np.nan}


def summarize(d):
    rows=[]
    for t in TARGETS:
        z=d[d.target_fraction.eq(t)]
        for p in MAJOR: rows.append({'target_fraction':t,'scope':'PARTITION','name':p,**metrics(z[z.partition.eq(p)])})
        rows.append({'target_fraction':t,'scope':'POOL','name':'POOLED_MAJOR',**metrics(z)})
        for p in MAJOR:
            for cb in CLOCKS:
                rows.append({'target_fraction':t,'scope':'CLOCK_'+p.upper(),'name':cb,**metrics(z[z.partition.eq(p)&z.clock_block.eq(cb)])})
        for cb in CLOCKS:
            rows.append({'target_fraction':t,'scope':'CLOCK_MAJOR','name':cb,**metrics(z[z.clock_block.eq(cb)])})
    return pd.DataFrame(rows)


def row(s,t,scope,name):
    q=s[(s.target_fraction.eq(t))&(s.scope.eq(scope))&(s.name.eq(name))]
    assert len(q)==1,(t,scope,name,len(q)); return q.iloc[0]


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def mins(v): return '-' if pd.isna(v) else f'{float(v):.1f}m'
def tname(t):
    return {0.05:'T5',0.075:'T7.5',0.10:'T10',0.15:'T15'}[round(float(t),3)]


def select_map(s):
    rows=[]
    for cb in CLOCKS:
        eligible=[]
        for t in TARGETS:
            r=row(s,t,'CLOCK_DEVELOPMENT',cb)
            ok=bool(int(r.fills_n)>=30 and float(r.target_rate_fill)>=.70-1e-12)
            if ok: eligible.append(t)
        sel=max(eligible) if eligible else .05
        er=row(s,sel,'CLOCK_EXTERNAL',cb); vr=row(s,sel,'CLOCK_REFERENCE_VALIDATION',cb); dr=row(s,sel,'CLOCK_DEVELOPMENT',cb)
        confirmed=bool(int(er.fills_n)>=15 and int(vr.fills_n)>=15 and float(er.target_rate_fill)>=.65 and float(vr.target_rate_fill)>=.65)
        rows.append({'clock_block':cb,'wib':WIB[cb],'selected_target':sel,'reused_confirmed':confirmed,
                     'dev_fills':int(dr.fills_n),'dev_hit_fill':float(dr.target_rate_fill),
                     'ext_fills':int(er.fills_n),'ext_hit_fill':float(er.target_rate_fill),
                     'val_fills':int(vr.fills_n),'val_hit_fill':float(vr.target_rate_fill)})
    return pd.DataFrame(rows)


def selected_data(d,m):
    pieces=[]
    for rr in m.itertuples(index=False):
        pieces.append(d[d.clock_block.eq(rr.clock_block)&d.target_fraction.eq(rr.selected_target)].copy())
    q=pd.concat(pieces,ignore_index=True); assert len(q)==729
    return q


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    out=[]
    for r in src.itertuples(index=False):
        cache=fill_event(x5,r)
        for t in TARGETS: out.append(eval_target(x5,r,t,cache))
    d=pd.DataFrame(out); assert len(d)==729*len(TARGETS)
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)
    m=select_map(s); m.to_csv(OUT_MAP,index=False)
    sd=selected_data(d,m)

    # Exact B27CP F05 fill identity, invariant across target candidates.
    t10=d[d.target_fraction.eq(.10)]
    exp={'external':183,'development':297,'reference_validation':173}
    for p,n in exp.items(): assert int(t10[t10.partition.eq(p)].filled.sum())==n,(p,int(t10[t10.partition.eq(p)].filled.sum()),n)
    assert int(t10.filled.sum())==653

    devm=metrics(sd[sd.partition.eq('development')]); majm=metrics(sd)
    confirmed=int(m.reused_confirmed.sum())
    verdict='B27CR_CLOCK_TP_REUSED_CANDIDATE' if (confirmed>=4 and float(devm['target_rate_fill'])>=.70 and float(majm['target_rate_fill'])>=.65) else 'B27CR_CLOCK_TP_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\nrows={len(d)}\nfills_external=183\nfills_development=297\nfills_validation=173\nfills_major=653\nbase_b27cp_reproduced=TRUE\nuntouched_holdout=NONE\n')

    lines=['# B27CR — BTC 24H Clock-Specific TP Depth Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CP structural F05 fill identity reproduced: external 183 / development 297 / validation 173 / pooled major 653.','',
           '**Anatomy only:** trading WR/PF/expectancy/PnL/SL are **N/A**. External/reference_validation are reused-data confirmation, not untouched OOS.','',
           'Frozen targets: T5 / T7.5 / T10 / T15. Entry remains F05 for every clock; horizon remains original block + fixed 4h when unresolved.','',
           '## Six clocks — development selection first','',
           '| UTC / WIB | Target | Source | Fills | Rebreak/fill | Target/fill | Target yield/source | High fail/fill | Unresolved/fill | Fill→target | Selected |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    for cb in CLOCKS:
        sel=float(m.loc[m.clock_block.eq(cb),'selected_target'].iloc[0])
        for t in TARGETS:
            r=row(s,t,'CLOCK_DEVELOPMENT',cb)
            lines.append(f'| {cb} / {WIB[cb]} | {tname(t)} | {int(r.source_n)} | {int(r.fills_n)} | {pct(r.rebreak_rate_fill)} | **{pct(r.target_rate_fill)}** | {pct(r.target_yield_source)} | {pct(r.high_failure_rate_fill)} | {pct(r.unresolved_rate_fill)} | {mins(r.median_fill_target_min)} | {"**YES**" if abs(t-sel)<1e-12 else ""} |')

    lines += ['', '## Frozen clock TP map + reused confirmation','',
              '| UTC / WIB | Selected TP | Dev N / hit | External N / hit | Validation N / hit | Reused confirmed |',
              '|---|---|---:|---:|---:|---|']
    for rr in m.itertuples(index=False):
        lines.append(f'| {rr.clock_block} / {rr.wib} | **{tname(rr.selected_target)}** | {rr.dev_fills} / {pct(rr.dev_hit_fill)} | {rr.ext_fills} / {pct(rr.ext_hit_fill)} | {rr.val_fills} / {pct(rr.val_hit_fill)} | {"YES" if rr.reused_confirmed else "NO"} |')

    lines += ['', '## Selected-map aggregate anatomy','',
              '| Scope | Source | Fills | Target reached | Hit/fill | Yield/source | High fail/fill | Unresolved/fill |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for p in (*MAJOR,'POOLED_MAJOR'):
        mm=metrics(sd if p=='POOLED_MAJOR' else sd[sd.partition.eq(p)])
        lines.append(f'| {p} | {mm["source_n"]} | {mm["fills_n"]} | {mm["target_n"]} | **{pct(mm["target_rate_fill"])}** | {pct(mm["target_yield_source"])} | {pct(mm["high_failure_rate_fill"])} | {pct(mm["unresolved_rate_fill"])} |')
    lines += ['',f'Reused-confirmed selected targets: **{confirmed}/6**.','',f'**Frozen verdict: `{verdict}`.**','',
              'This is not trading WR. No SL economics were optimized. Any economic follow-up must freeze this clock-TP map and preserve nominal RR >=1:1; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
