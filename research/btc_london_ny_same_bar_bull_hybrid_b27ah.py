#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
TRADES = ROOT / 'BTC_LONDON_NY_E20_PROFIT_LOCK_RUNNER_B27AC_Trades.csv'
DETAIL = ROOT / 'BTC_LONDON_NY_4H_REGIME_ALIGNMENT_B27AG_Detail.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_SAME_BAR_BULL_HYBRID_B27AH_Result.md'
OUT_CSV = ROOT / 'BTC_LONDON_NY_SAME_BAR_BULL_HYBRID_B27AH_Summary.csv'
OUT_JOIN = ROOT / 'BTC_LONDON_NY_SAME_BAR_BULL_HYBRID_B27AH_Trades.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_SAME_BAR_BULL_HYBRID_B27AH_Status.txt'

MAJOR = ('external','development','reference_validation')
REGIMES = ('BULL','BEAR','SIDEWAYS')


def dt(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def pf(x):
    x = pd.to_numeric(pd.Series(x), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    if neg > 0:
        return pos / neg
    return np.nan


def metrics(g):
    n = len(g)
    if n == 0:
        return {
            'n': 0,
            'fixed_wr': np.nan, 'fixed_pf': np.nan, 'fixed_exp': np.nan, 'fixed_total': 0.0,
            'hybrid_wr': np.nan, 'hybrid_pf': np.nan, 'hybrid_exp': np.nan, 'hybrid_total': 0.0,
        }
    f = pd.to_numeric(g.baseline_net_pnl_usd, errors='coerce')
    h = pd.to_numeric(g.hybrid_net_pnl_usd, errors='coerce')
    return {
        'n': n,
        'fixed_wr': float((f > 0).mean()), 'fixed_pf': pf(f), 'fixed_exp': float(f.mean()), 'fixed_total': float(f.sum()),
        'hybrid_wr': float((h > 0).mean()), 'hybrid_pf': pf(h), 'hybrid_exp': float(h.mean()), 'hybrid_total': float(h.sum()),
    }


def fmt_pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def fmt_pf(x):
    if pd.isna(x): return '-'
    if np.isinf(x): return 'inf'
    return f'{float(x):.2f}'


def fmt_money(x):
    return f'$ {float(x):+.2f}'.replace('$ ','$')


def main():
    t = pd.read_csv(TRADES)
    t = t[t.rule == 'SAME_BAR_REJECTION'].copy()
    t = dt(t, ['signal_ts','entry_start'])
    d = pd.read_csv(DETAIL)
    d = d[d.side == 'LONG'].copy()
    d = dt(d, ['signal_ts','regime_bar_start','regime_available_ts','entry_ts','entry_regime_available_ts'])

    # One persisted B27AG LONG state row per signal identity.
    keys = ['partition','signal_ts']
    assert not d.duplicated(keys).any(), 'duplicate B27AG LONG signal identity'
    keep = keys + ['regime_at_signal','regime_bar_start','regime_available_ts','alignment','regime_at_entry','state_changed_signal_to_entry']
    j = t.merge(d[keep], on=keys, how='left', validate='many_to_one')
    assert len(j) == len(t), 'join changed SAME_BAR cohort size'
    assert j.regime_at_signal.notna().all(), 'unmatched SAME_BAR trade to B27AG regime detail'
    assert (j.regime_available_ts <= j.signal_ts).all(), 'noncausal regime availability'

    # B27AC persisted baseline reproduction before attribution.
    major = j[j.partition.isin(MAJOR)].copy()
    base = metrics(major)
    assert base['n'] == 68, base
    assert abs(base['fixed_total'] - 61.802) < 0.05, base
    assert abs(base['hybrid_total'] - 91.31) < 0.05, base
    assert abs(base['fixed_wr'] - 0.7352941176470589) < 1e-12, base
    assert abs(base['hybrid_wr'] - 0.6911764705882353) < 1e-12, base

    rows = []
    def add(scope, part, regime, g):
        m = metrics(g)
        rows.append({'scope':scope,'partition':part,'regime':regime,**m})

    add('POOLED_MAJOR','POOLED_MAJOR','ALL',major)
    for rg in REGIMES:
        add('POOLED_MAJOR','POOLED_MAJOR',rg,major[major.regime_at_signal == rg])
    for part in MAJOR:
        q = major[major.partition == part]
        add('PARTITION_BULL',part,'BULL',q[q.regime_at_signal == 'BULL'])
    aug = j[j.partition == 'august']
    add('AUGUST_DIAGNOSTIC','august','BULL',aug[aug.regime_at_signal == 'BULL'])

    out = pd.DataFrame(rows)
    out.to_csv(OUT_CSV, index=False)
    j.to_csv(OUT_JOIN, index=False)

    bull = out[(out.scope=='POOLED_MAJOR') & (out.regime=='BULL')].iloc[0]
    bear = out[(out.scope=='POOLED_MAJOR') & (out.regime=='BEAR')].iloc[0]
    side = out[(out.scope=='POOLED_MAJOR') & (out.regime=='SIDEWAYS')].iloc[0]

    lines = [
        '# B27AH — SAME_BAR_REJECTION + 4H BULL Hybrid Attribution — Result','',
        '**Audit status: PASS.** Existing B27AC SAME_BAR pooled-major cohort/economics and B27AG causal pre-signal regime labels reproduce before attribution.','',
        '## Pooled major: same trades, split only by pre-signal 4H state','',
        '| 4H state | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ]
    for rg in ('ALL','BULL','BEAR','SIDEWAYS'):
        r = out[(out.scope=='POOLED_MAJOR') & (out.regime==rg)].iloc[0]
        lines.append(f"| {rg} | {int(r.n)} | {fmt_pct(r.fixed_wr)} | {fmt_pf(r.fixed_pf)} | {fmt_money(r.fixed_exp)} | {fmt_money(r.fixed_total)} | {fmt_pct(r.hybrid_wr)} | {fmt_pf(r.hybrid_pf)} | {fmt_money(r.hybrid_exp)} | {fmt_money(r.hybrid_total)} |")

    lines += ['', '## 4H BULL only by major partition','',
              '| Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in MAJOR:
        r = out[(out.scope=='PARTITION_BULL') & (out.partition==part)].iloc[0]
        lines.append(f"| {part} | {int(r.n)} | {fmt_pct(r.fixed_wr)} | {fmt_pf(r.fixed_pf)} | {fmt_money(r.fixed_exp)} | {fmt_money(r.fixed_total)} | {fmt_pct(r.hybrid_wr)} | {fmt_pf(r.hybrid_pf)} | {fmt_money(r.hybrid_exp)} | {fmt_money(r.hybrid_total)} |")

    base_h = base['hybrid_exp']
    bull_h = float(bull.hybrid_exp) if int(bull.n) else np.nan
    verdict = 'B27AH_BULL_CONCENTRATION_IMPROVES_HYBRID' if (int(bull.n) > 0 and bull_h > base_h and float(bull.hybrid_pf) > base['hybrid_pf']) else 'B27AH_BULL_CONCENTRATION_NOT_BETTER_ON_BOTH_QUALITY_METRICS'
    lines += ['', '## Frozen readout','',
              f"- Original SAME_BAR all-regime hybrid: N={base['n']}, WR={fmt_pct(base['hybrid_wr'])}, PF={fmt_pf(base['hybrid_pf'])}, exp={fmt_money(base['hybrid_exp'])}, total={fmt_money(base['hybrid_total'])}.",
              f"- SAME_BAR + 4H BULL hybrid: N={int(bull.n)}, WR={fmt_pct(bull.hybrid_wr)}, PF={fmt_pf(bull.hybrid_pf)}, exp={fmt_money(bull.hybrid_exp)}, total={fmt_money(bull.hybrid_total)}.",
              f"- SAME_BAR + 4H BEAR hybrid: N={int(bear.n)}, WR={fmt_pct(bear.hybrid_wr)}, PF={fmt_pf(bear.hybrid_pf)}, exp={fmt_money(bear.hybrid_exp)}, total={fmt_money(bear.hybrid_total)}.",
              f"- SAME_BAR + 4H SIDEWAYS hybrid: N={int(side.n)}, WR={fmt_pct(side.hybrid_wr)}, PF={fmt_pf(side.hybrid_pf)}, exp={fmt_money(side.hybrid_exp)}, total={fmt_money(side.hybrid_total)}.",
              '', f'**Overall: {verdict}.**','',
              'This remains a post-hoc attribution of an adaptively observed SAME_BAR subset, not an independent OOS promotion. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines) + '\n')
    OUT_STATUS.write_text(verdict + '\n')
    print(verdict)


if __name__ == '__main__':
    main()
