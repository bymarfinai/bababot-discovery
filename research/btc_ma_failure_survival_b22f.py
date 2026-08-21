#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_opposing_htf_fakeout_b22e as b22e

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_MA_FAILURE_SURVIVAL_B22F_Result.md'
OUT_JSON = ROOT / 'BTC_MA_FAILURE_SURVIVAL_B22F_Result.json'
OUT_SUMMARY = ROOT / 'BTC_MA_FAILURE_SURVIVAL_B22F_Summary.csv'
OUT_EVENTS = ROOT / 'BTC_MA_FAILURE_SURVIVAL_B22F_Events.csv'

PARTS = b22b.PARTS
ENTRY_TYPES = ['PULLBACK_RECLAIM', 'CROSSOVER_INIT']
CHECKPOINTS = [1, 2, 3, 4, 6, 12, 24, 48]
PAIRS = b22e.PAIRS


def first_hit(hit_idx: np.ndarray, start_idx: int, hi: int):
    j = int(np.searchsorted(hit_idx, start_idx, side='left'))
    if j >= len(hit_idx):
        return None
    v = int(hit_idx[j])
    return v if v < hi else None


def collect_events(z: pd.DataFrame, hstate: np.ndarray, entry_tf: str, higher_tf: str,
                   entry_type: str, dur: pd.Timedelta):
    sig = z[f'entry_{entry_type}'].fillna(False).to_numpy(bool)
    idx = z.index
    opens = z.open.to_numpy(float)

    soft = (
        (z.close < z.ema20)
        & (z.ema20 < z.ema20.shift(1))
        & (z.spread < z.spread.shift(1))
    ).fillna(False).to_numpy(bool)
    hard = ((z.close < z.ema50) | (z.ema20 < z.ema50)).fillna(False).to_numpy(bool)

    rows = []
    for part, (start, end) in PARTS.items():
        lo = int(idx.searchsorted(start, side='left'))
        hi = int(idx.searchsorted(end, side='left'))
        if hi - lo < 3:
            continue
        soft_hits = np.flatnonzero(soft[lo:hi]) + lo
        hard_hits = np.flatnonzero(hard[lo:hi]) + lo
        sig_hits = np.flatnonzero(sig[lo:max(lo, hi - 1)]) + lo

        for s_i in sig_hits:
            s_i = int(s_i)
            e_i = s_i + 1
            if e_i >= hi:
                continue
            max_follow_bars = int(hi - e_i)
            sh = first_hit(soft_hits, e_i, hi)
            hh = first_hit(hard_hits, e_i, hi)

            bars_soft = None if sh is None else int(sh - e_i + 1)
            bars_hard = None if hh is None else int(hh - e_i + 1)
            hours_soft = None if sh is None else float(((idx[sh] + dur) - idx[e_i]) / pd.Timedelta(hours=1))
            hours_hard = None if hh is None else float(((idx[hh] + dur) - idx[e_i]) / pd.Timedelta(hours=1))

            rows.append({
                'partition': part,
                'entry_tf': entry_tf,
                'higher_tf': higher_tf,
                'entry_type': entry_type,
                'signal_ts': idx[s_i],
                'entry_ts': idx[e_i],
                'higher_state': str(hstate[s_i]),
                'entry_px': float(opens[e_i]),
                'max_follow_bars': max_follow_bars,
                'bars_to_soft_failure': bars_soft,
                'hours_to_soft_failure': hours_soft,
                'soft_censored': sh is None,
                'bars_to_hard_failure': bars_hard,
                'hours_to_hard_failure': hours_hard,
                'hard_censored': hh is None,
            })
    return rows


def survival_at(g: pd.DataFrame, col: str, k: int):
    q = g[g.max_follow_bars >= k]
    if q.empty:
        return 0, None
    # Survived checkpoint k if no failure observed by bar k.
    survived = q[col].isna() | (q[col] > k)
    return int(len(q)), float(survived.mean())


def summarize(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ['partition', 'entry_tf', 'higher_tf', 'entry_type', 'higher_state']
    for key, g in events.groupby(keys, dropna=False):
        base = {
            **dict(zip(keys, key)),
            'n': int(len(g)),
            'soft_fail_n': int(g.bars_to_soft_failure.notna().sum()),
            'hard_fail_n': int(g.bars_to_hard_failure.notna().sum()),
            'median_bars_soft_uncensored': float(g.bars_to_soft_failure.dropna().median()) if g.bars_to_soft_failure.notna().any() else None,
            'median_bars_hard_uncensored': float(g.bars_to_hard_failure.dropna().median()) if g.bars_to_hard_failure.notna().any() else None,
        }
        for k in CHECKPOINTS:
            nsoft, ssoft = survival_at(g, 'bars_to_soft_failure', k)
            nhard, shard = survival_at(g, 'bars_to_hard_failure', k)
            base[f'soft_n_at_risk_{k}'] = nsoft
            base[f'soft_survival_{k}'] = ssoft
            base[f'hard_n_at_risk_{k}'] = nhard
            base[f'hard_survival_{k}'] = shard
        rows.append(base)
    return pd.DataFrame(rows)


def state_row(s: pd.DataFrame, part: str, entry_tf: str, state: str):
    q = s[(s.partition == part) & (s.entry_tf == entry_tf) &
          (s.entry_type == 'PULLBACK_RECLAIM') & (s.higher_state == state)]
    return None if q.empty else q.iloc[0]


def gate_for(s: pd.DataFrame, entry_tf: str):
    n_min = 20 if entry_tf == '5m' else 10
    details = {}
    enough = True
    supported = True
    strong_effect = True
    for part in ['external', 'development', 'reference_validation']:
        bear = state_row(s, part, entry_tf, 'STRONG_BEAR')
        bull = state_row(s, part, entry_tf, 'STRONG_BULL')
        if bear is None or bull is None:
            enough = False
            supported = False
            strong_effect = False
            details[part] = {'status': 'MISSING_STATE'}
            continue
        ok_n = int(bear.n) >= n_min and int(bull.n) >= n_min
        bmed = bear.median_bars_soft_uncensored
        umed = bull.median_bars_soft_uncensored
        bsurv = bear.soft_survival_6
        usurv = bull.soft_survival_6
        if pd.isna(bmed) or pd.isna(umed) or pd.isna(bsurv) or pd.isna(usurv):
            ok_n = False
        delta = None if pd.isna(bsurv) or pd.isna(usurv) else float(bsurv - usurv)
        this_support = bool(ok_n and float(bmed) < float(umed) and delta <= -0.10) if ok_n else False
        this_strong = bool(ok_n and float(bmed) < float(umed) and delta <= -0.20) if ok_n else False
        enough = enough and ok_n
        supported = supported and this_support
        strong_effect = strong_effect and this_strong
        details[part] = {
            'bear_n': int(bear.n), 'bull_n': int(bull.n),
            'bear_median_soft_bars': None if pd.isna(bmed) else float(bmed),
            'bull_median_soft_bars': None if pd.isna(umed) else float(umed),
            'bear_soft_survival_6': None if pd.isna(bsurv) else float(bsurv),
            'bull_soft_survival_6': None if pd.isna(usurv) else float(usurv),
            'survival_delta_pp': None if delta is None else delta * 100,
        }
    status = 'INCONCLUSIVE' if not enough else ('PASS' if supported else 'FAIL')
    return {'status': status, 'strong_effect': bool(enough and strong_effect), 'details': details}


def pct(v):
    return '-' if v is None or pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=1):
    return '-' if v is None or pd.isna(v) else f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    rows = []
    for entry_tf, cfg in PAIRS.items():
        z = b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['rule'])))
        h = b22e.add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['higher_rule'])))
        close_clock = z.index + cfg['dur']
        hs = b22e.higher_state(h, cfg['higher_dur'], close_clock)
        for ent in ENTRY_TYPES:
            rows.extend(collect_events(z, hs, entry_tf, cfg['higher_name'], ent, cfg['dur']))

    events = pd.DataFrame(rows)
    events.to_csv(OUT_EVENTS, index=False)
    s = summarize(events)
    s.to_csv(OUT_SUMMARY, index=False)

    gates = {'5m_to_1h': gate_for(s, '5m'), '1h_to_4h': gate_for(s, '1h')}
    payload = {
        'experiment': 'B22F_CONTINUOUS_MA_FAILURE_SURVIVAL',
        'data_rows_5m': int(len(x5)), 'coverage': float(coverage), 'gates': gates,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Continuous MA Failure Survival B22F — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Every completed candle after entry is monitored continuously. No six-bar fakeout cutoff is used. The tables below show how long the bullish MA structure survives before first failure.', '',
        '## Pullback/reclaim survival by higher-TF state', '',
        '| Partition | Entry→HTF | HTF state | N | Median bars→soft fail | Soft survive 1 | 2 | 3 | 4 | 6 | 12 | 24 | 48 | Median bars→hard fail |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    prim = s[s.entry_type == 'PULLBACK_RECLAIM'].copy()
    order = {'STRONG_BEAR': 0, 'NEUTRAL': 1, 'STRONG_BULL': 2}
    prim['ord'] = prim.higher_state.map(order).fillna(9)
    prim = prim.sort_values(['partition', 'entry_tf', 'ord'])
    for r in prim.itertuples(index=False):
        surv = [pct(getattr(r, f'soft_survival_{k}')) for k in CHECKPOINTS]
        md.append(
            f'| {r.partition} | {r.entry_tf}→{r.higher_tf} | {r.higher_state} | {r.n} | '
            f'{num(r.median_bars_soft_uncensored)} | ' + ' | '.join(surv) +
            f' | {num(r.median_bars_hard_uncensored)} |'
        )

    md += ['', '## Frozen opposing-HTF hypothesis', '']
    for key, g in gates.items():
        md.append(f'- {key}: **{g["status"]}**; >=20pp strong effect: **{"YES" if g["strong_effect"] else "NO"}**')
        for p, d in g['details'].items():
            if 'survival_delta_pp' not in d:
                md.append(f'  - {p}: {d["status"]}')
            else:
                md.append(
                    f'  - {p}: bear N={d["bear_n"]}, bull N={d["bull_n"]}; median soft failure '
                    f'{num(d["bear_median_soft_bars"])} vs {num(d["bull_median_soft_bars"])} bars; '
                    f'bar-6 survival {pct(d["bear_soft_survival_6"])} vs {pct(d["bull_soft_survival_6"])} '
                    f'(Δ {d["survival_delta_pp"]:+.2f}pp)'
                )

    md += ['', '## Interpretation', '',
           '- Failure time starts at bar 1 immediately after execution and every later candle is inspected.',
           '- Because every trend eventually ends, eventual failure alone is not called a fakeout; earlier failure is the object of comparison.',
           '- Higher-TF states are causally shifted to candle-close availability.',
           '- Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
