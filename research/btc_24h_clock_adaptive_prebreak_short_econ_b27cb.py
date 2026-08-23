#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
CAND = ROOT / 'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Candidates.csv'
SEL = ROOT / 'BTC_24H_PREBREAK_RETEST_LADDER_B27CA_Selection.csv'
OUT_MD = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_PREBREAK_SHORT_ECON_B27CB_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_PREBREAK_SHORT_ECON_B27CB_Trades.csv'
OUT_SUM = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_PREBREAK_SHORT_ECON_B27CB_Summary.csv'
OUT_SEL = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_PREBREAK_SHORT_ECON_B27CB_Selection.csv'
OUT_STATUS = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_PREBREAK_SHORT_ECON_B27CB_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
H4 = pd.Timedelta(hours=4)
MAJOR = ('external', 'development', 'reference_validation')
OOS = ('external', 'reference_validation')
CLOCKS = ('00-04', '04-08', '08-12', '12-16', '16-20', '20-00')
FROZEN_CLOCK_FRAC = {
    '00-04': 0.05,
    '04-08': 0.05,
    '08-12': 0.10,
    '12-16': 0.05,
    '16-20': 0.05,
    '20-00': 0.05,
}
VARIANTS = (
    ('S1_T1', 1.0, 1.0),
    ('S1_T1_5', 1.0, 1.5),
    ('S1_T2', 1.0, 2.0),
    ('S1_5_T1_5', 1.5, 1.5),
    ('S1_5_T2', 1.5, 2.0),
    ('S2_T2', 2.0, 2.0),
)
NOTIONAL = 500.0
FEE = 0.40


def as_bool(s: pd.Series) -> pd.Series:
    if s.dtype == bool:
        return s.copy()
    return s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_entries() -> pd.DataFrame:
    c = pd.read_csv(CAND)
    c['filled'] = as_bool(c['filled'])
    for col in ('obs_start', 'fill_ts'):
        c[col] = pd.to_datetime(c[col], utc=True, errors='coerce')

    s = pd.read_csv(SEL)
    got = {str(r.clock_block): float(r.selected_fraction) for r in s.itertuples(index=False)}
    assert got == FROZEN_CLOCK_FRAC, (got, FROZEN_CLOCK_FRAC)

    rows = []
    for cb, f in FROZEN_CLOCK_FRAC.items():
        z = c[(c.clock_block == cb) & np.isclose(c.fraction.astype(float), f)].copy()
        rows.append(z)
    q = pd.concat(rows, ignore_index=True)
    q = q[q.partition.isin(MAJOR) & q.filled].copy()
    q = q.sort_values(['partition', 'obs_start']).reset_index(drop=True)

    expected = {'external': 250, 'development': 380, 'reference_validation': 177}
    assert len(q) == sum(expected.values()), len(q)
    for p, n in expected.items():
        gotn = len(q[q.partition == p])
        assert gotn == n, (p, gotn, n)
    assert q.fill_ts.notna().all()
    assert (q['price'].astype(float) > q['L'].astype(float)).all()
    assert (q['price'].astype(float) < q['H'].astype(float)).all()
    return q


def eval_trade(x5: pd.DataFrame, r, variant: str, sm: float, tm: float) -> dict:
    obs_start = pd.Timestamp(r.obs_start)
    obs_end = obs_start + H4
    fill_ts = pd.Timestamp(r.fill_ts)
    entry = float(r.price)
    L = float(r.L)
    H = float(r.H)
    R4 = H - L
    frac = float(r.fraction)
    local_r = entry - L
    assert R4 > 0 and local_r > 0
    assert abs(local_r - frac * R4) <= max(1e-8, 1e-10 * abs(entry))

    stop = entry + sm * local_r
    target = entry - tm * local_r
    assert stop > entry > target
    nominal_rr = tm / sm
    assert nominal_rr >= 1.0 - 1e-12

    q = fast_slice(x5, obs_start, obs_end)
    assert len(q) == 48, (obs_start, len(q))
    assert q.index[0] == obs_start and q.index[-1] == obs_end - BAR5
    idx = int(q.index.searchsorted(fill_ts, side='left'))
    assert idx < len(q) and q.index[idx] == fill_ts, (fill_ts, obs_start)
    fb = q.iloc[idx]
    assert float(fb.low) <= entry <= float(fb.high)

    exit_reason = None
    exit_ts = None
    exit_px = None

    # Conservative fill-bar treatment: same-bar stop counts; same-bar TP is never credited.
    if float(fb.high) >= stop:
        exit_reason = 'STOP_FILL_BAR'
        exit_ts = fill_ts
        exit_px = stop
    else:
        for i in range(idx + 1, len(q)):
            ts = q.index[i]
            b = q.iloc[i]
            hit_stop = float(b.high) >= stop
            hit_tp = float(b.low) <= target
            if hit_stop and hit_tp:
                exit_reason = 'STOP_SAME_BAR_BOTH'
                exit_ts = ts
                exit_px = stop
                break
            if hit_stop:
                exit_reason = 'STOP'
                exit_ts = ts
                exit_px = stop
                break
            if hit_tp:
                exit_reason = 'TP'
                exit_ts = ts
                exit_px = target
                break

    if exit_reason is None:
        exit_reason = 'TIME'
        exit_ts = obs_end
        exit_px = float(q.iloc[-1].close)

    gross_return = (entry - float(exit_px)) / entry
    net_pnl = gross_return * NOTIONAL - FEE
    hold_min = max(0.0, float((pd.Timestamp(exit_ts) - fill_ts) / pd.Timedelta(minutes=1)))

    return {
        'partition': str(r.partition),
        'regime': str(r.regime),
        'clock_block': str(r.clock_block),
        'obs_start': obs_start,
        'obs_end': obs_end,
        'fraction': frac,
        'entry_label': f'F{int(round(frac*100)):02d}',
        'fill_ts': fill_ts,
        'entry_price': entry,
        'H': H,
        'L': L,
        'R4': R4,
        'LOCAL_R': local_r,
        'variant': variant,
        'stop_multiple': sm,
        'target_multiple': tm,
        'nominal_rr': nominal_rr,
        'stop_price': stop,
        'target_price': target,
        'exit_ts': exit_ts,
        'exit_price': float(exit_px),
        'exit_reason': exit_reason,
        'gross_return': gross_return,
        'net_pnl_usd': net_pnl,
        'win': bool(net_pnl > 0),
        'hold_minutes': hold_min,
    }


def metrics(g: pd.DataFrame) -> dict:
    n = len(g)
    if n == 0:
        return {
            'trades': 0, 'wr': np.nan, 'pf': np.nan, 'expectancy': np.nan,
            'total_net': 0.0, 'tp_n': 0, 'stop_n': 0, 'time_n': 0,
            'median_hold': np.nan, 'median_win': np.nan, 'median_loss': np.nan,
        }
    pnl = g.net_pnl_usd.astype(float)
    gp = float(pnl[pnl > 0].sum())
    gl = float(-pnl[pnl < 0].sum())
    pf = math.inf if gl == 0 and gp > 0 else (gp / gl if gl > 0 else np.nan)
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    return {
        'trades': int(n),
        'wr': float((pnl > 0).mean()),
        'pf': pf,
        'expectancy': float(pnl.mean()),
        'total_net': float(pnl.sum()),
        'tp_n': int((g.exit_reason == 'TP').sum()),
        'stop_n': int(g.exit_reason.astype(str).str.startswith('STOP').sum()),
        'time_n': int((g.exit_reason == 'TIME').sum()),
        'median_hold': float(g.hold_minutes.median()),
        'median_win': float(wins.median()) if len(wins) else np.nan,
        'median_loss': float(losses.median()) if len(losses) else np.nan,
    }


def summarize(t: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for v, sm, tm in VARIANTS:
        z = t[t.variant == v]
        for p in MAJOR:
            rows.append({'scope': 'PARTITION', 'name': p, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **metrics(z[z.partition == p])})
        rows.append({'scope': 'POOL', 'name': 'POOLED_OOS', 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **metrics(z[z.partition.isin(OOS)])})
        rows.append({'scope': 'POOL', 'name': 'POOLED_MAJOR', 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **metrics(z[z.partition.isin(MAJOR)])})
        for cb in CLOCKS:
            rows.append({'scope': 'CLOCK_MAJOR', 'name': cb, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **metrics(z[z.clock_block == cb])})
            rows.append({'scope': 'CLOCK_OOS', 'name': cb, 'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm, **metrics(z[z.clock_block == cb and z.partition.isin(OOS)])})
    return pd.DataFrame(rows)


def row(s: pd.DataFrame, scope: str, name: str, variant: str):
    z = s[(s.scope == scope) & (s.name == name) & (s.variant == variant)]
    assert len(z) == 1, (scope, name, variant, len(z))
    return z.iloc[0]


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def money(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def main() -> None:
    entries = load_entries()
    x5, coverage = b21.load5()
    assert len(x5) == 698112 and abs(float(coverage) - 1.0) < 1e-12

    trades = []
    for r in entries.itertuples(index=False):
        for v, sm, tm in VARIANTS:
            trades.append(eval_trade(x5, r, v, sm, tm))
    t = pd.DataFrame(trades)
    assert len(t) == len(entries) * len(VARIANTS)
    assert not t.duplicated(['partition', 'obs_start', 'variant']).any()
    assert (t.stop_price > t.entry_price).all() and (t.entry_price > t.target_price).all()
    assert (t.nominal_rr >= 1.0 - 1e-12).all()
    t.to_csv(OUT_TRADES, index=False)

    s = summarize(t)
    s.to_csv(OUT_SUM, index=False)

    selection_rows = []
    passes = []
    for v, sm, tm in VARIANTS:
        major_rows = [row(s, 'PARTITION', p, v) for p in MAJOR]
        po = row(s, 'POOL', 'POOLED_OOS', v)
        n_ok = major_rows[0].trades >= 100 and major_rows[1].trades >= 150 and major_rows[2].trades >= 60
        exp_ok = all(float(r.expectancy) > 0 for r in major_rows)
        pf_ok = all(float(r.pf) >= 1.20 for r in major_rows)
        wr_ok = all(float(r.wr) >= 0.50 for r in major_rows)
        oos_ok = float(po.expectancy) > 0 and float(po.pf) >= 1.20
        robust = bool(n_ok and exp_ok and pf_ok and wr_ok and oos_ok)
        high70 = bool(robust and all(float(r.wr) >= 0.70 for r in major_rows))
        min_pf = min(float(r.pf) for r in major_rows)
        rec = {
            'variant': v, 'stop_multiple': sm, 'target_multiple': tm, 'nominal_rr': tm/sm,
            'robust_pass': robust, 'high_quality_70': high70,
            'min_major_pf': min_pf,
            'pooled_oos_expectancy': float(po.expectancy),
            'pooled_oos_pf': float(po.pf),
            'pooled_oos_wr': float(po.wr),
        }
        selection_rows.append(rec)
        if robust:
            passes.append(rec)

    sel = pd.DataFrame(selection_rows)
    if passes:
        passes.sort(key=lambda r: (-r['min_major_pf'], -r['pooled_oos_expectancy'], -r['nominal_rr'], r['stop_multiple']))
        chosen = passes[0]['variant']
        verdict = 'B27CB_CLOCK_ADAPTIVE_ECON_SUPPORTED'
    else:
        chosen = ''
        verdict = 'B27CB_CLOCK_ADAPTIVE_ECON_NOT_SUPPORTED'
    sel['selected'] = sel.variant.eq(chosen) if chosen else False
    sel.to_csv(OUT_SEL, index=False)
    OUT_STATUS.write_text(verdict + ('__' + chosen if chosen else '') + '\n')

    # Diagnostic ranking only when nothing passes; this cannot promote a failed variant.
    rank = sorted(selection_rows, key=lambda r: (-r['min_major_pf'], -r['pooled_oos_expectancy'], -r['nominal_rr'], r['stop_multiple']))
    diagnostic_top = chosen if chosen else rank[0]['variant']

    lines = [
        '# B27CB — BTC 24H Clock-Adaptive Pre-Break SHORT Economic Backtest — Result', '',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.', '',
        '**Audit status: PASS.** Exact B27CA clock-selected entries were reused. All variants have nominal RR >=1:1. Same-fill-bar and same-bar TP/STOP ambiguity is resolved conservatively in favor of STOP.', '',
        f'Illustrative economics: **${NOTIONAL:.0f} notional/trade, ${FEE:.2f} round-trip fee, no extra slippage**.', '',
        'Frozen B27CA clock entries: **00-04 F05 / 04-08 F05 / 08-12 F10 / 12-16 F05 / 16-20 F05 / 20-00 F05**.', '',
        '## Major-partition economics', '',
        '| Variant | RR | Partition | N | WR | PF | Exp/trade | Total net | TP | STOP | TIME |',
        '|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    for v, sm, tm in VARIANTS:
        for p in MAJOR:
            r = row(s, 'PARTITION', p, v)
            lines.append(f'| {v} | {tm/sm:.2f} | {p} | {int(r.trades)} | {pct(r.wr)} | {num(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} | {int(r.tp_n)} | {int(r.stop_n)} | {int(r.time_n)} |')

    lines += ['', '## Pooled OOS', '',
              '| Variant | RR | N | WR | PF | Exp/trade | Total net |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for v, sm, tm in VARIANTS:
        r = row(s, 'POOL', 'POOLED_OOS', v)
        lines.append(f'| {v} | {tm/sm:.2f} | {int(r.trades)} | {pct(r.wr)} | {num(r.pf)} | {money(r.expectancy)} | {money(r.total_net)} |')

    lines += ['', f'## Clock diagnostics — {diagnostic_top}', '',
              'If no variant passes the frozen gate, this table is diagnostic only and does not select/promote the variant.', '',
              '| UTC block | Entry | OOS N | OOS WR | OOS PF | OOS Exp | Major N | Major WR | Major PF |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        ro = row(s, 'CLOCK_OOS', cb, diagnostic_top)
        rm = row(s, 'CLOCK_MAJOR', cb, diagnostic_top)
        f = FROZEN_CLOCK_FRAC[cb]
        lines.append(f'| {cb} | F{int(round(f*100)):02d} | {int(ro.trades)} | {pct(ro.wr)} | {num(ro.pf)} | {money(ro.expectancy)} | {int(rm.trades)} | {pct(rm.wr)} | {num(rm.pf)} |')

    lines += ['', '## Frozen gate', '']
    for rec in selection_rows:
        lines.append(f"- {rec['variant']}: ROBUST_PASS **{'PASS' if rec['robust_pass'] else 'FAIL'}**; HIGH_QUALITY_70 **{'PASS' if rec['high_quality_70'] else 'FAIL'}**; min major PF {rec['min_major_pf']:.2f}; pooled-OOS expectancy {money(rec['pooled_oos_expectancy'])}.")
    lines += ['', f'**Frozen verdict: `{verdict}`.**']
    if chosen:
        lines += ['', f'Frozen selected economic candidate: **{chosen}**. This remains research-only and does not alter live BBC.']
    else:
        lines += ['', 'No economic geometry passed. Do not rescue a clock, stop, or target post hoc inside B27CB. Research only; live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
