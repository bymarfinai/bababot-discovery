#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import math
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Result.md'
OUT_JSON = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Result.json'
OUT_CSV = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Cascades.csv'
OUT_STAGE = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Stage_Summary.csv'
OUT_LAGS = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Lag_Summary.csv'
OUT_LATEST = ROOT / 'BTC_MTF_BULL_CASCADE_B21_Latest_State.json'

BASE = 'https://data.binance.vision/data/futures/um'
FETCH_START = pd.Timestamp('2019-09-01T00:00:00Z')
ANALYSIS_START = pd.Timestamp('2020-01-01T00:00:00Z')
END = pd.Timestamp('2026-08-21T00:00:00Z')
HORIZON = pd.Timedelta(days=7)

PARTS = {
    'external': (pd.Timestamp('2020-01-01', tz='UTC'), pd.Timestamp('2022-01-01', tz='UTC')),
    'development': (pd.Timestamp('2022-01-01', tz='UTC'), pd.Timestamp('2025-01-01', tz='UTC')),
    'reference_validation': (pd.Timestamp('2025-01-01', tz='UTC'), pd.Timestamp('2026-07-30', tz='UTC')),
    'august': (pd.Timestamp('2026-08-01', tz='UTC'), pd.Timestamp('2026-08-21', tz='UTC')),
}
MAJOR = ('external', 'development', 'reference_validation')
STAGES = ['S0_5M', 'S1_15M', 'S2_1H', 'S3_4H', 'S4_1D']
TF_ORDER = ['m5', 'm15', 'h1', 'h4', 'd1']
DURS = {
    'm5': pd.Timedelta(minutes=5),
    'm15': pd.Timedelta(minutes=15),
    'h1': pd.Timedelta(hours=1),
    'h4': pd.Timedelta(hours=4),
    'd1': pd.Timedelta(days=1),
}


def _urls():
    urls = []
    current = pd.Timestamp(FETCH_START.year, FETCH_START.month, 1, tz='UTC')
    end_month = pd.Timestamp(END.year, END.month, 1, tz='UTC')
    while current < end_month:
        ym = current.strftime('%Y-%m')
        urls.append(f'{BASE}/monthly/klines/BTCUSDT/5m/BTCUSDT-5m-{ym}.zip')
        current += pd.offsets.MonthBegin(1)
    d = end_month
    while d < END.normalize():
        ds = d.strftime('%Y-%m-%d')
        urls.append(f'{BASE}/daily/klines/BTCUSDT/5m/BTCUSDT-5m-{ds}.zip')
        d += pd.Timedelta(days=1)
    return urls


def _fetch_one(url: str):
    r = requests.get(url, timeout=90, headers={'User-Agent': 'bababot-b21/1.0'})
    if r.status_code == 404:
        return None
    r.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(r.content)) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith('.csv')]
        if not names:
            return None
        with zf.open(names[0]) as fh:
            z = pd.read_csv(fh, header=None, usecols=[0, 1, 2, 3, 4], names=['ts', 'open', 'high', 'low', 'close'])
    return z


def load5():
    frames = []
    urls = _urls()
    with ThreadPoolExecutor(max_workers=10) as ex:
        futs = {ex.submit(_fetch_one, u): u for u in urls}
        for fut in as_completed(futs):
            z = fut.result()
            if z is not None and len(z):
                frames.append(z)
    if not frames:
        raise RuntimeError('No Binance 5m data downloaded')
    x = pd.concat(frames, ignore_index=True)
    t = pd.to_numeric(x['ts'], errors='coerce')
    # Binance archives may use microseconds in newer files.
    t = np.where(t > 100_000_000_000_000, t / 1000.0, t)
    x['ts'] = pd.to_datetime(t, unit='ms', utc=True, errors='coerce')
    for c in ['open', 'high', 'low', 'close']:
        x[c] = pd.to_numeric(x[c], errors='coerce')
    x = x.dropna().drop_duplicates('ts').sort_values('ts')
    x = x[(x.ts >= FETCH_START) & (x.ts < END)].set_index('ts')
    if len(x) < 650_000:
        raise RuntimeError(f'Insufficient 5m rows: {len(x)}')
    # Verify continuity quality rather than silently interpolating missing bars.
    idx = x.index
    expected = int((idx[-1] - idx[0]) / pd.Timedelta(minutes=5)) + 1
    coverage = len(x) / expected
    if coverage < 0.995:
        raise RuntimeError(f'5m coverage too low: {coverage:.6f}')
    return x, coverage


def _resample(src: pd.DataFrame, rule: str):
    return src[['open', 'high', 'low', 'close']].resample(
        rule, origin='start_day', label='left', closed='left'
    ).agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'}).dropna()


def _bull_available(frame: pd.DataFrame, duration: pd.Timedelta):
    z = frame[['close']].copy()
    z['sma7'] = z.close.rolling(7, min_periods=7).mean()
    z['sma25'] = z.close.rolling(25, min_periods=25).mean()
    z['sma99'] = z.close.rolling(99, min_periods=99).mean()
    z['bull'] = (z.sma7 > z.sma25) & (z.sma25 > z.sma99) & (z.close > z.sma25)
    out = z[['bull', 'close', 'sma7', 'sma25', 'sma99']].copy()
    out.index = out.index + duration
    return out


def build_state_table(x5: pd.DataFrame):
    frames = {
        'm5': x5[['open', 'high', 'low', 'close']].copy(),
        'm15': _resample(x5, '15min'),
        'h1': _resample(x5, '1h'),
        'h4': _resample(x5, '4h'),
        'd1': _resample(x5, '1d'),
    }
    idx = x5.index[(x5.index >= ANALYSIS_START) & (x5.index < END)]
    q = pd.DataFrame(index=idx)
    for tf in TF_ORDER:
        av = _bull_available(frames[tf], DURS[tf])
        mapped = av.reindex(idx, method='ffill')
        q[f'{tf}_bull'] = mapped.bull.fillna(False).astype(bool)
        q[f'{tf}_close'] = mapped.close
        q[f'{tf}_sma25'] = mapped.sma25
    return q


def _on_times(state: pd.Series):
    s = state.fillna(False).astype(bool)
    return s.index[s & ~s.shift(1, fill_value=False)].asi8


def _first_on(on_ns: np.ndarray, seed: pd.Timestamp):
    s = seed.value
    j = int(np.searchsorted(on_ns, s, side='left'))
    if j >= len(on_ns):
        return pd.NaT
    t = pd.Timestamp(on_ns[j], tz='UTC')
    return t if t <= seed + HORIZON else pd.NaT


def _partition(t: pd.Timestamp):
    for name, (a, z) in PARTS.items():
        if a <= t < z:
            return name
    return None


def _fwd(x5: pd.DataFrame, seed: pd.Timestamp, hours: int):
    end = seed + pd.Timedelta(hours=hours)
    data_end = x5.index[-1] + pd.Timedelta(minutes=5)
    if end > data_end:
        return {'n_ok': 0, 'ret': None, 'mfe': None, 'mae': None}
    if seed not in x5.index:
        return {'n_ok': 0, 'ret': None, 'mfe': None, 'mae': None}
    q = x5[(x5.index >= seed) & (x5.index < end)]
    if len(q) < int(hours * 12 * 0.995):
        return {'n_ok': 0, 'ret': None, 'mfe': None, 'mae': None}
    entry = float(x5.loc[seed, 'open'])
    # close of last completed bar before the horizon boundary
    final = float(q.iloc[-1].close)
    return {
        'n_ok': 1,
        'ret': final / entry - 1.0,
        'mfe': float(q.high.max()) / entry - 1.0,
        'mae': float(q.low.min()) / entry - 1.0,
    }


def build_cascades(states: pd.DataFrame, x5: pd.DataFrame):
    on = {tf: _on_times(states[f'{tf}_bull']) for tf in TF_ORDER[1:]}
    seed_mask = states.m5_bull & ~states.m5_bull.shift(1, fill_value=False)
    seeds = states.index[seed_mask]
    rows = []
    for seed in seeds:
        part = _partition(seed)
        if part is None:
            continue
        raw = {tf: _first_on(on[tf], seed) for tf in TF_ORDER[1:]}
        stage = 0
        prev = seed
        lags = {}
        valid_chain = True
        for i, tf in enumerate(TF_ORDER[1:], 1):
            t = raw[tf]
            if pd.isna(t) or t < prev:
                valid_chain = False
            if valid_chain:
                stage = i
                lags[tf] = float((t - prev) / pd.Timedelta(hours=1))
                prev = t
            else:
                lags[tf] = None
        pos = states.index.get_loc(seed)
        prevrow = states.iloc[pos - 1] if pos > 0 else states.iloc[pos]
        fresh = all(not bool(prevrow[f'{tf}_bull']) for tf in TF_ORDER[1:])
        f24 = _fwd(x5, seed, 24)
        f72 = _fwd(x5, seed, 72)
        f168 = _fwd(x5, seed, 168)
        row = {
            'partition': part,
            'seed_ts': seed,
            'fresh': fresh,
            'stage_index': stage,
            'stage': STAGES[stage],
            'ordered_d1_cascade': stage == 4,
            'on_15m': raw['m15'],
            'on_1h': raw['h1'],
            'on_4h': raw['h4'],
            'on_1d': raw['d1'],
            'lag_5m_to_15m_h': lags.get('m15'),
            'lag_15m_to_1h_h': lags.get('h1'),
            'lag_1h_to_4h_h': lags.get('h4'),
            'lag_4h_to_1d_h': lags.get('d1'),
            'lag_seed_to_deepest_h': float((prev - seed) / pd.Timedelta(hours=1)) if stage > 0 else 0.0,
            'ret24': f24['ret'], 'mfe24': f24['mfe'], 'mae24': f24['mae'],
            'ret72': f72['ret'], 'mfe72': f72['mfe'], 'mae72': f72['mae'],
            'ret168': f168['ret'], 'mfe168': f168['mfe'], 'mae168': f168['mae'],
            'mfe3_72h': (f72['mfe'] >= .03) if f72['n_ok'] else None,
            'mfe5_72h': (f72['mfe'] >= .05) if f72['n_ok'] else None,
            'mfe8_168h': (f168['mfe'] >= .08) if f168['n_ok'] else None,
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _safe_mean(s):
    x = pd.to_numeric(s, errors='coerce').dropna()
    return float(x.mean()) if len(x) else None


def _safe_median(s):
    x = pd.to_numeric(s, errors='coerce').dropna()
    return float(x.median()) if len(x) else None


def stage_summary(casc: pd.DataFrame):
    rows = []
    for part in PARTS:
        p = casc[casc.partition == part]
        for fresh_name, fresh_mask in [('ALL', pd.Series(True, index=p.index)), ('FRESH', p.fresh.astype(bool))]:
            z0 = p[fresh_mask]
            for i, stage in enumerate(STAGES):
                z = z0[z0.stage_index == i]
                f72 = z[z.mfe72.notna()]
                f168 = z[z.mfe168.notna()]
                rows.append({
                    'partition': part,
                    'cohort': fresh_name,
                    'stage_index': i,
                    'stage': stage,
                    'seeds': len(z),
                    'n72': len(f72),
                    'positive_ret72_rate': _safe_mean((f72.ret72 > 0).astype(float)) if len(f72) else None,
                    'median_ret72': _safe_median(f72.ret72),
                    'median_mfe72': _safe_median(f72.mfe72),
                    'median_mae72': _safe_median(f72.mae72),
                    'mfe3_72h_rate': _safe_mean(f72.mfe3_72h.astype(float)) if len(f72) else None,
                    'mfe5_72h_rate': _safe_mean(f72.mfe5_72h.astype(float)) if len(f72) else None,
                    'n168': len(f168),
                    'median_ret168': _safe_median(f168.ret168),
                    'median_mfe168': _safe_median(f168.mfe168),
                    'mfe8_168h_rate': _safe_mean(f168.mfe8_168h.astype(float)) if len(f168) else None,
                })
    return pd.DataFrame(rows)


def lag_summary(casc: pd.DataFrame):
    mapping = [
        (1, 'lag_5m_to_15m_h', '5m→15m'),
        (2, 'lag_15m_to_1h_h', '15m→1h'),
        (3, 'lag_1h_to_4h_h', '1h→4h'),
        (4, 'lag_4h_to_1d_h', '4h→1d'),
    ]
    rows = []
    for part in PARTS:
        p = casc[casc.partition == part]
        for min_stage, col, leg in mapping:
            x = pd.to_numeric(p.loc[p.stage_index >= min_stage, col], errors='coerce').dropna()
            rows.append({
                'partition': part, 'leg': leg, 'n': len(x),
                'p25_h': float(x.quantile(.25)) if len(x) else None,
                'median_h': float(x.median()) if len(x) else None,
                'p75_h': float(x.quantile(.75)) if len(x) else None,
            })
    return pd.DataFrame(rows)


def _gate(stage: pd.DataFrame):
    detail = {}
    propagation_ok = True
    for part in MAJOR:
        p = stage[(stage.partition == part) & (stage.cohort == 'ALL')].sort_values('stage_index')
        d = {int(r.stage_index): r for r in p.itertuples(index=False)}
        s4 = d[4].seeds if 4 in d else 0
        s3 = d[3].seeds if 3 in d else 0
        sample_ok = s4 >= 30 or s3 >= 30
        sufficiently = [i for i in range(1, 5) if i in d and d[i].n72 >= 30 and d[i].mfe5_72h_rate is not None]
        deepest = max(sufficiently) if sufficiently else None
        s0 = d.get(0)
        compare_ok = False
        monotonic_ok = False
        if deepest is not None and s0 is not None and s0.n72 >= 30 and s0.mfe5_72h_rate is not None:
            deep = d[deepest]
            compare_ok = deep.mfe5_72h_rate > s0.mfe5_72h_rate and deep.median_mfe72 > s0.median_mfe72
            seq = [d[i].mfe5_72h_rate for i in sufficiently if i <= deepest]
            violations = sum((seq[j] + .05) < seq[j - 1] for j in range(1, len(seq)))
            monotonic_ok = violations <= 1
        part_ok = sample_ok and compare_ok and monotonic_ok
        propagation_ok &= part_ok
        detail[part] = {
            's3_seeds': int(s3), 's4_seeds': int(s4), 'deepest_n30_stage': deepest,
            'sample_ok': bool(sample_ok), 'compare_ok': bool(compare_ok),
            'monotonic_ok': bool(monotonic_ok), 'pass': bool(part_ok),
        }

    early_candidates = []
    for i in (1, 2):
        ok = True
        deltas = {}
        for part in MAJOR:
            p = stage[(stage.partition == part) & (stage.cohort == 'ALL')]
            d = {int(r.stage_index): r for r in p.itertuples(index=False)}
            if 0 not in d or i not in d or d[0].n72 < 50 or d[i].n72 < 50 or d[0].mfe5_72h_rate is None or d[i].mfe5_72h_rate is None:
                ok = False
                deltas[part] = None
            else:
                delta = d[i].mfe5_72h_rate - d[0].mfe5_72h_rate
                deltas[part] = float(delta)
                ok &= delta >= .10
        if ok:
            early_candidates.append({'stage': STAGES[i], 'deltas': deltas})
    return {
        'B21_PROPAGATION_SUPPORTED': bool(propagation_ok),
        'B21_EARLY_ENTRY_CLUE': bool(early_candidates),
        'early_candidates': early_candidates,
        'partition_detail': detail,
    }


def latest_state(states: pd.DataFrame):
    row = states.iloc[-1]
    t = states.index[-1]
    out = {'asof_research_clock': str(t)}
    for tf in TF_ORDER:
        s = states[f'{tf}_bull'].astype(bool)
        prior = s.loc[:t]
        flips = prior.index[prior & ~prior.shift(1, fill_value=False)]
        offs = prior.index[~prior & prior.shift(1, fill_value=False)]
        out[tf] = {
            'bull': bool(row[f'{tf}_bull']),
            'last_on': str(flips[-1]) if len(flips) else None,
            'last_off': str(offs[-1]) if len(offs) else None,
            'close': float(row[f'{tf}_close']) if pd.notna(row[f'{tf}_close']) else None,
            'sma25': float(row[f'{tf}_sma25']) if pd.notna(row[f'{tf}_sma25']) else None,
        }
    return out


def f_pct(x):
    return '-' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{100*x:.1f}%'


def f_num(x, d=2):
    return '-' if x is None or (isinstance(x, float) and not math.isfinite(x)) else f'{x:.{d}f}'


def main():
    x5, coverage = load5()
    states = build_state_table(x5)
    casc = build_cascades(states, x5)
    stage = stage_summary(casc)
    lags = lag_summary(casc)
    gates = _gate(stage)
    latest = latest_state(states)

    casc.to_csv(OUT_CSV, index=False)
    stage.to_csv(OUT_STAGE, index=False)
    lags.to_csv(OUT_LAGS, index=False)
    OUT_LATEST.write_text(json.dumps(latest, indent=2) + '\n')

    result = {
        'experiment': 'B21_MTF_BULL_CASCADE',
        'definition': 'SMA7>SMA25>SMA99 and close>SMA25 on completed bars',
        'data_rows_5m': int(len(x5)),
        'data_start': str(x5.index[0]),
        'data_end': str(x5.index[-1]),
        'coverage': float(coverage),
        'total_seeds': int(len(casc)),
        'partition_seeds': {p: int((casc.partition == p).sum()) for p in PARTS},
        'ordered_d1_cascades': {p: int(((casc.partition == p) & (casc.stage_index == 4)).sum()) for p in PARTS},
        'fresh_seeds': {p: int(((casc.partition == p) & casc.fresh).sum()) for p in PARTS},
        'gates': gates,
        'latest_state': latest,
    }
    OUT_JSON.write_text(json.dumps(result, indent=2) + '\n')

    md = [
        '# BTC MTF Bull Cascade B21 — Result', '',
        f"5m rows: **{len(x5):,}**; source coverage: **{coverage:.4%}**",
        f"Data: **{x5.index[0]} → {x5.index[-1]}**", '',
        'Frozen bull state: `SMA7 > SMA25 > SMA99 AND close > SMA25`, observable only after each timeframe candle closes.', '',
        '## Ordered cascade stage by partition', '',
        '| Partition | 5m seeds | S0 5m | S1 15m | S2 1h | S3 4h | S4 1d | Fresh seeds |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for part in PARTS:
        p = casc[casc.partition == part]
        counts = [(p.stage_index == i).sum() for i in range(5)]
        md.append(f"| {part} | {len(p)} | {counts[0]} | {counts[1]} | {counts[2]} | {counts[3]} | {counts[4]} | {int(p.fresh.sum())} |")

    md += ['', '## 72h outcome by deepest ordered stage — ALL seeds', '',
           '| Partition | Stage | N72 | Positive 72h | Median 72h ret | Median MFE | Median MAE | MFE≥5% |',
           '|---|---|---:|---:|---:|---:|---:|---:|']
    for r in stage[stage.cohort == 'ALL'].itertuples(index=False):
        md.append(f"| {r.partition} | {r.stage} | {r.n72} | {f_pct(r.positive_ret72_rate)} | {f_pct(r.median_ret72)} | {f_pct(r.median_mfe72)} | {f_pct(r.median_mae72)} | {f_pct(r.mfe5_72h_rate)} |")

    md += ['', '## Propagation lag distribution', '',
           '| Partition | Leg | N | P25 h | Median h | P75 h |',
           '|---|---|---:|---:|---:|---:|']
    for r in lags.itertuples(index=False):
        md.append(f"| {r.partition} | {r.leg} | {r.n} | {f_num(r.p25_h)} | {f_num(r.median_h)} | {f_num(r.p75_h)} |")

    md += ['', '## Gates', '',
           f"- B21_PROPAGATION_SUPPORTED: **{'PASS' if gates['B21_PROPAGATION_SUPPORTED'] else 'FAIL'}**",
           f"- B21_EARLY_ENTRY_CLUE: **{'PASS' if gates['B21_EARLY_ENTRY_CLUE'] else 'FAIL'}**", '']
    for part, d in gates['partition_detail'].items():
        md.append(f"- {part}: S3={d['s3_seeds']}, S4={d['s4_seeds']}, deepest N>=30={d['deepest_n30_stage']}, sample={d['sample_ok']}, deeper-vs-S0={d['compare_ok']}, monotonic={d['monotonic_ok']}.")

    md += ['', '## Latest causal state at dataset end', '', '| TF | Bull | Last ON | Last OFF |', '|---|---|---|---|']
    for tf in TF_ORDER:
        z = latest[tf]
        md.append(f"| {tf} | {'ON' if z['bull'] else 'OFF'} | {z['last_on'] or '-'} | {z['last_off'] or '-'} |")

    md += ['', 'B21 is a propagation-forensics experiment, not a live trading rule. No B20 result was changed and live BBC remains untouched.']
    OUT_MD.write_text('\n'.join(md) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
