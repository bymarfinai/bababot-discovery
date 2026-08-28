from __future__ import annotations

from pathlib import Path
import math
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Same-directory imports when executed as `python research/...py`, matching B27EN/B27EO.
import bnb_session_native_london_ny_long_m1_structure_b27em as b27em
import bnb_session_native_london_ny_long_m3_entry_b27eo as b27eo

TARGET = 'BNBUSDT'
PARTITION = 'reference_validation'
CANDIDATE = 'E2_F95_RECLAIM'
EXPECTED_LEAVES = 45
EXPECTED_H2 = 35
EXPECTED_NON_H2 = 10
TARGET_RATE = 0.90

PFX = 'BNB_SESSION_NATIVE_LONDON_NY_LONG_M4_F95_VALIDATION_B27EP'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def pct(x: float) -> str:
    return '-' if pd.isna(x) else f'{100.0 * float(x):.1f}%'


def fr(x: float) -> str:
    return '-' if pd.isna(x) else f'{float(x):.3f}R'


def mins(x: float) -> str:
    return '-' if pd.isna(x) else f'{float(x):.1f}m'


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n <= 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / den
    half = z * math.sqrt((p * (1.0 - p) / n) + z * z / (4.0 * n * n)) / den
    return max(0.0, center - half), min(1.0, center + half)


def build_rows(x5: pd.DataFrame) -> pd.DataFrame:
    sessions = b27em.session_rows(x5)
    q = sessions[
        sessions.partition.eq(PARTITION)
        & sessions.leave.fillna(False).astype(bool)
    ].copy()

    if len(q) != EXPECTED_LEAVES:
        raise AssertionError(f'expected {EXPECTED_LEAVES} reference-validation leaves, got {len(q)}')

    upstream_h2 = int(q.terminal.eq('H2_ARRIVAL').sum())
    upstream_non = len(q) - upstream_h2
    if upstream_h2 != EXPECTED_H2 or upstream_non != EXPECTED_NON_H2:
        raise AssertionError(
            f'upstream reproduction mismatch H2={upstream_h2} NON_H2={upstream_non}; '
            f'expected {EXPECTED_H2}/{EXPECTED_NON_H2}'
        )

    rows: list[dict] = []
    for _, s in q.iterrows():
        ny_open = pd.Timestamp(s.ny_open_utc)
        ny_close = pd.Timestamp(s.ny_close_utc)
        exe = b27em.fs(x5, ny_open, ny_close)
        H = float(s.H)
        L = float(s.L)
        R = float(s.R)
        leave_ts = pd.Timestamp(s.leave_ts)

        z = b27eo.discover_candidate(CANDIDATE, exe, leave_ts, H, L, R)
        z.update({
            'local_date': str(s.local_date),
            'partition': str(s.partition),
            'duration_regime': str(s.duration_regime),
            'upstream_terminal': str(s.terminal),
            'H': H,
            'L': L,
            'R': R,
            'leave_ts': leave_ts,
        })
        rows.append(z)

    d = pd.DataFrame(rows).sort_values('leave_ts').reset_index(drop=True)
    if len(d) != EXPECTED_LEAVES or not d.partition.eq(PARTITION).all():
        raise AssertionError('B27EP partition integrity failed')
    if not d.candidate.eq(CANDIDATE).all():
        raise AssertionError('B27EP candidate integrity failed')
    return d


def summarize(d: pd.DataFrame) -> pd.DataFrame:
    eligible = d[d.eligible.fillna(False).astype(bool)].copy()
    h2 = eligible[eligible.outcome.eq('H2_ARRIVAL')].copy()
    non_h2 = eligible[~eligible.outcome.eq('H2_ARRIVAL')].copy()

    n = len(eligible)
    k = len(h2)
    rate = k / n if n else np.nan
    lo, hi = wilson(k, n)

    upstream_h2_dates = set(d.loc[d.upstream_terminal.eq('H2_ARRIVAL'), 'local_date'])
    captured = len(set(h2.local_date) & upstream_h2_dates)

    rec = {
        'candidate': CANDIDATE,
        'population_leaves': len(d),
        'upstream_h2': int(d.upstream_terminal.eq('H2_ARRIVAL').sum()),
        'eligible': n,
        'eligible_rate': n / len(d),
        'h2_after_entry': k,
        'non_h2_after_entry': len(non_h2),
        'h2_rate': rate,
        'wilson95_low': lo,
        'wilson95_high': hi,
        'winner_capture_n': captured,
        'winner_capture_share': captured / EXPECTED_H2,
        'median_leave_entry_min': pd.to_numeric(eligible.minutes_leave_to_entry, errors='coerce').median() if n else np.nan,
        'median_entry_h2_min': pd.to_numeric(h2.minutes_entry_to_h2, errors='coerce').median() if k else np.nan,
        'median_entry_depth_R': pd.to_numeric(eligible.entry_depth_R, errors='coerce').median() if n else np.nan,
        'median_mae_R': pd.to_numeric(eligible.post_entry_mae_R, errors='coerce').median() if n else np.nan,
        'p75_mae_R': pd.to_numeric(eligible.post_entry_mae_R, errors='coerce').quantile(.75) if n else np.nan,
        'headline_target_rate': TARGET_RATE,
        'headline_target_met': bool(n > 0 and rate >= TARGET_RATE),
    }
    return pd.DataFrame([rec])


def main() -> None:
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27EP preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'coverage gate failed: {coverage:.6f}')

    d = build_rows(x5)
    d.to_csv(OUT_DETAIL, index=False)

    s = summarize(d)
    s.to_csv(OUT_SUM, index=False)
    r = s.iloc[0]

    verdict = 'TARGET_MET' if bool(r.headline_target_met) else 'TARGET_NOT_MET'
    status = f'B27EP_BNB_F95_REFERENCE_VALIDATION_COMPLETE_{verdict}'
    OUT_STATUS.write_text(status + '\n')

    upstream_rate = EXPECTED_H2 / EXPECTED_LEAVES
    lines = [
        '# BNB Session-Native London→New York LONG M4 Frozen F95 Validation — B27EP Result', '',
        f'Raw BNB 5m coverage: **{coverage:.4%}**.', '',
        'Validation uses only **reference_validation (2025-01-01 → 2026-07-30)**.', '',
        'The entry rule is frozen from B27EO: **F95 touch + close back above F95, then fill at the next 5m open**. No alternative entry was searched or retuned.', '',
        '## Upstream integrity', '',
        f'- Causal leaves: **{len(d)} / {EXPECTED_LEAVES}**',
        f'- Upstream H2: **{int(d.upstream_terminal.eq("H2_ARRIVAL").sum())} / {EXPECTED_H2}**',
        f'- Upstream non-H2: **{int((~d.upstream_terminal.eq("H2_ARRIVAL")).sum())} / {EXPECTED_NON_H2}**',
        f'- Structural H2 rate before entry condition: **{pct(upstream_rate)}**', '',
        '## Frozen F95 validation', '',
        '| Metric | Result |',
        '|---|---:|',
        f'| Eligible F95 entries | **{int(r.eligible)}/{EXPECTED_LEAVES} ({pct(r.eligible_rate)})** |',
        f'| H2 after entry | **{int(r.h2_after_entry)}/{int(r.eligible)}** |' if int(r.eligible) else '| H2 after entry | **0/0** |',
        f'| H2-after-entry rate | **{pct(r.h2_rate)}** |',
        f'| Wilson 95% interval | **{pct(r.wilson95_low)} – {pct(r.wilson95_high)}** |',
        f'| Winner capture | **{int(r.winner_capture_n)}/{EXPECTED_H2} ({pct(r.winner_capture_share)})** |',
        f'| Median leave→entry | **{mins(r.median_leave_entry_min)}** |',
        f'| Median entry→H2 | **{mins(r.median_entry_h2_min)}** |',
        f'| Median entry depth | **{fr(r.median_entry_depth_R)}** |',
        f'| Median post-entry MAE | **{fr(r.median_mae_R)}** |',
        f'| P75 post-entry MAE | **{fr(r.p75_mae_R)}** |', '',
        '## Frozen target check', '',
        f'- Predeclared target: **H2-after-entry >= {pct(TARGET_RATE)}**',
        f'- Observed validation: **{pct(r.h2_rate)}**',
        f'- Target result: **{verdict}**', '',
        'The validation percentage must be interpreted together with eligible N and the Wilson interval. This milestone validates only the structural post-entry H2 event; it is **not yet a trading win rate** because no stop, TP, fees, slippage, or PnL model is active.', '',
        f'**Status: {status}**', '',
        'STOP: no F90/F85 comparison, retuning, TP/SL, economics, SHORT, August reveal, or live integration was run.'
    ]

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
