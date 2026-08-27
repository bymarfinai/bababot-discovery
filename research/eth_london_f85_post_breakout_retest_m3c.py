#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BASE_PATH = HERE / 'eth_f85_f15_transfer_m2_pre_h2_entry_grid.py'
spec = importlib.util.spec_from_file_location('eth_m2_base_m3c', BASE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(m)

PFX = 'ETH_LONDON_F85_POST_BREAKOUT_RETEST_M3C'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_CASES = ROOT / f'{PFX}_Cases.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'
M3B_STATUS = ROOT / 'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_Status.txt'
M3B_CASES = ROOT / 'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_Cases.csv'
REQUIRED_M3B = 'ETH_LONDON_F85_BREAKOUT_SEQUENCE_M3B_COMPLETED'
MAJOR = ('external', 'development', 'reference_validation')
EXPECTED_COHORT = 48


def raw_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(start, side='left'))
    j = int(x.index.searchsorted(end, side='left'))
    return x.iloc[i:j]


def depth_bucket(min_frac: float) -> str:
    if min_frac >= .95:
        return '0-5% below High'
    if min_frac >= .90:
        return '5-10% below High'
    if min_frac >= .85:
        return '10-15% below High'
    return '>15% below High'


def audit_case(x: pd.DataFrame, r: pd.Series) -> dict:
    H = float(r.H); L = float(r.L); R = H - L
    E20 = H + .20 * R
    breakout_ts = pd.Timestamp(r.breakout_ts)
    execution_start = pd.Timestamp(r.execution_start)
    execution_end = execution_start + m.EXE

    q = raw_slice(x, breakout_ts + m.BAR5, execution_end)
    back_in_ts = pd.NaT
    ambiguous_e20_on_back_in_bar = False

    # Reproduce the exact M3B terminal that created BACK_IN_RANGE_BEFORE_E20.
    for ts, b in q.iterrows():
        hi = float(b.high); cl = float(b.close)
        e20 = hi >= E20
        back_in = cl < H
        if e20 and back_in:
            back_in_ts = ts
            ambiguous_e20_on_back_in_bar = True
            break
        if e20:
            raise RuntimeError('Cohort mismatch: E20 occurred before back-in-range')
        if back_in:
            back_in_ts = ts
            break

    if pd.isna(back_in_ts):
        raise RuntimeError('Cohort mismatch: no back-in-range candle found')

    recovery_start = back_in_ts + m.BAR5
    post = raw_slice(x, recovery_start, execution_end)
    rebreak_ts = pd.NaT
    e20_ts = pd.NaT

    for ts, b in post.iterrows():
        cl = float(b.close); hi = float(b.high)
        if pd.isna(rebreak_ts) and cl > H:
            rebreak_ts = ts
        if hi >= E20:
            e20_ts = ts
            break

    eventual_e20 = pd.notna(e20_ts)
    confirmed_rebreak = pd.notna(rebreak_ts)

    depth_end = (e20_ts + m.BAR5) if eventual_e20 else execution_end
    depth_path = raw_slice(x, back_in_ts, depth_end)
    if depth_path.empty:
        raise RuntimeError('Empty retest depth path')
    min_low = float(depth_path.low.min())
    min_frac = (min_low - L) / R
    depth_pct_below_high = max(0.0, (H - min_low) / R * 100.0)

    if eventual_e20:
        if confirmed_rebreak and rebreak_ts <= e20_ts:
            recovery_type = 'E20_AFTER_CONFIRMED_REBREAK'
        else:
            recovery_type = 'E20_WITHOUT_CONFIRMED_REBREAK'
        mins = float((e20_ts - recovery_start) / pd.Timedelta(minutes=1))
    else:
        recovery_type = 'REBREAK_BUT_NO_E20' if confirmed_rebreak else 'NO_REBREAK_NO_E20'
        mins = np.nan

    return {
        'partition': r.partition,
        'reference_start': r.reference_start,
        'execution_start': execution_start,
        'H': H, 'L': L, 'R': R, 'E20': E20,
        'breakout_ts': breakout_ts,
        'back_in_ts': back_in_ts,
        'ambiguous_e20_on_back_in_bar': ambiguous_e20_on_back_in_bar,
        'recovery_start': recovery_start,
        'confirmed_rebreak': confirmed_rebreak,
        'rebreak_ts': rebreak_ts,
        'eventual_e20': eventual_e20,
        'e20_ts': e20_ts,
        'minutes_back_in_close_to_e20': mins,
        'min_low_after_back_in': min_low,
        'min_fraction_after_back_in': min_frac,
        'depth_pct_of_range_below_high': depth_pct_below_high,
        'depth_bucket': depth_bucket(min_frac),
        'recovery_type': recovery_type,
    }


def part_summary(c: pd.DataFrame, name: str) -> dict:
    z = c[c.partition == name]
    e = z[z.eventual_e20.astype(bool)]
    return {
        'partition': name,
        'cases': len(z),
        'eventual_e20': len(e),
        'eventual_e20_rate': len(e)/len(z) if len(z) else np.nan,
        'median_minutes_to_e20': pd.to_numeric(e.minutes_back_in_close_to_e20, errors='coerce').median() if len(e) else np.nan,
        'rebreak_and_e20': int((z.recovery_type == 'E20_AFTER_CONFIRMED_REBREAK').sum()),
        'e20_without_confirmed_rebreak': int((z.recovery_type == 'E20_WITHOUT_CONFIRMED_REBREAK').sum()),
        'rebreak_no_e20': int((z.recovery_type == 'REBREAK_BUT_NO_E20').sum()),
        'no_rebreak_no_e20': int((z.recovery_type == 'NO_REBREAK_NO_E20').sum()),
        'ambiguous_same_backin_bar': int(z.ambiguous_e20_on_back_in_bar.astype(bool).sum()),
    }


def pct(n: int, d: int) -> str:
    return f'{100*n/d:.1f}%' if d else '-'


def main():
    if not M3B_STATUS.exists() or M3B_STATUS.read_text().strip() != REQUIRED_M3B:
        raise RuntimeError('M3B status gate not satisfied')
    if not M3B_CASES.exists():
        raise RuntimeError('M3B cases file missing')

    base = pd.read_csv(M3B_CASES)
    for col in ['reference_start', 'execution_start', 'breakout_ts']:
        base[col] = pd.to_datetime(base[col], utc=True, errors='coerce')
    cohort = base[
        base.partition.isin(MAJOR) &
        (base.post_breakout_path == 'BACK_IN_RANGE_BEFORE_E20')
    ].copy()

    if len(cohort) != EXPECTED_COHORT:
        raise RuntimeError(f'Frozen cohort mismatch: expected {EXPECTED_COHORT}, got {len(cohort)}')
    if cohort.duplicated(['partition', 'reference_start']).any():
        raise RuntimeError('Duplicate M3B cohort identity')

    x, coverage = m.load5()
    if coverage < .995:
        raise RuntimeError(f'raw 5m coverage below gate: {coverage:.6%}')

    cases = pd.DataFrame([audit_case(x, r) for _, r in cohort.iterrows()])
    if len(cases) != EXPECTED_COHORT:
        raise RuntimeError('M3C case count mismatch')
    cases.to_csv(OUT_CASES, index=False)

    rows = [part_summary(cases, p) for p in MAJOR]
    pooled = part_summary(cases.assign(partition='POOLED_MAJOR'), 'POOLED_MAJOR')
    rows.append(pooled)
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT_SUM, index=False)

    total = len(cases)
    recovered = int(cases.eventual_e20.astype(bool).sum())
    failed = total - recovered
    re_e20 = int((cases.recovery_type == 'E20_AFTER_CONFIRMED_REBREAK').sum())
    wick_e20 = int((cases.recovery_type == 'E20_WITHOUT_CONFIRMED_REBREAK').sum())
    re_fail = int((cases.recovery_type == 'REBREAK_BUT_NO_E20').sum())
    no_re_fail = int((cases.recovery_type == 'NO_REBREAK_NO_E20').sum())
    amb = int(cases.ambiguous_e20_on_back_in_bar.astype(bool).sum())
    med = pd.to_numeric(cases.loc[cases.eventual_e20.astype(bool), 'minutes_back_in_close_to_e20'], errors='coerce').median()

    depth_order = ['0-5% below High', '5-10% below High', '10-15% below High', '>15% below High']
    depth_rows = []
    for d in depth_order:
        z = cases[cases.depth_bucket == d]
        w = int(z.eventual_e20.astype(bool).sum()) if len(z) else 0
        depth_rows.append((d, len(z), w, pct(w, len(z))))

    names = {
        'external': '2020-2021',
        'development': '2022-2024',
        'reference_validation': '2025-Jul 2026',
        'POOLED_MAJOR': 'Semua periode utama',
    }

    lines = [
        '# ETH London F85 — Post-Breakout Retest Audit M3C — Result', '',
        f'Raw ETH 5-minute coverage: **{coverage:.4%}**.',
        f'Kasus yang diaudit: **{total}** — semuanya adalah breakout yang kemudian kembali tutup di bawah High sebelum E20 pada M3B.', '',
        '## Apakah setelah balik masuk range masih bisa lanjut?', '',
        '| Hasil setelah kembali di bawah High | Jumlah | Persentase |',
        '|---|---:|---:|',
        f'| Akhirnya tetap mencapai E20 | {recovered} | {pct(recovered,total)} |',
        f'| Tidak mencapai E20 sampai sesi selesai | {failed} | {pct(failed,total)} |',
        '',
        f'Median waktu dari retest terkonfirmasi sampai E20, untuk yang recover: **{med:.0f} menit**.' if pd.notna(med) else 'Tidak ada recovery E20.',
        '',
        '## Jalurnya setelah retest', '',
        '| Jalur | Jumlah | % dari 48 kasus |',
        '|---|---:|---:|',
        f'| Breakout lagi dengan close 5 menit, lalu mencapai E20 | {re_e20} | {pct(re_e20,total)} |',
        f'| E20 tersentuh tanpa sempat close 5 menit breakout lagi | {wick_e20} | {pct(wick_e20,total)} |',
        f'| Sempat breakout lagi, tapi tetap tidak mencapai E20 | {re_fail} | {pct(re_fail,total)} |',
        f'| Tidak pernah breakout lagi dan tidak mencapai E20 | {no_re_fail} | {pct(no_re_fail,total)} |',
        '',
        '## Seberapa dalam retest-nya?', '',
        '| Kedalaman turun dari High | Jumlah kasus | Yang akhirnya mencapai E20 | Peluang recover |',
        '|---|---:|---:|---:|',
    ]
    for d, n, w, p in depth_rows:
        label = {
            '0-5% below High': '0-5% dari range di bawah High',
            '5-10% below High': '5-10% dari range di bawah High',
            '10-15% below High': '10-15% dari range di bawah High',
            '>15% below High': '>15% dari range di bawah High',
        }[d]
        lines.append(f'| {label} | {n} | {w} | {p} |')

    lines += ['', '## Konsistensi per periode', '',
              '| Periode | Kasus balik masuk range | Akhirnya E20 | Persentase |',
              '|---|---:|---:|---:|']
    for _, r in summary.iterrows():
        rate = f'{100*r.eventual_e20_rate:.1f}%' if pd.notna(r.eventual_e20_rate) else '-'
        lines.append(f'| {names[r.partition]} | {int(r.cases)} | {int(r.eventual_e20)} | {rate} |')

    if amb:
        lines += ['', f'Catatan konservatif: **{amb}** kasus sempat menyentuh E20 pada candle yang sama saat pertama kali close kembali di bawah High. Touch tersebut tidak dihitung sebagai recovery, karena urutan intrabar tidak diketahui; recovery baru dihitung mulai candle berikutnya.']

    lines += ['', '**Status: ETH_LONDON_F85_POST_BREAKOUT_RETEST_M3C_COMPLETED**', '',
              'Audit struktur saja. Tidak ada perubahan live, entry, stop, target, filter, atau parameter trading. Stop setelah M3C.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text('ETH_LONDON_F85_POST_BREAKOUT_RETEST_M3C_COMPLETED\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
