#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import eth_f85_f15_transfer_m1_k1_opp0 as data_base
import bnb_f85_f15_transfer_m3_frozen_economics_b27ef as m3

PFX = 'BNB_F85_F15_TRANSFER_M4_PATH_DIAGNOSTICS_B27EG'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_COHORT = ROOT / f'{PFX}_CohortSummary.csv'
OUT_SOURCE = ROOT / f'{PFX}_SourceDiagnosis.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
MAJOR = ('external', 'development', 'reference_validation')
SOURCES = ('ALT_0330', 'RAW_0530', 'SHORT_2000')
BAR5 = pd.Timedelta(minutes=5)


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    return x.iloc[int(x.index.searchsorted(a, side='left')):int(x.index.searchsorted(z, side='left'))]


def candidate_id(partition, side, source, entry_ts) -> str:
    return f'{partition}|{side}|{source}|{pd.Timestamp(entry_ts).isoformat()}'


def qtile(s, q):
    x = pd.to_numeric(pd.Series(s), errors='coerce').dropna()
    return float(x.quantile(q)) if len(x) else np.nan


def pct(x):
    return '-' if pd.isna(x) else f'{100.0*float(x):.1f}%'


def num(x):
    return '-' if pd.isna(x) else f'{float(x):.3f}'


def exact_end_open(x5: pd.DataFrame, end: pd.Timestamp) -> float:
    pos = int(x5.index.searchsorted(end, side='left'))
    if pos >= len(x5) or x5.index[pos] != end:
        raise AssertionError(f'missing execution-end open {end}')
    return float(x5.iloc[pos].open)


def first_level_ts(q: pd.DataFrame, side: str, level: float):
    if q.empty:
        return pd.NaT
    if side == 'LONG':
        hit = q.high.astype(float) >= float(level)
    else:
        hit = q.low.astype(float) <= float(level)
    if not bool(hit.any()):
        return pd.NaT
    return pd.Timestamp(q.index[np.flatnonzero(hit.to_numpy())[0]])


def path_row(r: pd.Series, x5: pd.DataFrame) -> dict:
    entry_ts = pd.Timestamp(r.entry_ts)
    end = pd.Timestamp(r.execution_end)
    entry = float(r.entry_px)
    H = float(r.H); L = float(r.L); R = float(r.R)
    side = str(r.side)
    q = fs(x5, entry_ts, end)
    if q.empty or q.index[0] != entry_ts:
        raise AssertionError(f'missing diagnostic path {r.candidate_id}')

    if side == 'LONG':
        mfe = (float(q.high.max()) - entry) / R
        mae = (entry - float(q.low.min())) / R
    else:
        mfe = (entry - float(q.low.min())) / R
        mae = (float(q.high.max()) - entry) / R

    h2 = str(r.structural_outcome) == 'H2'
    h2_ts = pd.Timestamp(r.structural_h2_ts) if h2 and pd.notna(r.structural_h2_ts) else pd.NaT
    pre_mfe = np.nan; pre_mae = np.nan; post_ext = np.nan
    e_hits = {10: False, 20: False, 30: False, 50: False}
    e_ts = {10: pd.NaT, 20: pd.NaT, 30: pd.NaT, 50: pd.NaT}

    if h2:
        if pd.isna(h2_ts) or not (entry_ts <= h2_ts < end):
            raise AssertionError(f'invalid H2 timestamp {r.candidate_id}: {h2_ts}')
        pre = fs(x5, entry_ts, h2_ts)  # strictly before H2 bar; avoids intrabar ordering assumption
        if len(pre):
            if side == 'LONG':
                pre_mfe = (float(pre.high.max()) - entry) / R
                pre_mae = (entry - float(pre.low.min())) / R
            else:
                pre_mfe = (entry - float(pre.low.min())) / R
                pre_mae = (float(pre.high.max()) - entry) / R
        post = fs(x5, h2_ts, end)
        if side == 'LONG':
            post_ext = (float(post.high.max()) - H) / R
            levels = {k: H + (k / 100.0) * R for k in e_hits}
        else:
            post_ext = (L - float(post.low.min())) / R
            levels = {k: L - (k / 100.0) * R for k in e_hits}
        for k, lev in levels.items():
            ts = first_level_ts(post, side, lev)
            e_ts[k] = ts
            e_hits[k] = pd.notna(ts)

    end_open = exact_end_open(x5, end)
    if side == 'LONG':
        end_ret = (end_open - entry) / R
    else:
        end_ret = (entry - end_open) / R

    exit_ts = pd.Timestamp(r.exit_ts)
    e20_before_exit = bool(e_hits[20] and pd.Timestamp(e_ts[20]) <= exit_ts)
    e20_after_exit = bool(e_hits[20] and pd.Timestamp(e_ts[20]) > exit_ts)

    return {
        'full_mfe_R': float(mfe), 'full_mae_R': float(mae),
        'pre_h2_mfe_R': pre_mfe, 'pre_h2_mae_R': pre_mae,
        'post_h2_extension_R': post_ext,
        'e10_reached': bool(e_hits[10]), 'e20_reached': bool(e_hits[20]),
        'e30_reached': bool(e_hits[30]), 'e50_reached': bool(e_hits[50]),
        'first_e10_ts': e_ts[10], 'first_e20_ts': e_ts[20],
        'first_e30_ts': e_ts[30], 'first_e50_ts': e_ts[50],
        'e20_before_or_at_exit': e20_before_exit, 'e20_after_exit': e20_after_exit,
        'execution_end_open': end_open, 'execution_end_return_R': float(end_ret),
    }


def cohort_metrics(q: pd.DataFrame) -> dict:
    n = len(q)
    h = q[q.structural_outcome.eq('H2')]
    return {
        'n': int(n),
        'h2_rate': float(q.structural_outcome.eq('H2').mean()) if n else np.nan,
        'mfe_p25_R': qtile(q.full_mfe_R, .25), 'mfe_median_R': qtile(q.full_mfe_R, .50), 'mfe_p75_R': qtile(q.full_mfe_R, .75),
        'mae_p25_R': qtile(q.full_mae_R, .25), 'mae_median_R': qtile(q.full_mae_R, .50), 'mae_p75_R': qtile(q.full_mae_R, .75),
        'pre_h2_mae_median_R': qtile(h.pre_h2_mae_R, .50),
        'post_h2_extension_median_R': qtile(h.post_h2_extension_R, .50),
        'h2_e10_rate': float(h.e10_reached.mean()) if len(h) else np.nan,
        'h2_e20_rate': float(h.e20_reached.mean()) if len(h) else np.nan,
        'h2_e30_rate': float(h.e30_reached.mean()) if len(h) else np.nan,
        'h2_e50_rate': float(h.e50_reached.mean()) if len(h) else np.nan,
        'execution_end_return_median_R': qtile(q.execution_end_return_R, .50),
    }


def classify_source(q: pd.DataFrame) -> tuple[str, dict]:
    losses = q[q.economic_label.eq('LOSS')]
    h2_losses = losses[losses.structural_outcome.eq('H2')]
    loss_h2_rate = float(losses.structural_outcome.eq('H2').mean()) if len(losses) else np.nan
    h2_loss_e20 = float(h2_losses.e20_reached.mean()) if len(h2_losses) else np.nan
    h2_loss_e20_before = float(h2_losses.e20_before_or_at_exit.mean()) if len(h2_losses) else np.nan
    h2_loss_e20_after = float(h2_losses.e20_after_exit.mean()) if len(h2_losses) else np.nan

    if len(losses) and float((~losses.structural_outcome.eq('H2')).mean()) >= .60:
        label = 'STRUCTURE_FAILS_BEFORE_H2'
    elif len(h2_losses) and loss_h2_rate >= .60 and float((~h2_losses.e20_reached).mean()) >= .60:
        label = 'H2_WITHOUT_EXTENSION'
    elif len(h2_losses) and h2_loss_e20 >= .60:
        label = 'EXTENSION_THEN_GIVEBACK'
    else:
        label = 'MIXED_PATH_FAILURE'

    diag = {
        'source': str(q.source.iloc[0]) if len(q) else '',
        'accepted_major_n': int(len(q)), 'economic_losses': int(len(losses)),
        'loss_h2_rate': loss_h2_rate,
        'h2_loss_e20_rate': h2_loss_e20,
        'h2_loss_e20_before_exit_rate': h2_loss_e20_before,
        'h2_loss_e20_after_exit_rate': h2_loss_e20_after,
        'diagnosis': label,
    }
    return label, diag


def main():
    status = (ROOT / 'BNB_F85_F15_TRANSFER_M3_FROZEN_ECONOMICS_B27EF_Status.txt').read_text().strip()
    if status != 'B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED':
        raise AssertionError(f'B27EF prerequisite drift: {status}')

    x5, coverage = data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'BNB raw coverage below gate: {coverage:.6f}')

    saved = pd.read_csv(ROOT / 'BNB_F85_F15_TRANSFER_M3_FROZEN_ECONOMICS_B27EF_Detail.csv')
    for c in ('entry_ts', 'execution_end', 'exit_ts'):
        saved[c] = pd.to_datetime(saved[c], utc=True)
    if saved.candidate_id.duplicated().any():
        raise AssertionError('duplicate B27EF candidate IDs')

    # Reproduce B27EF candidate identity, economics, and portfolio arbitration exactly.
    regen = m3.replay_candidates(x5)
    eval_rows = []
    for r in regen.itertuples(index=False):
        out = m3.evaluate_candidate(r, x5)
        eval_rows.append({**r._asdict(), **out})
    locked = m3.lock_portfolio(pd.DataFrame(eval_rows))
    locked['entry_ts'] = pd.to_datetime(locked.entry_ts, utc=True)
    locked['exit_ts'] = pd.to_datetime(locked.exit_ts, utc=True)
    locked = locked.sort_values('candidate_id').reset_index(drop=True)
    chk = saved.sort_values('candidate_id').reset_index(drop=True)
    if locked.candidate_id.tolist() != chk.candidate_id.tolist():
        raise AssertionError('B27EF candidate ID reproduction failed')
    if locked.accepted.astype(bool).tolist() != chk.accepted.astype(bool).tolist():
        raise AssertionError('B27EF accepted/blocked reproduction failed')
    if locked.exit_reason.astype(str).tolist() != chk.exit_reason.astype(str).tolist():
        raise AssertionError('B27EF exit-reason reproduction failed')
    if not np.allclose(locked.pnl.astype(float), chk.pnl.astype(float), rtol=0, atol=1e-9):
        raise AssertionError('B27EF PnL reproduction failed')

    # Exact B27EE one-to-one structural join.
    s2 = pd.read_csv(ROOT / 'BNB_F85_F15_TRANSFER_M2_EXACT_SIGNAL_B27EE_Detail.csv')
    s2 = s2[(s2.symbol == TARGET) & s2.source.isin(SOURCES)].copy()
    s2['entry_ts'] = pd.to_datetime(s2.entry_ts, utc=True)
    s2['candidate_id'] = [candidate_id(r.partition, r.side, r.source, r.entry_ts) for r in s2.itertuples(index=False)]
    if s2.candidate_id.duplicated().any():
        raise AssertionError('duplicate B27EE diagnostic IDs')
    if set(s2.candidate_id) != set(saved.candidate_id):
        raise AssertionError(f'B27EE/B27EF one-to-one join failed: B27EE={len(s2)}, B27EF={len(saved)}')
    structural = s2[['candidate_id', 'outcome', 'outcome_bar_start']].rename(columns={'outcome':'structural_outcome','outcome_bar_start':'structural_h2_ts'})
    structural['structural_h2_ts'] = pd.to_datetime(structural.structural_h2_ts, utc=True, errors='coerce')
    d = saved.merge(structural, on='candidate_id', how='left', validate='one_to_one')

    rows=[]
    for _, r in d.iterrows():
        rows.append({**r.to_dict(), **path_row(r, x5)})
    d = pd.DataFrame(rows)
    d['economic_label'] = np.where(d.pnl.astype(float) > 0, 'WIN', 'LOSS')
    d.to_csv(OUT_DETAIL, index=False)

    primary = d[d.accepted.astype(bool) & d.partition.isin(MAJOR)].copy()
    if len(primary) != 170:
        raise AssertionError(f'pooled-major accepted count drift: {len(primary)} != 170')

    cohort_rows=[]
    for src in SOURCES:
        for label in ('ALL','WIN','LOSS'):
            q = primary[primary.source.eq(src)]
            if label != 'ALL': q = q[q.economic_label.eq(label)]
            cohort_rows.append({'source':src, 'cohort':label, **cohort_metrics(q)})
    cohort = pd.DataFrame(cohort_rows)
    cohort.to_csv(OUT_COHORT, index=False)

    source_rows=[]
    for src in SOURCES:
        _, diag = classify_source(primary[primary.source.eq(src)])
        source_rows.append(diag)
    source = pd.DataFrame(source_rows)
    source.to_csv(OUT_SOURCE, index=False)

    # Overall loss/H2 facts plus source-specific decomposition.
    losses = primary[primary.economic_label.eq('LOSS')]
    h2_losses = losses[losses.structural_outcome.eq('H2')]
    overall_loss_h2 = float(losses.structural_outcome.eq('H2').mean()) if len(losses) else np.nan
    overall_h2 = primary[primary.structural_outcome.eq('H2')]

    lines = [
        '# BNB F85/F15 Transfer — M4 Path Diagnostics — B27EG Result','',
        f'Raw BNB 5m coverage: **{coverage:.4%}**. B27EF reproduction: **PASS ({len(saved)} candidates; 170 pooled-major accepted)**. B27EE structural join: **PASS one-to-one**.','',
        'This is path diagnosis only. Frozen B27EF exits/PnL were not changed; diagnostic paths continue to the original execution-window end.','',
        '## Core contradiction','',
        f'- Economic losers that nevertheless reached structural H2: **{pct(overall_loss_h2)}** ({int((losses.structural_outcome=="H2").sum())}/{len(losses)}).',
        f'- Among all accepted H2 trades, later E10/E20/E30/E50 reach: **{pct(overall_h2.e10_reached.mean())} / {pct(overall_h2.e20_reached.mean())} / {pct(overall_h2.e30_reached.mean())} / {pct(overall_h2.e50_reached.mean())}**.','',
        '## Source diagnosis','',
        '| Source | Accepted | Losses | Loss→H2 | H2-loss→E20 | E20 before exit | E20 after exit | Diagnosis |',
        '|---|---:|---:|---:|---:|---:|---:|---|'
    ]
    for r in source.itertuples(index=False):
        lines.append(f'| {r.source} | {r.accepted_major_n} | {r.economic_losses} | {pct(r.loss_h2_rate)} | {pct(r.h2_loss_e20_rate)} | {pct(r.h2_loss_e20_before_exit_rate)} | {pct(r.h2_loss_e20_after_exit_rate)} | {r.diagnosis} |')

    lines += ['', '## Winner vs loser path distribution','',
              '| Source | Cohort | N | H2 | MFE p25/med/p75 R | MAE p25/med/p75 R | Pre-H2 MAE med R | Post-H2 ext med R | H2→E10/E20/E30/E50 | End return med R |',
              '|---|---|---:|---:|---|---|---:|---:|---|---:|']
    for r in cohort.itertuples(index=False):
        lines.append(
            f'| {r.source} | {r.cohort} | {r.n} | {pct(r.h2_rate)} | '
            f'{num(r.mfe_p25_R)}/{num(r.mfe_median_R)}/{num(r.mfe_p75_R)} | '
            f'{num(r.mae_p25_R)}/{num(r.mae_median_R)}/{num(r.mae_p75_R)} | '
            f'{num(r.pre_h2_mae_median_R)} | {num(r.post_h2_extension_median_R)} | '
            f'{pct(r.h2_e10_rate)}/{pct(r.h2_e20_rate)}/{pct(r.h2_e30_rate)}/{pct(r.h2_e50_rate)} | '
            f'{num(r.execution_end_return_median_R)} |')

    # Explicit mechanistic notes from frozen labels and timing counts.
    lines += ['', '## Mechanistic readout','']
    for src in SOURCES:
        q = primary[(primary.source == src) & (primary.economic_label == 'LOSS')]
        h = q[q.structural_outcome == 'H2']
        before = int(h.e20_before_or_at_exit.sum()) if len(h) else 0
        after = int(h.e20_after_exit.sum()) if len(h) else 0
        no_e20 = int((~h.e20_reached).sum()) if len(h) else 0
        lines.append(f'- **{src}**: losses={len(q)}, H2-losses={len(h)}; among H2-losses E20 before/at frozen exit={before}, only after frozen exit={after}, never by execution end={no_e20}. Diagnosis: **{source.loc[source.source==src,"diagnosis"].iloc[0]}**.')

    lines += ['', '**Status: B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE**','',
              'B27EG stops here. No BNB-native target/stop/runner optimization and no decision rule is executed automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27EG_BNB_PATH_DIAGNOSTICS_COMPLETE\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
