#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_OPPOSING_HTF_FAKEOUT_B22E_Result.md'
OUT_JSON = ROOT / 'BTC_OPPOSING_HTF_FAKEOUT_B22E_Result.json'
OUT_CSV = ROOT / 'BTC_OPPOSING_HTF_FAKEOUT_B22E_Summary.csv'
OUT_EVENTS = ROOT / 'BTC_OPPOSING_HTF_FAKEOUT_B22E_Events.csv'

PARTS = b22b.PARTS
ENTRY_TYPES = ['PULLBACK_RECLAIM', 'CROSSOVER_INIT']
PAIRS = {
    '5m': {'rule': '5min', 'dur': pd.Timedelta(minutes=5), 'higher_rule': '1h', 'higher_dur': pd.Timedelta(hours=1), 'higher_name': '1h'},
    '1h': {'rule': '1h', 'dur': pd.Timedelta(hours=1), 'higher_rule': '4h', 'higher_dur': pd.Timedelta(hours=4), 'higher_name': '4h'},
}


def add_bear(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    x['bear_spread'] = (x.ema50 - x.ema20) / x.close
    x['bear_strong'] = (
        (x.ema20 < x.ema50)
        & (x.ema20 < x.ema20.shift(3))
        & (x.ema50 < x.ema50.shift(3))
        & (x.bear_spread > x.bear_spread.shift(3))
        & (x.close < x.ema20)
    )
    return x


def available_bool(source: pd.Series, source_dur: pd.Timedelta, target_close: pd.DatetimeIndex) -> np.ndarray:
    s = source.fillna(False).astype(bool).copy()
    s.index = s.index + source_dur
    return s.reindex(target_close, method='ffill').fillna(False).to_numpy(bool)


def higher_state(higher: pd.DataFrame, higher_dur: pd.Timedelta, target_close: pd.DatetimeIndex) -> np.ndarray:
    bull = available_bool(higher.strong, higher_dur, target_close)
    bear = available_bool(higher.bear_strong, higher_dur, target_close)
    out = np.full(len(target_close), 'NEUTRAL', dtype=object)
    out[bull] = 'STRONG_BULL'
    out[bear] = 'STRONG_BEAR'
    return out


def collect_events(z: pd.DataFrame, hstate: np.ndarray, entry_tf: str, higher_tf: str, entry_type: str):
    sig = z[f'entry_{entry_type}'].fillna(False).to_numpy(bool)
    idx = z.index
    opens = z.open.to_numpy(float)
    highs = z.high.to_numpy(float)
    lows = z.low.to_numpy(float)
    closes = z.close.to_numpy(float)
    ema20 = z.ema20.to_numpy(float)
    ema50 = z.ema50.to_numpy(float)
    spread = z.spread.to_numpy(float)
    strong = z.strong.fillna(False).to_numpy(bool)

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
        for s_i in np.flatnonzero(sig[lo:max(lo, hi-1)]):
            s_i = int(s_i + lo)
            e_i = s_i + 1
            if e_i >= hi:
                continue
            six_end = min(e_i + 6, hi)
            twelve_end = min(e_i + 12, hi)
            if six_end - e_i < 6:
                continue
            entry = opens[e_i]
            fake6 = bool(np.any(soft[e_i:six_end]))
            hard12 = bool(np.any(hard[e_i:twelve_end])) if twelve_end > e_i else False
            mfe6 = float(np.nanmax(highs[e_i:six_end]) / entry - 1.0)
            mae6 = float(np.nanmin(lows[e_i:six_end]) / entry - 1.0)
            ret6 = float(closes[six_end-1] / entry - 1.0)
            strong_frac6 = float(np.mean(strong[e_i:six_end]))
            first_soft_bar = None
            hit = np.flatnonzero(soft[e_i:six_end])
            if len(hit):
                first_soft_bar = int(hit[0] + 1)
            rows.append({
                'partition': part,
                'entry_tf': entry_tf,
                'higher_tf': higher_tf,
                'entry_type': entry_type,
                'signal_ts': idx[s_i],
                'entry_ts': idx[e_i],
                'higher_state': str(hstate[s_i]),
                'entry_px': float(entry),
                'fakeout_ma6': fake6,
                'hard_reversal_12': hard12,
                'ret6': ret6,
                'mfe6': mfe6,
                'mae6': mae6,
                'strong_frac6': strong_frac6,
                'first_soft_failure_bar': first_soft_bar,
                'signal_ema20': float(ema20[s_i]),
                'signal_ema50': float(ema50[s_i]),
                'signal_spread': float(spread[s_i]),
            })
    return rows


def summarize(events: pd.DataFrame) -> pd.DataFrame:
    rows = []
    keys = ['partition', 'entry_tf', 'higher_tf', 'entry_type', 'higher_state']
    for k, g in events.groupby(keys, dropna=False):
        rows.append({
            **dict(zip(keys, k)),
            'n': int(len(g)),
            'fakeout_ma6_rate': float(g.fakeout_ma6.mean()),
            'hard_reversal_12_rate': float(g.hard_reversal_12.mean()),
            'median_ret6': float(g.ret6.median()),
            'median_mfe6': float(g.mfe6.median()),
            'median_mae6': float(g.mae6.median()),
            'mean_strong_frac6': float(g.strong_frac6.mean()),
        })
    return pd.DataFrame(rows)


def state_row(s: pd.DataFrame, part: str, entry_tf: str, state: str):
    q = s[(s.partition == part) & (s.entry_tf == entry_tf) & (s.entry_type == 'PULLBACK_RECLAIM') & (s.higher_state == state)]
    return None if q.empty else q.iloc[0]


def gate_for(s: pd.DataFrame, entry_tf: str):
    n_min = 20 if entry_tf == '5m' else 10
    details = {}
    enough = True
    direction10 = True
    direction20 = True
    for part in ['external', 'development', 'reference_validation']:
        b = state_row(s, part, entry_tf, 'STRONG_BEAR')
        u = state_row(s, part, entry_tf, 'STRONG_BULL')
        if b is None or u is None:
            enough = False; direction10 = False; direction20 = False
            details[part] = {'status': 'MISSING_STATE'}
            continue
        delta = float(b.fakeout_ma6_rate - u.fakeout_ma6_rate)
        ok_n = int(b.n) >= n_min
        enough = enough and ok_n
        direction10 = direction10 and ok_n and delta >= .10
        direction20 = direction20 and ok_n and delta >= .20
        details[part] = {
            'bear_n': int(b.n), 'bull_n': int(u.n),
            'bear_fakeout': float(b.fakeout_ma6_rate),
            'bull_fakeout': float(u.fakeout_ma6_rate),
            'delta_pp': delta * 100,
        }
    status = 'INCONCLUSIVE' if not enough else ('PASS' if direction10 else 'FAIL')
    strong = bool(enough and direction20)
    return {'status': status, 'strong_effect': strong, 'details': details}


def pct(v):
    return '-' if v is None or pd.isna(v) else f'{100*float(v):.2f}%'


def main():
    x5, coverage = b21.load5()
    all_rows = []
    for entry_tf, cfg in PAIRS.items():
        z = add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['rule'])))
        h = add_bear(b22b.enrich(b22b.resample_ohlc(x5, cfg['higher_rule'])))
        close_clock = z.index + cfg['dur']
        hs = higher_state(h, cfg['higher_dur'], close_clock)
        for ent in ENTRY_TYPES:
            all_rows.extend(collect_events(z, hs, entry_tf, cfg['higher_name'], ent))

    events = pd.DataFrame(all_rows)
    events.to_csv(OUT_EVENTS, index=False)
    s = summarize(events)
    s.to_csv(OUT_CSV, index=False)

    gates = {
        '5m_to_1h': gate_for(s, '5m'),
        '1h_to_4h': gate_for(s, '1h'),
    }
    payload = {
        'experiment': 'B22E_OPPOSING_HTF_FAKEOUT',
        'data_rows_5m': int(len(x5)),
        'coverage': float(coverage),
        'gates': gates,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + '\n')

    md = [
        '# BTC Opposing Higher-TF Fakeout B22E — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        'Primary fakeout = within first 6 entry-TF bars after execution: close < EMA20, EMA20 turns down, and bullish EMA spread narrows. This is an immediate MA-structure failure, not a failed higher-high label.', '',
        '## Pullback/reclaim primary comparison', '',
        '| Partition | Entry→Higher TF | Higher state | N | Fakeout MA6 | Hard reversal 12 | Median ret6 | Median MFE6 | Median MAE6 | Strong-shape persistence |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    prim = s[s.entry_type == 'PULLBACK_RECLAIM'].copy()
    order = {'STRONG_BEAR':0, 'NEUTRAL':1, 'STRONG_BULL':2}
    prim['ord'] = prim.higher_state.map(order).fillna(9)
    prim = prim.sort_values(['partition','entry_tf','ord'])
    for r in prim.itertuples(index=False):
        md.append(f'| {r.partition} | {r.entry_tf}→{r.higher_tf} | {r.higher_state} | {r.n} | {pct(r.fakeout_ma6_rate)} | {pct(r.hard_reversal_12_rate)} | {pct(r.median_ret6)} | {pct(r.median_mfe6)} | {pct(r.median_mae6)} | {pct(r.mean_strong_frac6)} |')

    md += ['', '## Frozen hypothesis gates', '']
    for key, g in gates.items():
        md.append(f'- {key}: **{g["status"]}**; strong >=20pp effect: **{"YES" if g["strong_effect"] else "NO"}**')
        for p, d in g['details'].items():
            if 'delta_pp' in d:
                md.append(f'  - {p}: bear N={d["bear_n"]}, bull N={d["bull_n"]}, fakeout {100*d["bear_fakeout"]:.2f}% vs {100*d["bull_fakeout"]:.2f}% (Δ {d["delta_pp"]:+.2f}pp)')
            else:
                md.append(f'  - {p}: {d["status"]}')

    md += ['', '## Secondary crossover diagnostic', '',
           'CROSSOVER_INIT groups are included in the CSV/events for diagnosis but do not determine the preregistered gate.', '',
           'All higher-TF states are shifted to candle-close availability. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
