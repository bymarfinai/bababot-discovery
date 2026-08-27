#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
spec = importlib.util.spec_from_file_location('eth_m2_base', BASE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

PFX = 'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_CASES = ROOT / f'{PFX}_Cases.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
M2_STATUS = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt'
M2_CAND = ROOT / 'ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Candidates.csv'
REQUIRED_STATUS = 'ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY'
MAJOR = ('external', 'development', 'reference_validation')
PART_ORDER = ('external', 'development', 'reference_validation', 'august', 'POOLED_MAJOR')


def as_bool(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin(['true', '1', 'yes'])


def raw_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(start, side='left'))
    j = int(x.index.searchsorted(end, side='left'))
    return x.iloc[i:j]


def audit_case(x: pd.DataFrame, r: pd.Series) -> dict:
    H = float(r.H)
    L = float(r.L)
    R = H - L
    E20 = H + 0.20 * R
    fill_ts = pd.Timestamp(r.fill_ts)
    execution_start = pd.Timestamp(r.execution_start)
    execution_end = execution_start + m.EXE

    # The corrected M2 F85 fill is strictly pre-H2, so the first later High
    # approach is Attack #2. We begin strictly after the fill candle.
    q = raw_slice(x, fill_ts + m.BAR5, execution_end)
    attack_no = 1
    in_attack = False
    breakout_ts = pd.NaT
    breakout_attack = np.nan
    breakout_high = np.nan

    for ts, b in q.iterrows():
        hi = float(b.high)
        cl = float(b.close)
        breakout = cl > H
        touch = hi >= H and cl <= H

        if breakout or touch:
            if not in_attack:
                attack_no += 1
                in_attack = True
            if breakout:
                breakout_ts = ts
                breakout_attack = attack_no
                breakout_high = hi
                break
        else:
            in_attack = False

    out = {
        'partition': r.partition,
        'reference_start': r.reference_start,
        'execution_start': execution_start,
        'fill_ts': fill_ts,
        'H': H,
        'L': L,
        'R': R,
        'F85': float(r.price),
        'E20': E20,
        'breakout': pd.notna(breakout_ts),
        'breakout_attack': breakout_attack,
        'breakout_ts': breakout_ts,
        'minutes_fill_to_breakout': (
            float((breakout_ts - fill_ts) / pd.Timedelta(minutes=1))
            if pd.notna(breakout_ts) else np.nan
        ),
        'post_breakout_path': 'NO_BREAKOUT_BY_END',
    }

    if pd.isna(breakout_ts):
        return out

    # If the confirmed breakout candle itself already extends to E20, keep
    # that separate because a trader only knows the breakout at candle close.
    if breakout_high >= E20:
        out['post_breakout_path'] = 'E20_ON_BREAKOUT_BAR'
        return out

    post = raw_slice(x, breakout_ts + m.BAR5, execution_end)
    had_retest = False
    for ts, b in post.iterrows():
        hi = float(b.high)
        lo = float(b.low)
        cl = float(b.close)
        e20 = hi >= E20
        back_in_range = cl < H

        # Conservative ordering when E20 touch and close-back occur in one 5m bar.
        if e20 and back_in_range:
            out['post_breakout_path'] = 'BACK_IN_RANGE_BEFORE_E20'
            return out
        if e20:
            out['post_breakout_path'] = (
                'RETEST_THEN_CONTINUATION' if had_retest else 'DIRECT_CONTINUATION'
            )
            return out
        if back_in_range:
            out['post_breakout_path'] = 'BACK_IN_RANGE_BEFORE_E20'
            return out
        if lo <= H:
            had_retest = True

    out['post_breakout_path'] = 'UNRESOLVED_BY_END'
    return out


def summarize(c: pd.DataFrame, partition: str) -> dict:
    z = c[c.partition.isin(MAJOR)] if partition == 'POOLED_MAJOR' else c[c.partition == partition]
    n = len(z)
    br = z[z.breakout.astype(bool)] if n else z
    def cnt_attack(k):
        return int((pd.to_numeric(br.breakout_attack, errors='coerce') == k).sum()) if len(br) else 0
    attack6p = int((pd.to_numeric(br.breakout_attack, errors='coerce') >= 6).sum()) if len(br) else 0
    paths = br.post_breakout_path.value_counts() if len(br) else pd.Series(dtype=int)
    return {
        'partition': partition,
        'f85_fills': n,
        'breakouts': len(br),
        'breakout_rate': len(br)/n if n else np.nan,
        'attack_2': cnt_attack(2),
        'attack_3': cnt_attack(3),
        'attack_4': cnt_attack(4),
        'attack_5': cnt_attack(5),
        'attack_6_plus': attack6p,
        'no_breakout': n-len(br),
        'median_minutes_fill_to_breakout': pd.to_numeric(br.minutes_fill_to_breakout, errors='coerce').median() if len(br) else np.nan,
        'e20_on_breakout_bar': int(paths.get('E20_ON_BREAKOUT_BAR', 0)),
        'direct_continuation': int(paths.get('DIRECT_CONTINUATION', 0)),
        'retest_then_continuation': int(paths.get('RETEST_THEN_CONTINUATION', 0)),
        'back_in_range_before_e20': int(paths.get('BACK_IN_RANGE_BEFORE_E20', 0)),
        'unresolved_by_end': int(paths.get('UNRESOLVED_BY_END', 0)),
    }


def pct(n: int, d: int) -> str:
    return f'{100*n/d:.1f}%' if d else '-'


def main():
    if not M2_STATUS.exists() or M2_STATUS.read_text().strip() != REQUIRED_STATUS:
        raise RuntimeError('Corrected M2 status gate not satisfied')
    if not M2_CAND.exists():
        raise RuntimeError('Corrected M2 candidate file missing')

    cand = pd.read_csv(M2_CAND)
    cand['filled_bool'] = as_bool(cand['filled'])
    for col in ['reference_start', 'execution_start', 'fill_ts']:
        cand[col] = pd.to_datetime(cand[col], utc=True, errors='coerce')

    cohort = cand[
        (cand.clock == 'LONDON') &
        (cand.side == 'LONG') &
        (cand.level == 'F85') &
        cand.filled_bool
    ].copy()
    if cohort.empty:
        raise RuntimeError('No corrected M2 London F85 fills found')
    if cohort.duplicated(['partition', 'reference_start']).any():
        raise RuntimeError('Duplicate corrected-M2 London F85 identity')

    x, coverage = m.load5()
    if coverage < .995:
        raise RuntimeError(f'raw 5m coverage below gate: {coverage:.6%}')

    cases = pd.DataFrame([audit_case(x, r) for _, r in cohort.iterrows()])
    if len(cases) != len(cohort):
        raise RuntimeError('Case count mismatch vs corrected M2 cohort')
    if (pd.to_numeric(cases.breakout_attack, errors='coerce').dropna() < 2).any():
        raise RuntimeError('Invalid breakout attack ordinal below #2')

    cases.to_csv(OUT_CASES, index=False)
    summary = pd.DataFrame([summarize(cases, p) for p in PART_ORDER])
    summary.to_csv(OUT_SUM, index=False)

    pooled = summary[summary.partition == 'POOLED_MAJOR'].iloc[0]
    total = int(pooled.f85_fills)
    brn = int(pooled.breakouts)

    attack_rows = []
    for label, col in [
        ('Attack ke-2', 'attack_2'), ('Attack ke-3', 'attack_3'),
        ('Attack ke-4', 'attack_4'), ('Attack ke-5', 'attack_5'),
        ('Attack ke-6 atau lebih', 'attack_6_plus')]:
        v = int(pooled[col])
        attack_rows.append((label, v, pct(v, brn)))

    path_rows = []
    for label, col in [
        ('E20 sudah tersentuh pada candle breakout', 'e20_on_breakout_bar'),
        ('Langsung lanjut ke E20 tanpa retest High', 'direct_continuation'),
        ('Retest High dulu lalu lanjut ke E20', 'retest_then_continuation'),
        ('Balik tutup di bawah High sebelum E20', 'back_in_range_before_e20'),
        ('Belum selesai sampai akhir sesi', 'unresolved_by_end')]:
        v = int(pooled[col])
        path_rows.append((label, v, pct(v, brn)))

    lines = [
        '# ETH London F85 — Breakout Sequence Audit M3B — Result', '',
        f'Raw ETH 5-minute coverage: **{coverage:.4%}**.',
        f'Corrected M2 London F85 fills audited (pooled major): **{total}**.', '',
        '## Kapan High akhirnya breakout?', '',
        f'Confirmed breakout before New York execution end: **{brn}/{total} ({100*brn/total:.1f}%)**.',
        f'Median F85 fill -> confirmed breakout: **{pooled.median_minutes_fill_to_breakout:.0f} minutes**.', '',
        '| Breakout terjadi pada | Jumlah | % dari semua breakout |',
        '|---|---:|---:|',
    ]
    for a, n, p in attack_rows:
        lines.append(f'| {a} | {n} | {p} |')
    lines += [f'| Tidak breakout sampai akhir sesi | {int(pooled.no_breakout)} | {pct(int(pooled.no_breakout), total)} dari semua F85 fill |', '',
              '## Setelah breakout, apa yang terjadi?', '',
              '| Jalur setelah breakout | Jumlah | % dari breakout |',
              '|---|---:|---:|']
    for a, n, p in path_rows:
        lines.append(f'| {a} | {n} | {p} |')

    lines += ['', '## Ringkasan per periode', '',
              '| Periode | F85 fill | Breakout | Breakout rate | Median menit ke breakout |',
              '|---|---:|---:|---:|---:|']
    names = {'external':'2020-2021','development':'2022-2024','reference_validation':'2025-Jul 2026','august':'Aug 2026','POOLED_MAJOR':'Pooled major'}
    for _, r in summary.iterrows():
        rate = f'{100*r.breakout_rate:.1f}%' if pd.notna(r.breakout_rate) else '-'
        med = f'{r.median_minutes_fill_to_breakout:.0f}' if pd.notna(r.median_minutes_fill_to_breakout) else '-'
        lines.append(f'| {names[r.partition]} | {int(r.f85_fills)} | {int(r.breakouts)} | {rate} | {med} |')

    lines += ['', '**Status: ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_COMPLETED**', '',
              'Descriptive structural audit only. No live BBC change, no new clock/filter/entry/stop optimization, and no automatic next milestone.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_COMPLETED\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
