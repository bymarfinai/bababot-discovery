#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Detail.csv'
OUT_SUM = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Summary.csv'
OUT_SEL = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_POST_REBREAK_TP_FRONTIER_B27CI_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
LEVELS = (0.025,0.05,0.075,0.10,0.15,0.20,0.25,0.35,0.50)


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
    for c in ('obs_start','obs_end','terminal_ts'):
        d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    d['eligible']=as_bool(d['eligible'])
    q=d[d.partition.isin(MAJOR)&d.eligible&d.terminal_type.eq('REBREAK_LOW')].copy()
    exp={'external':149,'development':237,'reference_validation':133}
    assert len(q)==519, len(q)
    for p,n in exp.items(): assert len(q[q.partition==p])==n,(p,len(q[q.partition==p]),n)
    assert len(q[q.partition.isin(OOS)])==282
    assert q.terminal_ts.notna().all()
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_one(x5,r):
    start=pd.Timestamp(r.terminal_ts)
    end=pd.Timestamp(r.obs_end)
    L=float(r.L); H=float(r.H); R4=float(r.R4)
    assert R4>0
    base={'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
          'obs_start':pd.Timestamp(r.obs_start),'obs_end':end,'rebreak_complete_ts':start,
          'H':H,'L':L,'R4':R4}
    if start>=end:
        out={**base,'followthrough_eligible':False,'terminal_type':'NO_FOLLOWTHROUGH_WINDOW',
             'continuation_terminal_ts':pd.NaT,'max_down_ext_r4':np.nan,'minutes_to_reclaim':np.nan}
        for f in LEVELS:
            tag=str(f).replace('.','p')
            out[f'hit_{tag}']=np.nan; out[f'min_{tag}']=np.nan
        return out

    q=fast_slice(x5,start,end)
    assert len(q)>=1 and q.index[0]==start
    reclaim_idx=None
    for i,b in enumerate(q.itertuples()):
        if float(b.close)>L:
            reclaim_idx=i; break
    if reclaim_idx is None:
        z=q; terminal_type='BLOCK_END'; terminal_ts=end; mins_reclaim=np.nan
    else:
        z=q.iloc[:reclaim_idx+1]
        terminal_type='RECLAIM_ABOVE_L'
        terminal_ts=q.index[reclaim_idx]+BAR5
        mins_reclaim=float((terminal_ts-start)/pd.Timedelta(minutes=1))

    min_low=float(z.low.min())
    max_down=max(0.0,(L-min_low)/R4)
    out={**base,'followthrough_eligible':True,'terminal_type':terminal_type,
         'continuation_terminal_ts':terminal_ts,'max_down_ext_r4':max_down,
         'minutes_to_reclaim':mins_reclaim}
    for f in LEVELS:
        tag=str(f).replace('.','p')
        target=L-f*R4
        hits=z.index[z.low.astype(float)<=target]
        hit=len(hits)>0
        out[f'hit_{tag}']=hit
        out[f'min_{tag}']=float((hits[0]-start)/pd.Timedelta(minutes=1)) if hit else np.nan
    return out


def metrics(g):
    e=g[g.followthrough_eligible].copy(); n=len(g); ne=len(e)
    out={'source_n':int(n),'eligible_n':int(ne),'no_window_n':int(n-ne),
         'max_down_p25':float(e.max_down_ext_r4.quantile(.25)) if ne else np.nan,
         'max_down_p50':float(e.max_down_ext_r4.quantile(.50)) if ne else np.nan,
         'max_down_p75':float(e.max_down_ext_r4.quantile(.75)) if ne else np.nan,
         'max_down_p90':float(e.max_down_ext_r4.quantile(.90)) if ne else np.nan,
         'reclaim_rate':float((e.terminal_type=='RECLAIM_ABOVE_L').mean()) if ne else np.nan}
    for f in LEVELS:
        tag=str(f).replace('.','p'); h=f'hit_{tag}'; m=f'min_{tag}'
        hit=e[h].astype(bool) if ne else pd.Series(dtype=bool)
        out[f'hit_rate_{tag}']=float(hit.mean()) if ne else np.nan
        out[f'hit_n_{tag}']=int(hit.sum()) if ne else 0
        out[f'median_min_{tag}']=float(e.loc[hit,m].median()) if ne and hit.any() else np.nan
    return out


def summarize(d):
    rows=[]
    for p in MAJOR: rows.append({'scope':'PARTITION','name':p,**metrics(d[d.partition==p])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(d)})
    for cb in CLOCKS: rows.append({'scope':'CLOCK','name':cb,**metrics(d[d.clock_block==cb])})
    return pd.DataFrame(rows)


def row(s,scope,name):
    z=s[(s.scope==scope)&(s.name==name)]; assert len(z)==1; return z.iloc[0]

def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v): return '-' if pd.isna(v) else f'{float(v):.1f}'
def lab(f):
    x=100*f
    return f'T{int(x):02d}' if float(x).is_integer() else f'T{x:g}'


def main():
    src=load_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==519 and len(d[d.partition.isin(OOS)])==282
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)

    dev=row(s,'PARTITION','development')
    dev_rows=[]
    candidates=[]
    for f in LEVELS:
        tag=str(f).replace('.','p')
        rate=float(dev[f'hit_rate_{tag}']) if pd.notna(dev[f'hit_rate_{tag}']) else np.nan
        eligible=bool(int(dev.eligible_n)>=150 and pd.notna(rate) and rate>=.70)
        dev_rows.append({'target_fraction':f,'development_eligible_n':int(dev.eligible_n),'development_hit_rate':rate,'development_eligible':eligible})
        if eligible: candidates.append(f)
    selected=max(candidates) if candidates else None
    sel=pd.DataFrame(dev_rows); sel['selected']=False; sel['oos_supported']=False
    oos_supported=False
    if selected is not None:
        tag=str(selected).replace('.','p')
        ext=row(s,'PARTITION','external'); val=row(s,'PARTITION','reference_validation'); oos=row(s,'POOL','POOLED_OOS')
        oos_supported=bool(float(ext[f'hit_rate_{tag}'])>=.65 and float(val[f'hit_rate_{tag}'])>=.65 and float(oos[f'hit_rate_{tag}'])>=.65)
        sel.loc[sel.target_fraction==selected,'selected']=True
        sel.loc[sel.target_fraction==selected,'oos_supported']=oos_supported
    sel.to_csv(OUT_SEL,index=False)

    if selected is None: verdict='B27CI_NO_70PCT_TP_CANDIDATE'
    elif oos_supported: verdict='B27CI_TP_FRONTIER_SUPPORTED'
    else: verdict='B27CI_TP_FRONTIER_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=['# B27CI — BTC 24H Post-Rebreak TP Frontier — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CE confirmed-rebreak cohort reproduced: external 149 / development 237 / validation 133 / pooled OOS 282 / pooled major 519. Anatomy only; trading WR/PF/PnL/expectancy/SL are N/A.','',
           'Evaluation begins on the next raw 5m bar after the Low rebreak is confirmed. A target may be touched before a later same-bar close reclaims L.','',
           '## TP hit frontier — major partitions','',
           '| Target below L | External | Development | Validation | Pooled OOS |',
           '|---|---:|---:|---:|---:|']
    ext=row(s,'PARTITION','external'); val=row(s,'PARTITION','reference_validation'); oos=row(s,'POOL','POOLED_OOS')
    for f in LEVELS:
        tag=str(f).replace('.','p')
        lines.append(f'| {lab(f)} = {100*f:g}% R4 | {pct(ext[f"hit_rate_{tag}"])} | {pct(dev[f"hit_rate_{tag}"])} | {pct(val[f"hit_rate_{tag}"])} | {pct(oos[f"hit_rate_{tag}"])} |')

    lines += ['', '## Maximum downside extension after confirmed rebreak','',
              '| Scope | Source / eligible | P25 | P50 | P75 | P90 | Fresh reclaim rate |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for scope,name in [('PARTITION','external'),('PARTITION','development'),('PARTITION','reference_validation'),('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        r=row(s,scope,name)
        lines.append(f'| {name} | {int(r.source_n)} / {int(r.eligible_n)} | {pct(r.max_down_p25)} | {pct(r.max_down_p50)} | {pct(r.max_down_p75)} | {pct(r.max_down_p90)} | {pct(r.reclaim_rate)} |')

    lines += ['', '## Six-clock frontier — pooled major','',
              '| UTC block | Eligible N | T05 | T10 | T15 | T20 | T25 | Median max extension |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=row(s,'CLOCK',cb)
        vals=[]
        for f in (.05,.10,.15,.20,.25): vals.append(pct(r[f"hit_rate_{str(f).replace('.','p')}"]))
        lines.append(f'| {cb} | {int(r.eligible_n)} | {vals[0]} | {vals[1]} | {vals[2]} | {vals[3]} | {vals[4]} | {pct(r.max_down_p50)} |')

    lines += ['', '## Development selection','',
              '| Target | Dev eligible N | Dev hit | >=70% | Selected |',
              '|---|---:|---:|---|---|']
    for rr in sel.itertuples(index=False):
        lines.append(f'| {lab(rr.target_fraction)} | {int(rr.development_eligible_n)} | {pct(rr.development_hit_rate)} | {"YES" if rr.development_eligible else "NO"} | {"YES" if rr.selected else "NO"} |')
    if selected is None:
        lines += ['', 'No target met the frozen >=70% development frontier.']
    else:
        tag=str(selected).replace('.','p')
        lines += ['', f'Frozen structural TP candidate: **{lab(selected)} = L - {100*selected:g}% R4**.',
                  f'Untouched OOS support: **{"PASS" if oos_supported else "FAIL"}** (external {pct(ext[f"hit_rate_{tag}"])}, validation {pct(val[f"hit_rate_{tag}"])}, pooled OOS {pct(oos[f"hit_rate_{tag}"])}).']
    lines += ['', f'**Frozen verdict: `{verdict}`.**','',
              'This TP is a structural continuation target only, not a trading win rate or profit-optimal target. SL/economics require a separate preregistered test.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__': main()
