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

PFX = 'ETH_B27DX_S9B_EARLY_STRUCTURAL_FAILURE_EXIT'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_CAND = ROOT / f'{PFX}_Candidates.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_EXIT = ROOT / f'{PFX}_ExitReasons.csv'
OUT_LOSS = ROOT / f'{PFX}_BaselineLossImpact.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

BAR5 = s4.BAR5
PARTS = s4.PARTS


def time_exit_open(x: pd.DataFrame, ee: pd.Timestamp) -> float | None:
    return s4.time_exit_open(x, ee)


def score_path(x: pd.DataFrame, exe: pd.DataFrame, fill_ts: pd.Timestamp, ee: pd.Timestamp,
               ep: float, target: float, stop: float, H: float, leave_close: float,
               stress_bps: float = 0.0, enable_scratch: bool = True) -> dict | None:
    q = exe[exe.index >= fill_ts + BAR5]
    reason = None
    xp = None
    exit_ts = pd.NaT
    h_revisited = False

    for ts, r in q.iterrows():
        ts = pd.Timestamp(ts)
        hi = float(r.high)
        cl = float(r.close)

        if hi >= target:
            xp = float(target)
            reason = 'TARGET'
            exit_ts = ts + BAR5
            break

        if cl < stop:
            xp = cl
            reason = 'CLOSE_INVALIDATION'
            exit_ts = ts + BAR5
            break

        if enable_scratch and not h_revisited:
            if hi >= H:
                h_revisited = True
            elif cl < leave_close:
                xp = cl
                reason = 'EARLY_STRUCTURAL_FAILURE'
                exit_ts = ts + BAR5
                break

    if reason is None:
        xp = time_exit_open(x, ee)
        if xp is None:
            return None
        reason = 'TIME_EXIT'
        exit_ts = pd.Timestamp(ee)

    bps = float(stress_bps) / 10000.0
    entry_exec = float(ep) * (1.0 + bps)
    exit_exec = float(xp) if reason == 'TARGET' else float(xp) * (1.0 - bps)
    pnl = s4.NOTIONAL * (exit_exec / entry_exec - 1.0) - s4.FEE
    return {
        'exit_ts': pd.Timestamp(exit_ts),
        'exit_px': float(xp),
        'exit_reason': reason,
        'pnl': float(pnl),
        'h_revisited_before_exit': bool(h_revisited),
    }


def rescore_candidates(x: pd.DataFrame, c: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    audits = []
    for r in c.itertuples(index=False):
        es = pd.Timestamp(r.execution_start)
        ee = es + pd.Timedelta(minutes=s4.HORIZON_MIN)
        exe = x[(x.index >= es) & (x.index < ee)]
        H = float(r.H); L = float(r.L); R = H - L
        w = s4.b.m.corrected_find_window(exe, H, L, 'LONG')
        if w is None or not bool(w.get('clean', False)):
            raise AssertionError('candidate lost clean B27DX window')
        fill = s4.b.find_fill(exe, w, float(r.entry_px))
        fill_ts = pd.Timestamp(r.entry_bar_start)
        if fill is None or pd.Timestamp(fill) != fill_ts:
            raise AssertionError('candidate fill reconstruction mismatch')

        leave = pd.Timestamp(w['leave_bar'])
        eligible = pd.Timestamp(w['eligible_start'])
        if not (leave < eligible <= fill_ts):
            raise AssertionError('leave/eligible/fill chronology failed')
        leave_close = float(exe.loc[leave].close)
        target = s4.b.target_level(L, H, 'LONG', s4.TARGET_EXT)
        stop = s4.b.stop_level(L, H, s4.STOP_F)

        # Exact baseline parity with scratch disabled.
        b0 = score_path(x, exe, fill_ts, ee, float(r.entry_px), target, stop, H, leave_close, 0.0, False)
        b5 = score_path(x, exe, fill_ts, ee, float(r.entry_px), target, stop, H, leave_close, 5.0, False)
        if b0 is None or b5 is None:
            raise AssertionError('baseline rescore missing')
        baseline_match = (
            b0['exit_ts'] == pd.Timestamp(r.exit_ts)
            and b0['exit_reason'] == r.exit_reason
            and abs(float(b0['pnl']) - float(r.pnl_0)) <= 1e-9
            and abs(float(b5['pnl']) - float(r.pnl_5)) <= 1e-9
        )
        if not baseline_match:
            raise AssertionError('baseline path parity failed')

        d0 = score_path(x, exe, fill_ts, ee, float(r.entry_px), target, stop, H, leave_close, 0.0, True)
        d5 = score_path(x, exe, fill_ts, ee, float(r.entry_px), target, stop, H, leave_close, 5.0, True)
        if d0 is None or d5 is None:
            raise AssertionError('S9B rescore missing')
        if d0['exit_ts'] != d5['exit_ts'] or d0['exit_reason'] != d5['exit_reason']:
            raise AssertionError('stress changed structural exit chronology')

        d = r._asdict()
        d.update({
            'baseline_exit_ts': pd.Timestamp(r.exit_ts),
            'baseline_exit_reason': r.exit_reason,
            'baseline_pnl_0': float(r.pnl_0),
            'baseline_pnl_5': float(r.pnl_5),
            'leave_bar': leave,
            'leave_close': leave_close,
            'eligible_start': eligible,
            'exit_ts': d0['exit_ts'],
            'exit_px_0': d0['exit_px'],
            'exit_reason': d0['exit_reason'],
            'pnl_0': d0['pnl'],
            'pnl_5': d5['pnl'],
            'h_revisited_before_exit': d0['h_revisited_before_exit'],
            'exit_earlier_than_baseline': bool(d0['exit_ts'] < pd.Timestamp(r.exit_ts)),
        })
        rows.append(d)
        audits.append({
            'candidate_id': r.candidate_id,
            'partition': r.partition,
            'execution_utc': r.execution_utc,
            'baseline_path_parity': baseline_match,
            'leave_completed_before_eligible': leave < eligible,
            'eligible_before_or_at_fill': eligible <= fill_ts,
            'leave_close_known_by_entry': leave + BAR5 <= fill_ts,
            'stress_exit_chronology_match': d0['exit_ts'] == d5['exit_ts'] and d0['exit_reason'] == d5['exit_reason'],
        })
    return pd.DataFrame(rows), pd.DataFrame(audits)


def variant_summary(name: str, summ: pd.DataFrame) -> pd.DataFrame:
    q = summ.copy(); q.insert(0, 'variant', name); return q


def loss_stats(dec: pd.DataFrame, pnl_col: str) -> dict:
    a = dec[dec.accepted].copy()
    losses = pd.to_numeric(a.loc[a[pnl_col] < 0, pnl_col], errors='coerce').dropna()
    return {
        'n_loss': int(len(losses)),
        'mean_loss': float(losses.mean()) if len(losses) else np.nan,
        'median_loss': float(losses.median()) if len(losses) else np.nan,
        'mean_abs_loss': float((-losses).mean()) if len(losses) else np.nan,
    }


def fmt(v, nd=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.1f}%'


def main():
    x, cov = s4.b.m.m.load5()
    base_c = s4.build_candidates(x)
    parity = s4.parity_check(x, base_c)
    base_detail_parity = bool(len(parity) and parity['pass'].all())

    c, audit = rescore_candidates(x, base_c)
    audit.to_csv(OUT_AUDIT, index=False)
    c.to_csv(OUT_CAND, index=False)
    audit_ok = bool(len(audit) == len(c) and audit[['baseline_path_parity','leave_completed_before_eligible','eligible_before_or_at_fill','leave_close_known_by_entry','stress_exit_chronology_match']].all().all())

    base_dec, base_summ, _ = s4.summarize(base_c)
    s9_dec, s9_summ, _ = s4.summarize(c)
    pd.concat([variant_summary('S4_BASELINE', base_summ), variant_summary('S9B_STRUCTURAL_EXIT', s9_summ)], ignore_index=True).to_csv(OUT_SUM, index=False)

    # Exit reason profile on the re-locked S9B portfolio.
    erows = []
    for p in [*PARTS, 'POOLED_MAJOR']:
        q = s9_dec[s9_dec.accepted].copy()
        if p != 'POOLED_MAJOR': q = q[q.partition == p]
        n = len(q)
        for reason, g in q.groupby('exit_reason'):
            erows.append({'partition': p, 'exit_reason': reason, 'n': len(g), 'share': len(g)/n if n else np.nan,
                          'wr': float((g.pnl_0 > 0).mean()) if len(g) else np.nan,
                          'mean_pnl': float(g.pnl_0.mean()) if len(g) else np.nan})
    exit_df = pd.DataFrame(erows)
    exit_df.to_csv(OUT_EXIT, index=False)

    # What happened to the exact baseline accepted losses under S9B candidate-level rescoring?
    s9_map = c.set_index('candidate_id')
    lrows = []
    for r in base_dec[(base_dec.accepted) & (base_dec.pnl_0 < 0)].itertuples(index=False):
        z = s9_map.loc[r.candidate_id]
        lrows.append({
            'candidate_id': r.candidate_id,
            'partition': r.partition,
            'execution_utc': r.execution_utc,
            'baseline_pnl': float(r.pnl_0),
            's9b_pnl_same_candidate': float(z.pnl_0),
            'baseline_exit_ts': pd.Timestamp(r.exit_ts),
            's9b_exit_ts_same_candidate': pd.Timestamp(z.exit_ts),
            's9b_exit_reason': z.exit_reason,
            'cut_earlier': bool(pd.Timestamp(z.exit_ts) < pd.Timestamp(r.exit_ts)),
            'converted_to_nonloss': bool(float(z.pnl_0) >= 0),
            'loss_reduction': float(z.pnl_0 - r.pnl_0),
        })
    loss_df = pd.DataFrame(lrows)
    loss_df.to_csv(OUT_LOSS, index=False)

    bp0 = base_summ[(base_summ.partition == 'POOLED_MAJOR') & (base_summ.stress_bps == 0)].iloc[0]
    sp0 = s9_summ[(s9_summ.partition == 'POOLED_MAJOR') & (s9_summ.stress_bps == 0)].iloc[0]
    sp5 = s9_summ[(s9_summ.partition == 'POOLED_MAJOR') & (s9_summ.stress_bps == 5)].iloc[0]
    major = s9_summ[(s9_summ.partition.isin(PARTS)) & (s9_summ.stress_bps == 0)]

    base_loss = loss_stats(base_dec, 'pnl_0')
    s9_loss = loss_stats(s9_dec, 'pnl_0')
    major_positive = bool(len(major) == len(PARTS) and ((major.pf > 1.0) & (major.net > 0)).all())
    stress_ok = bool(sp5.pf > 1.0 and sp5.net > 0)
    economics_improve = bool(sp0.pf > bp0.pf and sp0.expectancy > bp0.expectancy and sp0.net > bp0.net)
    loss_improve = bool(pd.notna(base_loss['mean_abs_loss']) and pd.notna(s9_loss['mean_abs_loss']) and s9_loss['mean_abs_loss'] < base_loss['mean_abs_loss'])
    support = bool(base_detail_parity and audit_ok and major_positive and stress_ok and economics_improve and loss_improve)
    btc_quality = bool(sp0.wr >= s4.BTC_WR and sp0.pf >= s4.BTC_PF and sp0.expectancy >= s4.BTC_EXP)

    base_ids = set(base_dec.loc[base_dec.accepted, 'candidate_id'].astype(str))
    s9_ids = set(s9_dec.loc[s9_dec.accepted, 'candidate_id'].astype(str))
    newly_freed = s9_ids - base_ids
    early_n = int(((s9_dec.accepted) & (s9_dec.exit_reason == 'EARLY_STRUCTURAL_FAILURE')).sum())
    baseline_losses = len(loss_df)
    cut_n = int(loss_df.cut_earlier.sum()) if len(loss_df) else 0
    conv_n = int(loss_df.converted_to_nonloss.sum()) if len(loss_df) else 0
    avg_reduction = float(loss_df.loss_reduction.mean()) if len(loss_df) else np.nan

    status = 'ETH_S9B_EARLY_STRUCTURAL_FAILURE_EXIT_SUPPORTED' if support else 'ETH_S9B_EARLY_STRUCTURAL_FAILURE_EXIT_NOT_SUPPORTED'

    lines = [
        '# ETH B27DX — S9B Early Structural Failure Exit — Result', '',
        f'ETH raw 5m coverage: **{cov:.4%}**.', '',
        'Frozen rule: before any post-entry H revisit, a completed bar closing below the frozen leave-bar close exits as `EARLY_STRUCTURAL_FAILURE`; target and F20 precedence remain frozen.', '',
        f'- S4 candidate-detail parity: **{"PASS" if base_detail_parity else "FAIL"}**.',
        f'- Leave / execution causal audit: **{"PASS" if audit_ok else "FAIL"}**.', '',
        '## Portfolio comparison', '',
        '| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for p in [*PARTS, 'POOLED_MAJOR']:
        for variant, ss in (('S4', base_summ), ('S9B', s9_summ)):
            for stress in (0, 5):
                r = ss[(ss.partition == p) & (ss.stress_bps == stress)].iloc[0]
                lines.append(f'| {p} | {variant} | {stress} bps | {int(r.accepted)} | {r.trades_per_week:.3f} | {pct(r.wr)} | {fmt(r.pf)} | {fmt(r.expectancy)} | {fmt(r.net)} | {int(r.max_ls)} |')

    lines += [
        '', '## Loss impact', '',
        f'- S4 losing accepted trades: **{baseline_losses}**.',
        f'- Exact baseline losses exited earlier under S9B candidate path: **{cut_n} ({(cut_n/baseline_losses if baseline_losses else 0):.1%})**.',
        f'- Exact baseline losses converted to non-loss on the same candidate path: **{conv_n} ({(conv_n/baseline_losses if baseline_losses else 0):.1%})**.',
        f'- Mean PnL improvement across exact baseline losses: **{fmt(avg_reduction)}**.',
        f'- Mean absolute losing PnL, executable portfolio: **{fmt(base_loss["mean_abs_loss"])} → {fmt(s9_loss["mean_abs_loss"])}**.',
        f'- Median losing PnL: **{fmt(base_loss["median_loss"])} → {fmt(s9_loss["median_loss"])}**.',
        f'- Accepted S9B `EARLY_STRUCTURAL_FAILURE` exits: **{early_n}**.',
        f'- Newly freed accepted trades after shorter holding periods: **{len(newly_freed)}**.', '',
        '## Frozen gates', '',
        f'- All major partitions PF>1 and net>0: **{"PASS" if major_positive else "FAIL"}**.',
        f'- Pooled 5 bps positive: **{"PASS" if stress_ok else "FAIL"}**.',
        f'- Pooled PF + expectancy + net all improve: **{"PASS" if economics_improve else "FAIL"}**.',
        f'- Mean absolute loss decreases: **{"PASS" if loss_improve else "FAIL"}**.',
        f'- BTC-class diagnostic: **{"PASS" if btc_quality else "FAIL"}**.', '',
        '## Decision', '',
        f'**Status: {status}**', '',
        '- No S9A freshness rule, alternate scratch threshold, geometry, runner, leverage, fee, or live-code change was made.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
