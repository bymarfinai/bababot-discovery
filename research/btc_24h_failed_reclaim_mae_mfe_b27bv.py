#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIG_FILE = ROOT / 'BTC_24H_FAILED_RECLAIM_CAUSAL_B27BT_Episodes.csv'
OUT_MD = ROOT / 'BTC_24H_FAILED_RECLAIM_MAE_MFE_B27BV_Result.md'
OUT_EP = ROOT / 'BTC_24H_FAILED_RECLAIM_MAE_MFE_B27BV_Episodes.csv'
OUT_SUM = ROOT / 'BTC_24H_FAILED_RECLAIM_MAE_MFE_B27BV_Summary.csv'
OUT_STATUS = ROOT / 'BTC_24H_FAILED_RECLAIM_MAE_MFE_B27BV_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external', 'development', 'reference_validation')
OOS = ('external', 'reference_validation')
OUTCOMES = ('ALL', 'TRANSITION', 'RESUME')
Q = (.25, .50, .75, .90)


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_signals() -> pd.DataFrame:
    d = pd.read_csv(SIG_FILE)
    for c in (
        'first_sideways_ts', 'age2_source_start', 'age2_source_end',
        'confirmation_bar_start', 'confirmation_complete_ts',
        'eligible_open_ts', 'exit_effective_ts',
    ):
        d[c] = pd.to_datetime(d[c], utc=True, errors='coerce')
    d['transition'] = as_bool(d['transition'])
    d['eligible_before_exit'] = as_bool(d['eligible_before_exit'])

    q = d[
        d.partition.isin(MAJOR) &
        (d.origin_state == 'BEAR') &
        (d.path_class == 'FAILED_RECLAIM')
    ].copy().sort_values(['partition', 'eligible_open_ts', 'episode_id']).reset_index(drop=True)

    expected = {'external': 6, 'development': 20, 'reference_validation': 8}
    for part, n in expected.items():
        got = len(q[q.partition == part])
        assert got == n, (part, got, n)
    assert len(q) == 34
    assert len(q[q.partition.isin(OOS)]) == 14
    assert int(q.transition.sum()) == 22
    assert int((~q.transition).sum()) == 12
    qoos = q[q.partition.isin(OOS)]
    assert int(qoos.transition.sum()) == 11
    assert int((~qoos.transition).sum()) == 3
    assert q.eligible_before_exit.all()
    assert q.confirmation_complete_ts.notna().all()
    assert q.eligible_open_ts.notna().all()
    assert q.exit_effective_ts.notna().all()
    assert (q.eligible_open_ts == q.confirmation_complete_ts).all()
    assert (q.eligible_open_ts < q.exit_effective_ts).all()
    return q


def get_open_at(x5: pd.DataFrame, ts: pd.Timestamp) -> float:
    pos = int(x5.index.searchsorted(ts, side='left'))
    assert pos < len(x5)
    assert x5.index[pos] == ts, (ts, x5.index[pos])
    return float(x5.iloc[pos].open)


def anatomy_one(x5: pd.DataFrame, r) -> dict:
    source_start = pd.Timestamp(r.age2_source_start)
    source_end = pd.Timestamp(r.age2_source_end)
    src = fast_slice(x5, source_start, source_end)
    assert len(src) == 48, (r.episode_id, len(src))
    assert src.index[0] == source_start and src.index[-1] == source_end - BAR5
    assert (src.index.to_series().diff().dropna() == BAR5).all()

    reclaim_i = int(float(r.first_reclaim_pos)) - 1
    rebreak_i = int(float(r.first_rebreak_pos)) - 1
    assert 0 <= reclaim_i < rebreak_i < 48
    local_low = float(src.iloc[reclaim_i:rebreak_i + 1].low.min())

    entry_ts = pd.Timestamp(r.eligible_open_ts)
    exit_ts = pd.Timestamp(r.exit_effective_ts)
    entry_px = get_open_at(x5, entry_ts)
    local_r = entry_px - local_low
    assert local_low < entry_px
    assert local_r > 0

    w = fast_slice(x5, entry_ts, exit_ts)
    assert not w.empty, (r.episode_id, entry_ts, exit_ts)
    assert w.index[0] == entry_ts
    assert w.index[-1] == exit_ts - BAR5
    assert (w.index.to_series().diff().dropna() == BAR5).all()

    lows = w.low.to_numpy(float)
    highs = w.high.to_numpy(float)
    i_low = int(np.argmin(lows))
    i_high = int(np.argmax(highs))
    min_low = float(lows[i_low])
    max_high = float(highs[i_high])
    mae_abs = max(0.0, entry_px - min_low)
    mfe_abs = max(0.0, max_high - entry_px)
    mae_pct = mae_abs / entry_px
    mfe_pct = mfe_abs / entry_px
    mae_r = mae_abs / local_r
    mfe_r = mfe_abs / local_r
    mae_ts = w.index[i_low]
    mfe_ts = w.index[i_high]

    exit_open = get_open_at(x5, exit_ts)
    exit_return = exit_open / entry_px - 1.0

    return {
        'episode_id': int(r.episode_id),
        'partition': str(r.partition),
        'outcome': str(r.outcome),
        'transition': bool(r.transition),
        'entry_ts': entry_ts,
        'entry_px': entry_px,
        'regime_exit_effective_ts': exit_ts,
        'observation_bars': int(len(w)),
        'observation_hours': float((exit_ts - entry_ts) / pd.Timedelta(hours=1)),
        'local_low': local_low,
        'local_r_abs': local_r,
        'local_r_pct_entry': local_r / entry_px,
        'min_low': min_low,
        'max_high': max_high,
        'mae_abs': mae_abs,
        'mfe_abs': mfe_abs,
        'mae_pct_entry': mae_pct,
        'mfe_pct_entry': mfe_pct,
        'mae_local_r': mae_r,
        'mfe_local_r': mfe_r,
        'local_low_breached': bool(min_low <= local_low),
        'mae_bar_start': mae_ts,
        'mfe_bar_start': mfe_ts,
        'minutes_to_mae': float((mae_ts - entry_ts) / pd.Timedelta(minutes=1)),
        'minutes_to_mfe': float((mfe_ts - entry_ts) / pd.Timedelta(minutes=1)),
        'reach_1r': bool(mfe_r >= 1.0),
        'reach_1p5r': bool(mfe_r >= 1.5),
        'reach_2r': bool(mfe_r >= 2.0),
        'exit_open': exit_open,
        'detector_exit_return': exit_return,
    }


def subset(d: pd.DataFrame, part: str) -> pd.DataFrame:
    if part == 'POOLED_OOS':
        return d[d.partition.isin(OOS)].copy()
    if part == 'POOLED_MAJOR':
        return d[d.partition.isin(MAJOR)].copy()
    return d[d.partition == part].copy()


def qv(g: pd.DataFrame, col: str, p: float) -> float:
    return float(g[col].quantile(p)) if len(g) else np.nan


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in (*MAJOR, 'POOLED_OOS', 'POOLED_MAJOR'):
        q = subset(d, part)
        for outcome in OUTCOMES:
            g = q if outcome == 'ALL' else q[q.outcome == outcome]
            rec = {
                'partition': part,
                'outcome': outcome,
                'n': len(g),
                'local_low_breach_rate': float(g.local_low_breached.mean()) if len(g) else np.nan,
                'median_minutes_to_mae': float(g.minutes_to_mae.median()) if len(g) else np.nan,
                'median_minutes_to_mfe': float(g.minutes_to_mfe.median()) if len(g) else np.nan,
                'median_detector_exit_return': float(g.detector_exit_return.median()) if len(g) else np.nan,
                'reach_1r_rate': float(g.reach_1r.mean()) if len(g) else np.nan,
                'reach_1p5r_rate': float(g.reach_1p5r.mean()) if len(g) else np.nan,
                'reach_2r_rate': float(g.reach_2r.mean()) if len(g) else np.nan,
            }
            for col in ('mae_pct_entry', 'mfe_pct_entry', 'mae_local_r', 'mfe_local_r'):
                for p in Q:
                    rec[f'{col}_p{int(p*100)}'] = qv(g, col, p)
            rows.append(rec)
    return pd.DataFrame(rows)


def row(s: pd.DataFrame, part: str, outcome: str):
    q = s[(s.partition == part) & (s.outcome == outcome)]
    assert len(q) == 1
    return q.iloc[0]


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v):
    return '-' if pd.isna(v) else f'{float(v):.2f}'


def main():
    sig = load_signals()
    x5, coverage = b21.load5()
    assert len(x5) == 698112
    assert abs(float(coverage) - 1.0) < 1e-12

    d = pd.DataFrame([anatomy_one(x5, r) for r in sig.itertuples(index=False)])
    assert len(d) == 34
    assert int(d.transition.sum()) == 22
    assert int((~d.transition).sum()) == 12
    assert (d.local_r_abs > 0).all()
    assert (d.observation_bars > 0).all()
    d.to_csv(OUT_EP, index=False)

    s = summarize(d)
    s.to_csv(OUT_SUM, index=False)

    major_t = row(s, 'POOLED_MAJOR', 'TRANSITION')
    oos_t = row(s, 'POOLED_OOS', 'TRANSITION')
    gate_identity = (
        len(d) == 34 and
        int(d.transition.sum()) == 22 and
        int((~d.transition).sum()) == 12 and
        len(d[d.partition.isin(OOS)]) == 14 and
        int(d[d.partition.isin(OOS)].transition.sum()) == 11
    )
    gate_windows = bool((d.observation_bars > 0).all())
    gate_risk = bool((d.local_r_abs > 0).all())
    gate_n = int(major_t.n) >= 20 and int(oos_t.n) >= 10
    gate_major_ratio = float(major_t.mfe_local_r_p50) > float(major_t.mae_local_r_p50)
    gate_oos_ratio = float(oos_t.mfe_local_r_p50) > float(oos_t.mae_local_r_p50)
    gate_p75_mae = float(major_t.mae_local_r_p75) > 1.0

    informative = all([
        gate_identity, gate_windows, gate_risk, gate_n,
        gate_major_ratio, gate_oos_ratio, gate_p75_mae,
    ])
    verdict = (
        'B27BV_FAILED_RECLAIM_EXCURSION_INFORMATIVE'
        if informative else
        'B27BV_FAILED_RECLAIM_EXCURSION_NOT_INFORMATIVE'
    )
    OUT_STATUS.write_text(verdict + '\n')

    lines = [
        '# B27BV — BTC 24H BEAR-Origin Failed-Reclaim MAE/MFE Anatomy — Result', '',
        '**Audit status: PASS.** No entry/stop/target parameter was optimized. The exact B27BU next-5m-open anchor and LOCAL_LOW risk unit are used only as frozen measurement coordinates.', '',
        'Frozen signal identity reproduced exactly: **34 = external 6 + development 20 + reference_validation 8; pooled OOS 14. Outcomes: pooled major 22 TRANSITION + 12 RESUME; pooled OOS 11 + 3.**', '',
        '## Pooled excursion envelope', '',
        '| Pool | Outcome | N | LOCAL_LOW breached | MAE median / P75 / P90 | MFE median / P75 / P90 | MAE local-R median / P75 / P90 | MFE local-R median / P75 / P90 |',
        '|---|---|---:|---:|---|---|---|---|',
    ]
    for part in ('POOLED_OOS', 'POOLED_MAJOR'):
        for outcome in OUTCOMES:
            r = row(s, part, outcome)
            lines.append(
                f'| {part} | {outcome} | {int(r.n)} | {pct(r.local_low_breach_rate)} | '
                f'{pct(r.mae_pct_entry_p50)} / {pct(r.mae_pct_entry_p75)} / {pct(r.mae_pct_entry_p90)} | '
                f'{pct(r.mfe_pct_entry_p50)} / {pct(r.mfe_pct_entry_p75)} / {pct(r.mfe_pct_entry_p90)} | '
                f'{num(r.mae_local_r_p50)}R / {num(r.mae_local_r_p75)}R / {num(r.mae_local_r_p90)}R | '
                f'{num(r.mfe_local_r_p50)}R / {num(r.mfe_local_r_p75)}R / {num(r.mfe_local_r_p90)}R |'
            )

    lines += ['', '## Major partition transition anatomy', '',
              '| Partition | N transition | LOCAL_LOW breached | MAE median | MAE P75 | MFE median | MFE P75 | >=1R MFE | >=1.5R | >=2R |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in MAJOR:
        r = row(s, part, 'TRANSITION')
        lines.append(
            f'| {part} | {int(r.n)} | {pct(r.local_low_breach_rate)} | '
            f'{num(r.mae_local_r_p50)}R | {num(r.mae_local_r_p75)}R | '
            f'{num(r.mfe_local_r_p50)}R | {num(r.mfe_local_r_p75)}R | '
            f'{pct(r.reach_1r_rate)} | {pct(r.reach_1p5r_rate)} | {pct(r.reach_2r_rate)} |'
        )

    lines += ['', '## Timing and detector-exit diagnostics', '',
              '| Pool | Outcome | Median min to MAE | Median min to MFE | Median detector-exit return |',
              '|---|---|---:|---:|---:|']
    for part in ('POOLED_OOS', 'POOLED_MAJOR'):
        for outcome in ('TRANSITION', 'RESUME'):
            r = row(s, part, outcome)
            lines.append(
                f'| {part} | {outcome} | {r.median_minutes_to_mae:.0f} | '
                f'{r.median_minutes_to_mfe:.0f} | {pct(r.median_detector_exit_return)} |'
            )

    lines += ['', '## Frozen interpretation gate', '',
              f'- Exact signal/outcome identity: **{"PASS" if gate_identity else "FAIL"}**.',
              f'- Non-empty continuous post-entry observation windows: **{"PASS" if gate_windows else "FAIL"}**.',
              f'- Positive frozen LOCAL_R for every signal: **{"PASS" if gate_risk else "FAIL"}**.',
              f'- Transition sample >=20 pooled-major and >=10 pooled-OOS: **{"PASS" if gate_n else "FAIL"}**.',
              f'- Pooled-major TRANSITION median MFE_local_R > MAE_local_R: **{"PASS" if gate_major_ratio else "FAIL"}**.',
              f'- Pooled-OOS TRANSITION median MFE_local_R > MAE_local_R: **{"PASS" if gate_oos_ratio else "FAIL"}**.',
              f'- Pooled-major TRANSITION P75 MAE_local_R > 1.0: **{"PASS" if gate_p75_mae else "FAIL"}**.',
              '- No geometry selected or changed from this audit: **PASS**.', '',
              f'**Frozen verdict: `{verdict}`.**', '',
              'An informative result is not a trade approval. It only permits a separately preregistered geometry experiment using this frozen excursion envelope.', '',
              'Research only. Live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
