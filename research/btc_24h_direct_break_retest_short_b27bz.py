#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Result.md'
OUT_EVENTS = ROOT / 'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Events.csv'
OUT_SUM = ROOT / 'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_DIRECT_BREAK_RETEST_SHORT_B27BZ_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external', 'development', 'reference_validation')
OOS = ('external', 'reference_validation')
REGIMES = ('BULL', 'BEAR', 'SIDEWAYS')
CLOCKS = ('00-04', '04-08', '08-12', '12-16', '16-20', '20-00')
EXT_F = 0.15


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_source() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    d['k1_opp0'] = as_bool(d['k1_opp0'])
    for c in ('obs_start', 'obs_end', 'k1_ts', 'k2_ts', 'k3_ts', 'regime_available_ts'):
        if c in d.columns:
            d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    q = d[d.partition.isin(MAJOR) & d.k1_opp0].copy()
    expected = {'external': 862, 'development': 1264, 'reference_validation': 641}
    assert len(q) == 2767, len(q)
    for part, n in expected.items():
        got = len(q[q.partition == part])
        assert got == n, (part, got, n)
    assert q.k1_ts.notna().all()
    return q.sort_values(['obs_start', 'partition']).reset_index(drop=True)


def low_touch(bar, L: float) -> bool:
    return float(bar.low) <= L and float(bar.close) >= L


def evaluate_one(x5: pd.DataFrame, r) -> dict:
    start = pd.Timestamp(r.obs_start)
    end = pd.Timestamp(r.obs_end)
    H = float(r.H)
    L = float(r.L)
    R4 = H - L
    assert R4 > 0
    ext15 = L - EXT_F * R4

    q = fast_slice(x5, start, end)
    assert len(q) == 48, (start, len(q))
    assert q.index[0] == start and q.index[-1] == end - BAR5
    assert (q.index.to_series().diff().dropna() == BAR5).all()

    k1_complete = pd.Timestamp(r.k1_ts)
    k1_start = k1_complete - BAR5
    pos = int(q.index.searchsorted(k1_start, side='left'))
    assert pos < len(q) and q.index[pos] == k1_start
    assert low_touch(q.iloc[pos], L)

    base = {
        'partition': str(r.partition), 'regime': str(r.regime), 'clock_block': str(r.clock_block),
        'obs_start': start, 'obs_end': end, 'H': H, 'L': L, 'range': R4, 'ext15_px': ext15,
        'k1_ts': k1_complete, 'k1_start': k1_start,
    }

    # Identify the first strict boundary close after K1. B27BE stops on this same event.
    break_idx = None
    break_side = None
    for i in range(pos, len(q)):
        c = float(q.iloc[i].close)
        if c < L:
            break_idx = i; break_side = 'LOW'; break
        if c > H:
            break_idx = i; break_side = 'HIGH'; break

    src_side = str(r.breakout_side) if pd.notna(r.breakout_side) else ''
    if break_side is None:
        assert src_side in ('', 'None', 'nan') or str(r.status) == 'NO_BREAK'
    else:
        assert src_side == break_side, (start, src_side, break_side)

    src_visits = pd.to_numeric(pd.Series([r.low_visits]), errors='coerce').iloc[0]
    direct = bool(break_side == 'LOW' and pd.notna(src_visits) and int(src_visits) == 1)
    if not direct:
        return {**base, 'direct_break': False, 'break_ts': pd.NaT, 'break_complete_ts': pd.NaT,
                'retest_ts': pd.NaT, 'retest_complete_ts': pd.NaT, 'retest_class': 'NOT_DIRECT_PATH',
                'accepted_retest': False, 'terminal_ts': end, 'terminal_type': 'NOT_DIRECT_PATH',
                'ext15_success': False, 'minutes_break_to_retest': np.nan, 'minutes_accept_to_ext15': np.nan}

    assert break_idx is not None
    # Source direct-path identity means no distinct Low #2 existed before the break.
    assert int(src_visits) == 1
    break_ts = q.index[break_idx]
    break_complete = break_ts + BAR5
    assert float(q.iloc[break_idx].close) < L

    # Search starts only after the breakdown candle has completed.
    retest_idx = None
    for i in range(break_idx + 1, len(q)):
        if float(q.iloc[i].high) >= L:
            retest_idx = i
            break

    if retest_idx is None:
        return {**base, 'direct_break': True, 'break_ts': break_ts, 'break_complete_ts': break_complete,
                'retest_ts': pd.NaT, 'retest_complete_ts': pd.NaT, 'retest_class': 'NO_RETEST_BEFORE_BLOCK_END',
                'accepted_retest': False, 'terminal_ts': end, 'terminal_type': 'NO_RETEST_BEFORE_BLOCK_END',
                'ext15_success': False, 'minutes_break_to_retest': np.nan, 'minutes_accept_to_ext15': np.nan}

    retest_ts = q.index[retest_idx]
    retest_complete = retest_ts + BAR5
    retest_bar = q.iloc[retest_idx]
    accepted = float(retest_bar.close) <= L
    retest_class = 'RETEST_ACCEPTED_BELOW' if accepted else 'RETEST_RECLAIMED'
    mins_break_retest = float((retest_ts - break_complete) / pd.Timedelta(minutes=1))
    if mins_break_retest < 0:
        raise AssertionError('retest before breakdown completion')

    if not accepted:
        return {**base, 'direct_break': True, 'break_ts': break_ts, 'break_complete_ts': break_complete,
                'retest_ts': retest_ts, 'retest_complete_ts': retest_complete, 'retest_class': retest_class,
                'accepted_retest': False, 'terminal_ts': retest_complete, 'terminal_type': 'RETEST_RECLAIMED',
                'ext15_success': False, 'minutes_break_to_retest': mins_break_retest, 'minutes_accept_to_ext15': np.nan}

    terminal_ts = end
    terminal_type = 'UNRESOLVED_BLOCK_END'
    success = False
    mins_accept_ext = np.nan

    # Outcome begins strictly after retest confirmation is complete.
    for i in range(retest_idx + 1, len(q)):
        ts = q.index[i]
        b = q.iloc[i]
        ext = float(b.low) <= ext15
        reclaim = float(b.close) > L
        if ext and reclaim:
            terminal_ts = ts + BAR5
            terminal_type = 'AMBIGUOUS_EXTENSION_RECLAIM'
            break
        if reclaim:
            terminal_ts = ts + BAR5
            terminal_type = 'RECLAIM_ABOVE_L'
            break
        if ext:
            terminal_ts = ts
            terminal_type = 'EXT15'
            success = True
            mins_accept_ext = float((ts - retest_complete) / pd.Timedelta(minutes=1))
            break

    return {**base, 'direct_break': True, 'break_ts': break_ts, 'break_complete_ts': break_complete,
            'retest_ts': retest_ts, 'retest_complete_ts': retest_complete, 'retest_class': retest_class,
            'accepted_retest': True, 'terminal_ts': terminal_ts, 'terminal_type': terminal_type,
            'ext15_success': success, 'minutes_break_to_retest': mins_break_retest,
            'minutes_accept_to_ext15': mins_accept_ext}


def metrics(g: pd.DataFrame) -> dict:
    direct = g[g.direct_break].copy()
    retest = direct[direct.retest_ts.notna()].copy()
    accepted = retest[retest.accepted_retest].copy()
    succ = accepted[accepted.ext15_success].copy()
    return {
        'k1_n': int(len(g)),
        'direct_n': int(len(direct)),
        'direct_rate': float(len(direct)/len(g)) if len(g) else np.nan,
        'retest_n': int(len(retest)),
        'retest_direct_rate': float(len(retest)/len(direct)) if len(direct) else np.nan,
        'accepted_n': int(len(accepted)),
        'accepted_retest_rate': float(len(accepted)/len(retest)) if len(retest) else np.nan,
        'ext15_n': int(len(succ)),
        'ext15_rate': float(len(succ)/len(accepted)) if len(accepted) else np.nan,
        'reclaim_n': int((accepted.terminal_type == 'RECLAIM_ABOVE_L').sum()),
        'ambiguous_n': int((accepted.terminal_type == 'AMBIGUOUS_EXTENSION_RECLAIM').sum()),
        'unresolved_n': int((accepted.terminal_type == 'UNRESOLVED_BLOCK_END').sum()),
        'median_min_break_to_retest': float(retest.minutes_break_to_retest.median()) if len(retest) else np.nan,
        'median_min_accept_to_ext15': float(succ.minutes_accept_to_ext15.median()) if len(succ) else np.nan,
    }


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows=[]
    for part in MAJOR:
        rows.append({'scope':'PARTITION','name':part,**metrics(d[d.partition==part])})
    rows.append({'scope':'POOL','name':'POOLED_OOS',**metrics(d[d.partition.isin(OOS)])})
    rows.append({'scope':'POOL','name':'POOLED_MAJOR',**metrics(d[d.partition.isin(MAJOR)])})
    pm=d[d.partition.isin(MAJOR)]
    for rg in REGIMES:
        rows.append({'scope':'REGIME','name':rg,**metrics(pm[pm.regime==rg])})
    for cb in CLOCKS:
        rows.append({'scope':'CLOCK','name':cb,**metrics(pm[pm.clock_block==cb])})
    return pd.DataFrame(rows)


def getrow(s, scope, name):
    q=s[(s.scope==scope)&(s.name==name)]
    assert len(q)==1
    return q.iloc[0]


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def fmtm(v):
    return '-' if pd.isna(v) else f'{float(v):.1f}m'


def main() -> None:
    src=load_source()
    x5,coverage=b21.load5()
    assert len(x5)==698112 and abs(float(coverage)-1.0)<1e-12

    d=pd.DataFrame([evaluate_one(x5,r) for r in src.itertuples(index=False)])
    assert len(d)==2767
    assert not d.duplicated(['partition','obs_start']).any()
    # Direct-path rows must match persisted B27BE first-break/visit identity.
    src_direct=((src.breakout_side=='LOW') & (pd.to_numeric(src.low_visits,errors='coerce')==1)).to_numpy(bool)
    assert np.array_equal(d.direct_break.to_numpy(bool),src_direct)
    if d.retest_ts.notna().any():
        z=d[d.retest_ts.notna()]
        assert (pd.to_datetime(z.retest_ts,utc=True) >= pd.to_datetime(z.break_complete_ts,utc=True)).all()

    d.to_csv(OUT_EVENTS,index=False)
    s=summarize(d)
    s.to_csv(OUT_SUM,index=False)

    support=True
    high70=True
    for part in MAJOR:
        r=getrow(s,'PARTITION',part)
        support = support and int(r.direct_n)>=100 and int(r.accepted_n)>=30 and pd.notna(r.ext15_rate) and float(r.ext15_rate)>=.65
        high70 = high70 and int(r.accepted_n)>=30 and pd.notna(r.ext15_rate) and float(r.ext15_rate)>=.70
    po=getrow(s,'POOL','POOLED_OOS')
    support = support and pd.notna(po.ext15_rate) and float(po.ext15_rate)>=.65

    verdict='B27BZ_DIRECT_BREAK_RETEST_SUPPORTED' if support else 'B27BZ_DIRECT_BREAK_RETEST_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict+'\n')

    lines=[
        '# B27BZ — BTC 24H Direct-Break Retest SHORT Anatomy — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Exact B27BE K1+OPP0 identities were reused. Direct path means first Low close-break occurs before any distinct Low #2. No session/regime filter, trading stop/TP, fee, PF, PnL, or live change was used.','',
        'Frozen continuation geometry: direct `close < L` -> first retest `high >= L` -> retest must complete `close <= L` -> from next 5m bar require `EXT15 = L - 0.15*(H-L)` before a completed reclaim `close > L`.','',
        '## Major partitions','',
        '| Partition | K1 OPP0 | Direct break | Direct rate | Retest | Retest/direct | Accepted | Accept/retest | EXT15 | EXT15/accepted | Break->retest | Accept->EXT15 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in MAJOR:
        r=getrow(s,'PARTITION',part)
        lines.append(f'| {part} | {int(r.k1_n)} | {int(r.direct_n)} | {pct(r.direct_rate)} | {int(r.retest_n)} | {pct(r.retest_direct_rate)} | {int(r.accepted_n)} | {pct(r.accepted_retest_rate)} | {int(r.ext15_n)} | {pct(r.ext15_rate)} | {fmtm(r.median_min_break_to_retest)} | {fmtm(r.median_min_accept_to_ext15)} |')

    lines += ['', '## Pooled readout','',
              '| Pool | K1 | Direct | Retest | Accepted | EXT15/accepted | Reclaim | Ambiguous | Unresolved |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for name in ('POOLED_OOS','POOLED_MAJOR'):
        r=getrow(s,'POOL',name)
        lines.append(f'| {name} | {int(r.k1_n)} | {int(r.direct_n)} | {int(r.retest_n)} | {int(r.accepted_n)} | {pct(r.ext15_rate)} | {int(r.reclaim_n)} | {int(r.ambiguous_n)} | {int(r.unresolved_n)} |')

    lines += ['', '## Regime diagnostics — pooled major','',
              '| Regime | Direct | Accepted | EXT15/accepted |', '|---|---:|---:|---:|']
    for rg in REGIMES:
        r=getrow(s,'REGIME',rg)
        lines.append(f'| {rg} | {int(r.direct_n)} | {int(r.accepted_n)} | {pct(r.ext15_rate)} |')

    lines += ['', '## Clock diagnostics — pooled major','',
              '| UTC block | Direct | Accepted | EXT15/accepted |', '|---|---:|---:|---:|']
    for cb in CLOCKS:
        r=getrow(s,'CLOCK',cb)
        lines.append(f'| {cb} | {int(r.direct_n)} | {int(r.accepted_n)} | {pct(r.ext15_rate)} |')

    lines += ['', '## Frozen gate','',
              f'- Support gate: **{"PASS" if support else "FAIL"}**.',
              f'- High-quality >=70% in every major partition: **{"PASS" if high70 else "FAIL"}**.',
              '', f'**Frozen verdict: `{verdict}`.**','',
              'A structural pass only permits a separately preregistered economic experiment. Research only. Live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
