#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd

import btc_f85_long_f15_short_collision_b27dt as dt
import btc_generic_f15_short_clock_scan_b27dr as dr

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_Result.md'
OUT_WIN = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_WindowSummary.csv'
OUT_YEAR = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_YearSummary.csv'
OUT_SLIP = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_Slippage.csv'
OUT_PARITY = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_Parity.csv'
OUT_STATUS = ROOT / 'BTC_F15_SHORT_2000_WALKFORWARD_PORTFOLIO_B27DU_Status.txt'

PRIMARY_CLOCK = 1200
MAJOR = dt.MAJOR
WINDOWS = (
    ('W1', '2020-01-01', '2021-07-01', True),
    ('W2', '2021-07-01', '2023-01-01', True),
    ('W3', '2023-01-01', '2024-07-01', True),
    ('W4', '2024-07-01', '2026-01-01', True),
    ('W5_YTD', '2026-01-01', '2027-01-01', False),
)
SLIPPAGE_BPS = (0, 2, 5, 10)


def pf(vals):
    x = pd.to_numeric(pd.Series(vals), errors='coerce').dropna()
    pos = float(x[x > 0].sum())
    neg = float(-x[x < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def metrics_df(d, col='pnl'):
    if d is None or len(d) == 0:
        return {'n':0,'wins':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'net':0.0}
    v = pd.to_numeric(d[col], errors='coerce').dropna()
    return {
        'n': int(len(v)),
        'wins': int((v > 0).sum()),
        'wr': float((v > 0).mean()) if len(v) else np.nan,
        'pf': pf(v),
        'expectancy': float(v.mean()) if len(v) else np.nan,
        'net': float(v.sum()),
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.2f}'


def usd(x):
    return '-' if pd.isna(x) else f'${float(x):+.2f}'


def between(d, start, end):
    a = pd.Timestamp(start, tz='UTC')
    z = pd.Timestamp(end, tz='UTC')
    return d[(d.entry_ts >= a) & (d.entry_ts < z)].copy()


def accepted_portfolio(raw_long, shorts, label):
    q = dt.lock_rows(pd.concat([raw_long, shorts], ignore_index=True), label)
    return q[q.accepted_portfolio.astype(bool)].copy(), q


def parity_checks(short20, base, fs20_acc, fs6_acc):
    rows = []
    s20 = metrics_df(dt.pooled(short20))
    exp20 = {'n':56, 'wins':43, 'wr':43/56, 'pf':2.81, 'net':77.73}
    for k, exp in exp20.items():
        act = s20[k]
        tol = {'n':0,'wins':0,'wr':1e-12,'pf':0.03,'net':0.20}[k]
        ok = int(act) == int(exp) if k in ('n','wins') else abs(float(act)-float(exp)) <= tol
        rows.append({'layer':'SHORT20_B27DS','field':k,'actual':act,'expected':exp,'pass':ok})

    exp_base = {'accepted':227,'wr':.722,'pf':2.25,'total_net':289.76,'max_loss_streak':3}
    for k, exp in exp_base.items():
        act = base[k]
        if k in ('accepted','max_loss_streak'):
            ok = int(act) == int(exp)
        else:
            tol = .003 if k == 'wr' else (.03 if k == 'pf' else .20)
            ok = abs(float(act)-float(exp)) <= tol
        rows.append({'layer':'LONG_B27DQ','field':k,'actual':act,'expected':exp,'pass':ok})

    p20 = metrics_df(dt.pooled(fs20_acc))
    p6 = metrics_df(dt.pooled(fs6_acc))
    for layer, m, expn, expnet in (
        ('PORTFOLIO20_B27DT', p20, 283, 367.49),
        ('PORTFOLIO6_B27DT', p6, 548, 478.86),
    ):
        rows.append({'layer':layer,'field':'n','actual':m['n'],'expected':expn,'pass':int(m['n'])==expn})
        rows.append({'layer':layer,'field':'net','actual':m['net'],'expected':expnet,'pass':abs(float(m['net'])-expnet)<=.25})
    out = pd.DataFrame(rows)
    if not bool(out['pass'].all()):
        raise AssertionError('B27DU parity failure:\n'+out.to_string(index=False))
    return out


def window_summary(short20, base_long, fs20_acc, fs6_acc):
    rows = []
    for name, start, end, completed in WINDOWS:
        s = between(dt.pooled(short20), start, end)
        b = between(dt.pooled(base_long), start, end)
        p20 = between(dt.pooled(fs20_acc), start, end)
        p6 = between(dt.pooled(fs6_acc), start, end)
        p20s = p20[p20.side == 'SHORT'].copy()
        p6s = p6[p6.side == 'SHORT'].copy()
        p20l = p20[p20.side == 'LONG'].copy()
        p6l = p6[p6.side == 'LONG'].copy()
        sm = metrics_df(s); bm = metrics_df(b); m20 = metrics_df(p20); m6 = metrics_df(p6)
        m20s = metrics_df(p20s); m6s = metrics_df(p6s)
        base_ids = set(b.candidate_id)
        displaced20 = base_ids - set(p20l.candidate_id)
        displaced6 = base_ids - set(p6l.candidate_id)
        short_pass = bool(sm['n'] >= 8 and pd.notna(sm['wr']) and sm['wr'] >= .60 and
                          pd.notna(sm['pf']) and sm['pf'] >= 1.20 and sm['net'] > 0)
        rows.append({
            'window':name,'start':start,'end':end,'completed_gate_window':completed,
            'short20_n':sm['n'],'short20_wr':sm['wr'],'short20_pf':sm['pf'],'short20_expectancy':sm['expectancy'],'short20_net':sm['net'],'short20_window_pass':short_pass,
            'long_only_n':bm['n'],'long_only_wr':bm['wr'],'long_only_pf':bm['pf'],'long_only_net':bm['net'],
            'long_plus_short20_n':m20['n'],'long_plus_short20_wr':m20['wr'],'long_plus_short20_pf':m20['pf'],'long_plus_short20_net':m20['net'],
            'short20_accepted_n':m20s['n'],'short20_accepted_wr':m20s['wr'],'short20_accepted_net':m20s['net'],
            'short20_delta_vs_long':m20['net']-bm['net'],'short20_displaced_long_n':len(displaced20),
            'long_plus_short6_n':m6['n'],'long_plus_short6_wr':m6['wr'],'long_plus_short6_pf':m6['pf'],'long_plus_short6_net':m6['net'],
            'short6_accepted_n':m6s['n'],'short6_accepted_wr':m6s['wr'],'short6_accepted_net':m6s['net'],
            'short6_delta_vs_long':m6['net']-bm['net'],'short6_displaced_long_n':len(displaced6),
        })
    return pd.DataFrame(rows)


def year_summary(short20):
    q = dt.pooled(short20).copy()
    q['year'] = q.entry_ts.dt.year
    rows=[]
    for y in sorted(q.year.unique()):
        m=metrics_df(q[q.year==y])
        rows.append({'year':int(y),**m})
    return pd.DataFrame(rows)


def slippage_summary(short_cases):
    q = short_cases[(short_cases.clock_min == PRIMARY_CLOCK) &
                    short_cases.partition.isin(MAJOR) &
                    short_cases.entry_executed.astype(bool) &
                    short_cases.fixed_net_pnl_usd.notna()].copy()
    rows=[]
    notional=float(dr.b27ad.NOTIONAL); fee=float(dr.b27ad.FEE)
    for bps in SLIPPAGE_BPS:
        f=float(bps)/10000.0
        entry=pd.to_numeric(q.entry_px,errors='raise')*(1.0-f)
        exitp=pd.to_numeric(q.fixed_exit_px,errors='raise')*(1.0+f)
        pnl=(1.0-exitp/entry)*notional-fee
        tmp=pd.DataFrame({'pnl':pnl})
        m=metrics_df(tmp)
        rows.append({'slippage_bps_per_fill':bps,**m})
    return pd.DataFrame(rows)


def main():
    x5, coverage = dt.dq.dn.dl.dj.b21.load5()
    raw_long_all, locked_long_all, base = dt.build_long(x5)
    raw_long = dt.normalize_long(raw_long_all, accepted_source=False)
    base_long = dt.normalize_long(locked_long_all, accepted_source=True)

    short_cases = dt.build_shorts(x5)
    short_all = dt.normalize_short(short_cases)
    short20 = short_all[short_all.clock_min_norm == PRIMARY_CLOCK].copy()
    short6 = short_all.copy()

    fs20_acc, fs20_all = accepted_portfolio(raw_long, short20, 'B27DU_SHORT20')
    fs6_acc, fs6_all = accepted_portfolio(raw_long, short6, 'B27DU_SHORT6')

    parity = parity_checks(short20, base, fs20_acc, fs6_acc)
    win = window_summary(short20, base_long, fs20_acc, fs6_acc)
    years = year_summary(short20)
    slip = slippage_summary(short_cases)

    completed = win[win.completed_gate_window.astype(bool)].copy()
    chronological_supported = bool(
        int(completed.short20_window_pass.astype(bool).sum()) >= 3 and
        not ((completed.short20_pf.notna()) & (completed.short20_pf < .80)).any()
    )

    pooled_base = metrics_df(dt.pooled(base_long))
    pooled20 = metrics_df(dt.pooled(fs20_acc))
    base_ids = set(dt.pooled(base_long).candidate_id)
    fs20_long_ids = set(dt.pooled(fs20_acc[fs20_acc.side=='LONG']).candidate_id)
    displaced_total = len(base_ids - fs20_long_ids)
    positive_delta_windows = int((completed.short20_delta_vs_long > 0).sum())
    portfolio_supported = bool(
        positive_delta_windows >= 3 and displaced_total == 0 and pooled20['net'] > pooled_base['net']
    )

    s5 = slip[slip.slippage_bps_per_fill == 5].iloc[0]
    execution_supported = bool(
        pd.notna(s5.wr) and float(s5.wr) >= .65 and
        pd.notna(s5.pf) and float(s5.pf) >= 1.50 and float(s5.net) > 0
    )

    if chronological_supported and portfolio_supported and execution_supported:
        status='B27DU_SHORT2000_HISTORICAL_ROBUSTNESS_SUPPORTED'
    elif not chronological_supported:
        status='B27DU_SHORT2000_CHRONOLOGICAL_STABILITY_NOT_SUPPORTED'
    elif not portfolio_supported:
        status='B27DU_SHORT2000_PORTFOLIO_STABILITY_NOT_SUPPORTED'
    else:
        status='B27DU_SHORT2000_EXECUTION_STRESS_NOT_SUPPORTED'

    parity.to_csv(OUT_PARITY,index=False)
    win.to_csv(OUT_WIN,index=False)
    years.to_csv(OUT_YEAR,index=False)
    slip.to_csv(OUT_SLIP,index=False)
    OUT_STATUS.write_text(status+'\n')

    lines=[
        '# B27DU — F15 SHORT 20:00 UTC Walk-Forward / Portfolio / Execution-Stress Validation — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{coverage:.4%}**.','',
        '**Parity: PASS** for B27DQ LONG, B27DS SHORT20, B27DT LONG+SHORT20 and B27DT six-SHORT basket.','',
        '## Frozen SHORT20 chronological windows','',
        '| Window | Period | N | WR | PF | Exp | Net | Gate |',
        '|---|---|---:|---:|---:|---:|---:|---|'
    ]
    for r in win.itertuples(index=False):
        lines.append(f'| {r.window} | {r.start} to {r.end} | {r.short20_n} | {pct(r.short20_wr)} | {num(r.short20_pf)} | {usd(r.short20_expectancy)} | {usd(r.short20_net)} | {"PASS" if r.short20_window_pass else ("YTD" if not r.completed_gate_window else "FAIL")} |')

    lines += ['',f'Completed-window chronological stability: **{"SUPPORTED" if chronological_supported else "NOT SUPPORTED"}** ({int(completed.short20_window_pass.astype(bool).sum())}/4 windows pass).','',
              '## Portfolio chronology by window','',
              '| Window | LONG-only Net | LONG+SHORT20 Net | Delta20 | SHORT20 N/WR | Displaced LONG | LONG+6SHORT Net | Delta6 | SHORT6 N/WR |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in win.itertuples(index=False):
        lines.append(f'| {r.window} | {usd(r.long_only_net)} | {usd(r.long_plus_short20_net)} | {usd(r.short20_delta_vs_long)} | {r.short20_accepted_n}/{pct(r.short20_accepted_wr)} | {r.short20_displaced_long_n} | {usd(r.long_plus_short6_net)} | {usd(r.short6_delta_vs_long)} | {r.short6_accepted_n}/{pct(r.short6_accepted_wr)} |')

    lines += ['',f'LONG+SHORT20 portfolio stability: **{"SUPPORTED" if portfolio_supported else "NOT SUPPORTED"}**; positive completed-window deltas={positive_delta_windows}/4; pooled-major displaced LONG={displaced_total}.','',
              '## Calendar-year SHORT20 anatomy','',
              '| Year | N | WR | PF | Exp | Net |','|---:|---:|---:|---:|---:|---:|']
    for r in years.itertuples(index=False):
        lines.append(f'| {r.year} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} |')

    lines += ['', '## Conservative execution stress — SHORT20 only','',
              '| Slippage per fill | N | WR | PF | Exp | Net |','|---:|---:|---:|---:|---:|---:|']
    for r in slip.itertuples(index=False):
        lines.append(f'| {r.slippage_bps_per_fill} bps | {r.n} | {pct(r.wr)} | {num(r.pf)} | {usd(r.expectancy)} | {usd(r.net)} |')
    lines += ['',f'5 bps-per-fill execution robustness: **{"SUPPORTED" if execution_supported else "NOT SUPPORTED"}**.','',
              f'## Final status: **{status}**','',
              'Interpretation guardrail: B27DU is frozen-rule retrospective robustness evidence, not pristine unseen OOS and not live authorization. Live BBC unchanged.']

    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__=='__main__':
    main()
