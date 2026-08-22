#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
LONG_E = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
LONG_W = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
SHORT_T = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Trades.csv'
SHORT_W = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Windows.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_F85_F15_POST_FILL_PATH_B27AF_Result.md'
OUT_TRADES = ROOT / 'BTC_LONDON_NY_F85_F15_POST_FILL_PATH_B27AF_Trades.csv'
OUT_SUM = ROOT / 'BTC_LONDON_NY_F85_F15_POST_FILL_PATH_B27AF_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_F85_F15_POST_FILL_PATH_B27AF_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
EXPECTED = {
    ('LONG','external'):46, ('LONG','development'):72, ('LONG','reference_validation'):31, ('LONG','august'):3,
    ('SHORT','external'):50, ('SHORT','development'):79, ('SHORT','reference_validation'):34, ('SHORT','august'):1,
}


def dt(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def boolcol(s):
    return s.astype(str).str.lower().eq('true')


def load_long():
    e = pd.read_csv(LONG_E)
    e = e[e.entry_name == 'F85'].copy()
    e['filled'] = boolcol(e.filled)
    e['h2_success'] = boolcol(e.target_hit)
    e = e[e.filled].copy()
    e = dt(e, ['signal_ts','entry_ts','h2_bar_start','opposite_break_bar_start'])
    w = pd.read_csv(LONG_W)
    w = dt(w, ['signal_ts','session_end','terminal_bar_start','h2_bar_start','opposite_break_bar_start'])
    w = w[['partition','date_utc','signal_ts','session_end','terminal_bar_start']]
    x = e.merge(w, on=['partition','date_utc','signal_ts'], how='left', validate='one_to_one')
    x['side'] = 'LONG'
    x['entry_start'] = x['entry_ts']
    x['entry_px_norm'] = pd.to_numeric(x.entry_px)
    x['R'] = pd.to_numeric(x.H) - pd.to_numeric(x.L)
    expected_px = pd.to_numeric(x.L) + 0.85*x.R
    assert np.allclose(x.entry_px_norm, expected_px, rtol=1e-12, atol=1e-9)
    return x


def load_short():
    t = pd.read_csv(SHORT_T)
    t = t[t.rule == 'BLIND_F15'].copy()
    t['blind_filled_b'] = boolcol(t.blind_filled)
    t['h2_success'] = boolcol(t.h2_after_fill)
    t = t[t.blind_filled_b].copy()
    t = dt(t, ['signal_ts','blind_touch_bar_start','h2_bar_start','opposite_break_bar_start','session_end'])
    w = pd.read_csv(SHORT_W)
    w = dt(w, ['signal_ts','terminal_bar_start','session_end'])
    w = w[['partition','date_utc','signal_ts','terminal_bar_start']]
    x = t.merge(w, on=['partition','date_utc','signal_ts'], how='left', validate='one_to_one')
    x['side'] = 'SHORT'
    x['entry_start'] = x['blind_touch_bar_start']
    x['entry_px_norm'] = pd.to_numeric(x.blind_entry_px)
    x['R'] = pd.to_numeric(x.H) - pd.to_numeric(x.L)
    expected_px = pd.to_numeric(x.L) + 0.15*x.R
    assert np.allclose(x.entry_px_norm, expected_px, rtol=1e-12, atol=1e-9)
    return x


def terminal_of(r):
    if bool(r.h2_success):
        assert pd.notna(r.h2_bar_start)
        return pd.Timestamp(r.h2_bar_start), 'H2_SUCCESS'
    if pd.notna(r.opposite_break_bar_start):
        return pd.Timestamp(r.opposite_break_bar_start), 'OPPOSITE_BREAK'
    if pd.notna(r.terminal_bar_start):
        return pd.Timestamp(r.terminal_bar_start), 'AMBIGUOUS_TERMINAL'
    return pd.Timestamp(r.session_end), 'NO_H2_SESSION_END'


def max_streak(vals):
    best = cur = 0
    for v in vals:
        if bool(v):
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return best


def episodes(vals):
    n = 0
    prev = False
    for v in vals:
        v = bool(v)
        if v and not prev:
            n += 1
        prev = v
    return n


def analyze_one(x5, r):
    side = str(r.side)
    sign = 1.0 if side == 'LONG' else -1.0
    entry = float(r.entry_px_norm)
    R = float(r.R)
    assert R > 0
    start = pd.Timestamp(r.entry_start)
    terminal, terminal_type = terminal_of(r)
    assert start < terminal
    assert start in x5.index

    fill_bar = x5.loc[start]
    fill_z = sign*(float(fill_bar.close)-entry)/R

    # Full bars strictly after fill bar and strictly before terminal.
    q = fast_slice(x5, start + BAR5, terminal)
    close_z = [fill_z]
    if len(q):
        close_z.extend((sign*(q.close.astype(float).to_numpy()-entry)/R).tolist())
    close_z = np.asarray(close_z, dtype=float)
    wrong = close_z < 0

    if len(q):
        next_z = float(sign*(float(q.iloc[0].close)-entry)/R)
        next_eligible = True
        next_wrong = next_z < 0
        if side == 'LONG':
            adverse_wick_r = max(0.0, (entry-float(q.low.min()))/R)
            favorable_wick_r = max(0.0, (float(q.high.max())-entry)/R)
        else:
            adverse_wick_r = max(0.0, (float(q.high.max())-entry)/R)
            favorable_wick_r = max(0.0, (entry-float(q.low.min()))/R)
    else:
        next_z = np.nan
        next_eligible = False
        next_wrong = False
        adverse_wick_r = 0.0
        favorable_wick_r = 0.0

    return {
        'side': side,
        'partition': r.partition,
        'date_utc': r.date_utc,
        'signal_ts': pd.Timestamp(r.signal_ts),
        'entry_start': start,
        'entry_px': entry,
        'H': float(r.H), 'L': float(r.L), 'R': R,
        'h2_success': bool(r.h2_success),
        'terminal_type': terminal_type,
        'terminal_bar_start': terminal,
        'minutes_to_terminal': float((terminal-start)/pd.Timedelta(minutes=1)),
        'preterminal_completed_closes': int(len(close_z)),
        'fill_close_progress_r': float(fill_z),
        'fill_close_wrong': bool(fill_z < 0),
        'next_bar_eligible': bool(next_eligible),
        'next_bar_close_progress_r': next_z,
        'next_bar_close_wrong': bool(next_wrong) if next_eligible else False,
        'wrong_close_rate': float(wrong.mean()),
        'ever_wrong_close': bool(wrong.any()),
        'max_wrong_close_streak': int(max_streak(wrong)),
        'wrong_close_episodes': int(episodes(wrong)),
        'max_adverse_close_r': float(max(0.0, -float(close_z.min()))),
        'max_favorable_close_r': float(max(0.0, float(close_z.max()))),
        'max_adverse_wick_r_post_fillbar': float(adverse_wick_r),
        'max_favorable_wick_r_post_fillbar': float(favorable_wick_r),
        'stop_distance_consumed': float(adverse_wick_r / 0.50),
    }


def med(s):
    s = pd.to_numeric(s, errors='coerce').dropna()
    return float(s.median()) if len(s) else np.nan


def summarize(g):
    nxt = g[g.next_bar_eligible.astype(bool)]
    return {
        'N': int(len(g)),
        'h2_rate': float(g.h2_success.mean()) if len(g) else np.nan,
        'fill_close_wrong_rate': float(g.fill_close_wrong.mean()) if len(g) else np.nan,
        'next_bar_eligible_N': int(len(nxt)),
        'next_bar_wrong_rate': float(nxt.next_bar_close_wrong.mean()) if len(nxt) else np.nan,
        'ever_wrong_rate': float(g.ever_wrong_close.mean()) if len(g) else np.nan,
        'median_fill_close_progress_r': med(g.fill_close_progress_r),
        'median_next_bar_progress_r': med(nxt.next_bar_close_progress_r),
        'median_wrong_close_rate': med(g.wrong_close_rate),
        'median_max_wrong_streak': med(g.max_wrong_close_streak),
        'median_wrong_episodes': med(g.wrong_close_episodes),
        'median_close_mae_r': med(g.max_adverse_close_r),
        'median_close_mfe_r': med(g.max_favorable_close_r),
        'median_wick_mae_r': med(g.max_adverse_wick_r_post_fillbar),
        'median_stop_consumed': med(g.stop_distance_consumed),
        'median_minutes_terminal': med(g.minutes_to_terminal),
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def num(x):
    return '-' if pd.isna(x) else f'{float(x):.3f}'


def main():
    x5, coverage = b21.load5()
    assert abs(float(coverage)-1.0) < 1e-12
    L = load_long(); S = load_short()

    # Frozen count reproduction.
    for side, df in [('LONG',L),('SHORT',S)]:
        for part in PARTS:
            got = len(df[df.partition == part])
            assert got == EXPECTED[(side,part)], (side, part, got, EXPECTED[(side,part)])

    # H2 count reproduction from persisted results.
    expected_h2 = {
        ('LONG','external'):41, ('LONG','development'):53, ('LONG','reference_validation'):27, ('LONG','august'):3,
        ('SHORT','external'):37, ('SHORT','development'):59, ('SHORT','reference_validation'):24, ('SHORT','august'):1,
    }
    for side, df in [('LONG',L),('SHORT',S)]:
        for part in PARTS:
            got = int(df[df.partition == part].h2_success.sum())
            assert got == expected_h2[(side,part)], (side,part,got)

    rows = []
    for _, r in pd.concat([L,S], ignore_index=True).iterrows():
        rows.append(analyze_one(x5, r))
    t = pd.DataFrame(rows)
    assert len(t) == len(L)+len(S)
    assert not t.duplicated(['side','partition','date_utc','signal_ts']).any()

    sums = []
    for part in PARTS:
        for side in ('LONG','SHORT'):
            g = t[(t.partition==part)&(t.side==side)]
            if len(g):
                sums.append({'partition':part,'side':side,'outcome':'ALL',**summarize(g)})
                for outcome, flag in [('H2_SUCCESS',True),('H2_FAIL',False)]:
                    q = g[g.h2_success == flag]
                    sums.append({'partition':part,'side':side,'outcome':outcome,**summarize(q)})
    major = t[t.partition.isin(MAJOR)]
    for side in ('LONG','SHORT'):
        g = major[major.side==side]
        sums.append({'partition':'POOLED_MAJOR','side':side,'outcome':'ALL',**summarize(g)})
        for outcome, flag in [('H2_SUCCESS',True),('H2_FAIL',False)]:
            q=g[g.h2_success==flag]
            sums.append({'partition':'POOLED_MAJOR','side':side,'outcome':outcome,**summarize(q)})
    s = pd.DataFrame(sums)

    t.to_csv(OUT_TRADES,index=False)
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text('B27AF_AUDIT_PASS\n')

    lines = [
        '# B27AF — BTC London -> New York F85/F15 Post-Fill Path Anatomy — Result','',
        f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
        '**Audit status: PASS.** Frozen F85/F15 cohorts and H2 identities reproduce. Fill-bar high/low are excluded; all OHLC excursion diagnostics start on the next complete 5m bar.','',
        '## All-fill post-entry behavior','',
        '| Partition | Side | N | H2 | Fill close wrong | Next-bar N | Next-bar wrong | Ever wrong | Median wrong-close rate | Median close MAE | Median wick MAE | Median stop distance consumed |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order = list(MAJOR)+['POOLED_MAJOR','august']
    for part in order:
        for side in ('LONG','SHORT'):
            q=s[(s.partition==part)&(s.side==side)&(s.outcome=='ALL')]
            if q.empty: continue
            r=q.iloc[0]
            lines.append(f"| {part} | {side} | {int(r.N)} | {pct(r.h2_rate)} | {pct(r.fill_close_wrong_rate)} | {int(r.next_bar_eligible_N)} | {pct(r.next_bar_wrong_rate)} | {pct(r.ever_wrong_rate)} | {pct(r.median_wrong_close_rate)} | {num(r.median_close_mae_r)}R | {num(r.median_wick_mae_r)}R | {pct(r.median_stop_consumed)} |")

    lines += ['', '## Pooled-major winners vs failures','',
              '| Side | Outcome | N | Fill close wrong | Next-bar wrong | Ever wrong | Median wrong-close rate | Max wrong streak med | Close MAE med | Wick MAE med | Stop consumed med | Terminal min med |',
              '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for side in ('LONG','SHORT'):
        for outcome in ('H2_SUCCESS','H2_FAIL'):
            r=s[(s.partition=='POOLED_MAJOR')&(s.side==side)&(s.outcome==outcome)].iloc[0]
            lines.append(f"| {side} | {outcome} | {int(r.N)} | {pct(r.fill_close_wrong_rate)} | {pct(r.next_bar_wrong_rate)} | {pct(r.ever_wrong_rate)} | {pct(r.median_wrong_close_rate)} | {num(r.median_max_wrong_streak)} | {num(r.median_close_mae_r)}R | {num(r.median_wick_mae_r)}R | {pct(r.median_stop_consumed)} | {num(r.median_minutes_terminal)} |")

    # Fixed pooled diagnostic deltas, descriptive only.
    la=s[(s.partition=='POOLED_MAJOR')&(s.side=='LONG')&(s.outcome=='ALL')].iloc[0]
    sa=s[(s.partition=='POOLED_MAJOR')&(s.side=='SHORT')&(s.outcome=='ALL')].iloc[0]
    lw=s[(s.partition=='POOLED_MAJOR')&(s.side=='LONG')&(s.outcome=='H2_SUCCESS')].iloc[0]
    lf=s[(s.partition=='POOLED_MAJOR')&(s.side=='LONG')&(s.outcome=='H2_FAIL')].iloc[0]
    sw=s[(s.partition=='POOLED_MAJOR')&(s.side=='SHORT')&(s.outcome=='H2_SUCCESS')].iloc[0]
    sf=s[(s.partition=='POOLED_MAJOR')&(s.side=='SHORT')&(s.outcome=='H2_FAIL')].iloc[0]

    lines += ['', '## Diagnostic readout','']
    lines.append(f"- All fills: SHORT minus LONG fill-bar-wrong = {100*(sa.fill_close_wrong_rate-la.fill_close_wrong_rate):+.1f}pp; next-bar-wrong = {100*(sa.next_bar_wrong_rate-la.next_bar_wrong_rate):+.1f}pp; ever-wrong = {100*(sa.ever_wrong_rate-la.ever_wrong_rate):+.1f}pp.")
    lines.append(f"- All fills median wick MAE: LONG {la.median_wick_mae_r:.3f}R vs SHORT {sa.median_wick_mae_r:.3f}R; median mirrored stop-distance consumed: LONG {100*la.median_stop_consumed:.1f}% vs SHORT {100*sa.median_stop_consumed:.1f}%.")
    lines.append(f"- H2 winners median wrong-close rate: LONG {100*lw.median_wrong_close_rate:.1f}% vs SHORT {100*sw.median_wrong_close_rate:.1f}%; H2 failures: LONG {100*lf.median_wrong_close_rate:.1f}% vs SHORT {100*sf.median_wrong_close_rate:.1f}%.")
    lines.append(f"- SHORT internal separation (FAIL minus SUCCESS): fill-bar-wrong {100*(sf.fill_close_wrong_rate-sw.fill_close_wrong_rate):+.1f}pp; next-bar-wrong {100*(sf.next_bar_wrong_rate-sw.next_bar_wrong_rate):+.1f}pp; median wick MAE {sf.median_wick_mae_r-sw.median_wick_mae_r:+.3f}R.")
    lines += ['', 'No filter is selected from these diagnostics. Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
