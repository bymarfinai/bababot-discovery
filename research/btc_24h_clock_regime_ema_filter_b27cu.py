#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import btc_mtf_bull_cascade_b21 as b21

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'BTC_24H_CLOCK_TP_DEPTH_B27CR_Detail.csv'
OUT_MD=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Result.md'
OUT_DETAIL=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Detail.csv'
OUT_CELLS=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Cells.csv'
OUT_MAP=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Map.csv'
OUT_SUM=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Summary.csv'
OUT_STATUS=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Status.txt'
OUT_AUDIT=ROOT/'BTC_24H_CLOCK_REGIME_EMA_FILTER_B27CU_Audit.txt'

MAJOR=('external','development','reference_validation')
CLOCKS=('00-04','04-08','08-12','12-16','16-20','20-00')
REGIMES=('BULL','BEAR','SIDEWAYS')
WIB={'00-04':'07-11','04-08':'11-15','08-12':'15-19','12-16':'19-23','16-20':'23-03','20-00':'03-07'}
TP_MAP={'00-04':.05,'04-08':.15,'08-12':.15,'12-16':.10,'16-20':.10,'20-00':.15}
GATES=('BASE','EMA50_DOWN','EMA20_50_DOWN')
BAR5=pd.Timedelta(minutes=5)
EPS=1e-12


def as_bool(s):
    if s.dtype==bool:return s.copy()
    return s.astype(str).str.lower().eq('true')


def load_selected_source():
    d=pd.read_csv(SRC)
    for c in ('obs_start','obs_end','reclaim_complete_ts','fill_ts','target_ts','high_failure_ts'):
        if c in d.columns:d[c]=pd.to_datetime(d[c],utc=True,errors='coerce')
    for c in ('filled','target_reached','high_failure','unresolved','rebreak_confirmed'):
        if c in d.columns:d[c]=as_bool(d[c])
    d=d[d.partition.isin(MAJOR)].copy()
    pieces=[]
    for cb,t in TP_MAP.items():
        z=d[d.clock_block.astype(str).eq(cb)&np.isclose(pd.to_numeric(d.target_fraction),t)].copy()
        pieces.append(z)
    q=pd.concat(pieces,ignore_index=True).sort_values(['partition','obs_start']).reset_index(drop=True)
    exp_src={'external':202,'development':333,'reference_validation':194}
    exp_fill={'external':183,'development':297,'reference_validation':173}
    assert len(q)==729,len(q)
    for p,n in exp_src.items(): assert len(q[q.partition.eq(p)])==n,(p,len(q[q.partition.eq(p)]),n)
    for p,n in exp_fill.items(): assert int(q[q.partition.eq(p)].filled.sum())==n,(p,int(q[q.partition.eq(p)].filled.sum()),n)
    assert int(q.filled.sum())==653
    assert set(q.clock_block.astype(str).unique())==set(CLOCKS)
    assert set(q.regime.astype(str).unique()).issubset(set(REGIMES))
    q['event_id']=np.arange(len(q),dtype=int)
    return q


def build_h1(x5):
    h=x5[['open','high','low','close']].resample('1h',label='left',closed='left').agg(
        open=('open','first'),high=('high','max'),low=('low','min'),close=('close','last'))
    n=x5['close'].resample('1h',label='left',closed='left').size().rename('n')
    h=h.join(n)
    h=h[h.n.eq(12)].copy()
    h['complete_ts']=h.index+pd.Timedelta(hours=1)
    h['ema20_1h']=h.close.astype(float).ewm(span=20,adjust=False).mean()
    h['ema50_1h']=h.close.astype(float).ewm(span=50,adjust=False).mean()
    h['ema50_lag3_1h']=h.ema50_1h.shift(3)
    return h


def attach_ema(q,x5,h1):
    left=q.sort_values('reclaim_complete_ts').copy()
    right=h1[['complete_ts','ema20_1h','ema50_1h','ema50_lag3_1h']].sort_values('complete_ts').copy()
    out=pd.merge_asof(left,right,left_on='reclaim_complete_ts',right_on='complete_ts',direction='backward',allow_exact_matches=True)
    out=out.sort_values('event_id').reset_index(drop=True)
    assert out.ema50_lag3_1h.notna().all()
    bar_ts=out.reclaim_complete_ts-BAR5
    reclaim=[]
    for ts in bar_ts:
        assert ts in x5.index,ts
        reclaim.append(float(x5.loc[ts,'close']))
    out['reclaim_close']=reclaim
    out['ema50_down']=(out.reclaim_close<out.ema50_1h)&(out.ema50_1h<out.ema50_lag3_1h)
    out['ema20_50_down']=out.ema50_down&(out.ema20_1h<out.ema50_1h)
    assert (out.complete_ts<=out.reclaim_complete_ts).all()
    return out


def gate_mask(df,gate):
    if gate=='BASE': return pd.Series(True,index=df.index)
    if gate=='EMA50_DOWN': return df.ema50_down.astype(bool)
    if gate=='EMA20_50_DOWN': return df.ema20_50_down.astype(bool)
    raise KeyError(gate)


def metrics(df,gate='BASE'):
    source_n=int(len(df)); m=gate_mask(df,gate); g=df[m].copy(); pass_n=int(len(g))
    z=g[g.filled].copy(); fills=int(len(z)); basefills=int(df.filled.sum())
    target=int(z.target_reached.sum()) if fills else 0
    high=int(z.high_failure.sum()) if fills else 0
    unresolved=int(z.unresolved.sum()) if fills else 0
    return {'source_n':source_n,'pass_n':pass_n,'pass_rate':pass_n/source_n if source_n else np.nan,
            'fills_n':fills,'fill_rate_pass':fills/pass_n if pass_n else np.nan,
            'retained_fills':fills/basefills if basefills else np.nan,
            'target_n':target,'target_rate_fill':target/fills if fills else np.nan,
            'target_yield_source':target/source_n if source_n else np.nan,
            'high_failure_n':high,'high_failure_rate_fill':high/fills if fills else np.nan,
            'unresolved_n':unresolved,'unresolved_rate_fill':unresolved/fills if fills else np.nan}


def candidate_rows(d):
    rows=[]
    for p in MAJOR:
        for cb in CLOCKS:
            for rg in REGIMES:
                cell=d[d.partition.eq(p)&d.clock_block.eq(cb)&d.regime.eq(rg)]
                for gate in GATES:
                    rows.append({'partition':p,'clock_block':cb,'wib':WIB[cb],'regime':rg,'gate':gate,**metrics(cell,gate)})
    return pd.DataFrame(rows)


def getrow(c,p,cb,rg,gate):
    z=c[c.partition.eq(p)&c.clock_block.eq(cb)&c.regime.eq(rg)&c.gate.eq(gate)]
    assert len(z)==1,(p,cb,rg,gate,len(z)); return z.iloc[0]


def qualifies(b,r):
    if int(b.fills_n)<10 or int(r.fills_n)<8:return False
    vals=(r.retained_fills,r.target_rate_fill,b.target_rate_fill,r.high_failure_rate_fill,b.high_failure_rate_fill)
    if any(pd.isna(v) for v in vals):return False
    return bool(float(r.retained_fills)>=.50-EPS and
                float(r.target_rate_fill)>=float(b.target_rate_fill)+.05-EPS and
                float(r.high_failure_rate_fill)<=float(b.high_failure_rate_fill)+EPS)


def select_map(c):
    rows=[]
    for cb in CLOCKS:
        for rg in REGIMES:
            b=getrow(c,'development',cb,rg,'BASE')
            eligible=[]
            for gate in ('EMA50_DOWN','EMA20_50_DOWN'):
                r=getrow(c,'development',cb,rg,gate)
                if qualifies(b,r):eligible.append((gate,r))
            if eligible:
                eligible.sort(key=lambda x:(-float(x[1].target_rate_fill),float(x[1].high_failure_rate_fill),-float(x[1].retained_fills),0 if x[0]=='EMA50_DOWN' else 1))
                sel=eligible[0][0]
            else:sel='BASE'
            dr=getrow(c,'development',cb,rg,sel)
            conf=[]
            for p in ('external','reference_validation'):
                bb=getrow(c,p,cb,rg,'BASE'); rr=getrow(c,p,cb,rg,sel)
                if sel=='BASE' or int(rr.fills_n)<5:
                    ok=False
                else:
                    vals=(rr.retained_fills,rr.target_rate_fill,bb.target_rate_fill,rr.high_failure_rate_fill,bb.high_failure_rate_fill)
                    ok=not any(pd.isna(v) for v in vals)
                    ok=bool(ok and float(rr.retained_fills)>=.40-EPS and
                            float(rr.target_rate_fill)>=float(bb.target_rate_fill)-EPS and
                            float(rr.high_failure_rate_fill)<=float(bb.high_failure_rate_fill)+EPS)
                conf.append(ok)
            rows.append({'clock_block':cb,'wib':WIB[cb],'regime':rg,'selected_gate':sel,
                         'dev_base_fills':int(b.fills_n),'dev_selected_fills':int(dr.fills_n),
                         'dev_base_target_fill':float(b.target_rate_fill) if pd.notna(b.target_rate_fill) else np.nan,
                         'dev_selected_target_fill':float(dr.target_rate_fill) if pd.notna(dr.target_rate_fill) else np.nan,
                         'dev_base_high_fail':float(b.high_failure_rate_fill) if pd.notna(b.high_failure_rate_fill) else np.nan,
                         'dev_selected_high_fail':float(dr.high_failure_rate_fill) if pd.notna(dr.high_failure_rate_fill) else np.nan,
                         'reused_confirmed':bool(sel!='BASE' and all(conf))})
    return pd.DataFrame(rows)


def apply_map(d,m):
    pieces=[]
    for rr in m.itertuples(index=False):
        cell=d[d.clock_block.eq(rr.clock_block)&d.regime.eq(rr.regime)].copy()
        cell['selected_gate']=rr.selected_gate
        cell['selected_pass']=gate_mask(cell,rr.selected_gate).to_numpy(bool)
        pieces.append(cell)
    q=pd.concat(pieces,ignore_index=True)
    assert len(q)==len(d)
    return q


def map_metrics(df):
    source_n=int(len(df)); g=df[df.selected_pass].copy(); pass_n=int(len(g)); z=g[g.filled].copy(); fills=int(len(z))
    target=int(z.target_reached.sum()) if fills else 0; high=int(z.high_failure.sum()) if fills else 0; un=int(z.unresolved.sum()) if fills else 0
    basefills=int(df.filled.sum())
    return {'source_n':source_n,'pass_n':pass_n,'pass_rate':pass_n/source_n if source_n else np.nan,
            'fills_n':fills,'retained_fills':fills/basefills if basefills else np.nan,
            'target_n':target,'target_rate_fill':target/fills if fills else np.nan,
            'target_yield_source':target/source_n if source_n else np.nan,
            'high_failure_n':high,'high_failure_rate_fill':high/fills if fills else np.nan,
            'unresolved_n':un,'unresolved_rate_fill':un/fills if fills else np.nan}


def pct(x):return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def main():
    src=load_selected_source(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    h1=build_h1(x5); assert len(h1)>1000
    d=attach_ema(src,x5,h1); d.to_csv(OUT_DETAIL,index=False)
    c=candidate_rows(d); c.to_csv(OUT_CELLS,index=False)
    m=select_map(c); m.to_csv(OUT_MAP,index=False)
    sm=apply_map(d,m)

    rows=[]
    groups=[('PARTITION_OR_POOL','external',sm[sm.partition.eq('external')]),
            ('PARTITION_OR_POOL','development',sm[sm.partition.eq('development')]),
            ('PARTITION_OR_POOL','reference_validation',sm[sm.partition.eq('reference_validation')]),
            ('PARTITION_OR_POOL','POOLED_MAJOR',sm)]
    groups += [('CLOCK',cb,sm[sm.clock_block.eq(cb)]) for cb in CLOCKS]
    groups += [('REGIME',rg,sm[sm.regime.eq(rg)]) for rg in REGIMES]
    for scope,name,z in groups:
        mm=map_metrics(z); bb=metrics(z,'BASE')
        rows.append({'scope':scope,'name':name,**{f'map_{k}':v for k,v in mm.items()},**{f'base_{k}':v for k,v in bb.items()}})
    s=pd.DataFrame(rows); s.to_csv(OUT_SUM,index=False)

    selected_non=int(m.selected_gate.ne('BASE').sum()); confirmed=int(m.reused_confirmed.sum())
    dev=s[(s.scope=='PARTITION_OR_POOL')&s.name.eq('development')].iloc[0]
    maj=s[(s.scope=='PARTITION_OR_POOL')&s.name.eq('POOLED_MAJOR')].iloc[0]
    gate=bool(selected_non>=4 and confirmed>=math.ceil(selected_non/2) and
              float(dev.map_target_rate_fill)>=float(dev.base_target_rate_fill)+.05-EPS and
              float(maj.map_target_rate_fill)>float(maj.base_target_rate_fill)+EPS and
              float(maj.map_retained_fills)>=.60-EPS and
              float(maj.map_high_failure_rate_fill)<=float(maj.base_high_failure_rate_fill)+EPS)
    verdict='B27CU_CLOCK_REGIME_EMA_REUSED_CANDIDATE' if gate else 'B27CU_CLOCK_REGIME_EMA_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')
    OUT_AUDIT.write_text(f'audit=PASS\nraw_rows={len(x5)}\ncoverage={float(cov)}\nsource_major={len(src)}\nfills_external=183\nfills_development=297\nfills_validation=173\nfills_major=653\nh1_complete_rows={len(h1)}\nema_gates=3\nclock_regime_cells=18\nuntouched_holdout=NONE\n')

    lines=['# B27CU — BTC 24H SHORT Clock × Regime EMA Filter Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CR selected-target source reproduced: 729 events; F05 fills external 183 / development 297 / validation 173 / pooled major 653.','',
           '**Anatomy only:** trading WR/PF/expectancy/PnL are **N/A**. EMA uses only completed 1H candles available at reclaim completion.','',
           'Frozen gates: BASE / EMA50_DOWN / EMA20_50_DOWN. Frozen clock TP map remains B27CR.','',
           '## 18 clock × regime cells — development selection','',
           '| WIB | Regime | BASE fills | BASE target/fill | EMA50 fills / target | EMA20<50 fills / target | Selected | Selected target/fill | High fail BASE→selected |',
           '|---|---|---:|---:|---:|---:|---|---:|---:|']
    for cb in CLOCKS:
        for rg in REGIMES:
            b=getrow(c,'development',cb,rg,'BASE'); e1=getrow(c,'development',cb,rg,'EMA50_DOWN'); e2=getrow(c,'development',cb,rg,'EMA20_50_DOWN')
            rr=m[m.clock_block.eq(cb)&m.regime.eq(rg)].iloc[0]
            lines.append(f'| {WIB[cb]} | {rg} | {int(b.fills_n)} | {pct(b.target_rate_fill)} | {int(e1.fills_n)} / {pct(e1.target_rate_fill)} | {int(e2.fills_n)} / {pct(e2.target_rate_fill)} | **{rr.selected_gate}** | {pct(rr.dev_selected_target_fill)} | {pct(rr.dev_base_high_fail)} → {pct(rr.dev_selected_high_fail)} |')

    lines += ['', '## Selected non-BASE cells — reused confirmation','',
              '| WIB | Regime | Gate | Dev target/fill | External BASE→gate | Validation BASE→gate | Reused confirmed |',
              '|---|---|---|---:|---:|---:|---|']
    non=m[m.selected_gate.ne('BASE')]
    if len(non)==0:lines.append('| - | - | none | - | - | - | - |')
    for rr in non.itertuples(index=False):
        eb=getrow(c,'external',rr.clock_block,rr.regime,'BASE'); er=getrow(c,'external',rr.clock_block,rr.regime,rr.selected_gate)
        vb=getrow(c,'reference_validation',rr.clock_block,rr.regime,'BASE'); vr=getrow(c,'reference_validation',rr.clock_block,rr.regime,rr.selected_gate)
        lines.append(f'| {rr.wib} | {rr.regime} | {rr.selected_gate} | {pct(rr.dev_selected_target_fill)} | {pct(eb.target_rate_fill)} → {pct(er.target_rate_fill)} | {pct(vb.target_rate_fill)} → {pct(vr.target_rate_fill)} | {"YES" if rr.reused_confirmed else "NO"} |')

    lines += ['', '## Selected-map aggregate anatomy','',
              '| Scope | BASE fills | Map fills | Retain | BASE target/fill | Map target/fill | BASE High fail | Map High fail |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name in ('external','development','reference_validation','POOLED_MAJOR'):
        r=s[(s.scope=='PARTITION_OR_POOL')&s.name.eq(name)].iloc[0]
        lines.append(f'| {name} | {int(r.base_fills_n)} | {int(r.map_fills_n)} | {pct(r.map_retained_fills)} | {pct(r.base_target_rate_fill)} | **{pct(r.map_target_rate_fill)}** | {pct(r.base_high_failure_rate_fill)} | {pct(r.map_high_failure_rate_fill)} |')

    lines += ['', '## Secondary regime aggregates','',
              '| Regime | BASE fills | Map fills | BASE target/fill | Map target/fill | BASE High fail | Map High fail |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for rg in REGIMES:
        r=s[(s.scope=='REGIME')&s.name.eq(rg)].iloc[0]
        lines.append(f'| {rg} | {int(r.base_fills_n)} | {int(r.map_fills_n)} | {pct(r.base_target_rate_fill)} | **{pct(r.map_target_rate_fill)}** | {pct(r.base_high_failure_rate_fill)} | {pct(r.map_high_failure_rate_fill)} |')
    lines += ['',f'Non-BASE EMA selected in **{selected_non}/18** cells; reused-confirmed **{confirmed}/{selected_non if selected_non else 0}**.','',
              f'**Frozen verdict: `{verdict}`.**','',
              'This is not trading WR. No SL/runner economics were optimized; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n'); print('\n'.join(lines))

if __name__=='__main__':main()
