#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b
import btc_previous_session_direct_sweep_b26c as b26c

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Result.md'
OUT_SUM = ROOT / 'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Summary.csv'
OUT_COMBO = ROOT / 'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Combos.csv'
OUT_EVENTS = ROOT / 'BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Events.csv'

PARTS = b22b.PARTS
TRANSITIONS = b26c.TRANSITIONS
TF_MINUTES = {'15m': 15, '1h': 60}
TOLS = {'TOL_0.10': 0.001, 'TOL_0.20': 0.002}
BAR5 = pd.Timedelta(minutes=5)


def session_bars(q5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp, tf_min: int) -> pd.DataFrame:
    if q5.empty:
        return pd.DataFrame()
    delta_min = ((q5.index - start) / pd.Timedelta(minutes=1)).astype(int)
    bucket = (delta_min // tf_min).astype(int)
    z = q5.assign(_bucket=bucket).groupby('_bucket', sort=True).agg(
        open=('open','first'), high=('high','max'), low=('low','min'), close=('close','last'), n5=('close','size')
    )
    starts = [start + pd.Timedelta(minutes=tf_min*int(k)) for k in z.index]
    ends = [min(s + pd.Timedelta(minutes=tf_min), end) for s in starts]
    z.index = pd.DatetimeIndex(starts)
    z['bar_end'] = pd.DatetimeIndex(ends)
    z['partial_bar'] = [(e-s) < pd.Timedelta(minutes=tf_min) for s,e in zip(starts,ends)]
    return z


def intersects(high: float, low: float, level: float, tol: float) -> bool:
    zl = level * (1.0 - tol)
    zu = level * (1.0 + tol)
    return high >= zl and low <= zu


def observe(bars: pd.DataFrame, prev_hi: float, prev_lo: float, tol: float):
    hi_visits = lo_visits = 0
    hi_raw = lo_raw = 0
    hi_reject = lo_reject = 0
    both_zone_bars = 0
    hi_touching = lo_touching = False
    direction = 'NO_BREAK'
    breakout_ts = pd.NaT
    breakout_bar_start = pd.NaT
    partial_breakout = False

    hi_zl, hi_zu = prev_hi*(1-tol), prev_hi*(1+tol)
    lo_zl, lo_zu = prev_lo*(1-tol), prev_lo*(1+tol)

    for ts, r in bars.iterrows():
        close = float(r.close); high = float(r.high); low = float(r.low)
        break_hi = close > prev_hi
        break_lo = close < prev_lo
        if break_hi or break_lo:
            direction = 'BULL' if break_hi else 'BEAR'
            breakout_ts = r.bar_end
            breakout_bar_start = ts
            partial_breakout = bool(r.partial_bar)
            break

        hit_hi = intersects(high, low, prev_hi, tol)
        hit_lo = intersects(high, low, prev_lo, tol)
        if hit_hi:
            hi_raw += 1
            if not hi_touching:
                hi_visits += 1
            if close < hi_zl:
                hi_reject += 1
        if hit_lo:
            lo_raw += 1
            if not lo_touching:
                lo_visits += 1
            if close > lo_zu:
                lo_reject += 1
        if hit_hi and hit_lo:
            both_zone_bars += 1

        # A distinct visit requires a full subsequent TF bar with no zone intersection.
        hi_touching = bool(hit_hi)
        lo_touching = bool(hit_lo)

    return {
        'direction': direction,
        'breakout_ts': breakout_ts,
        'breakout_bar_start': breakout_bar_start,
        'breakout_on_partial_bar': partial_breakout,
        'high_retests': int(hi_visits),
        'low_retests': int(lo_visits),
        'high_raw_touch_bars': int(hi_raw),
        'low_raw_touch_bars': int(lo_raw),
        'high_rejection_bars': int(hi_reject),
        'low_rejection_bars': int(lo_reject),
        'both_zone_bars': int(both_zone_bars),
    }


def simulate_day(x5, part, part_start, part_end, transition, cfg, day, tf_name, tf_min, tol_name, tol):
    prev_start = b26c.ts_for_day(day, cfg['prev_start'])
    prev_end = b26c.ts_for_day(day, cfg['prev_end'])
    next_start = b26c.ts_for_day(day, cfg['next_start'])
    next_end = b26c.ts_for_day(day, cfg['next_end'])
    if prev_start < part_start or next_end > part_end:
        return None
    prev = x5[(x5.index >= prev_start) & (x5.index < prev_end)]
    q5 = x5[(x5.index >= next_start) & (x5.index < next_end)]
    exp_prev = int((prev_end-prev_start)/BAR5)
    exp_next = int((next_end-next_start)/BAR5)
    if len(prev) != exp_prev or len(q5) != exp_next:
        return None
    prev_hi = float(prev.high.max()); prev_lo = float(prev.low.min())
    bars = session_bars(q5, next_start, next_end, tf_min)
    if bars.empty:
        return None
    obs = observe(bars, prev_hi, prev_lo, tol)
    return {
        'partition': part,
        'transition': transition,
        'date_utc': str(day.date()),
        'tf': tf_name,
        'tolerance': tol_name,
        'tol_value': tol,
        'previous_session_high': prev_hi,
        'previous_session_low': prev_lo,
        'active_session_start': next_start,
        'active_session_end': next_end,
        'active_tf_bars': int(len(bars)),
        'partial_tf_bars': int(bars.partial_bar.sum()),
        **obs,
    }


def qtile(s, q):
    return float(pd.to_numeric(s, errors='coerce').quantile(q)) if len(s) else np.nan


def summarize(g: pd.DataFrame):
    if len(g) == 0:
        return {'n':0}
    out = {'n': int(len(g))}
    for col, prefix in [
        ('high_retests','hi'), ('low_retests','lo'),
        ('high_raw_touch_bars','hi_raw'), ('low_raw_touch_bars','lo_raw'),
        ('high_rejection_bars','hi_rej'), ('low_rejection_bars','lo_rej')]:
        s = pd.to_numeric(g[col], errors='coerce')
        out[f'{prefix}_mean'] = float(s.mean())
        out[f'{prefix}_median'] = float(s.median())
        out[f'{prefix}_p75'] = qtile(s, .75)
        out[f'{prefix}_max'] = int(s.max())
        for k in (1,2,3,4):
            out[f'{prefix}_ge{k}'] = float((s >= k).mean())
    out['both_zone_bar_rate'] = float((g.both_zone_bars > 0).mean())
    out['partial_breakout_rate'] = float(g.breakout_on_partial_bar.astype(bool).mean())
    return out


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    rows = []
    for part, (start, end) in PARTS.items():
        first_day = start.normalize(); last_day = (end-pd.Timedelta(seconds=1)).normalize()
        for day in pd.date_range(first_day, last_day, freq='D', tz='UTC'):
            if day.weekday() >= 5:
                continue
            for transition, cfg in TRANSITIONS.items():
                for tf_name, tf_min in TF_MINUTES.items():
                    for tol_name, tol in TOLS.items():
                        r = simulate_day(x5, part, start, end, transition, cfg, day, tf_name, tf_min, tol_name, tol)
                        if r is not None:
                            rows.append(r)
    events = pd.DataFrame(rows)
    events.to_csv(OUT_EVENTS, index=False)

    sums = []
    dirs = ['BULL','BEAR','NO_BREAK']
    for tf_name in TF_MINUTES:
        for tol_name in TOLS:
            for transition in TRANSITIONS:
                for part in PARTS:
                    base = events[(events.tf==tf_name)&(events.tolerance==tol_name)&(events.transition==transition)&(events.partition==part)]
                    for direction in dirs:
                        g = base[base.direction==direction]
                        sums.append({'tf':tf_name,'tolerance':tol_name,'transition':transition,'partition':part,'direction':direction,**summarize(g)})
    s = pd.DataFrame(sums)
    s.to_csv(OUT_SUM, index=False)

    combos = (events.groupby(['tf','tolerance','transition','partition','direction','high_retests','low_retests'], dropna=False)
              .size().reset_index(name='n'))
    combos['share_within_group'] = combos['n'] / combos.groupby(['tf','tolerance','transition','partition','direction'])['n'].transform('sum')
    combos.to_csv(OUT_COMBO, index=False)

    md = [
        '# B27L — Previous-Session High/Low Retest Atlas', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.', '',
        'Faithful session-level detector: completed previous-session High/Low are frozen; active session is observed on 15m and 1H bars. Retest zones are ±0.10% and ±0.20%. BULL = first strict close above previous-session High; BEAR = first strict close below previous-session Low; NO_BREAK = neither by session end.', '',
        'Two touch metrics are retained: **distinct retests** (consecutive zone-intersecting TF bars collapse to one visit) and **raw touch bars** (every TF bar intersecting the zone before breakout). This makes visual repeated taps auditable instead of forcing one interpretation.', '',
        '1H bars are anchored to active-session start; the final 30-minute session-close partial bar is retained and flagged for London/New York windows rather than mixing the next session.', '',
        '## Direction sample counts', '',
        '| TF | Tol | Transition | Partition | Bull N | Bear N | No-break N |',
        '|---|---|---|---|---:|---:|---:|'
    ]
    count = s.pivot_table(index=['tf','tolerance','transition','partition'], columns='direction', values='n', fill_value=0).reset_index()
    for r in count.itertuples(index=False):
        md.append(f'| {r.tf} | {r.tolerance} | {r.transition} | {r.partition} | {int(getattr(r,"BULL",0))} | {int(getattr(r,"BEAR",0))} | {int(getattr(r,"NO_BREAK",0))} |')

    md += ['', '## Bull/Bear retest summary — distinct visits', '',
           '| TF | Tol | Transition | Partition | Dir | N | High retests med / mean / P75 / max | Low retests med / mean / P75 / max | H>=2 | H>=3 | L>=2 | L>=3 |',
           '|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|']
    use = s[s.direction.isin(['BULL','BEAR'])]
    for r in use.itertuples(index=False):
        if int(r.n) == 0: continue
        md.append(f'| {r.tf} | {r.tolerance} | {r.transition} | {r.partition} | {r.direction} | {int(r.n)} | {num(r.hi_median,1)} / {num(r.hi_mean,2)} / {num(r.hi_p75,1)} / {int(r.hi_max)} | {num(r.lo_median,1)} / {num(r.lo_mean,2)} / {num(r.lo_p75,1)} / {int(r.lo_max)} | {pct(r.hi_ge2)} | {pct(r.hi_ge3)} | {pct(r.lo_ge2)} | {pct(r.lo_ge3)} |')

    md += ['', '## Bull/Bear raw touch-candle summary', '',
           '| TF | Tol | Transition | Partition | Dir | N | High raw med / mean / P75 / max | Low raw med / mean / P75 / max | Hraw>=3 | Hraw>=4 | Lraw>=3 | Lraw>=4 |',
           '|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|']
    for r in use.itertuples(index=False):
        if int(r.n) == 0: continue
        md.append(f'| {r.tf} | {r.tolerance} | {r.transition} | {r.partition} | {r.direction} | {int(r.n)} | {num(r.hi_raw_median,1)} / {num(r.hi_raw_mean,2)} / {num(r.hi_raw_p75,1)} / {int(r.hi_raw_max)} | {num(r.lo_raw_median,1)} / {num(r.lo_raw_mean,2)} / {num(r.lo_raw_p75,1)} / {int(r.lo_raw_max)} | {pct(r.hi_raw_ge3)} | {pct(r.hi_raw_ge4)} | {pct(r.lo_raw_ge3)} | {pct(r.lo_raw_ge4)} |')

    md += ['', '## Exact combinations', '',
           'Every exact `(High distinct retests, Low distinct retests)` combination and frequency is persisted in `BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Combos.csv`. Raw day-level observations are in `BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Events.csv`.', '',
           'Diagnostic only. No retest-count bucket is a validated trading rule.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')


if __name__ == '__main__':
    main()
