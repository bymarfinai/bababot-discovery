#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_STRONG_TREND_TRANSITION_ATLAS_B23B_Result.md'
OUT_SUMMARY = ROOT / 'BTC_STRONG_TREND_TRANSITION_ATLAS_B23B_Summary.csv'
OUT_EPISODES = ROOT / 'BTC_STRONG_TREND_TRANSITION_ATLAS_B23B_Episodes.csv'
PARTS = b22b.PARTS
TFS = b22b.TFS


def classify(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    spread_narrow = x.spread < x.spread.shift(1)
    reversal = (
        (x.close < x.ema50)
        | (x.ema20 < x.ema50)
        | ((x.close < x.ema20) & (x.ema20 < x.ema20.shift(1)) & spread_narrow)
    ).fillna(False)
    strong = x.strong.fillna(False) & (~reversal)
    healthy = (
        (x.ema20 > x.ema50)
        & (x.close >= x.ema20)
        & (x.ema20 >= x.ema20.shift(1))
        & (~strong)
        & (~reversal)
    ).fillna(False)
    weakening = (
        (x.ema20 > x.ema50)
        & (x.close >= x.ema50)
        & (~strong)
        & (~healthy)
        & (~reversal)
    ).fillna(False)
    state = np.full(len(x), 'OTHER', dtype=object)
    state[weakening.to_numpy(bool)] = 'WEAKENING'
    state[healthy.to_numpy(bool)] = 'HEALTHY'
    state[strong.to_numpy(bool)] = 'STRONG'
    state[reversal.to_numpy(bool)] = 'REVERSAL'
    x['state'] = state
    return x


def compress(seq: list[str]) -> list[str]:
    out = []
    for s in seq:
        if not out or s != out[-1]:
            out.append(s)
    return out


def episodes_for(z: pd.DataFrame, tf: str, part: str, start: pd.Timestamp, end: pd.Timestamp):
    idx = z.index
    lo = int(idx.searchsorted(start, side='left'))
    hi = int(idx.searchsorted(end, side='left'))
    if hi - lo < 3:
        return []
    states = z.state.to_numpy(object)
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)

    rows = []
    i = lo
    while i < hi - 1:
        if states[i] != 'STRONG':
            i += 1
            continue
        onset = i
        entry_i = i + 1
        j = i + 1
        while j < hi and states[j] != 'REVERSAL':
            j += 1
        censored = j >= hi
        if censored:
            rev_i = None
            exit_rev_i = hi - 1
            seq_end = hi
        else:
            rev_i = j
            exit_rev_i = min(j + 1, hi - 1)
            seq_end = j + 1

        seq = [str(s) for s in states[onset:seq_end] if str(s) != 'OTHER']
        cpath = compress(seq)
        if not cpath or cpath[0] != 'STRONG':
            i = (j + 1) if rev_i is not None else hi
            continue

        before_rev = states[rev_i - 1] if rev_i is not None and rev_i - 1 >= onset else None
        nonstrong_candidates = [k for k in range(onset + 1, rev_i if rev_i is not None else hi)
                                if states[k] in ('HEALTHY', 'WEAKENING')]
        first_non_i = nonstrong_candidates[0] if nonstrong_candidates else None
        weak_candidates = [k for k in range(onset + 1, rev_i if rev_i is not None else hi)
                           if states[k] == 'WEAKENING']
        first_weak_i = weak_candidates[0] if weak_candidates else None

        strong_bars = int(sum(states[k] == 'STRONG' for k in range(onset, rev_i if rev_i is not None else hi)))
        healthy_bars = int(sum(states[k] == 'HEALTHY' for k in range(onset, rev_i if rev_i is not None else hi)))
        weakening_bars = int(sum(states[k] == 'WEAKENING' for k in range(onset, rev_i if rev_i is not None else hi)))

        entry_px = float(opens[entry_i])
        exit_rev_px = float(opens[exit_rev_i])
        ret_rev = exit_rev_px / entry_px - 1.0
        path_end = max(entry_i + 1, exit_rev_i)
        mfe = float(np.nanmax(highs[entry_i:path_end]) / entry_px - 1.0) if path_end > entry_i else np.nan
        mae = float(np.nanmin(lows[entry_i:path_end]) / entry_px - 1.0) if path_end > entry_i else np.nan

        if first_weak_i is not None:
            exit_weak_i = min(first_weak_i + 1, hi - 1)
            ret_weak = float(opens[exit_weak_i] / entry_px - 1.0)
            bars_to_first_weak = int(first_weak_i - onset)
        else:
            exit_weak_i = None
            ret_weak = np.nan
            bars_to_first_weak = np.nan

        direct = bool(rev_i is not None and cpath == ['STRONG', 'REVERSAL'])
        preceded = bool(rev_i is not None and any(s in ('HEALTHY', 'WEAKENING') for s in cpath[:-1]))
        bars_non_to_rev = (int(rev_i - first_non_i) if rev_i is not None and first_non_i is not None else np.nan)

        rows.append({
            'partition': part,
            'timeframe': tf,
            'onset_ts': idx[onset],
            'entry_reference_ts': idx[entry_i],
            'reversal_ts': pd.NaT if rev_i is None else idx[rev_i],
            'censored': censored,
            'compressed_path': '>'.join(cpath),
            'direct_strong_to_reversal': direct,
            'reversal_preceded_by_transition': preceded,
            'final_pre_reversal_state': None if before_rev is None else str(before_rev),
            'bars_to_reversal': np.nan if rev_i is None else int(rev_i - onset),
            'bars_to_first_weakening': bars_to_first_weak,
            'bars_first_nonstrong_to_reversal': bars_non_to_rev,
            'strong_bars': strong_bars,
            'healthy_bars': healthy_bars,
            'weakening_bars': weakening_bars,
            'entry_px': entry_px,
            'return_exit_first_weakening': ret_weak,
            'return_exit_reversal': ret_rev,
            'mfe_to_reversal': mfe,
            'mae_to_reversal': mae,
        })
        i = (rev_i + 1) if rev_i is not None else hi
    return rows


def summarize(g: pd.DataFrame) -> dict:
    u = g[~g.censored].copy()
    path_counts = Counter(u.compressed_path.dropna().tolist())
    top_paths = '; '.join(f'{p}:{n}' for p, n in path_counts.most_common(5))
    final = u.final_pre_reversal_state.value_counts(normalize=True)
    weak_ret = u.return_exit_first_weakening.dropna()
    return {
        'n_episodes': int(len(g)),
        'n_uncensored': int(len(u)),
        'direct_strong_to_reversal_rate': float(u.direct_strong_to_reversal.mean()) if len(u) else np.nan,
        'transition_before_reversal_rate': float(u.reversal_preceded_by_transition.mean()) if len(u) else np.nan,
        'median_bars_to_reversal': float(u.bars_to_reversal.median()) if len(u) else np.nan,
        'median_bars_first_nonstrong_to_reversal': float(u.bars_first_nonstrong_to_reversal.dropna().median()) if u.bars_first_nonstrong_to_reversal.notna().any() else np.nan,
        'median_strong_bars': float(u.strong_bars.median()) if len(u) else np.nan,
        'median_healthy_bars': float(u.healthy_bars.median()) if len(u) else np.nan,
        'median_weakening_bars': float(u.weakening_bars.median()) if len(u) else np.nan,
        'pre_rev_strong_rate': float(final.get('STRONG', 0.0)),
        'pre_rev_healthy_rate': float(final.get('HEALTHY', 0.0)),
        'pre_rev_weakening_rate': float(final.get('WEAKENING', 0.0)),
        'median_ret_exit_first_weakening': float(weak_ret.median()) if len(weak_ret) else np.nan,
        'first_weakening_available_rate': float(u.return_exit_first_weakening.notna().mean()) if len(u) else np.nan,
        'median_ret_exit_reversal': float(u.return_exit_reversal.median()) if len(u) else np.nan,
        'median_mfe_to_reversal': float(u.mfe_to_reversal.median()) if len(u) else np.nan,
        'top_paths': top_paths,
    }


def pct(v):
    return '-' if pd.isna(v) else f'{100 * float(v):.2f}%'


def num(v):
    return '-' if pd.isna(v) else f'{float(v):.1f}'


def main():
    x5, coverage = b21.load5()
    rows = []
    for tf, rule in TFS.items():
        z = classify(b22b.enrich(b22b.resample_ohlc(x5, rule)))
        for part, (start, end) in PARTS.items():
            rows.extend(episodes_for(z, tf, part, start, end))

    e = pd.DataFrame(rows)
    e.to_csv(OUT_EPISODES, index=False)
    sums = []
    for (part, tf), g in e.groupby(['partition', 'timeframe']):
        sums.append({'partition': part, 'timeframe': tf, **summarize(g)})
    s = pd.DataFrame(sums)
    s.to_csv(OUT_SUMMARY, index=False)

    order = {'5m': 0, '15m': 1, '1h': 2, '4h': 3}
    s['ord'] = s.timeframe.map(order)
    md = [
        '# BTC Strong Trend Transition Atlas B23B — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Every B23A-style STRONG episode is followed candle-by-candle through STRONG, HEALTHY, WEAKENING, and REVERSAL. No pullback-only entry universe and no fixed holding horizon.', '',
        '| Partition | TF | N | Direct Strong→Rev | Has transition before Rev | Median bars→Rev | Median nonstrong→Rev | Strong bars | Healthy bars | Weak bars | PreRev Strong | Healthy | Weak | First weak avail | Median ret exit weak | Median ret exit rev | Median MFE |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in s.sort_values(['partition', 'ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.timeframe} | {r.n_episodes} | {pct(r.direct_strong_to_reversal_rate)} | '
            f'{pct(r.transition_before_reversal_rate)} | {num(r.median_bars_to_reversal)} | '
            f'{num(r.median_bars_first_nonstrong_to_reversal)} | {num(r.median_strong_bars)} | '
            f'{num(r.median_healthy_bars)} | {num(r.median_weakening_bars)} | {pct(r.pre_rev_strong_rate)} | '
            f'{pct(r.pre_rev_healthy_rate)} | {pct(r.pre_rev_weakening_rate)} | {pct(r.first_weakening_available_rate)} | '
            f'{pct(r.median_ret_exit_first_weakening)} | {pct(r.median_ret_exit_reversal)} | {pct(r.median_mfe_to_reversal)} |'
        )
    md += ['', '## Dominant compressed paths', '']
    for r in s.sort_values(['partition', 'ord']).itertuples(index=False):
        md.append(f'- {r.partition} / {r.timeframe}: {r.top_paths}')
    md += ['', 'Interpretation: this is lifecycle forensics. Exit-at-first-WEAKENING versus exit-at-REVERSAL returns are diagnostic only, not a promoted strategy.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')


if __name__ == '__main__':
    main()
