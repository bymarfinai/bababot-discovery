#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SIGNALS = ROOT / 'BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Signals.csv'
LONG_W = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Windows.csv'
LONG_E = ROOT / 'BTC_LONDON_NY_PRE_SECOND_TOUCH_ENTRY_B27W_Entries.csv'
SHORT_W = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Windows.csv'
SHORT_T = ROOT / 'BTC_LONDON_NY_SHORT_MIRROR_B27AD_Trades.csv'
OUT_MD = ROOT / 'BTC_LONDON_NY_LONG_SHORT_STAGE_DIVERGENCE_B27AE_Result.md'
OUT_CSV = ROOT / 'BTC_LONDON_NY_LONG_SHORT_STAGE_DIVERGENCE_B27AE_Summary.csv'
OUT_STATUS = ROOT / 'BTC_LONDON_NY_LONG_SHORT_STAGE_DIVERGENCE_B27AE_Status.txt'

PARTS = ('external','development','reference_validation','august')
MAJOR = ('external','development','reference_validation')
BAR5 = pd.Timedelta(minutes=5)


def dt(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], utc=True, errors='coerce')
    return df


def fast_slice(x5, start, end):
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_side(side: str):
    sig = pd.read_csv(SIGNALS)
    sig = sig[(sig.transition == 'LONDON_TO_NEWYORK') &
              (sig.side == side) &
              (pd.to_numeric(sig.k) == 1) &
              (pd.to_numeric(sig.opp_visits_at_signal) == 0)].copy()
    sig = dt(sig, ['signal_ts','signal_bar_start','active_session_end'])

    if side == 'LONG':
        w = pd.read_csv(LONG_W)
        w = dt(w, ['signal_ts','eligible_start','h2_bar_start','session_end'])
        e = pd.read_csv(LONG_E)
        e = e[e.entry_name == 'F85'].copy()
        e = dt(e, ['signal_ts','eligible_start','h2_bar_start','entry_ts'])
        e['filled'] = e.filled.astype(str).str.lower().eq('true')
        entry_frac = 0.85
        entry_col = 'entry_ts'
        h2_col = 'target_hit'
    else:
        w = pd.read_csv(SHORT_W)
        w = dt(w, ['signal_ts','eligible_start','h2_bar_start','session_end'])
        e = pd.read_csv(SHORT_T)
        e = e[e.rule == 'BLIND_F15'].copy()
        e = dt(e, ['signal_ts','eligible_start','h2_bar_start','blind_touch_bar_start'])
        e['filled'] = e.blind_filled.astype(str).str.lower().eq('true')
        e['entry_ts'] = e['blind_touch_bar_start']
        e['target_hit'] = e.h2_after_fill.astype(str).str.lower().eq('true')
        entry_frac = 0.15
        entry_col = 'entry_ts'
        h2_col = 'target_hit'

    # Exact identity reproduction between B27Q and side-window census.
    sk = sig[['partition','date_utc','signal_ts']].sort_values(['partition','signal_ts']).reset_index(drop=True)
    wk = w[['partition','date_utc','signal_ts']].sort_values(['partition','signal_ts']).reset_index(drop=True)
    assert len(sk) == len(wk), (side, len(sk), len(wk))
    assert sk.equals(wk), f'{side} B27Q/window identity mismatch'

    # One entry-row per window for the frozen mirrored depth.
    ek = e[['partition','date_utc','signal_ts']].sort_values(['partition','signal_ts']).reset_index(drop=True)
    assert len(ek) == len(wk), (side, len(ek), len(wk))
    assert ek.equals(wk), f'{side} window/entry identity mismatch'

    # Mirrored entry geometry.
    fill = e[e.filled].copy()
    expected = pd.to_numeric(fill.L) + entry_frac * (pd.to_numeric(fill.H) - pd.to_numeric(fill.L))
    actual = pd.to_numeric(fill.entry_px if side == 'LONG' else fill.blind_entry_px)
    assert np.allclose(actual.to_numpy(), expected.to_numpy(), rtol=1e-12, atol=1e-9)
    for r in fill.itertuples(index=False):
        if pd.notna(r.h2_bar_start):
            assert pd.Timestamp(getattr(r, entry_col)) < pd.Timestamp(r.h2_bar_start)

    return sig, w, e


def post_h2_path(x5, side: str, r):
    H = float(r.H); L = float(r.L); R = H - L
    h2 = pd.Timestamp(r.h2_bar_start)
    end = pd.Timestamp(r.session_end)
    q = fast_slice(x5, h2, end)
    assert len(q) and q.index[0] == h2

    accept_ts = pd.NaT
    e20_ts = pd.NaT
    e20 = H + 0.20 * R if side == 'LONG' else L - 0.20 * R
    for ts, b in q.iterrows():
        if pd.isna(accept_ts):
            if (side == 'LONG' and float(b.close) > H) or (side == 'SHORT' and float(b.close) < L):
                accept_ts = ts + BAR5
        if pd.isna(e20_ts):
            if (side == 'LONG' and float(b.high) >= e20) or (side == 'SHORT' and float(b.low) <= e20):
                # Touch is known intrabar; use bar start for elapsed 5m-grid timing.
                e20_ts = ts
        if pd.notna(accept_ts) and pd.notna(e20_ts):
            break
    return accept_ts, e20_ts


def summarize_side(x5, side, sig, w, e):
    rows = []
    for part in PARTS:
        sp = sig[sig.partition == part]
        wp = w[w.partition == part]
        ep = e[e.partition == part].copy()
        opps = len(sp)
        target_break = int((sp.structural_outcome == 'TARGET_BREAK').sum())
        clean = wp[wp.eligible_start.notna()].copy()
        fills = ep[ep.filled].copy()
        h2fills = fills[fills.target_hit.astype(str).str.lower().eq('true')].copy()

        acc = 0; e20 = 0; acc_mins = []; e20_mins = []; fill_h2_mins = []
        for r in h2fills.itertuples(index=False):
            a, t = post_h2_path(x5, side, r)
            h2 = pd.Timestamp(r.h2_bar_start)
            if pd.notna(a):
                acc += 1
                acc_mins.append(float((a - (h2 + BAR5)) / pd.Timedelta(minutes=1)))
            if pd.notna(t):
                e20 += 1
                e20_mins.append(float((t - h2) / pd.Timedelta(minutes=1)))
            et = pd.Timestamp(r.entry_ts)
            fill_h2_mins.append(float((h2-et)/pd.Timedelta(minutes=1)))

        rows.append({
            'side': side, 'partition': part,
            'k1_opps': opps,
            's0_target_break_rate': target_break/opps if opps else np.nan,
            's1_clean_count': len(clean),
            's1_clean_rate': len(clean)/opps if opps else np.nan,
            's2_fill_count': len(fills),
            's2_fill_given_clean': len(fills)/len(clean) if len(clean) else np.nan,
            's3_h2_count': len(h2fills),
            's3_h2_given_fill': len(h2fills)/len(fills) if len(fills) else np.nan,
            's4_accept_count': acc,
            's4_accept_given_h2': acc/len(h2fills) if len(h2fills) else np.nan,
            's5_e20_count': e20,
            's5_e20_given_h2': e20/len(h2fills) if len(h2fills) else np.nan,
            'median_fill_to_h2_min': np.median(fill_h2_mins) if fill_h2_mins else np.nan,
            'median_h2_to_accept_min': np.median(acc_mins) if acc_mins else np.nan,
            'median_h2_to_e20_min': np.median(e20_mins) if e20_mins else np.nan,
        })
    return rows


def pooled(df, side):
    g = df[(df.side == side) & (df.partition.isin(MAJOR))]
    def ratio(num, den):
        d = g[den].sum(); return g[num].sum()/d if d else np.nan
    # target-break denominator k1; clean denominator k1; fill denominator clean; H2 denominator fill; later denom H2.
    return {
        'side':side,'partition':'POOLED_MAJOR',
        'k1_opps':int(g.k1_opps.sum()),
        's0_target_break_rate': float((g.s0_target_break_rate*g.k1_opps).sum()/g.k1_opps.sum()),
        's1_clean_count':int(g.s1_clean_count.sum()),
        's1_clean_rate':float(g.s1_clean_count.sum()/g.k1_opps.sum()),
        's2_fill_count':int(g.s2_fill_count.sum()),
        's2_fill_given_clean':float(g.s2_fill_count.sum()/g.s1_clean_count.sum()),
        's3_h2_count':int(g.s3_h2_count.sum()),
        's3_h2_given_fill':float(g.s3_h2_count.sum()/g.s2_fill_count.sum()),
        's4_accept_count':int(g.s4_accept_count.sum()),
        's4_accept_given_h2':float(g.s4_accept_count.sum()/g.s3_h2_count.sum()),
        's5_e20_count':int(g.s5_e20_count.sum()),
        's5_e20_given_h2':float(g.s5_e20_count.sum()/g.s3_h2_count.sum()),
        'median_fill_to_h2_min':np.nan,
        'median_h2_to_accept_min':np.nan,
        'median_h2_to_e20_min':np.nan,
    }


def pct(x):
    return '-' if pd.isna(x) else f'{100*float(x):.1f}%'


def main():
    x5, coverage = b21.load5()
    assert abs(float(coverage)-1.0) < 1e-12
    ls, lw, le = load_side('LONG')
    ss, sw, se = load_side('SHORT')
    rows = summarize_side(x5,'LONG',ls,lw,le) + summarize_side(x5,'SHORT',ss,sw,se)
    d = pd.DataFrame(rows)
    d = pd.concat([d, pd.DataFrame([pooled(d,'LONG'), pooled(d,'SHORT')])], ignore_index=True)
    d.to_csv(OUT_CSV,index=False)

    lines = ['# B27AE — BTC London -> New York LONG vs SHORT Stage-Divergence Audit — Result','',
             f'5m rows: **{len(x5):,}**; coverage: **{100*float(coverage):.4f}%**.','',
             '**Audit status: PASS.** Exact B27Q K1 OPP0 identities, B27W F85 and B27AD F15 mirrored entry geometry, and post-H2 raw-5m chronology reproduce without tuning.','',
             '## Stage funnel','',
             '| Partition | Side | K1 | S0 Target break | S1 Clean/K1 | S2 Fill/Clean | S3 H2/Fill | S4 Accept/H2 | S5 E20/H2 |',
             '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    order = list(MAJOR)+['POOLED_MAJOR','august']
    for part in order:
        for side in ('LONG','SHORT'):
            q=d[(d.partition==part)&(d.side==side)]
            if q.empty: continue
            r=q.iloc[0]
            lines.append(f"| {part} | {side} | {int(r.k1_opps)} | {pct(r.s0_target_break_rate)} | {pct(r.s1_clean_rate)} | {pct(r.s2_fill_given_clean)} | {pct(r.s3_h2_given_fill)} | {pct(r.s4_accept_given_h2)} | {pct(r.s5_e20_given_h2)} |")

    lines += ['', '## LONG minus SHORT percentage-point gaps','',
              '| Partition | S0 Target break | S1 Clean | S2 Fill | S3 H2 | S4 Accept | S5 E20 |',
              '|---|---:|---:|---:|---:|---:|---:|']
    for part in list(MAJOR)+['POOLED_MAJOR']:
        a=d[(d.partition==part)&(d.side=='LONG')].iloc[0]
        b=d[(d.partition==part)&(d.side=='SHORT')].iloc[0]
        vals=[]
        for c in ['s0_target_break_rate','s1_clean_rate','s2_fill_given_clean','s3_h2_given_fill','s4_accept_given_h2','s5_e20_given_h2']:
            vals.append(100*(float(a[c])-float(b[c])))
        lines.append('| '+part+' | '+' | '.join(f'{v:+.1f}pp' for v in vals)+' |')

    # Earliest pooled nested-stage divergence after opportunity creation.
    lp=d[(d.partition=='POOLED_MAJOR')&(d.side=='LONG')].iloc[0]
    sp=d[(d.partition=='POOLED_MAJOR')&(d.side=='SHORT')].iloc[0]
    gaps={
        'S1 clean leave':100*(lp.s1_clean_rate-sp.s1_clean_rate),
        'S2 mirrored fill':100*(lp.s2_fill_given_clean-sp.s2_fill_given_clean),
        'S3 second-touch H2':100*(lp.s3_h2_given_fill-sp.s3_h2_given_fill),
        'S4 breakout acceptance':100*(lp.s4_accept_given_h2-sp.s4_accept_given_h2),
        'S5 E20 extension':100*(lp.s5_e20_given_h2-sp.s5_e20_given_h2),
    }
    lines += ['', '## Diagnostic interpretation','']
    lines.append(f"- Pooled S1 gap: {gaps['S1 clean leave']:+.1f}pp; pooled S2 gap: {gaps['S2 mirrored fill']:+.1f}pp.")
    lines.append(f"- Pooled S3 H2 gap: {gaps['S3 second-touch H2']:+.1f}pp; S4 acceptance gap: {gaps['S4 breakout acceptance']:+.1f}pp; S5 E20 gap: {gaps['S5 E20 extension']:+.1f}pp.")
    lines.append('- The earliest materially visible divergence should be read from the stage table, not used to retune a threshold in this audit.')
    lines += ['', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    OUT_STATUS.write_text('B27AE_AUDIT_PASS\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
