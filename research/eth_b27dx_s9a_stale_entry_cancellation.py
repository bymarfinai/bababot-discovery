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

PFX = 'ETH_B27DX_S9A_STALE_ENTRY_CANCELLATION'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_CAND = ROOT / f'{PFX}_Candidates.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_ANAT = ROOT / f'{PFX}_OriginalLockFreshness.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = s4.BAR5
PARTS = s4.PARTS


def annotate_freshness(x: pd.DataFrame, c: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    audits = []
    for r in c.itertuples(index=False):
        es = pd.Timestamp(r.execution_start)
        ee = es + pd.Timedelta(minutes=s4.HORIZON_MIN)
        exe = x[(x.index >= es) & (x.index < ee)]
        w = s4.b.m.corrected_find_window(exe, float(r.H), float(r.L), 'LONG')
        if w is None or not bool(w.get('clean', False)):
            raise AssertionError('S4 candidate no longer has clean causal window')
        fill = s4.b.find_fill(exe, w, float(r.entry_px))
        eligible = pd.Timestamp(w['eligible_start'])
        fill_ts = pd.Timestamp(r.entry_bar_start)
        fill_match = fill is not None and pd.Timestamp(fill) == fill_ts
        if not fill_match:
            raise AssertionError('S4 candidate fill reconstruction mismatch')
        delta = fill_ts - eligible
        if delta < pd.Timedelta(0) or delta % BAR5 != pd.Timedelta(0):
            raise AssertionError('invalid eligible-to-fill chronology')
        delay_bars = int(delta / BAR5)
        d = r._asdict()
        d['eligible_start'] = eligible
        d['delay_bars'] = delay_bars
        d['immediate_fill'] = bool(delay_bars == 0)
        rows.append(d)
        audits.append({
            'candidate_id': r.candidate_id,
            'partition': r.partition,
            'execution_utc': r.execution_utc,
            'fill_match': fill_match,
            'eligible_before_or_at_fill': eligible <= fill_ts,
            'delay_is_5m_multiple': delta % BAR5 == pd.Timedelta(0),
            'immediate_fill': bool(delay_bars == 0),
        })
    return pd.DataFrame(rows), pd.DataFrame(audits)


def variant_summary(name: str, summ: pd.DataFrame) -> pd.DataFrame:
    q = summ.copy()
    q.insert(0, 'variant', name)
    return q


def freshness_anatomy(base_dec: pd.DataFrame) -> pd.DataFrame:
    a = base_dec[base_dec.accepted].copy()
    rows = []
    for p in [*PARTS, 'POOLED_MAJOR']:
        q = a if p == 'POOLED_MAJOR' else a[a.partition == p]
        for imm, label in ((True, 'IMMEDIATE'), (False, 'STALE')):
            g = q[q.immediate_fill == imm].sort_values('entry_bar_start')
            m = s4.metrics(g, 'pnl_0')
            rows.append({
                'partition': p,
                'freshness': label,
                'n': int(len(g)),
                'losses': int((g.pnl_0 < 0).sum()),
                'loss_rate': float((g.pnl_0 < 0).mean()) if len(g) else np.nan,
                **m,
            })
    return pd.DataFrame(rows)


def fmt(v, nd=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    x, cov = s4.b.m.m.load5()
    base_raw = s4.build_candidates(x)
    parity = s4.parity_check(x, base_raw)
    parity_ok = bool(len(parity) and parity['pass'].all())

    c, audit = annotate_freshness(x, base_raw)
    audit_ok = bool(len(audit) == len(c) and audit[['fill_match','eligible_before_or_at_fill','delay_is_5m_multiple']].all().all())
    c.to_csv(OUT_CAND, index=False)
    audit.to_csv(OUT_AUDIT, index=False)

    base_dec, base_summ, _ = s4.summarize(c)
    filt_candidates = c[c.immediate_fill].copy()
    filt_dec, filt_summ, _ = s4.summarize(filt_candidates)

    combined = pd.concat([variant_summary('S4_BASELINE', base_summ), variant_summary('FIRST_ELIGIBLE_ONLY', filt_summ)], ignore_index=True)
    combined.to_csv(OUT_SUM, index=False)

    anat = freshness_anatomy(base_dec)
    anat.to_csv(OUT_ANAT, index=False)

    bp0 = base_summ[(base_summ.partition == 'POOLED_MAJOR') & (base_summ.stress_bps == 0)].iloc[0]
    fp0 = filt_summ[(filt_summ.partition == 'POOLED_MAJOR') & (filt_summ.stress_bps == 0)].iloc[0]
    fp5 = filt_summ[(filt_summ.partition == 'POOLED_MAJOR') & (filt_summ.stress_bps == 5)].iloc[0]
    fmajor = filt_summ[(filt_summ.partition.isin(PARTS)) & (filt_summ.stress_bps == 0)]

    baseline_ids = set(base_dec.loc[base_dec.accepted, 'candidate_id'].astype(str))
    filtered_ids = set(filt_dec.loc[filt_dec.accepted, 'candidate_id'].astype(str))
    newly_freed = filtered_ids - baseline_ids
    removed_baseline = baseline_ids - filtered_ids

    retention = float(fp0.accepted / bp0.accepted) if bp0.accepted else np.nan
    major_positive = bool(len(fmajor) == len(PARTS) and ((fmajor.pf > 1.0) & (fmajor.net > 0)).all())
    stress_ok = bool(fp5.pf > 1.0 and fp5.net > 0)
    improved = bool(fp0.wr > bp0.wr and fp0.pf > bp0.pf and fp0.expectancy > bp0.expectancy)
    support = bool(parity_ok and audit_ok and major_positive and stress_ok and retention >= 0.50 and improved)
    btc_quality = bool(fp0.wr >= s4.BTC_WR and fp0.pf >= s4.BTC_PF and fp0.expectancy >= s4.BTC_EXP)

    status = 'ETH_S9A_STALE_ENTRY_CANCELLATION_SUPPORTED' if support else 'ETH_S9A_STALE_ENTRY_CANCELLATION_NOT_SUPPORTED'

    orig_imm = anat[(anat.partition == 'POOLED_MAJOR') & (anat.freshness == 'IMMEDIATE')].iloc[0]
    orig_stale = anat[(anat.partition == 'POOLED_MAJOR') & (anat.freshness == 'STALE')].iloc[0]

    lines = [
        '# ETH B27DX — S9A Stale Entry Cancellation — Result', '',
        f'ETH raw 5m coverage: **{cov:.4%}**.', '',
        'Frozen rule: **F75 fill must occur on the first eligible raw 5m bar after completed leave; later fills are cancelled.**', '',
        f'- Candidate-detail parity: **{"PASS" if parity_ok else "FAIL"}**.',
        f'- Eligible-bar causal audit: **{"PASS" if audit_ok else "FAIL"}**.',
        f'- Raw candidates: **{len(c)}**; immediate **{int(c.immediate_fill.sum())}**; stale **{int((~c.immediate_fill).sum())}**.', '',
        '## Original S4 accepted-trade freshness anatomy', '',
        '| Freshness | N | Losses | Loss rate | WR | PF | Exp | Net |',
        '|---|---:|---:|---:|---:|---:|---:|---:|',
        f'| Immediate | {int(orig_imm.n)} | {int(orig_imm.losses)} | {pct(orig_imm.loss_rate)} | {pct(orig_imm.wr)} | {fmt(orig_imm.pf)} | {fmt(orig_imm.expectancy)} | {fmt(orig_imm.net)} |',
        f'| Stale | {int(orig_stale.n)} | {int(orig_stale.losses)} | {pct(orig_stale.loss_rate)} | {pct(orig_stale.wr)} | {fmt(orig_stale.pf)} | {fmt(orig_stale.expectancy)} | {fmt(orig_stale.net)} |', '',
        '## Re-locked portfolio comparison', '',
        '| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in [*PARTS, 'POOLED_MAJOR']:
        for variant, ss in (('S4', base_summ), ('First-only', filt_summ)):
            for stress in (0, 5):
                r = ss[(ss.partition == p) & (ss.stress_bps == stress)].iloc[0]
                lines.append(f'| {p} | {variant} | {stress} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')
    lines += [
        '', '## Portfolio impact', '',
        f'- Accepted-trade retention vs S4: **{retention:.1%}**.',
        f'- Baseline accepted removed by freshness rule/re-lock: **{len(removed_baseline)}**.',
        f'- Newly freed accepted trades after re-lock: **{len(newly_freed)}**.',
        f'- Pooled 0 bps WR change: **{pct(bp0.wr)} → {pct(fp0.wr)}**.',
        f'- Pooled 0 bps PF change: **{fmt(bp0.pf)} → {fmt(fp0.pf)}**.',
        f'- Pooled 0 bps expectancy change: **{fmt(bp0.expectancy)} → {fmt(fp0.expectancy)}**.',
        f'- Pooled frequency: **{bp0.trades_per_week:.3f} → {fp0.trades_per_week:.3f} trades/week**.', '',
        '## Frozen gates', '',
        f'- All three major partitions positive at 0 bps: **{"PASS" if major_positive else "FAIL"}**.',
        f'- 5 bps pooled stress positive: **{"PASS" if stress_ok else "FAIL"}**.',
        f'- Retention >= 50%: **{"PASS" if retention >= 0.50 else "FAIL"}**.',
        f'- WR + PF + expectancy all improve vs S4: **{"PASS" if improved else "FAIL"}**.',
        f'- BTC-class diagnostic (WR/PF/expectancy): **{"PASS" if btc_quality else "FAIL"}**.', '',
        '## Decision', '',
        f'**Status: {status}**', '',
        '- No alternate freshness cutoff, geometry, runner, leverage, fee, or live-code change was made.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
