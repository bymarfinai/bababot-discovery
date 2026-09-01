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

PFX = 'ETH_B27DX_S8L_LOSS_ANATOMY'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_TRADES = ROOT / f'{PFX}_AcceptedTrades.csv'
OUT_CLOCK = ROOT / f'{PFX}_LossByClock.csv'
OUT_CONT = ROOT / f'{PFX}_ContinuousAssociations.csv'
OUT_BIN = ROOT / f'{PFX}_BinaryAssociations.csv'
OUT_PATH = ROOT / f'{PFX}_LossPath.csv'
OUT_AUDIT = ROOT / f'{PFX}_Audit.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

PARTS = s4.PARTS
BAR5 = s4.BAR5
REF_MIN = s4.REF_MIN
HORIZON_MIN = s4.HORIZON_MIN
TARGET_DISTANCE_R = (1.0 + s4.TARGET_EXT) - s4.ENTRY_F

CONT_FEATURES = (
    'pre4_return',
    'pre24_return',
    'pre24_vol',
    'pre24_range_pct',
    'ref_return',
    'ref_range_pct',
    'ref_close_location',
    'range_completion_frac',
    'extreme_spacing_frac',
    'k1_start_frac',
    'leave_time_frac',
    'k1_episode_bars',
    'k1_overshoot_R',
    'leave_drop_from_H_R',
    'k1_to_fill_frac',
    'post_leave_to_fill_frac',
)

BIN_FEATURES = (
    'high_before_low',
    'single_k1',
    'pre4_up',
    'pre24_up',
    'ref_up',
    'ref_close_upper_half',
)


def fast_slice(x: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x.index.searchsorted(start, side='left'))
    b = int(x.index.searchsorted(end, side='left'))
    return x.iloc[a:b]


def first_extreme_ts(ref: pd.DataFrame, col: str, val: float) -> pd.Timestamp:
    arr = ref[col].to_numpy(float)
    tol = max(1e-10, abs(float(val)) * 1e-12)
    idx = np.flatnonzero(np.isclose(arr, float(val), rtol=0.0, atol=tol))
    if len(idx) == 0:
        raise AssertionError(f'{col} extreme occurrence missing')
    return pd.Timestamp(ref.index[int(idx[0])])


def simple_return(q: pd.DataFrame) -> float:
    if q.empty:
        return np.nan
    op = float(q.iloc[0].open)
    cl = float(q.iloc[-1].close)
    return cl / op - 1.0 if op > 0 else np.nan


def realized_vol(q: pd.DataFrame) -> float:
    if len(q) < 3:
        return np.nan
    c = pd.to_numeric(q.close, errors='coerce').astype(float)
    lr = np.log(c).diff().dropna()
    return float(lr.std(ddof=0)) if len(lr) else np.nan


def range_pct(q: pd.DataFrame) -> float:
    if q.empty:
        return np.nan
    op = float(q.iloc[0].open)
    if op <= 0:
        return np.nan
    return (float(q.high.max()) - float(q.low.min())) / op


def build_feature_rows(x: pd.DataFrame, c: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    audits = []
    for r in c.itertuples(index=False):
        es = pd.Timestamp(r.execution_start)
        rs = es - pd.Timedelta(minutes=REF_MIN)
        ee = es + pd.Timedelta(minutes=HORIZON_MIN)
        ref = fast_slice(x, rs, es)
        exe = fast_slice(x, es, ee)
        if len(ref) != REF_MIN // 5 or len(exe) != HORIZON_MIN // 5:
            raise AssertionError('frozen reference/execution coverage mismatch')

        H = float(r.H); L = float(r.L); R = H - L
        if not R > 0:
            raise AssertionError('non-positive range')
        w = s4.b.m.corrected_find_window(exe, H, L, 'LONG')
        if w is None or not bool(w.get('clean', False)):
            raise AssertionError('candidate no longer has clean B27DX window')
        fill = s4.b.find_fill(exe, w, float(r.entry_px))
        fill_match = fill is not None and pd.Timestamp(fill) == pd.Timestamp(r.entry_bar_start)
        if not fill_match:
            raise AssertionError('candidate fill reconstruction mismatch')

        hts = first_extreme_ts(ref, 'high', H)
        lts = first_extreme_ts(ref, 'low', L)
        completion = max(hts, lts)
        k1 = pd.Timestamp(w['k1'])
        leave = pd.Timestamp(w['leave_bar'])
        eligible = pd.Timestamp(w['eligible_start'])
        fill_ts = pd.Timestamp(fill)
        if not (completion < es and k1 <= leave < eligible <= fill_ts):
            raise AssertionError('causal feature chronology failed')

        episode = exe[(exe.index >= k1) & (exe.index < leave)]
        if episode.empty:
            raise AssertionError('empty K1 episode')
        leave_row = exe.loc[leave]

        pre4 = fast_slice(x, rs - pd.Timedelta(hours=4), rs)
        pre24 = fast_slice(x, rs - pd.Timedelta(hours=24), rs)

        ref_open = float(ref.iloc[0].open)
        ref_close = float(ref.iloc[-1].close)
        ref_ret = ref_close / ref_open - 1.0 if ref_open > 0 else np.nan
        ref_close_loc = (ref_close - L) / R
        episode_bars = int(len(episode))

        row = {
            'candidate_id': r.candidate_id,
            'partition': r.partition,
            'exec_min': int(r.exec_min),
            'execution_utc': r.execution_utc,
            'execution_start': es,
            'entry_bar_start': fill_ts,
            'pre4_return': simple_return(pre4),
            'pre24_return': simple_return(pre24),
            'pre24_vol': realized_vol(pre24),
            'pre24_range_pct': range_pct(pre24),
            'ref_return': ref_ret,
            'ref_range_pct': R / ref_open if ref_open > 0 else np.nan,
            'ref_close_location': ref_close_loc,
            'range_completion_frac': float((completion - rs) / pd.Timedelta(minutes=1)) / REF_MIN,
            'extreme_spacing_frac': abs(float((hts - lts) / pd.Timedelta(minutes=1))) / REF_MIN,
            'high_before_low': bool(hts < lts),
            'k1_start_frac': float((k1 - es) / pd.Timedelta(minutes=1)) / HORIZON_MIN,
            'leave_time_frac': float((leave - es) / pd.Timedelta(minutes=1)) / HORIZON_MIN,
            'k1_episode_bars': episode_bars,
            'k1_overshoot_R': max(0.0, (float(episode.high.max()) - H) / R),
            'leave_drop_from_H_R': (H - float(leave_row.close)) / R,
            'k1_to_fill_frac': float((fill_ts - k1) / pd.Timedelta(minutes=1)) / HORIZON_MIN,
            'post_leave_to_fill_frac': float((fill_ts - eligible) / pd.Timedelta(minutes=1)) / HORIZON_MIN,
            'single_k1': bool(episode_bars == 1),
        }
        row['pre4_up'] = bool(row['pre4_return'] > 0) if pd.notna(row['pre4_return']) else np.nan
        row['pre24_up'] = bool(row['pre24_return'] > 0) if pd.notna(row['pre24_return']) else np.nan
        row['ref_up'] = bool(ref_ret > 0) if pd.notna(ref_ret) else np.nan
        row['ref_close_upper_half'] = bool(ref_close_loc >= 0.5) if pd.notna(ref_close_loc) else np.nan
        rows.append(row)
        audits.append({
            'candidate_id': r.candidate_id,
            'partition': r.partition,
            'execution_utc': r.execution_utc,
            'fill_match': fill_match,
            'reference_complete_before_execution': completion < es,
            'k1_before_or_at_leave': k1 <= leave,
            'leave_completed_before_eligible': leave < eligible,
            'eligible_before_or_at_fill': eligible <= fill_ts,
            'all_pre_entry_features_causal': completion < es and k1 <= leave < eligible <= fill_ts,
        })
    return pd.DataFrame(rows), pd.DataFrame(audits)


def add_path_diagnostics(x: pd.DataFrame, accepted: pd.DataFrame) -> pd.DataFrame:
    q = accepted.copy()
    mfe = []; mae = []; hold = []; mfe_target = []
    for r in q.itertuples(index=False):
        start = pd.Timestamp(r.entry_bar_start) + BAR5
        end = pd.Timestamp(r.exit_ts)
        path = x[(x.index >= start) & (x.index < end)]
        R = float(r.H) - float(r.L)
        if path.empty or R <= 0:
            mfe_r = mae_r = np.nan
        else:
            mfe_r = (float(path.high.max()) - float(r.entry_px)) / R
            mae_r = (float(r.entry_px) - float(path.low.min())) / R
        mfe.append(mfe_r)
        mae.append(mae_r)
        hold.append(float((end - pd.Timestamp(r.entry_bar_start)) / pd.Timedelta(minutes=1)))
        mfe_target.append(mfe_r / TARGET_DISTANCE_R if pd.notna(mfe_r) and TARGET_DISTANCE_R > 0 else np.nan)
    q['mfe_R'] = mfe
    q['mae_R'] = mae
    q['hold_min'] = hold
    q['mfe_target_fraction'] = mfe_target
    q['is_loss'] = q.pnl_0 < 0
    q['is_win'] = q.pnl_0 > 0
    return q


def rank_loss_effect(df: pd.DataFrame, feature: str) -> dict:
    q = df[[feature, 'pnl_0']].copy()
    q[feature] = pd.to_numeric(q[feature], errors='coerce')
    q = q[q[feature].notna() & (q.pnl_0 != 0)]
    loss = q.pnl_0 < 0
    nl = int(loss.sum()); nw = int((~loss).sum())
    if nl == 0 or nw == 0:
        auc = effect = np.nan
    else:
        ranks = q[feature].rank(method='average')
        rank_loss = float(ranks[loss].sum())
        auc = (rank_loss - nl * (nl + 1) / 2.0) / (nl * nw)
        effect = 2.0 * auc - 1.0
    return {
        'n_loss': nl,
        'n_win': nw,
        'loss_median': float(q.loc[loss, feature].median()) if nl else np.nan,
        'win_median': float(q.loc[~loss, feature].median()) if nw else np.nan,
        'auc_loss_higher': auc,
        'effect': effect,
    }


def continuous_associations(a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [*PARTS, 'POOLED_MAJOR']
    for feature in CONT_FEATURES:
        for p in scopes:
            q = a if p == 'POOLED_MAJOR' else a[a.partition == p]
            z = rank_loss_effect(q, feature)
            rows.append({'feature': feature, 'partition': p, **z})
    out = pd.DataFrame(rows)
    repl = {}
    for feature in CONT_FEATURES:
        q = out[out.feature == feature].set_index('partition')
        vals = [q.loc[p, 'effect'] for p in PARTS]
        adequate = all(int(q.loc[p, 'n_loss']) >= 5 and int(q.loc[p, 'n_win']) >= 5 for p in PARTS)
        finite = all(pd.notna(v) and float(v) != 0.0 for v in vals)
        same_sign = finite and (all(float(v) > 0 for v in vals) or all(float(v) < 0 for v in vals))
        min_effect = finite and all(abs(float(v)) >= 0.05 for v in vals)
        pooled = q.loc['POOLED_MAJOR', 'effect']
        pooled_ok = pd.notna(pooled) and abs(float(pooled)) >= 0.15
        repl[feature] = bool(adequate and same_sign and min_effect and pooled_ok)
    out['directionally_replicated'] = out.feature.map(repl)
    return out


def binary_stats(df: pd.DataFrame, feature: str) -> dict:
    q = df[[feature, 'pnl_0']].copy()
    q = q[q[feature].notna() & (q.pnl_0 != 0)]
    q[feature] = q[feature].astype(bool)
    t = q[q[feature]]; f = q[~q[feature]]
    nt = len(t); nf = len(f)
    lt = int((t.pnl_0 < 0).sum()); lf = int((f.pnl_0 < 0).sum())
    rt = lt / nt if nt else np.nan; rf = lf / nf if nf else np.nan
    if pd.isna(rt) or pd.isna(rf): rr = np.nan
    elif rf == 0 and rt > 0: rr = math.inf
    elif rf == 0: rr = np.nan
    else: rr = rt / rf
    return {'n_true': nt, 'n_false': nf, 'losses_true': lt, 'losses_false': lf,
            'loss_rate_true': rt, 'loss_rate_false': rf, 'risk_ratio_true_vs_false': rr}


def binary_associations(a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    scopes = [*PARTS, 'POOLED_MAJOR']
    for feature in BIN_FEATURES:
        for p in scopes:
            q = a if p == 'POOLED_MAJOR' else a[a.partition == p]
            rows.append({'feature': feature, 'partition': p, **binary_stats(q, feature)})
    out = pd.DataFrame(rows)
    repl = {}
    for feature in BIN_FEATURES:
        q = out[out.feature == feature].set_index('partition')
        rr = [q.loc[p, 'risk_ratio_true_vs_false'] for p in PARTS]
        adequate = all(int(q.loc[p, 'n_true']) >= 5 and int(q.loc[p, 'n_false']) >= 5 for p in PARTS)
        valid = all(pd.notna(v) and float(v) != 1.0 for v in rr)
        same_dir = valid and (all(float(v) > 1.0 for v in rr) or all(float(v) < 1.0 for v in rr))
        min_dev = valid and all((float(v) >= 1.05 or float(v) <= 0.95) for v in rr)
        pooled = q.loc['POOLED_MAJOR', 'risk_ratio_true_vs_false']
        pooled_ok = pd.notna(pooled) and (float(pooled) >= 1.25 or float(pooled) <= 0.80)
        repl[feature] = bool(adequate and same_dir and min_dev and pooled_ok)
    out['directionally_replicated'] = out.feature.map(repl)
    return out


def loss_by_clock(a: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for p in [*PARTS, 'POOLED_MAJOR']:
        q = a if p == 'POOLED_MAJOR' else a[a.partition == p]
        total_losses = int((q.pnl_0 < 0).sum())
        for clock, g in q.groupby('execution_utc'):
            losses = int((g.pnl_0 < 0).sum())
            rows.append({
                'partition': p,
                'execution_utc': clock,
                'n': len(g),
                'wins': int((g.pnl_0 > 0).sum()),
                'losses': losses,
                'loss_rate': losses / len(g) if len(g) else np.nan,
                'share_of_partition_losses': losses / total_losses if total_losses else np.nan,
                'mean_loss_pnl': float(g.loc[g.pnl_0 < 0, 'pnl_0'].mean()) if losses else np.nan,
            })
    return pd.DataFrame(rows)


def loss_path_summary(a: pd.DataFrame) -> pd.DataFrame:
    losses = a[a.pnl_0 < 0].copy()
    rows = []
    for p in [*PARTS, 'POOLED_MAJOR']:
        q = losses if p == 'POOLED_MAJOR' else losses[losses.partition == p]
        denom = len(q)
        for reason, g in q.groupby('exit_reason'):
            rows.append({
                'partition': p,
                'exit_reason': reason,
                'n_losses': len(g),
                'share_of_losses': len(g) / denom if denom else np.nan,
                'median_pnl': float(g.pnl_0.median()) if len(g) else np.nan,
                'median_hold_min': float(g.hold_min.median()) if len(g) else np.nan,
                'median_mfe_R': float(g.mfe_R.median()) if len(g) else np.nan,
                'median_mae_R': float(g.mae_R.median()) if len(g) else np.nan,
                'median_mfe_target_fraction': float(g.mfe_target_fraction.median()) if len(g) else np.nan,
                'near_target_80pct_rate': float((g.mfe_target_fraction >= 0.80).mean()) if len(g) else np.nan,
            })
    return pd.DataFrame(rows)


def fmt(v: float, nd: int = 3) -> str:
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{nd}f}'


def pct(v: float) -> str:
    return '-' if pd.isna(v) else f'{100.0 * float(v):.1f}%'


def main() -> None:
    x, cov = s4.b.m.m.load5()
    c = s4.build_candidates(x)
    parity = s4.parity_check(x, c)
    dec, _, _ = s4.summarize(c)
    features, audit = build_feature_rows(x, c)
    audit_ok = bool(parity['pass'].all()) and bool(audit.all_pre_entry_features_causal.all()) and len(features) == len(c)

    accepted = dec[dec.accepted].copy().merge(features, on=['candidate_id','partition','exec_min','execution_utc','execution_start','entry_bar_start'], how='left', validate='one_to_one')
    if len(accepted) != int(dec.accepted.sum()):
        raise AssertionError('accepted trade merge mismatch')
    accepted = add_path_diagnostics(x, accepted)
    accepted.to_csv(OUT_TRADES, index=False)

    clock = loss_by_clock(accepted); clock.to_csv(OUT_CLOCK, index=False)
    cont = continuous_associations(accepted); cont.to_csv(OUT_CONT, index=False)
    binary = binary_associations(accepted); binary.to_csv(OUT_BIN, index=False)
    path = loss_path_summary(accepted); path.to_csv(OUT_PATH, index=False)
    audit.to_csv(OUT_AUDIT, index=False)

    pooled = accepted
    n = len(pooled); losses = int((pooled.pnl_0 < 0).sum()); wins = int((pooled.pnl_0 > 0).sum())
    repl_cont = [f for f in CONT_FEATURES if bool(cont[(cont.feature == f)].directionally_replicated.iloc[0])]
    repl_bin = [f for f in BIN_FEATURES if bool(binary[(binary.feature == f)].directionally_replicated.iloc[0])]

    status = 'ETH_S8L_LOSS_ANATOMY_REPLICATED_ASSOCIATIONS_FOUND' if audit_ok and (repl_cont or repl_bin) else ('ETH_S8L_LOSS_ANATOMY_COMPLETED_NO_REPLICATED_ASSOCIATION' if audit_ok else 'ETH_S8L_LOSS_ANATOMY_AUDIT_FAILED')

    lines = [
        '# ETH B27DX — S8L Loss Anatomy — Result', '',
        f'ETH raw 5m coverage: **{cov:.4%}**.', '',
        'Frozen portfolio: **R300/X360 · F75/E25/F20 · 05:00/09:00/10:00/16:00 UTC · S4 global one-position lock**.', '',
        f'- Candidate/parity/causal audit: **{"PASS" if audit_ok else "FAIL"}**.',
        f'- Accepted trades: **{n}**; wins **{wins}**; losses **{losses}**; loss rate **{pct(losses/n if n else np.nan)}**.', '',
        '## Where losses concentrate', '',
        '| Clock | N | Losses | Loss rate | Share of all losses | Mean loss PnL |',
        '|---:|---:|---:|---:|---:|---:|',
    ]
    for r in clock[clock.partition == 'POOLED_MAJOR'].sort_values('execution_utc').itertuples(index=False):
        lines.append(f'| {r.execution_utc} | {int(r.n)} | {int(r.losses)} | {pct(r.loss_rate)} | {pct(r.share_of_partition_losses)} | {fmt(r.mean_loss_pnl,2)} |')

    lines += ['', '## Causal pre-entry associations with loss', '',
              'Positive continuous effect means the feature is **higher on losses**; negative means **lower on losses**. No cutoff was optimized.', '']
    if repl_cont:
        lines += ['### Directionally replicated continuous features', '',
                  '| Feature | Direction on losses | Pooled effect | Loss median | Win median | External | Development | RefVal |',
                  '|---|---|---:|---:|---:|---:|---:|---:|']
        for f in repl_cont:
            q = cont[cont.feature == f].set_index('partition'); pe = float(q.loc['POOLED_MAJOR','effect'])
            direction = 'HIGHER' if pe > 0 else 'LOWER'
            lines.append(f'| {f} | {direction} | {fmt(pe)} | {fmt(q.loc["POOLED_MAJOR","loss_median"])} | {fmt(q.loc["POOLED_MAJOR","win_median"])} | {fmt(q.loc["external","effect"])} | {fmt(q.loc["development","effect"])} | {fmt(q.loc["reference_validation","effect"])} |')
    else:
        lines.append('**No continuous feature met the frozen three-partition directional-replication criterion.**')

    # Always show the strongest pooled effects for transparency, but label them non-promoted.
    pooled_cont = cont[cont.partition == 'POOLED_MAJOR'].copy()
    pooled_cont['abs_effect'] = pooled_cont.effect.abs()
    lines += ['', '### Strongest pooled continuous signals (diagnostic; not automatically replicated)', '',
              '| Feature | Effect | Loss median | Win median | Replicated |',
              '|---|---:|---:|---:|---|']
    for r in pooled_cont.sort_values('abs_effect', ascending=False).head(8).itertuples(index=False):
        lines.append(f'| {r.feature} | {fmt(r.effect)} | {fmt(r.loss_median)} | {fmt(r.win_median)} | {"YES" if r.directionally_replicated else "NO"} |')

    lines += ['', '## Natural binary anatomy', '']
    if repl_bin:
        lines += ['| Feature=True | Pooled loss RR vs False | True loss rate | False loss rate | External RR | Development RR | RefVal RR |',
                  '|---|---:|---:|---:|---:|---:|---:|']
        for f in repl_bin:
            q = binary[binary.feature == f].set_index('partition')
            lines.append(f'| {f} | {fmt(q.loc["POOLED_MAJOR","risk_ratio_true_vs_false"])} | {pct(q.loc["POOLED_MAJOR","loss_rate_true"])} | {pct(q.loc["POOLED_MAJOR","loss_rate_false"])} | {fmt(q.loc["external","risk_ratio_true_vs_false"])} | {fmt(q.loc["development","risk_ratio_true_vs_false"])} | {fmt(q.loc["reference_validation","risk_ratio_true_vs_false"])} |')
    else:
        lines.append('**No natural binary feature met the frozen three-partition replication criterion.**')

    lines += ['', '## Ex-post loss path — diagnostic only, never an entry filter', '',
              '| Exit reason | Losses | Share | Median hold min | Median MFE/R | Median MAE/R | Median target progress | Near-target >=80% |',
              '|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in path[path.partition == 'POOLED_MAJOR'].sort_values('n_losses', ascending=False).itertuples(index=False):
        lines.append(f'| {r.exit_reason} | {int(r.n_losses)} | {pct(r.share_of_losses)} | {fmt(r.median_hold_min,1)} | {fmt(r.median_mfe_R)} | {fmt(r.median_mae_R)} | {pct(r.median_mfe_target_fraction)} | {pct(r.near_target_80pct_rate)} |')

    lines += ['', '## Decision', '', f'**Status: {status}**', '',
              '- S8L does not create or optimize a new trading rule.',
              '- Replicated pre-entry associations, if any, are hypotheses for a separately preregistered validation test.',
              '- MFE/MAE/exit-path observations are ex-post explanations only and cannot be used as causal entry information.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(status + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
