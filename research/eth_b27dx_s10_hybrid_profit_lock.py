#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

S4_PATH = HERE / 'eth_b27dx_s4_portfolio_lock.py'
spec = importlib.util.spec_from_file_location('eth_s4', S4_PATH)
s4 = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(s4)

S5_PATH = HERE / 'eth_b27dx_s5a_runner_arm_geometry.py'
spec2 = importlib.util.spec_from_file_location('eth_s5a', S5_PATH)
s5 = importlib.util.module_from_spec(spec2)
assert spec2.loader is not None
spec2.loader.exec_module(s5)

PFX = 'ETH_B27DX_S10_HYBRID_PROFIT_LOCK'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_CAND = ROOT / f'{PFX}_Candidates.csv'
OUT_DEC = ROOT / f'{PFX}_Decisions.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_CLOCK = ROOT / f'{PFX}_ClockSummary.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

RUNNER_EXEC_MIN = 600  # 10:00 UTC only
RUNNER_ARM_EXT = 0.10  # E10 only
PARTS = s4.PARTS
BTC_WR = s4.BTC_WR
BTC_PF = s4.BTC_PF
BTC_EXP = s4.BTC_EXP


def key_cols() -> list[str]:
    return ['partition', 'exec_min', 'execution_start', 'entry_bar_start']


def canonicalize_times(df: pd.DataFrame) -> pd.DataFrame:
    q = df.copy()
    for c in ('execution_start', 'entry_bar_start', 'exit_ts'):
        if c in q.columns:
            q[c] = pd.to_datetime(q[c], utc=True)
    return q


def build_hybrid(x: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixed = canonicalize_times(s4.build_candidates(x))
    all_runner = canonicalize_times(s5.build_candidates(x))
    runner = all_runner[(all_runner.exec_min == RUNNER_EXEC_MIN) & (np.isclose(all_runner.arm_ext, RUNNER_ARM_EXT))].copy()
    fixed10 = fixed[fixed.exec_min == RUNNER_EXEC_MIN].copy()

    kc = key_cols()
    if fixed10.duplicated(kc).any() or runner.duplicated(kc).any():
        raise AssertionError('duplicate candidate identity in fixed/runner source')

    fidx = fixed10.set_index(kc).sort_index()
    ridx = runner.set_index(kc).sort_index()
    exact_key_match = fidx.index.equals(ridx.index)
    if not exact_key_match:
        missing_runner = len(fidx.index.difference(ridx.index))
        missing_fixed = len(ridx.index.difference(fidx.index))
        raise AssertionError(f'10:00 candidate identity mismatch fixed_only={missing_runner} runner_only={missing_fixed}')

    parity_fields = []
    for field in ('entry_px', 'H', 'L'):
        a = pd.to_numeric(fidx[field], errors='coerce').to_numpy(float)
        b = pd.to_numeric(ridx[field], errors='coerce').to_numpy(float)
        ok = bool(np.allclose(a, b, rtol=0.0, atol=1e-10, equal_nan=True))
        parity_fields.append({'check': f'10:00_{field}_parity', 'value': len(a), 'pass': ok})
        if not ok:
            raise AssertionError(f'10:00 {field} parity failed')

    early_violations = int(pd.to_numeric(runner.early_floor_violation, errors='coerce').fillna(0).sum())
    if early_violations != 0:
        raise AssertionError(f'runner early-floor violations={early_violations}')

    hybrid = fixed.copy()
    hybrid['management_mode'] = 'FIXED_E25'
    hybrid['runner_armed'] = False
    hybrid['runner_scheduled_updates'] = 0
    hybrid['runner_activations'] = 0
    hybrid['runner_ratchet_updates'] = 0
    hybrid['runner_floor_exit'] = False

    rflat = runner.reset_index(drop=True).copy()
    rmap = {
        tuple(getattr(r, c) for c in kc): r
        for r in rflat.itertuples(index=False)
    }
    mask = hybrid.exec_min == RUNNER_EXEC_MIN
    for i, r in hybrid[mask].iterrows():
        k = tuple(r[c] for c in kc)
        rr = rmap[k]
        hybrid.at[i, 'exit_ts'] = pd.Timestamp(rr.exit_ts)
        hybrid.at[i, 'exit_px_0'] = float(rr.exit_px_0)
        hybrid.at[i, 'exit_reason'] = str(rr.exit_reason)
        hybrid.at[i, 'pnl_0'] = float(rr.pnl_0)
        hybrid.at[i, 'pnl_5'] = float(rr.pnl_5)
        hybrid.at[i, 'management_mode'] = 'B27DQ_E10_PROFIT_LOCK'
        hybrid.at[i, 'runner_armed'] = bool(rr.armed)
        hybrid.at[i, 'runner_scheduled_updates'] = int(rr.scheduled_updates)
        hybrid.at[i, 'runner_activations'] = int(rr.activations)
        hybrid.at[i, 'runner_ratchet_updates'] = int(rr.ratchet_updates)
        hybrid.at[i, 'runner_floor_exit'] = str(rr.exit_reason) in ('LIVE_FLOOR_GAP_OPEN', 'LIVE_FLOOR_TOUCH')

    hybrid = canonicalize_times(hybrid)

    audit_rows = [
        {'check': 'fixed_candidate_count', 'value': len(fixed), 'pass': len(fixed) > 0},
        {'check': 'fixed_10_candidate_count', 'value': len(fixed10), 'pass': len(fixed10) > 0},
        {'check': 'runner_10_E10_candidate_count', 'value': len(runner), 'pass': len(runner) == len(fixed10)},
        {'check': '10:00_exact_candidate_identity', 'value': len(runner), 'pass': exact_key_match},
        *parity_fields,
        {'check': 'runner_early_floor_violations', 'value': early_violations, 'pass': early_violations == 0},
        {'check': 'hybrid_candidate_count_equals_fixed', 'value': len(hybrid), 'pass': len(hybrid) == len(fixed)},
    ]
    audit = pd.DataFrame(audit_rows)
    return fixed, runner, hybrid, audit


def fmt(v: float, nd: int = 2) -> str:
    if pd.isna(v):
        return '-'
    if math.isinf(float(v)):
        return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v: float) -> str:
    return '-' if pd.isna(v) else f'{100.0*float(v):.1f}%'


def main() -> None:
    x, cov = s4.b.m.m.load5()
    fixed, runner, hybrid, audit = build_hybrid(x)

    base_dec, base_sum, base_clock = s4.summarize(fixed)
    hyb_dec, hyb_sum, hyb_clock = s4.summarize(hybrid)

    base_sum = base_sum.copy(); base_sum['variant'] = 'S4_FIXED_E25'
    hyb_sum = hyb_sum.copy(); hyb_sum['variant'] = 'S10_HYBRID_10_E10_RUNNER'
    summary = pd.concat([base_sum, hyb_sum], ignore_index=True)

    base_clock = base_clock.copy(); base_clock['variant'] = 'S4_FIXED_E25'
    hyb_clock = hyb_clock.copy(); hyb_clock['variant'] = 'S10_HYBRID_10_E10_RUNNER'
    clock = pd.concat([base_clock, hyb_clock], ignore_index=True)

    hyb_dec = hyb_dec.copy()
    hybrid_lookup = hybrid.set_index(key_cols())
    modes=[]; armed=[]; floor_exit=[]; updates=[]; activations=[]; ratchets=[]
    for r in hyb_dec.itertuples(index=False):
        k=(r.partition, int(r.exec_min), pd.Timestamp(r.execution_start), pd.Timestamp(r.entry_bar_start))
        z=hybrid_lookup.loc[k]
        modes.append(str(z.management_mode)); armed.append(bool(z.runner_armed)); floor_exit.append(bool(z.runner_floor_exit))
        updates.append(int(z.runner_scheduled_updates)); activations.append(int(z.runner_activations)); ratchets.append(int(z.runner_ratchet_updates))
    hyb_dec['management_mode']=modes; hyb_dec['runner_armed']=armed; hyb_dec['runner_floor_exit']=floor_exit
    hyb_dec['runner_scheduled_updates']=updates; hyb_dec['runner_activations']=activations; hyb_dec['runner_ratchet_updates']=ratchets

    hybrid.to_csv(OUT_CAND, index=False)
    hyb_dec.to_csv(OUT_DEC, index=False)
    summary.to_csv(OUT_SUM, index=False)
    clock.to_csv(OUT_CLOCK, index=False)
    audit.to_csv(OUT_AUDIT, index=False)

    def row(df, part, stress):
        return df[(df.partition == part) & (df.stress_bps == stress)].iloc[0]

    b0 = row(base_sum, 'POOLED_MAJOR', 0)
    b5 = row(base_sum, 'POOLED_MAJOR', 5)
    h0 = row(hyb_sum, 'POOLED_MAJOR', 0)
    h5 = row(hyb_sum, 'POOLED_MAJOR', 5)
    major = hyb_sum[(hyb_sum.partition.isin(PARTS)) & (hyb_sum.stress_bps == 0)]

    audit_ok = bool(audit['pass'].all())
    major_positive = bool(((major.pf > 1.0) & (major.net > 0)).all())
    stress_ok = bool(h5.pf > 1.0 and h5.net > 0)
    retention_ok = bool(h0.accepted >= 0.95 * b0.accepted)
    quality_improves = bool(
        h0.wr >= b0.wr and
        h0.pf > b0.pf and
        h0.expectancy > b0.expectancy and
        h0.net > b0.net
    )
    supported = bool(audit_ok and major_positive and stress_ok and retention_ok and quality_improves)
    btc_quality = bool(
        audit_ok and major_positive and stress_ok and
        h0.wr >= BTC_WR and h0.pf >= BTC_PF and h0.expectancy >= BTC_EXP
    )
    status = 'ETH_S10_HYBRID_PROFIT_LOCK_SUPPORTED' if supported else 'ETH_S10_HYBRID_PROFIT_LOCK_NOT_SUPPORTED'

    accepted = hyb_dec[hyb_dec.accepted]
    runner_acc = accepted[accepted.management_mode == 'B27DQ_E10_PROFIT_LOCK']
    runner_armed = int(runner_acc.runner_armed.sum())
    runner_floor_exits = int(runner_acc.runner_floor_exit.sum())
    scheduled = int(pd.to_numeric(runner_acc.runner_scheduled_updates, errors='coerce').fillna(0).sum())
    activations = int(pd.to_numeric(runner_acc.runner_activations, errors='coerce').fillna(0).sum())
    ratchets = int(pd.to_numeric(runner_acc.runner_ratchet_updates, errors='coerce').fillna(0).sum())

    lines = [
        '# ETH B27DX — S10 Hybrid Profit-Lock — Result', '',
        f'ETH raw 5m coverage: **{cov:.4%}**.', '',
        'Frozen hybrid map: **05:00 fixed E25 · 09:00 fixed E25 · 10:00 B27DQ-style E10 profit-lock runner · 16:00 fixed E25**.', '',
        f'- Candidate/parity/causal audit: **{"PASS" if audit_ok else "FAIL"}**.',
        '- Runner selection is exploratory because 10:00 was identified from previously inspected S5A history.', '',
        '## Portfolio comparison', '',
        '| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in [*PARTS, 'POOLED_MAJOR']:
        for variant, df in [('S4 fixed', base_sum), ('S10 hybrid', hyb_sum)]:
            for stress in (0,5):
                r=row(df,p,stress)
                lines.append(f'| {p} | {variant} | {stress} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')

    lines += ['', '## Pooled-major source-clock comparison (0 bps)', '',
              '| Clock | S4 N | S4 WR | S4 PF | S4 Exp | S4 Net | S10 N | S10 WR | S10 PF | S10 Exp | S10 Net |',
              '|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for ex in s4.CLOCKS:
        label=s4.clock_label(ex)
        a=base_clock[(base_clock.partition=='POOLED_MAJOR')&(base_clock.execution_utc==label)].iloc[0]
        z=hyb_clock[(hyb_clock.partition=='POOLED_MAJOR')&(hyb_clock.execution_utc==label)].iloc[0]
        lines.append(f'| {label} | {int(a.accepted)} | {pct(a.wr)} | {fmt(a.pf)} | {fmt(a.expectancy)} | {fmt(a.net)} | {int(z.accepted)} | {pct(z.wr)} | {fmt(z.pf)} | {fmt(z.expectancy)} | {fmt(z.net)} |')

    lines += ['', '## Runner anatomy — accepted 10:00 trades', '',
              f'- Accepted runner-managed 10:00 trades: **{len(runner_acc)}**.',
              f'- Armed after E10 touch: **{runner_armed}**.',
              f'- Live floor exits: **{runner_floor_exits}**.',
              f'- Scheduled floor updates: **{scheduled}**; activations: **{activations}**; ratchet updates: **{ratchets}**.', '',
              '## Pooled impact vs S4', '',
              f'- WR: **{pct(b0.wr)} → {pct(h0.wr)}**.',
              f'- PF: **{fmt(b0.pf)} → {fmt(h0.pf)}**.',
              f'- Expectancy: **{fmt(b0.expectancy)} → {fmt(h0.expectancy)}**.',
              f'- Net: **{fmt(b0.net)} → {fmt(h0.net)}**.',
              f'- Frequency: **{b0.trades_per_week:.3f} → {h0.trades_per_week:.3f} trades/week**.',
              f'- Accepted N: **{int(b0.accepted)} → {int(h0.accepted)}**.', '',
              '## Frozen gates', '',
              f'- All major partitions PF>1 and net>0: **{"PASS" if major_positive else "FAIL"}**.',
              f'- Pooled 5 bps PF>1 and net>0: **{"PASS" if stress_ok else "FAIL"}**.',
              f'- Accepted N >=95% S4: **{"PASS" if retention_ok else "FAIL"}**.',
              f'- WR/PF/expectancy/net all improve vs S4: **{"PASS" if quality_improves else "FAIL"}**.',
              f'- BTC-class diagnostic: **{"PASS" if btc_quality else "FAIL"}**.', '',
              '## Decision', '', f'**Status: {status}**', '',
              '- No S9A freshness cancellation, S9B scratch, alternate runner clock, arm/gap/step sweep, geometry, leverage, fee, or live-code change was made.',
              '- Evidence remains exploratory/engineering validation because the runner habitat was selected from previously inspected history.'
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
