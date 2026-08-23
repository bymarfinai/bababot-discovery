#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_POST_REBREAK_T10_HYBRID_B27CJ_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_POST_REBREAK_T10_HYBRID_B27CJ_Detail.csv'
OUT_SUM = ROOT / 'BTC_24H_POST_REBREAK_T10_HYBRID_B27CJ_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_POST_REBREAK_T10_HYBRID_B27CJ_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
EPS = 1e-12


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5,start,end):
    a=int(x5.index.searchsorted(start,'left'))
    b=int(x5.index.searchsorted(end,'left'))
    return x5.iloc[a:b]


def load_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','rebreak_complete_ts','continuation_terminal_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['followthrough_eligible']=as_bool(d['followthrough_eligible'])
    d['hit_0p1']=as_bool(d['hit_0p1'])
    q=d[d.partition.isin(MAJOR)&d.followthrough_eligible].copy()
    exp={'external':147,'development':233,'reference_validation':133}
    hits={'external':96,'development':172,'reference_validation':98}
    assert len(q)==513
    for p,n in exp.items():
        z=q[q.partition==p]
        assert len(z)==n,(p,len(z),n)
        assert int(z.hit_0p1.sum())==hits[p],(p,int(z.hit_0p1.sum()),hits[p])
    assert len(q[q.partition.isin(OOS)])==280
    assert int(q.hit_0p1.sum())==366
    return q.sort_values(['partition','obs_start','rebreak_complete_ts']).reset_index(drop=True)


def block_end_open(x5,end):
    pos=int(x5.index.searchsorted(end,'left'))
    if pos>=len(x5) or x5.index[pos]!=end:
        return None
    return float(x5.iloc[pos].open)


def simulate_reacher(x5,r):
    start=pd.Timestamp(r.rebreak_complete_ts); end=pd.Timestamp(r.obs_end)
    L=float(r.L); H=float(r.H); R4=float(r.R4); t10=L-.10*R4
    assert R4>0 and start<end and bool(r.hit_0p1)
    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start

    touch_idx=None
    for i,b in enumerate(q.itertuples()):
        if float(b.low)<=t10:
            touch_idx=i; break
    assert touch_idx is not None
    touch_ts=q.index[touch_idx]
    expected_min=float(r.min_0p1)
    got_min=float((touch_ts-start)/pd.Timedelta(minutes=1))
    assert abs(got_min-expected_min)<1e-9,(got_min,expected_min)

    highs=q.high.astype(float).to_numpy()
    active_ceiling=np.nan
    floor_active=False
    ratchets=0
    touch_close=float(q.iloc[touch_idx].close)
    activation_close_above=bool(touch_close>t10)
    exit_ts=pd.NaT; exit_px=np.nan; reason=None; ceiling_kind=None

    for i,(ts,bar) in enumerate(q.iterrows()):
        op=float(bar.open); hi=float(bar.high)

        if floor_active:
            assert np.isfinite(active_ceiling) and active_ceiling<=t10+EPS
            if op>=active_ceiling:
                exit_ts=ts; exit_px=op; reason='CEILING_OPEN_EXIT'
                ceiling_kind='T10' if active_ceiling>=t10-EPS else 'STRUCTURAL'
                break
            if hi>=active_ceiling:
                exit_ts=ts; exit_px=active_ceiling; reason='CEILING_STOP'
                ceiling_kind='T10' if active_ceiling>=t10-EPS else 'STRUCTURAL'
                break

        pivot_now=np.nan
        if i>=2 and highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
            pivot_now=float(highs[i-1])

        if i==touch_idx:
            active_ceiling=t10
            if np.isfinite(pivot_now) and pivot_now<active_ceiling:
                active_ceiling=pivot_now; ratchets+=1
            floor_active=True
            continue

        if floor_active and np.isfinite(pivot_now) and pivot_now<active_ceiling:
            old=active_ceiling
            active_ceiling=pivot_now; ratchets+=1
            assert active_ceiling<=old+EPS

    if reason is None:
        op=block_end_open(x5,end)
        if op is None:
            reason='CENSORED'
        else:
            exit_ts=end; exit_px=op; reason='TIME_EXIT_BLOCK_END'; ceiling_kind='NONE'

    if reason=='CENSORED':
        exit_ext=np.nan; hold=np.nan
    else:
        exit_ext=float((L-float(exit_px))/R4)
        hold=float((pd.Timestamp(exit_ts)-touch_ts)/pd.Timedelta(minutes=1))

    aq=fast_slice(x5,touch_ts,end)
    peak_ext=float((L-float(aq.low.min()))/R4) if len(aq) else np.nan
    giveback=float(peak_ext-exit_ext) if np.isfinite(exit_ext) and np.isfinite(peak_ext) else np.nan
    capture=float(max(0.0,exit_ext)/max(0.0,peak_ext)) if np.isfinite(exit_ext) and peak_ext>0 else np.nan
    preserved=bool(np.isfinite(exit_ext) and exit_ext>=.10-EPS)

    return {
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'rebreak_complete_ts':start,
        'H':H,'L':L,'R4':R4,'T10':t10,'t10_touch_ts':touch_ts,
        't10_touch_close':touch_close,'activation_close_above_t10':activation_close_above,
        'final_active_ceiling':active_ceiling,'ratchets':int(ratchets),
        'exit_ts':exit_ts,'exit_px':exit_px,'exit_reason':reason,'ceiling_kind':ceiling_kind,
        'realized_exit_ext_r4':exit_ext,'fixed_t10_ext_r4':.10,
        'delta_vs_fixed_r4':exit_ext-.10 if np.isfinite(exit_ext) else np.nan,
        'peak_down_ext_r4':peak_ext,'giveback_r4':giveback,'capture_ratio':capture,
        't10_preserved':preserved,'minutes_t10_to_exit':hold,
    }


def synthetic_tests():
    idx=pd.date_range('2026-01-01 00:00',periods=8,freq='5min',tz='UTC')
    def df(rows): return pd.DataFrame(rows,index=idx[:len(rows)])
    x=df([
        {'open':89.8,'high':90.0,'low':88.8,'close':89.2},
        {'open':88.9,'high':89.2,'low':88.5,'close':88.8},
        {'open':88.8,'high':88.9,'low':88.0,'close':88.2},
    ])
    assert float(x.iloc[0].low)<=89.0 and float(x.iloc[1].high)>=89.0
    h=np.array([88.8,88.5,88.7])
    assert not bool(h[1]>h[0])
    h=np.array([88.0,88.7,88.2])
    assert bool(h[1]>h[0] and h[1]>h[2])


def metrics(src,detail):
    n=len(src); reach=int(src.hit_0p1.sum()); g=detail.copy(); nr=len(g)
    valid=g[g.exit_reason!='CENSORED'].copy(); nv=len(valid)
    return {'eligible_n':int(n),'t10_reach_n':reach,'t10_reach_rate':reach/n if n else np.nan,
         'hybrid_valid_n':nv,'censored_n':nr-nv,
         't10_ceiling_exits':int(((valid.exit_reason=='CEILING_STOP')&(valid.ceiling_kind=='T10')).sum()),
         'structural_ceiling_exits':int(((valid.exit_reason=='CEILING_STOP')&(valid.ceiling_kind=='STRUCTURAL')).sum()),
         'open_gap_exits':int((valid.exit_reason=='CEILING_OPEN_EXIT').sum()),
         'time_exits':int((valid.exit_reason=='TIME_EXIT_BLOCK_END').sum()),
         'preservation_rate':float(valid.t10_preserved.mean()) if nv else np.nan,
         'mean_exit_ext':float(valid.realized_exit_ext_r4.mean()) if nv else np.nan,
         'median_exit_ext':float(valid.realized_exit_ext_r4.median()) if nv else np.nan,
         'mean_delta_fixed':float(valid.delta_vs_fixed_r4.mean()) if nv else np.nan,
         'median_delta_fixed':float(valid.delta_vs_fixed_r4.median()) if nv else np.nan,
         'median_peak_ext':float(valid.peak_down_ext_r4.median()) if nv else np.nan,
         'median_capture':float(valid.capture_ratio.median()) if nv else np.nan,
         'median_giveback':float(valid.giveback_r4.median()) if nv else np.nan,
         'median_ratchets':float(valid.ratchets.median()) if nv else np.nan,
         'median_hold_min':float(valid.minutes_t10_to_exit.median()) if nv else np.nan,
         'activation_close_above_rate':float(valid.activation_close_above_t10.mean()) if nv else np.nan}


def summarize(src,d):
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**metrics(src[src.partition==p],d[d.partition==p])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**metrics(src[src.partition.isin(OOS)],d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(src,d)})
    for cb in CLOCKS: rows.append({'scope':'CLOCK','name':cb,**metrics(src[src.clock_block==cb],d[d.clock_block==cb])})
    return pd.DataFrame(rows)


def getrow(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]; assert len(z)==1; return z.iloc[0]
def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
def num(x): return '-' if pd.isna(x) else f'{float(x):.2f}'


def main():
    synthetic_tests()
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    reach=src[src.hit_0p1].copy()
    d=pd.DataFrame([simulate_reacher(x5,r) for r in reach.itertuples(index=False)])
    assert len(d)==366
    for p,n in {'external':96,'development':172,'reference_validation':98}.items(): assert len(d[d.partition==p])==n
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(src,d); s.to_csv(OUT_SUM,index=False)

    ext=getrow(s,'PARTITION','external'); dev=getrow(s,'PARTITION','development'); val=getrow(s,'PARTITION','reference_validation'); major=getrow(s,'POOL','POOLED_MAJOR')
    sample=bool(dev.t10_reach_n>=80 and ext.t10_reach_n>=60 and val.t10_reach_n>=60)
    med=all(float(r.median_exit_ext)>=.10-EPS for r in (ext,dev,val))
    mean=all(float(r.mean_exit_ext)>.10 for r in (ext,dev,val))
    preserve=all(float(r.preservation_rate)>=.80 for r in (ext,dev,val))
    pooled=bool(float(major.mean_exit_ext)>.10)
    verdict='B27CJ_T10_HYBRID_SUPPORTED' if sample and med and mean and preserve and pooled else 'B27CJ_T10_HYBRID_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CJ — BTC 24H Post-Rebreak T10 Profit-Lock Hybrid — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** B27CI eligible identity reproduced: external 147 / development 233 / validation 133 / pooled OOS 280 / pooled major 513; exact T10 reaches external 96 / development 172 / validation 98 / pooled major 366.','',
           'TP-management anatomy only. Trading WR/PF/PnL/expectancy/SL are **N/A**. T10 is frozen; no alternate milestone or pivot width was searched.','',
           '## Fixed T10 vs hybrid — major partitions','',
           '| Scope | Eligible | T10 reach | Hybrid valid | Preserve >=T10 | Mean exit ext | Median exit ext | Mean delta vs fixed | Median peak | Median capture | Median giveback | Median ratchets | Median hold |',
           '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {int(r.eligible_n)} | {int(r.t10_reach_n)} ({pct(r.t10_reach_rate)}) | {int(r.hybrid_valid_n)} | {pct(r.preservation_rate)} | {pct(r.mean_exit_ext)} | {pct(r.median_exit_ext)} | {pct(r.mean_delta_fixed)} | {pct(r.median_peak_ext)} | {pct(r.median_capture)} | {pct(r.median_giveback)} | {num(r.median_ratchets)} | {num(r.median_hold_min)}m |')
    lines += ['', '## Hybrid exit anatomy — major partitions','',
              '| Scope | T10 ceiling | Structural ceiling | Open/gap | Time | Touch-bar close > T10 |','|---|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=getrow(s,scope,name)
        lines.append(f'| {name} | {int(r.t10_ceiling_exits)} | {int(r.structural_ceiling_exits)} | {int(r.open_gap_exits)} | {int(r.time_exits)} | {pct(r.activation_close_above_rate)} |')
    lines += ['', '## Six-clock diagnostics — pooled major','',
              '| UTC block | Eligible | T10 reach | Preserve | Mean exit ext | Median exit ext | Mean delta | Median peak | Median hold |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=getrow(s,'CLOCK',cb)
        lines.append(f'| {cb} | {int(r.eligible_n)} | {int(r.t10_reach_n)} ({pct(r.t10_reach_rate)}) | {pct(r.preservation_rate)} | {pct(r.mean_exit_ext)} | {pct(r.median_exit_ext)} | {pct(r.mean_delta_fixed)} | {pct(r.median_peak_ext)} | {num(r.median_hold_min)}m |')
    lines += ['', '## Frozen gate','',
              f'- sample gate: **{"PASS" if sample else "FAIL"}**',
              f'- median hybrid exit >= T10 in every major partition: **{"PASS" if med else "FAIL"}**',
              f'- mean hybrid exit > fixed T10 in every major partition: **{"PASS" if mean else "FAIL"}**',
              f'- T10 preservation >=80% in every major partition: **{"PASS" if preserve else "FAIL"}**',
              f'- pooled-major mean extension > fixed T10: **{"PASS" if pooled else "FAIL"}**','',
              f'**Frozen verdict: `{verdict}`.**','',
              'This verdict concerns TP management only. No SL/economic inference is authorized by B27CJ. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__': main()
