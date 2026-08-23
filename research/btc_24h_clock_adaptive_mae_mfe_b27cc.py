#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / 'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Candidates.csv'
EV = ROOT / 'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Events.csv'
SEL = ROOT / 'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Selection.csv'
OUT_MD = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_MAE_MFE_B27CC_Result.md'
OUT_DETAIL = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_MAE_MFE_B27CC_Detail.csv'
OUT_SUM = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_MAE_MFE_B27CC_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_MAE_MFE_B27CC_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
FROZEN = {'00-04':.05,'04-08':.05,'08-12':.10,'12-16':.05,'16-20':.05,'20-00':.05}


def as_bool(s: pd.Series) -> pd.Series:
    return s if s.dtype == bool else s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_entries() -> pd.DataFrame:
    c = pd.read_csv(CAND)
    c['filled'] = as_bool(c.filled)
    c['eventual_low_break_after_fill'] = as_bool(c.eventual_low_break_after_fill)
    for col in ('obs_start','fill_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')
    s = pd.read_csv(SEL)
    got = {str(r.clock_block):float(r.selected_fraction) for r in s.itertuples(index=False)}
    assert got == FROZEN, (got,FROZEN)
    parts=[]
    for cb,f in FROZEN.items():
        parts.append(c[(c.clock_block==cb)&np.isclose(c.fraction.astype(float),f)])
    q = pd.concat(parts, ignore_index=True)
    q = q[q.partition.isin(MAJOR)&q.filled].copy()
    exp={'external':250,'development':380,'reference_validation':177}
    assert len(q)==807
    for p,n in exp.items():
        assert len(q[q.partition==p])==n

    e = pd.read_csv(EV)
    for col in ('obs_start','obs_end','break_ts'):
        e[col] = pd.to_datetime(e[col], utc=True, errors='coerce')
    keep=['partition','obs_start','obs_end','break_side','break_ts']
    e=e[keep].copy()
    assert not e.duplicated(['partition','obs_start']).any()
    q=q.merge(e,on=['partition','obs_start'],how='left',validate='many_to_one')
    assert q.obs_end.notna().all()
    assert q.fill_ts.notna().all()
    return q.sort_values(['partition','obs_start']).reset_index(drop=True)


def eval_one(x5: pd.DataFrame, r) -> dict:
    start=pd.Timestamp(r.obs_start); end=pd.Timestamp(r.obs_end); fill=pd.Timestamp(r.fill_ts)
    entry=float(r.price); H=float(r.H); L=float(r.L); R4=H-L; local_r=entry-L
    assert R4>0 and local_r>0 and start<=fill<end
    q=fast_slice(x5,start,end)
    assert len(q)==48 and q.index[0]==start and q.index[-1]==end-BAR5
    idx=int(q.index.searchsorted(fill,'left')); assert idx<len(q) and q.index[idx]==fill
    fb=q.iloc[idx]; assert float(fb.low)<=entry<=float(fb.high)
    winner=bool(r.eventual_low_break_after_fill)

    if winner:
        assert str(r.break_side)=='LOW' and pd.notna(r.break_ts)
        terminal_complete=pd.Timestamp(r.break_ts)
        terminal_type='LOW_BREAK'
    elif str(r.break_side)=='HIGH' and pd.notna(r.break_ts) and pd.Timestamp(r.break_ts)>fill:
        terminal_complete=pd.Timestamp(r.break_ts)
        terminal_type='HIGH_BREAK'
    else:
        terminal_complete=end
        terminal_type='BLOCK_END'
    assert fill < terminal_complete <= end

    causal_start=fill+BAR5
    z=fast_slice(x5,causal_start,terminal_complete)
    # If the fill is on the final 5m bar of the 4H block, there is no completed
    # post-fill bar. Primary causal MAE/MFE is undefined for that row; do not
    # fabricate a zero excursion. Fill-bar adverse span remains available.
    if len(z):
        max_hi=float(z.high.max()); min_lo=float(z.low.min())
        mae=max(0.0,max_hi-entry); mfe=max(0.0,entry-min_lo)
        mae_r4=mae/R4; mae_localr=mae/local_r
        mfe_r4=mfe/R4; mfe_localr=mfe/local_r
    else:
        mae=mfe=np.nan
        mae_r4=mae_localr=mfe_r4=mfe_localr=np.nan

    fb_adv=max(0.0,float(fb.high)-entry)
    return {
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':start,'obs_end':end,'fill_ts':fill,'entry_price':entry,'fraction':float(r.fraction),
        'H':H,'L':L,'R4':R4,'LOCAL_R':local_r,'structural_winner':winner,
        'terminal_type':terminal_type,'terminal_complete_ts':terminal_complete,
        'causal_bars':len(z),'terminal_minutes':float((terminal_complete-fill)/pd.Timedelta(minutes=1)),
        'fillbar_adv_px':fb_adv,'fillbar_adv_r4':fb_adv/R4,'fillbar_adv_localr':fb_adv/local_r,
        'mae_px':mae,'mae_r4':mae_r4,'mae_localr':mae_localr,
        'mfe_px':mfe,'mfe_r4':mfe_r4,'mfe_localr':mfe_localr,
    }


def qv(s: pd.Series,p:float)->float:
    s=pd.to_numeric(s,errors='coerce').dropna()
    return float(s.quantile(p)) if len(s) else np.nan


def metrics(g: pd.DataFrame)->dict:
    if len(g)==0:
        return {'n':0,'causal_n':0}
    valid=g[g.causal_bars.astype(int)>0].copy()
    return {
        'n':int(len(g)),
        'causal_n':int(len(valid)),
        'mae_r4_p50':qv(valid.mae_r4,.50),'mae_r4_p75':qv(valid.mae_r4,.75),'mae_r4_p90':qv(valid.mae_r4,.90),
        'mae_lr_p50':qv(valid.mae_localr,.50),'mae_lr_p75':qv(valid.mae_localr,.75),'mae_lr_p90':qv(valid.mae_localr,.90),
        'mfe_r4_p50':qv(valid.mfe_r4,.50),'mfe_r4_p75':qv(valid.mfe_r4,.75),'mfe_r4_p90':qv(valid.mfe_r4,.90),
        'mfe_lr_p50':qv(valid.mfe_localr,.50),'mfe_lr_p75':qv(valid.mfe_localr,.75),'mfe_lr_p90':qv(valid.mfe_localr,.90),
        'filladv_lr_p50':qv(g.fillbar_adv_localr,.50),'filladv_lr_p75':qv(g.fillbar_adv_localr,.75),'filladv_lr_p90':qv(g.fillbar_adv_localr,.90),
        'mae_gt1r':float((valid.mae_localr>1).mean()) if len(valid) else np.nan,
        'mae_gt2r':float((valid.mae_localr>2).mean()) if len(valid) else np.nan,
        'mae_gt3r':float((valid.mae_localr>3).mean()) if len(valid) else np.nan,
        'mae_gt4r':float((valid.mae_localr>4).mean()) if len(valid) else np.nan,
        'median_terminal_min':float(g.terminal_minutes.median()),
    }


def summarize(d:pd.DataFrame)->pd.DataFrame:
    rows=[]
    scopes=[]
    for p in MAJOR:
        scopes.append(('PARTITION',p,d[d.partition==p]))
    scopes += [('POOL','POOLED_OOS',d[d.partition.isin(OOS)]),('POOL','POOLED_MAJOR',d)]
    for cb in CLOCKS:
        scopes.append(('CLOCK_MAJOR',cb,d[d.clock_block==cb]))
        scopes.append(('CLOCK_OOS',cb,d[d.clock_block.eq(cb)&d.partition.isin(OOS)]))
    for scope,name,g in scopes:
        for lab,flag in [('WINNER_STRUCTURAL',True),('FAILURE_STRUCTURAL',False)]:
            rows.append({'scope':scope,'name':name,'outcome':lab,**metrics(g[g.structural_winner==flag])})
    return pd.DataFrame(rows)


def get(s,scope,name,outcome):
    z=s[(s.scope==scope)&(s.name==name)&(s.outcome==outcome)]
    assert len(z)==1
    return z.iloc[0]


def x(v): return '-' if pd.isna(v) else f'{float(v):.2f}'
def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    e=load_entries(); x5,cov=b21.load5(); assert len(x5)==698112 and abs(float(cov)-1)<1e-12
    d=pd.DataFrame([eval_one(x5,r) for r in e.itertuples(index=False)])
    assert len(d)==807 and int(d.partition.isin(OOS).sum())==427
    d.to_csv(OUT_DETAIL,index=False)
    s=summarize(d); s.to_csv(OUT_SUM,index=False)

    p75=[]; clocks_ok=True
    for cb in CLOCKS:
        r=get(s,'CLOCK_MAJOR',cb,'WINNER_STRUCTURAL')
        clocks_ok=clocks_ok and int(r.n)>=20 and int(r.causal_n)>0 and pd.notna(r.mae_lr_p75)
        p75.append(float(r.mae_lr_p75) if pd.notna(r.mae_lr_p75) else np.nan)
    informative=bool(clocks_ok and (max(p75)>2.0 or (max(p75)-min(p75))>=1.0))
    verdict='B27CC_CLOCK_EXCURSION_INFORMATIVE' if informative else 'B27CC_CLOCK_EXCURSION_NOT_INFORMATIVE'
    OUT_STATUS.write_text(verdict+'\n')

    zero_causal=int((d.causal_bars==0).sum())
    lines=['# B27CC — BTC 24H Clock-Adaptive Pre-Break SHORT MAE/MFE Anatomy — Result','',
           f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
           '**Audit status: PASS.** Exact B27CA adaptive filled-entry identity reproduced: external 250 / development 380 / validation 177. Anatomy only: trading WR/PF/PnL/expectancy are not applicable.','',
           'Primary excursions start on the **next 5m bar after the fill bar**. Fill-bar adverse span is reported separately because intrabar ordering is unknown.','',
           f'Rows with no completed post-fill 5m bar before the structural terminal: **{zero_causal}**. Their causal MAE/MFE is undefined and excluded from causal quantiles/proportions; fill-bar adverse remains reported.','',
           '## Pooled anatomy','',
           '| Scope | Outcome | N / causal N | MAE P50/P75/P90 (LOCAL_R) | MAE P75 (%R4) | MFE P50/P75/P90 (LOCAL_R) | >1R / >2R / >3R / >4R MAE | Fill-bar adverse P75 | Median terminal |',
           '|---|---|---:|---|---:|---|---|---:|---:|']
    for scope,name in [('POOL','POOLED_OOS'),('POOL','POOLED_MAJOR')]:
        for out in ('WINNER_STRUCTURAL','FAILURE_STRUCTURAL'):
            r=get(s,scope,name,out)
            lines.append(f'| {name} | {out} | {int(r.n)} / {int(r.causal_n)} | {x(r.mae_lr_p50)} / {x(r.mae_lr_p75)} / {x(r.mae_lr_p90)} | {pct(r.mae_r4_p75)} | {x(r.mfe_lr_p50)} / {x(r.mfe_lr_p75)} / {x(r.mfe_lr_p90)} | {pct(r.mae_gt1r)} / {pct(r.mae_gt2r)} / {pct(r.mae_gt3r)} / {pct(r.mae_gt4r)} | {x(r.filladv_lr_p75)}R | {x(r.median_terminal_min)}m |')

    lines += ['', '## Structural winners by clock — pooled major','',
              '| UTC block | Entry | N / causal N | MAE P50 | MAE P75 | MAE P90 | MAE P75 %R4 | MFE P75 | >2R MAE | >4R MAE |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=get(s,'CLOCK_MAJOR',cb,'WINNER_STRUCTURAL'); f=FROZEN[cb]
        lines.append(f'| {cb} | F{int(round(f*100)):02d} | {int(r.n)} / {int(r.causal_n)} | {x(r.mae_lr_p50)}R | {x(r.mae_lr_p75)}R | {x(r.mae_lr_p90)}R | {pct(r.mae_r4_p75)} | {x(r.mfe_lr_p75)}R | {pct(r.mae_gt2r)} | {pct(r.mae_gt4r)} |')

    lines += ['', '## Structural winners by clock — pooled OOS','',
              '| UTC block | N / causal N | MAE P75 | MAE P90 | MAE P75 %R4 | MFE P75 |',
              '|---|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        r=get(s,'CLOCK_OOS',cb,'WINNER_STRUCTURAL')
        lines.append(f'| {cb} | {int(r.n)} / {int(r.causal_n)} | {x(r.mae_lr_p75)}R | {x(r.mae_lr_p90)}R | {pct(r.mae_r4_p75)} | {x(r.mfe_lr_p75)}R |')

    lines += ['', f'**Frozen verdict: `{verdict}`.**','',
              'B27CC does not choose a stop. An informative verdict only permits a new preregistered risk-geometry test. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
