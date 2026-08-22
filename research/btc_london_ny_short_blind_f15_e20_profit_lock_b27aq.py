#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_london_ny_short_mirror_b27ad as b27ad
import btc_london_ny_short_f15_extension_econ_b27an as b27an

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_BLIND_F15_E20_PROFIT_LOCK_B27AQ_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_BLIND_F15_E20_PROFIT_LOCK_B27AQ_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_BLIND_F15_E20_PROFIT_LOCK_B27AQ_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_BLIND_F15_E20_PROFIT_LOCK_B27AQ_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
NOTIONAL = 500.0
FEE = 0.40
ENTRY_F = 0.15
STOP_F = 0.65
EXT = 0.20
EPS = 1e-12


def pf(vals):
    x=pd.to_numeric(pd.Series(vals),errors='coerce').dropna()
    pos=float(x[x>0].sum()); neg=float(-x[x<0].sum())
    if neg==0 and pos>0: return float('inf')
    return pos/neg if neg>0 else np.nan


def session_open(x5,end):
    p=int(x5.index.searchsorted(end,side='left'))
    if p>=len(x5) or x5.index[p]!=end: raise AssertionError('missing session-end open')
    return float(x5.iloc[p].open)


def hybrid(x5: pd.DataFrame, r: pd.Series) -> dict:
    H=float(r.H); L=float(r.L); R=H-L
    entry=float(r.entry_px); start=pd.Timestamp(r.fill_bar_start); end=pd.Timestamp(r.session_end)
    f65=L+STOP_F*R; e20=L-EXT*R
    assert abs(entry-(L+ENTRY_F*R))<1e-9*max(1.0,abs(entry))
    q=b27ad.fast_slice(x5,start,end)
    if q.empty or q.index[0]!=start: raise AssertionError('missing entry bar')
    highs=q.high.astype(float).to_numpy()

    reached=False; active=False; ceiling=np.nan; ratchets=0; e20_bar=pd.NaT
    exit_bar=pd.NaT; exit_ts=pd.NaT; exit_px=np.nan; reason=None

    for i,(ts,b) in enumerate(q.iterrows()):
        o=float(b.open); h=float(b.high); lo=float(b.low); c=float(b.close)

        if active:
            # resting ceiling known before this bar
            if o>=ceiling:
                exit_bar=ts; exit_ts=ts; exit_px=o; reason='PROFIT_CEILING_GAP_OPEN'; break
            if h>=ceiling:
                exit_bar=ts; exit_ts=ts; exit_px=ceiling; reason='PROFIT_CEILING_HIT'; break

        # strict 3-bar pivot high centered on i-1 becomes known at this close
        pivot=np.nan
        if i>=2 and highs[i-1]>highs[i-2] and highs[i-1]>highs[i]:
            pivot=float(highs[i-1])

        if not reached:
            # E20 intrabar touch happens before the bar close and therefore
            # takes precedence over a same-bar completed-close F65 invalidation.
            if i>0 and lo<=e20:
                reached=True; active=True; e20_bar=ts; ceiling=e20
                if np.isfinite(pivot) and pivot<ceiling:
                    ceiling=pivot; ratchets+=1
                continue
            if c>f65:
                exit_bar=ts; exit_ts=ts+BAR5; exit_px=c; reason='PRE_E20_CLOSE_INVALIDATION_F65'; break
        else:
            # any newly confirmed pivot can only ratchet ceiling downward,
            # effective from next bar because this bar has already survived.
            if np.isfinite(pivot) and pivot<ceiling:
                old=ceiling; ceiling=pivot; ratchets+=1
                assert ceiling<=old+EPS

    if reason is None:
        exit_bar=end; exit_ts=end; exit_px=session_open(x5,end); reason='TIME_EXIT_SESSION_END'

    gross=1.0-exit_px/entry
    net=gross*NOTIONAL-FEE
    hold=float((pd.Timestamp(exit_ts)-start)/pd.Timedelta(minutes=1))

    trough_ext=np.nan; exit_ext=np.nan; cap=np.nan; give=np.nan
    if reached:
        aq=b27ad.fast_slice(x5,pd.Timestamp(e20_bar),end)
        trough=float(aq.low.min()) if len(aq) else np.nan
        if np.isfinite(trough):
            trough_ext=(L-trough)/R
            exit_ext=(L-exit_px)/R
            denom=max(0.0,L-trough)
            cap=max(0.0,L-exit_px)/denom if denom>0 else np.nan
            give=trough_ext-exit_ext

    return {
        'partition':r.partition,'date_utc':r.date_utc,'signal_ts':r.signal_ts,
        'entry_start':start,'entry_px':entry,'H':H,'L':L,'range':R,
        'F65':f65,'E20_DOWN':e20,'session_end':end,
        'e20_reached':bool(reached),'e20_bar_start':e20_bar,
        'ratchets':int(ratchets),'final_ceiling':float(ceiling) if active else np.nan,
        'exit_bar_start':exit_bar,'exit_ts':exit_ts,'exit_px':float(exit_px),'exit_reason':reason,
        'net_pnl_usd':net,'win':bool(net>0),'hold_minutes':hold,
        'trough_extension_r':trough_ext,'realized_exit_extension_r':exit_ext,
        'capture_ratio':cap,'giveback_r':give,
    }


def summarize_rows(tr):
    rows=[]
    for part in PARTS:
        g=tr[tr.partition==part].copy()
        rows.append({'partition':part,'n':len(g),'wr':float((g.net_pnl_usd>0).mean()),
                     'pf':pf(g.net_pnl_usd),'exp':float(g.net_pnl_usd.mean()),
                     'total':float(g.net_pnl_usd.sum()),'e20_rate':float(g.e20_reached.mean()),
                     'median_hold':float(g.hold_minutes.median()),
                     'ceiling_hits':int((g.exit_reason=='PROFIT_CEILING_HIT').sum()),
                     'gap_exits':int((g.exit_reason=='PROFIT_CEILING_GAP_OPEN').sum()),
                     'time_exits':int((g.exit_reason=='TIME_EXIT_SESSION_END').sum()),
                     'median_ratchets':float(g.ratchets.median()),
                     'median_trough_ext':float(g.loc[g.e20_reached,'trough_extension_r'].median()) if g.e20_reached.any() else np.nan,
                     'median_exit_ext':float(g.loc[g.e20_reached,'realized_exit_extension_r'].median()) if g.e20_reached.any() else np.nan,
                     'median_capture':float(g.loc[g.e20_reached,'capture_ratio'].median()) if g.e20_reached.any() else np.nan,
                     'median_giveback':float(g.loc[g.e20_reached,'giveback_r'].median()) if g.e20_reached.any() else np.nan})
    g=tr[tr.partition.isin(MAJOR)].copy()
    rows.append({'partition':'POOLED_MAJOR','n':len(g),'wr':float((g.net_pnl_usd>0).mean()),
                 'pf':pf(g.net_pnl_usd),'exp':float(g.net_pnl_usd.mean()),
                 'total':float(g.net_pnl_usd.sum()),'e20_rate':float(g.e20_reached.mean()),
                 'median_hold':float(g.hold_minutes.median()),
                 'ceiling_hits':int((g.exit_reason=='PROFIT_CEILING_HIT').sum()),
                 'gap_exits':int((g.exit_reason=='PROFIT_CEILING_GAP_OPEN').sum()),
                 'time_exits':int((g.exit_reason=='TIME_EXIT_SESSION_END').sum()),
                 'median_ratchets':float(g.ratchets.median()),
                 'median_trough_ext':float(g.loc[g.e20_reached,'trough_extension_r'].median()) if g.e20_reached.any() else np.nan,
                 'median_exit_ext':float(g.loc[g.e20_reached,'realized_exit_extension_r'].median()) if g.e20_reached.any() else np.nan,
                 'median_capture':float(g.loc[g.e20_reached,'capture_ratio'].median()) if g.e20_reached.any() else np.nan,
                 'median_giveback':float(g.loc[g.e20_reached,'giveback_r'].median()) if g.e20_reached.any() else np.nan})
    return pd.DataFrame(rows)


def synthetic_tests():
    idx=pd.date_range('2026-01-05 14:00',periods=7,freq='5min',tz='UTC')
    # Fill bar cannot hit E20; second bar reaches E20 and closes above F65.
    # E20 must activate runner rather than be invalidated by same-bar close.
    x=pd.DataFrame([
      {'open':91.5,'high':92.0,'low':91.0,'close':91.6},
      {'open':91.6,'high':97.0,'low':87.8,'close':97.0},
      {'open':87.5,'high':87.8,'low':86.0,'close':86.5},
      {'open':86.5,'high':87.0,'low':85.5,'close':86.0},
      {'open':86.0,'high':88.2,'low':85.8,'close':87.5},
      {'open':87.5,'high':87.8,'low':86.5,'close':87.0},
      {'open':87.0,'high':87.2,'low':86.5,'close':86.8},
    ],index=idx)
    r=pd.Series({'partition':'x','date_utc':'2026-01-05','signal_ts':idx[0]-BAR5,
                 'fill_bar_start':idx[0],'entry_px':91.5,'H':100.0,'L':90.0,
                 'session_end':idx[6]})
    z=hybrid(x,r)
    assert z['e20_reached']
    assert z['exit_reason']!='PRE_E20_CLOSE_INVALIDATION_F65'
    assert z['net_pnl_usd']>0


def main():
    synthetic_tests()
    x5,coverage=b27ad.b21.load5()
    assert abs(float(coverage)-1.0)<1e-12
    f=b27an.reconstruct_f15(x5)

    # Reproduce B27AN fixed E20/D50 baseline before interpreting exit management.
    fixed=[]
    for _,r in f.iterrows():
        fixed.append(b27an.simulate(x5,r,'E20',.20,'D50',.50))
    fx=pd.DataFrame(fixed)
    expected={
      'external':(50,40.886),'development':(79,-22.549),
      'reference_validation':(34,-30.002),'august':(1,-2.420)}
    for part,(n,total) in expected.items():
        g=fx[fx.partition==part]
        assert len(g)==n
        assert abs(float(g.net_pnl_usd.sum())-total)<0.02,(part,float(g.net_pnl_usd.sum()),total)

    tr=pd.DataFrame([hybrid(x5,r) for _,r in f.iterrows()])
    assert len(tr)==164
    # Runner assertions.
    for r in tr.itertuples(index=False):
        if r.exit_reason=='PROFIT_CEILING_HIT':
            b=x5.loc[pd.Timestamp(r.exit_bar_start)]
            assert float(b.high)+1e-9>=float(r.exit_px)
        if r.e20_reached and np.isfinite(r.final_ceiling):
            assert float(r.final_ceiling)<=float(r.E20_DOWN)+1e-9

    sm=summarize_rows(tr)
    pooled=sm[sm.partition=='POOLED_MAJOR'].iloc[0]
    fixed_major=fx[fx.partition.isin(MAJOR)]
    fixed_total=float(fixed_major.net_pnl_usd.sum())
    ok=(float(pooled.exp)>0 and float(pooled.pf)>=1.20 and float(pooled.total)>fixed_total)
    for part in MAJOR:
        rr=sm[sm.partition==part].iloc[0]
        ok=ok and float(rr.exp)>=0 and float(rr.pf)>=1.0
    status='B27AQ_SUPPORTED' if ok else 'B27AQ_NOT_SUPPORTED'

    tr.to_csv(OUT_TRADES,index=False); sm.to_csv(OUT_SUM,index=False); OUT_STATUS.write_text(status+'\n')
    def pct(x): return f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'
    md=['# B27AQ — BTC London->NY SHORT BLIND_F15 E20 Profit-Lock Audit — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** B27AK F15 identities and B27AN E20/D50 fixed baseline reproduced before the post-E20 runner was interpreted.','',
        f'Fixed pooled-major E20/D50 total: **${fixed_total:+.3f}**.','',
        '| Partition | N | WR | PF | Exp/trade $ | Total $ | E20 reach | Ceiling hits | Gap exits | Time exits | Med ratchets | Med trough ext | Med exit ext | Med capture | Med giveback |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in sm.itertuples(index=False):
        md.append(f'| {r.partition} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.exp)} | {num(r.total)} | {pct(r.e20_rate)} | {int(r.ceiling_hits)} | {int(r.gap_exits)} | {int(r.time_exits)} | {num(r.median_ratchets)} | {num(r.median_trough_ext)} | {num(r.median_exit_ext)} | {num(r.median_capture)} | {num(r.median_giveback)} |')
    md += ['','## Frozen support gate','',f'**Status: {status}.**','',
           'No alternate target, stop, regime gate, confirmation, or runner parameter was introduced.','',
           'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')
    print('\n'.join(md))

if __name__=='__main__':
    main()
