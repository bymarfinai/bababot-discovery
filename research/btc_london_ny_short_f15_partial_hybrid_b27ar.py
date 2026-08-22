#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_f15_extension_econ_b27an as b27an

ROOT = Path(__file__).resolve().parent.parent
B27AN_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_EXTENSION_ECON_B27AN_Summary.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_PARTIAL_HYBRID_B27AR_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_PARTIAL_HYBRID_B27AR_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_PARTIAL_HYBRID_B27AR_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_PARTIAL_HYBRID_B27AR_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
MILESTONES = {'E05':0.05,'E10':0.10,'E15':0.15,'E20':0.20}
ENTRY_F = 0.15
STOP_F = 0.65
NOTIONAL = 500.0
LEG_NOTIONAL = 250.0
FEE = 0.40
EPS = 1e-12


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def time_exit(x5: pd.DataFrame, end: pd.Timestamp):
    p = int(x5.index.searchsorted(end, side='left'))
    if p >= len(x5) or x5.index[p] != end:
        raise AssertionError('missing exact session-end open')
    return end, float(x5.iloc[p].open)


def simulate(x5: pd.DataFrame, r: pd.Series, name: str, ext: float) -> dict:
    H=float(r.H); L=float(r.L); R=H-L
    entry=float(r.entry_px); start=pd.Timestamp(r.fill_bar_start); end=pd.Timestamp(r.session_end)
    f65=L+STOP_F*R; milestone=L-ext*R
    assert R>0
    assert abs(entry-(L+ENTRY_F*R)) < 1e-9*max(1.0,abs(entry))
    assert abs(milestone-(L-ext*R)) < 1e-9*max(1.0,abs(milestone))
    assert entry < f65 < H and milestone < L < entry

    q=b27an.b27ad.fast_slice(x5,start,end)
    if q.empty or q.index[0]!=start:
        raise AssertionError('missing entry slice')
    highs=q.high.astype(float).to_numpy()

    activated=False; activation_bar=pd.NaT
    ceiling=np.nan; ratchets=0
    runner_exit_ts=pd.NaT; runner_exit_px=np.nan; runner_reason=None
    whole_exit_ts=pd.NaT; whole_exit_px=np.nan; whole_reason=None
    partial_gross=0.0; runner_gross=0.0

    for i,(ts,b) in enumerate(q.iterrows()):
        op=float(b.open); hi=float(b.high); lo=float(b.low); cl=float(b.close)
        if not activated:
            # Intrabar milestone precedes the completed-close invalidation on this bar.
            if lo <= milestone:
                activated=True; activation_bar=ts
                partial_gross=(entry-milestone)/entry*LEG_NOTIONAL
                ceiling=milestone
                # Pivot centered on i-1 becomes known at this activation bar close
                # and can affect only the NEXT bar.
                if i>=2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
                    p=float(highs[i-1])
                    if p < ceiling:
                        ceiling=p; ratchets+=1
                continue
            if cl > f65:
                whole_exit_ts=ts+BAR5; whole_exit_px=cl; whole_reason='PRE_MILESTONE_CLOSE_INVALIDATION_F65'
                break
            continue

        # Existing ceiling was known before this bar opened.
        if op >= ceiling:
            runner_exit_ts=ts; runner_exit_px=op; runner_reason='RUNNER_OPEN_GAP_AT_OR_ABOVE_CEILING'
            break
        if hi >= ceiling:
            runner_exit_ts=ts; runner_exit_px=ceiling; runner_reason='RUNNER_PROFIT_CEILING_HIT'
            break
        # Newly confirmed pivot is effective only next bar.
        if i>=2 and highs[i-1] > highs[i-2] and highs[i-1] > highs[i]:
            p=float(highs[i-1])
            if p < ceiling:
                old=ceiling; ceiling=p; ratchets+=1
                if ceiling > old + EPS:
                    raise AssertionError('short ceiling rose')

    if not activated and whole_reason is None:
        whole_exit_ts,whole_exit_px=time_exit(x5,end)
        whole_reason='WHOLE_TIME_EXIT_SESSION_END'

    if activated and runner_reason is None:
        runner_exit_ts,runner_exit_px=time_exit(x5,end)
        runner_reason='RUNNER_TIME_EXIT_SESSION_END'

    if activated:
        runner_gross=(entry-float(runner_exit_px))/entry*LEG_NOTIONAL
        net=partial_gross+runner_gross-FEE
        final_exit_ts=runner_exit_ts
    else:
        net=(entry-float(whole_exit_px))/entry*NOTIONAL-FEE
        final_exit_ts=whole_exit_ts

    trough=np.nan; trough_ext=np.nan; runner_exit_ext=np.nan; capture=np.nan; giveback=np.nan
    if activated:
        a=b27an.b27ad.fast_slice(x5,pd.Timestamp(activation_bar),end)
        if len(a):
            trough=float(a.low.min()); trough_ext=(L-trough)/R
        runner_exit_ext=(L-float(runner_exit_px))/R
        denom=max(0.0,L-float(trough)) if np.isfinite(trough) else 0.0
        if denom>0:
            capture=max(0.0,L-float(runner_exit_px))/denom
        if np.isfinite(trough_ext):
            giveback=trough_ext-runner_exit_ext

    return {
        'milestone':name,'milestone_ext':ext,'partition':r.partition,'date_utc':r.date_utc,
        'signal_ts':r.signal_ts,'entry_start':start,'entry_px':entry,'H':H,'L':L,'range':R,
        'F65':f65,'milestone_px':milestone,'session_end':end,
        'activated':activated,'activation_bar_start':activation_bar,
        'partial_gross_usd':partial_gross,'runner_gross_usd':runner_gross,
        'runner_exit_ts':runner_exit_ts,'runner_exit_px':runner_exit_px,'runner_reason':runner_reason,
        'whole_exit_ts':whole_exit_ts,'whole_exit_px':whole_exit_px,'whole_reason':whole_reason,
        'net_pnl_usd':net,'win':bool(net>0),'final_exit_ts':final_exit_ts,
        'ratchets':ratchets,'trough_extension_r':trough_ext,'runner_exit_extension_r':runner_exit_ext,
        'capture_ratio':capture,'giveback_r':giveback,
    }


def synthetic_tests():
    H,L=100.0,90.0; R=10.0; entry=91.5
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    x=pd.DataFrame([
        {'open':91.5,'high':92.0,'low':91.0,'close':91.4},
        {'open':91.4,'high':91.8,'low':88.8,'close':96.0}, # E10 touched before same-bar F65 close
        {'open':89.0,'high':89.4,'low':87.5,'close':88.0},
        {'open':88.0,'high':88.5,'low':87.0,'close':87.5},
        {'open':87.5,'high':89.1,'low':87.2,'close':88.5},
        {'open':88.5,'high':88.8,'low':87.0,'close':87.5},
        {'open':87.5,'high':87.8,'low':87.0,'close':87.4},
    ],index=idx)
    r=pd.Series({'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
                 'fill_bar_start':idx[0],'entry_px':entry,'H':H,'L':L,'range':R,
                 'session_end':idx[-1]})
    z=simulate(x,r,'E10',.10)
    assert z['activated']
    assert abs(z['partial_gross_usd']-((entry-89.0)/entry*250.0))<1e-12
    assert z['whole_reason'] is None
    assert z['runner_reason'] is not None


def summarize(tr: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for m in MILESTONES:
        for part in PARTS:
            g=tr[(tr.milestone==m)&(tr.partition==part)].copy()
            a=g[g.activated.astype(bool)]
            rows.append({
                'milestone':m,'partition':part,'n':len(g),
                'activation_rate':float(g.activated.mean()) if len(g) else np.nan,
                'wr':float((g.net_pnl_usd>0).mean()) if len(g) else np.nan,
                'pf':pf(g.net_pnl_usd),'expectancy':float(g.net_pnl_usd.mean()) if len(g) else np.nan,
                'total_pnl':float(g.net_pnl_usd.sum()) if len(g) else np.nan,
                'partial_gross_total':float(g.partial_gross_usd.sum()) if len(g) else np.nan,
                'runner_gross_total':float(g.runner_gross_usd.sum()) if len(g) else np.nan,
                'ceiling_hits':int((g.runner_reason=='RUNNER_PROFIT_CEILING_HIT').sum()),
                'gap_exits':int((g.runner_reason=='RUNNER_OPEN_GAP_AT_OR_ABOVE_CEILING').sum()),
                'runner_time_exits':int((g.runner_reason=='RUNNER_TIME_EXIT_SESSION_END').sum()),
                'pre_invalidations':int((g.whole_reason=='PRE_MILESTONE_CLOSE_INVALIDATION_F65').sum()),
                'whole_time_exits':int((g.whole_reason=='WHOLE_TIME_EXIT_SESSION_END').sum()),
                'median_ratchets':float(a.ratchets.median()) if len(a) else np.nan,
                'median_capture':float(a.capture_ratio.median()) if len(a) else np.nan,
                'median_giveback_r':float(a.giveback_r.median()) if len(a) else np.nan,
            })
        g=tr[(tr.milestone==m)&(tr.partition.isin(MAJOR))].copy(); a=g[g.activated.astype(bool)]
        rows.append({
            'milestone':m,'partition':'POOLED_MAJOR','n':len(g),
            'activation_rate':float(g.activated.mean()),'wr':float((g.net_pnl_usd>0).mean()),
            'pf':pf(g.net_pnl_usd),'expectancy':float(g.net_pnl_usd.mean()),'total_pnl':float(g.net_pnl_usd.sum()),
            'partial_gross_total':float(g.partial_gross_usd.sum()),'runner_gross_total':float(g.runner_gross_usd.sum()),
            'ceiling_hits':int((g.runner_reason=='RUNNER_PROFIT_CEILING_HIT').sum()),
            'gap_exits':int((g.runner_reason=='RUNNER_OPEN_GAP_AT_OR_ABOVE_CEILING').sum()),
            'runner_time_exits':int((g.runner_reason=='RUNNER_TIME_EXIT_SESSION_END').sum()),
            'pre_invalidations':int((g.whole_reason=='PRE_MILESTONE_CLOSE_INVALIDATION_F65').sum()),
            'whole_time_exits':int((g.whole_reason=='WHOLE_TIME_EXIT_SESSION_END').sum()),
            'median_ratchets':float(a.ratchets.median()) if len(a) else np.nan,
            'median_capture':float(a.capture_ratio.median()) if len(a) else np.nan,
            'median_giveback_r':float(a.giveback_r.median()) if len(a) else np.nan,
        })
    return pd.DataFrame(rows)


def main():
    synthetic_tests()
    x5,coverage=b27an.b27ad.b21.load5(); assert abs(float(coverage)-1.0)<1e-12
    f=b27an.reconstruct_f15(x5)
    expected={'external':50,'development':79,'reference_validation':34,'august':1}
    assert f.groupby('partition').size().to_dict()==expected

    # Reproduce frozen B27AN E20/D50 baseline before interpreting this experiment.
    bs=pd.read_csv(B27AN_SUM)
    bg=bs[(bs.target_name=='E20')&(bs.stop_name=='D50')&(bs.partition.isin(MAJOR))]
    fixed_total=float(bg.total_pnl.sum())
    assert abs(fixed_total-(-11.665)) < 0.01, fixed_total

    rows=[]
    for _,r in f.iterrows():
        for name,ext in MILESTONES.items():
            rows.append(simulate(x5,r,name,ext))
    tr=pd.DataFrame(rows)
    assert len(tr)==len(f)*len(MILESTONES)
    # Fee is once per combined trade; recheck algebra for activated rows.
    for r in tr.itertuples(index=False):
        if bool(r.activated):
            assert abs(float(r.net_pnl_usd)-(float(r.partial_gross_usd)+float(r.runner_gross_usd)-FEE))<1e-10
            assert pd.Timestamp(r.runner_exit_ts) >= pd.Timestamp(r.activation_bar_start)+BAR5
        if int(r.ratchets)>0:
            assert bool(r.activated)

    sm=summarize(tr)
    eligible=[]
    for m in MILESTONES:
        ok=True
        for p in MAJOR:
            r=sm[(sm.milestone==m)&(sm.partition==p)].iloc[0]
            ok = ok and float(r.expectancy)>=0 and float(r.pf)>=1.0
        if ok:
            pooled=sm[(sm.milestone==m)&(sm.partition=='POOLED_MAJOR')].iloc[0]
            eligible.append((m,float(pooled.total_pnl)))
    selected=max(eligible,key=lambda z:z[1])[0] if eligible else None

    tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False)
    status='B27AR_SELECTED_'+selected if selected else 'B27AR_NO_ELIGIBLE_MILESTONE'
    OUT_STATUS.write_text(status+'\n')

    def pct(x): return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    md=['# B27AR — BTC London->NY SHORT BLIND_F15 50/50 Partial-TP + Hybrid Runner — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AK F15 identities and B27AN fixed baseline reproduced before partial-hybrid interpretation.','',
        f'Frozen B27AN E20/D50 pooled-major benchmark: **${fixed_total:+.3f}**. B27AQ full-position E20 profit-lock benchmark: **$-15.058**.','',
        '| Milestone | Partition | N | Activation | WR | PF | Exp/trade $ | Total $ | Partial gross $ | Runner gross $ | Ceiling | Gap | Runner time | Pre-invalid | Med ratchets | Med capture | Med giveback |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for m in MILESTONES:
        for p in (*PARTS,'POOLED_MAJOR'):
            r=sm[(sm.milestone==m)&(sm.partition==p)].iloc[0]
            md.append(f'| {m} | {p} | {int(r.n)} | {pct(r.activation_rate)} | {pct(r.wr)} | {num(r.pf)} | {num(r.expectancy)} | {num(r.total_pnl)} | {num(r.partial_gross_total)} | {num(r.runner_gross_total)} | {int(r.ceiling_hits)} | {int(r.gap_exits)} | {int(r.runner_time_exits)} | {int(r.pre_invalidations)} | {num(r.median_ratchets)} | {pct(r.median_capture)} | {num(r.median_giveback_r)} |')
    md += ['','## Frozen selection','',
           'Eligibility requires expectancy >=0 and PF>=1.0 in EACH external/development/reference_validation partition.','',
           '**Selected milestone: '+(selected if selected else 'NONE')+'.**','',
           'No split ratio, stop, entry, regime, confirmation, or intermediate milestone was searched.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
