#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
AT = ROOT / 'BTC_LONDON_NY_SHORT_F15_FULL_HYBRID_ACTIVATION_GRID_B27AT_Trades.csv'
AM = ROOT / 'BTC_LONDON_NY_SHORT_F15_POST_H2_EXTENSION_B27AM_Paths.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SHORT_F15_FAILURE_STAGE_B27AV_Result.md'
OUT_SUM = ROOT / 'BTC_LONDON_NY_SHORT_F15_FAILURE_STAGE_B27AV_Summary.csv'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_SHORT_F15_FAILURE_STAGE_B27AV_Trades.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SHORT_F15_FAILURE_STAGE_B27AV_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
BUCKETS = ('PRE_H2_FAILURE','H2_NO_ACCEPTANCE','ACCEPTED_NO_E20','E20_ACTIVATED')
BASE_TOTAL = -15.05841591698896


def to_bool(v) -> bool:
    if isinstance(v, (bool, np.bool_)):
        return bool(v)
    return str(v).strip().lower() == 'true'


def pf(vals) -> float:
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def classify(activated: bool, h2_before_exit: bool, accept_by_exit: bool) -> str:
    if activated:
        return 'E20_ACTIVATED'
    if not h2_before_exit:
        return 'PRE_H2_FAILURE'
    if not accept_by_exit:
        return 'H2_NO_ACCEPTANCE'
    return 'ACCEPTED_NO_E20'


def synthetic_tests() -> None:
    assert classify(False, False, False) == 'PRE_H2_FAILURE'
    assert classify(False, True, False) == 'H2_NO_ACCEPTANCE'
    assert classify(False, True, True) == 'ACCEPTED_NO_E20'
    assert classify(True, True, True) == 'E20_ACTIVATED'


def stats(g: pd.DataFrame) -> dict:
    n = len(g)
    if not n:
        return {'n':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'total':0.0,'mean_win':np.nan,'mean_loss':np.nan}
    p = pd.to_numeric(g.net_pnl_usd, errors='coerce')
    w = p[p > 0]; l = p[p < 0]
    return {
        'n':n,
        'wr':float((p > 0).mean()),
        'pf':pf(p),
        'exp':float(p.mean()),
        'total':float(p.sum()),
        'mean_win':float(w.mean()) if len(w) else np.nan,
        'mean_loss':float(l.mean()) if len(l) else np.nan,
    }


def main() -> None:
    synthetic_tests()

    at = pd.read_csv(AT)
    at = at[at.activation.astype(str) == 'E20'].copy()
    for c in ('signal_ts','entry_start','session_end','activation_bar_start','exit_bar_start','exit_ts'):
        at[c] = pd.to_datetime(at[c], utc=True, errors='coerce')
    at['activated'] = at.activated.map(to_bool)
    at['win'] = pd.to_numeric(at.net_pnl_usd, errors='raise') > 0

    am = pd.read_csv(AM)
    for c in ('signal_ts','fill_bar_start','h2_bar_start','first_close_break_bar_start','first_close_break_ts','session_end'):
        am[c] = pd.to_datetime(am[c], utc=True, errors='coerce')
    am['has_h2'] = am.has_h2.map(to_bool)

    # Frozen B27AT assertions before attribution.
    assert len(at) == 164, len(at)
    major_at = at[at.partition.isin(MAJOR)].copy()
    assert len(major_at) == 163, len(major_at)
    assert abs(float(major_at.net_pnl_usd.sum()) - BASE_TOTAL) < 1e-9
    assert int(major_at.activated.sum()) == 92
    assert int((~major_at.activated).sum()) == 71

    # Join exact frozen identities.
    amj = am[['partition','signal_ts','fill_bar_start','has_h2','h2_bar_start',
              'first_close_break_bar_start','first_close_break_ts','E20_low_reach','E20_low_reach_bar_start']].copy()
    amj = amj.rename(columns={'fill_bar_start':'entry_start'})
    z = at.merge(amj, on=['partition','signal_ts','entry_start'], how='left', validate='one_to_one', indicator=True)
    assert len(z) == len(at)
    assert (z['_merge'] == 'both').all()
    z = z.drop(columns=['_merge'])
    z['E20_low_reach'] = z.E20_low_reach.map(to_bool)

    # Causal stage membership evaluated no later than actual exit.
    z['h2_before_exit'] = z.has_h2.astype(bool) & z.h2_bar_start.notna() & (z.h2_bar_start < z.exit_ts)
    # Completed-close acceptance becomes known at first_close_break_ts. Equality means
    # the milestone is known at the exact exit timestamp; there is no future leakage.
    z['accept_by_exit'] = z.first_close_break_ts.notna() & (z.first_close_break_ts <= z.exit_ts)
    z.loc[~z.h2_before_exit, 'accept_by_exit'] = False
    z['stage_bucket'] = [classify(bool(a), bool(h), bool(c)) for a,h,c in zip(z.activated,z.h2_before_exit,z.accept_by_exit)]

    # E20 activation necessarily implies a prior/same-path H2 liquidity touch.
    assert z.loc[z.activated, 'h2_before_exit'].all()
    assert set(z.stage_bucket.unique()).issubset(set(BUCKETS))

    # Eventual same-session milestones after exit are diagnostics only.
    z['eventual_h2'] = z.has_h2.astype(bool)
    z['eventual_accept'] = z.first_close_break_ts.notna()
    z['late_h2_after_exit'] = z.eventual_h2 & ~z.h2_before_exit
    z['late_accept_after_exit'] = z.eventual_accept & ~z.accept_by_exit

    # Pool count assertions.
    zm = z[z.partition.isin(MAJOR)].copy()
    assert len(zm) == 163
    assert int((zm.stage_bucket != 'E20_ACTIVATED').sum()) == 71
    assert int((zm.stage_bucket == 'E20_ACTIVATED').sum()) == 92
    assert abs(float(zm.net_pnl_usd.sum()) - BASE_TOTAL) < 1e-9

    rows = []
    for part in (*PARTS, 'POOLED_MAJOR'):
        gp = zm if part == 'POOLED_MAJOR' else z[z.partition == part]
        for bucket in BUCKETS:
            g = gp[gp.stage_bucket == bucket].copy()
            s = stats(g)
            s.update({
                'partition':part,'stage_bucket':bucket,
                'pre_invalid_n':int((g.exit_reason == 'PRE_ACT_CLOSE_INVALIDATION_F65').sum()),
                'time_exit_n':int((g.exit_reason == 'TIME_EXIT_SESSION_END').sum()),
                'ceiling_hit_n':int((g.exit_reason == 'PROFIT_CEILING_HIT').sum()),
                'gap_exit_n':int((g.exit_reason == 'PROFIT_CEILING_GAP_OPEN').sum()),
                'eventual_h2_rate':float(g.eventual_h2.mean()) if len(g) else np.nan,
                'eventual_accept_rate':float(g.eventual_accept.mean()) if len(g) else np.nan,
                'late_h2_n':int(g.late_h2_after_exit.sum()),
                'late_accept_n':int(g.late_accept_after_exit.sum()),
            })
            rows.append(s)
    sm = pd.DataFrame(rows)

    # Non-activated loss-drag share is descriptive, not a filter criterion.
    non = zm[~zm.activated].copy()
    non_total = float(non.net_pnl_usd.sum())
    assert non_total < 0
    sm['share_nonactivated_drag'] = np.nan
    mask = (sm.partition == 'POOLED_MAJOR') & sm.stage_bucket.isin(BUCKETS[:3])
    sm.loc[mask, 'share_nonactivated_drag'] = sm.loc[mask, 'total'] / non_total

    # Stage flow counts before actual exit.
    n_fill = len(zm)
    n_h2 = int(zm.h2_before_exit.sum())
    n_accept = int(zm.accept_by_exit.sum())
    n_e20 = int(zm.activated.sum())
    assert n_fill >= n_h2 >= n_accept >= n_e20

    # Cross-tab failure bucket x exit reason.
    xt = pd.crosstab(zm.stage_bucket, zm.exit_reason)

    z.to_csv(OUT_TRADES, index=False)
    sm.to_csv(OUT_SUM, index=False)
    OUT_STATUS.write_text('B27AV_PASS\n')

    def pct(x):
        return '-' if pd.isna(x) else f'{100*float(x):.1f}%'
    def num(x):
        if pd.isna(x): return '-'
        if math.isinf(float(x)): return 'inf'
        return f'{float(x):.3f}'

    md = [
        '# B27AV — BTC London->NY SHORT F15 Failure-Stage Decomposition — Result','',
        '**Audit status: PASS.** Frozen B27AT E20 identities/PnL and B27AM H2/acceptance timestamps joined one-to-one before stage attribution.','',
        f'Pooled-major N: **{n_fill}**; realized E20-hybrid total: **${float(zm.net_pnl_usd.sum()):+.3f}**.','',
        '## Causal stage flow before actual exit','',
        f'**F15 fill {n_fill} → H2 before exit {n_h2} → strict close < L known by exit {n_accept} → E20 activated {n_e20}.**','',
        '## Failure-stage economics — pooled major','',
        '| Stage bucket | N | WR | PF | Exp/trade $ | Total $ | Share of non-activated drag | F65 invalid | Time exit | Late H2 after exit | Late acceptance after exit |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for bucket in BUCKETS:
        r = sm[(sm.partition == 'POOLED_MAJOR') & (sm.stage_bucket == bucket)].iloc[0]
        md.append(f"| {bucket} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.exp)} | {num(r.total)} | {pct(r.share_nonactivated_drag)} | {int(r.pre_invalid_n)} | {int(r.time_exit_n)} | {int(r.late_h2_n)} | {int(r.late_accept_n)} |")

    md += ['','## Same buckets by partition','',
           '| Partition | Stage bucket | N | WR | PF | Exp/trade $ | Total $ | F65 invalid | Time exit |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for part in PARTS:
        for bucket in BUCKETS:
            r = sm[(sm.partition == part) & (sm.stage_bucket == bucket)].iloc[0]
            md.append(f"| {part} | {bucket} | {int(r.n)} | {pct(r.wr)} | {num(r.pf)} | {num(r.exp)} | {num(r.total)} | {int(r.pre_invalid_n)} | {int(r.time_exit_n)} |")

    md += ['','## Failure bucket × actual exit reason','']
    cols = list(xt.columns)
    md.append('| Stage bucket | ' + ' | '.join(cols) + ' |')
    md.append('|---|' + '|'.join(['---:'] * len(cols)) + '|')
    for bucket in BUCKETS:
        vals = [str(int(xt.loc[bucket,c])) if bucket in xt.index and c in xt.columns else '0' for c in cols]
        md.append('| ' + bucket + ' | ' + ' | '.join(vals) + ' |')

    # Direct diagnostic wording only; no strategy selection.
    failures = sm[(sm.partition == 'POOLED_MAJOR') & sm.stage_bucket.isin(BUCKETS[:3])].copy()
    worst = failures.sort_values('total').iloc[0]
    md += ['','## Frozen diagnostic readout','',
           f"Largest failure-stage PnL drag: **{worst.stage_bucket}**, N={int(worst.n)}, total **${float(worst.total):+.3f}**.",
           f"Non-activated total remains **${non_total:+.3f}**; B27AV does not convert this attribution into a filter.",
           '',
           'No threshold, filter, alternate stop, entry, TP, regime, candle rule, or runner parameter was selected. Research only; live BBC unchanged.']

    OUT_MD.write_text('\n'.join(md) + '\n')
    print('\n'.join(md))


if __name__ == '__main__':
    main()
