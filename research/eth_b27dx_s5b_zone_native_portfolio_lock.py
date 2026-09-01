#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_b27dx_pair_calibration_v2.py'
spec = importlib.util.spec_from_file_location('eth_v2_base', BASE_PATH)
b = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(b)

PFX = 'ETH_B27DX_S5B_ZONE_NATIVE_PORTFOLIO_LOCK'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_SUMMARY = ROOT / f'{PFX}_Summary.csv'
OUT_ZONE = ROOT / f'{PFX}_ZoneSummary.csv'
OUT_STRESS = ROOT / f'{PFX}_Stress.csv'
OUT_PARITY = ROOT / f'{PFX}_Parity.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
REF_MIN = 300
HORIZON_MIN = 360
STOP_F = 0.35
PARTS = ('external', 'development', 'reference_validation')
ZONE_RULES = {
    300: {'zone': 'ETH_0500', 'entry_f': 0.80, 'target_ext': 0.30, 'tie': 0},
    540: {'zone': 'ETH_0900', 'entry_f': 0.80, 'target_ext': 0.25, 'tie': 1},
    600: {'zone': 'ETH_1000', 'entry_f': 0.75, 'target_ext': 0.25, 'tie': 2},
    960: {'zone': 'ETH_1600', 'entry_f': 0.90, 'target_ext': 0.25, 'tie': 3},
}
BTC_WR = 0.719298
BTC_PF = 2.223193
BTC_EXP = 1.26
BTC_MAX_LS = 3
BTC_5BPS_WR = 0.688596
BTC_5BPS_PF = 2.093450
NOTIONAL = 500.0
FEE = 0.40


def clock_label(v: int) -> str:
    return f'{(v // 60) % 24:02d}:{v % 60:02d}'


def finite_pf(pnls: pd.Series | list[float]) -> float:
    x = pd.to_numeric(pd.Series(pnls), errors='coerce').dropna()
    gp = float(x[x > 0].sum())
    gl = float(-x[x < 0].sum())
    if gl == 0 and gp > 0:
        return float('inf')
    return gp / gl if gl > 0 else np.nan


def max_loss_streak(pnls: pd.Series | list[float]) -> int:
    cur = mx = 0
    for v in pd.to_numeric(pd.Series(pnls), errors='coerce').dropna():
        if float(v) < 0:
            cur += 1
            mx = max(mx, cur)
        else:
            cur = 0
    return int(mx)


def metrics(pnls: pd.Series | list[float]) -> dict:
    x = pd.to_numeric(pd.Series(pnls), errors='coerce').dropna()
    if len(x) == 0:
        return {'n': 0, 'wins': 0, 'wr': np.nan, 'pf': np.nan, 'expectancy': np.nan, 'net': 0.0, 'max_ls': 0}
    return {
        'n': int(len(x)),
        'wins': int((x > 0).sum()),
        'wr': float((x > 0).mean()),
        'pf': finite_pf(x),
        'expectancy': float(x.mean()),
        'net': float(x.sum()),
        'max_ls': max_loss_streak(x),
    }


def trade_detail(x: pd.DataFrame, s: dict, target_ext: float) -> dict | None:
    H = float(s['H'])
    L = float(s['L'])
    R = H - L
    entry_px = float(s['entry'])
    fill_ts = pd.Timestamp(s['fill_ts'])
    ee = pd.Timestamp(s['ee'])
    exe = s['exe']
    target = H + target_ext * R
    stop = L + STOP_F * R

    q = exe[exe.index >= fill_ts + BAR5]
    exit_ts = pd.NaT
    exit_px = np.nan
    reason = None
    for ts, r in q.iterrows():
        ts = pd.Timestamp(ts)
        if float(r.high) >= target:
            exit_ts = ts
            exit_px = target
            reason = 'TARGET'
            break
        if float(r.close) < stop:
            exit_ts = ts + BAR5
            exit_px = float(r.close)
            reason = 'CLOSE_INVALIDATION'
            break

    if reason is None:
        pos = int(x.index.searchsorted(ee, side='left'))
        if pos >= len(x) or x.index[pos] != ee:
            return None
        exit_ts = ee
        exit_px = float(x.iloc[pos].open)
        reason = 'TIME_EXIT'

    gross = exit_px / entry_px - 1.0
    pnl = NOTIONAL * gross - FEE
    return {
        'entry_ts': fill_ts,
        'entry_px': entry_px,
        'exit_ts': exit_ts,
        'exit_px': float(exit_px),
        'exit_reason': reason,
        'pnl_0bps': float(pnl),
        'H': H,
        'L': L,
        'range': R,
        'target_px': target,
        'stop_px': stop,
        'execution_start': pd.Timestamp(s['es']),
        'execution_end': ee,
    }


def build_candidates(x: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        for exec_min, rule in ZONE_RULES.items():
            sess = b.sessions_for(
                x=x,
                part_name=part,
                exec_min=exec_min,
                ref_min=REF_MIN,
                horizon_min=HORIZON_MIN,
                side='LONG',
                entry_f=rule['entry_f'],
            )
            for s in sess:
                d = trade_detail(x, s, rule['target_ext'])
                if d is None:
                    continue
                d.update({
                    'partition': part,
                    'exec_min': exec_min,
                    'execution_utc': clock_label(exec_min),
                    'zone': rule['zone'],
                    'tie_order': rule['tie'],
                    'entry_f': rule['entry_f'],
                    'target_ext': rule['target_ext'],
                    'stop_f': STOP_F,
                })
                rows.append(d)
    q = pd.DataFrame(rows)
    if not q.empty:
        q['entry_ts'] = pd.to_datetime(q.entry_ts, utc=True)
        q['exit_ts'] = pd.to_datetime(q.exit_ts, utc=True)
    return q


def close_enough(a, c, tol=1e-9) -> bool:
    if pd.isna(a) and pd.isna(c):
        return True
    if math.isinf(float(a)) and math.isinf(float(c)):
        return True
    return abs(float(a) - float(c)) <= tol


def parity_check(x: pd.DataFrame, cands: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for part in PARTS:
        for exec_min, rule in ZONE_RULES.items():
            q = cands[(cands.partition == part) & (cands.exec_min == exec_min)]
            got = metrics(q.pnl_0bps)
            exp = b.score_config(
                x=x,
                part_name=part,
                side='LONG',
                exec_min=exec_min,
                ref_min=REF_MIN,
                horizon_min=HORIZON_MIN,
                entry_f=rule['entry_f'],
                target_ext=rule['target_ext'],
                stop_f=STOP_F,
                stress_bps=0.0,
            )
            for field in ('n', 'wins', 'wr', 'pf', 'expectancy', 'net', 'max_ls'):
                ok = close_enough(got[field], exp[field])
                rows.append({
                    'partition': part,
                    'zone': rule['zone'],
                    'field': field,
                    'calculated': got[field],
                    'expected': exp[field],
                    'pass': ok,
                })
    return pd.DataFrame(rows)


def apply_lock(g: pd.DataFrame, label: str) -> pd.DataFrame:
    q = g.sort_values(['entry_ts', 'tie_order']).copy()
    locked_until = pd.NaT
    active_zone = None
    accepted = []
    decisions = []
    blockers = []
    for r in q.itertuples(index=False):
        if pd.isna(locked_until) or pd.Timestamp(r.entry_ts) >= pd.Timestamp(locked_until):
            accepted.append(True)
            decisions.append('ACCEPT')
            blockers.append('')
            locked_until = pd.Timestamp(r.exit_ts)
            active_zone = r.zone
        else:
            accepted.append(False)
            decisions.append('SKIP_OPEN_POSITION')
            blockers.append(active_zone)
    q['accepted'] = accepted
    q['decision'] = decisions
    q['blocked_by_zone'] = blockers
    q['portfolio'] = label
    return q


def stressed_pnl(r, bps: float) -> float:
    k = float(bps) / 10000.0
    entry = float(r.entry_px) * (1.0 + k)
    if str(r.exit_reason) == 'TARGET':
        exit_px = float(r.exit_px)
    else:
        exit_px = float(r.exit_px) * (1.0 - k)
    return NOTIONAL * (exit_px / entry - 1.0) - FEE


def partition_weeks(part: str) -> float:
    a, z = b.m.m.PARTS[part]
    return float((z - a) / pd.Timedelta(days=7))


def pooled_weeks() -> float:
    return sum(partition_weeks(p) for p in PARTS)


def summarize_locked(locked_parts: list[pd.DataFrame]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    zone_rows = []
    for d in locked_parts:
        part = str(d.partition.iloc[0]) if len(d) else ''
        a = d[d.accepted]
        m = metrics(a.pnl_0bps)
        rows.append({
            'partition': part,
            'candidates': len(d),
            'accepted': len(a),
            'skipped_open': int((~d.accepted).sum()),
            'retention': len(a) / len(d) if len(d) else np.nan,
            'trades_per_week': len(a) / partition_weeks(part) if part else np.nan,
            **m,
        })
        for zone in ZONE_RULES.values():
            zname = zone['zone']
            dz = d[d.zone == zname]
            az = dz[dz.accepted]
            mm = metrics(az.pnl_0bps)
            zone_rows.append({
                'partition': part,
                'zone': zname,
                'candidates': len(dz),
                'accepted': len(az),
                'blocked': int((~dz.accepted).sum()),
                'retention': len(az) / len(dz) if len(dz) else np.nan,
                **mm,
            })

    pooled = pd.concat(locked_parts, ignore_index=True)
    pa = pooled[pooled.accepted]
    pm = metrics(pa.pnl_0bps)
    rows.append({
        'partition': 'POOLED_MAJOR',
        'candidates': len(pooled),
        'accepted': len(pa),
        'skipped_open': int((~pooled.accepted).sum()),
        'retention': len(pa) / len(pooled) if len(pooled) else np.nan,
        'trades_per_week': len(pa) / pooled_weeks(),
        **pm,
    })
    for zone in ZONE_RULES.values():
        zname = zone['zone']
        dz = pooled[pooled.zone == zname]
        az = dz[dz.accepted]
        mm = metrics(az.pnl_0bps)
        zone_rows.append({
            'partition': 'POOLED_MAJOR',
            'zone': zname,
            'candidates': len(dz),
            'accepted': len(az),
            'blocked': int((~dz.accepted).sum()),
            'retention': len(az) / len(dz) if len(dz) else np.nan,
            **mm,
        })
    return pd.DataFrame(rows), pd.DataFrame(zone_rows)


def fmt(v, nd=2):
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100 * float(v):.1f}%'


def usd(v):
    return '-' if pd.isna(v) else f'${float(v):+.2f}'


def main():
    x, coverage = b.m.m.load5()
    cands = build_candidates(x)
    parity = parity_check(x, cands)
    parity.to_csv(OUT_PARITY, index=False)
    if parity.empty or not bool(parity['pass'].all()):
        raise AssertionError('S5B candidate-stream parity failed')

    locked_parts = []
    for part in PARTS:
        locked_parts.append(apply_lock(cands[cands.partition == part].copy(), f'ETH_S5B_{part}'))
    locked = pd.concat(locked_parts, ignore_index=True)
    locked.to_csv(OUT_TRADES, index=False)

    summary, zones = summarize_locked(locked_parts)
    summary.to_csv(OUT_SUMMARY, index=False)
    zones.to_csv(OUT_ZONE, index=False)

    pooled = locked[locked.accepted].copy()
    stress_rows = []
    for bps in (0, 2, 5, 10):
        vals = [stressed_pnl(r, bps) for r in pooled.itertuples(index=False)]
        m = metrics(vals)
        stress_rows.append({'stress_bps': bps, 'trades_per_week': len(vals) / pooled_weeks(), **m})
    stress = pd.DataFrame(stress_rows)
    stress.to_csv(OUT_STRESS, index=False)

    p = summary[summary.partition == 'POOLED_MAJOR'].iloc[0]
    quality_pass = bool(
        p.wr >= BTC_WR and p.pf >= BTC_PF and p.expectancy >= BTC_EXP and
        p.net > 0 and int(p.max_ls) <= BTC_MAX_LS
    )
    freq_pass = bool(p.trades_per_week >= 2.0)
    s5 = stress[stress.stress_bps == 5].iloc[0]
    stress5_btc_diag = bool(s5.wr >= BTC_5BPS_WR and s5.pf >= BTC_5BPS_PF)

    if quality_pass and freq_pass:
        status = 'ETH_S5B_BTC_QUALITY_AND_2PW_SUPPORTED'
    elif quality_pass:
        status = 'ETH_S5B_BTC_QUALITY_SUPPORTED_FREQUENCY_SHORT'
    elif freq_pass:
        status = 'ETH_S5B_FREQUENCY_SUPPORTED_QUALITY_SHORT'
    else:
        status = 'ETH_S5B_BOTH_TARGETS_SHORT'
    OUT_STATUS.write_text(status + '\n')

    ties = locked.groupby(['partition', 'entry_ts']).size()
    tie_n = int((ties > 1).sum())

    lines = [
        '# ETH B27DX — S5B Zone-Native Fixed-Exit Portfolio Lock — Result',
        '',
        f'ETH raw 5m coverage: **{coverage:.4%}**.',
        '',
        '**Candidate-stream parity: PASS.** Every frozen zone/partition reproduced the exact pre-lock `score_config` metrics before the global one-position rule was applied.',
        '',
        'Frozen zone rules: 05:00 F80/E30; 09:00 F80/E25; 10:00 F75/E25; 16:00 F90/E25. All use R300/X360 and completed-close F35 invalidation.',
        '',
        '## Global one-position portfolio',
        '',
        '| Partition | Candidates | Accepted | Blocked | Retention | Trades/wk | WR | PF | Exp | Net | Max LS |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for r in summary.itertuples(index=False):
        lines.append(
            f'| {r.partition} | {int(r.candidates)} | {int(r.accepted)} | {int(r.skipped_open)} | {pct(r.retention)} | '
            f'{fmt(r.trades_per_week,3)} | {pct(r.wr)} | {fmt(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {int(r.max_ls)} |'
        )

    lines += ['', '## Pooled-major contribution by zone', '',
              '| Zone | Candidates | Accepted | Blocked | Retention | WR | PF | Exp | Net |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    zz = zones[zones.partition == 'POOLED_MAJOR']
    for r in zz.itertuples(index=False):
        lines.append(f'| {r.zone} | {int(r.candidates)} | {int(r.accepted)} | {int(r.blocked)} | {pct(r.retention)} | {pct(r.wr)} | {fmt(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} |')

    lines += ['', '## Execution stress', '',
              '| Stress | N | WR | PF | Exp | Net | Max LS | Trades/wk |',
              '|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in stress.itertuples(index=False):
        lines.append(f'| {int(r.stress_bps)} bps | {int(r.n)} | {pct(r.wr)} | {fmt(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} | {int(r.max_ls)} | {fmt(r.trades_per_week,3)} |')

    lines += [
        '',
        '## BTC benchmark gates',
        '',
        f'- BTC-quality 0-bps gate (WR>=71.9%, PF>=2.22, Exp>=$+1.26, maxLS<=3): **{"PASS" if quality_pass else "FAIL"}**.',
        f'- ETH >=2.00 accepted trades/week gate: **{"PASS" if freq_pass else "FAIL"}**.',
        f'- 5-bps diagnostic vs BTC published WR 68.9% / PF 2.09: **{"PASS" if stress5_btc_diag else "FAIL"}** (stress models are not identical).',
        f'- Exact same-entry-timestamp candidate ties before lock: **{tie_n}**.',
        '',
        '## Decision',
        '',
        f'**Status: {status}**',
        '',
        '- No zone dropping, parameter search, runner selection, leverage tuning, or live-code changes were performed in S5B.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
