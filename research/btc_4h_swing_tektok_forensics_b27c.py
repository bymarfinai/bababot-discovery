#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
TRADES_CSV = ROOT / 'BTC_PREVIOUS_BAR_BREAKOUT_B27A_Trades.csv'
OUT_MD = ROOT / 'BTC_4H_SWING_TEKTOK_FORENSICS_B27C_Result.md'
OUT_CSV = ROOT / 'BTC_4H_SWING_TEKTOK_FORENSICS_B27C_Trades.csv'
DUR = pd.Timedelta(hours=4)


def pf(v):
    s = pd.Series(v, dtype=float).dropna()
    pos = float(s[s > 0].sum()); neg = float(-s[s < 0].sum())
    if neg == 0 and pos > 0: return float('inf')
    return pos / neg if neg > 0 else np.nan


def summarize(g):
    if len(g) == 0:
        return {'n':0,'w':0,'l':0,'wr':np.nan,'pf':np.nan,'exp':np.nan,'total':np.nan}
    net = pd.to_numeric(g.net_pnl_usd, errors='coerce').dropna()
    return {
        'n': int(len(net)), 'w': int((net>0).sum()), 'l': int((net<=0).sum()),
        'wr': float((net>0).mean()), 'pf': float(pf(net)), 'exp': float(net.mean()), 'total': float(net.sum())
    }


def fmt_pct(x): return '-' if pd.isna(x) else f'{100*x:.2f}%'
def fmt_num(x,d=2):
    if pd.isna(x): return '-'
    if math.isinf(float(x)): return 'inf'
    return f'{float(x):.{d}f}'


def main():
    x5, coverage = b21.load5()
    z = b22b.resample_ohlc(x5, '4h').copy()
    idx = z.index
    hi = z.high.to_numpy(float); lo = z.low.to_numpy(float); cl = z.close.to_numpy(float)

    # Causal 3-bar fractals. A swing centered at k is known only when k+1 closes,
    # i.e. at the start of bar k+2.
    sh = np.zeros(len(z), dtype=bool); sl = np.zeros(len(z), dtype=bool)
    for k in range(1, len(z)-1):
        sh[k] = hi[k] > hi[k-1] and hi[k] > hi[k+1]
        sl[k] = lo[k] < lo[k-1] and lo[k] < lo[k+1]

    trades = pd.read_csv(TRADES_CSV)
    for c in ['signal_ts','entry_ts','exit_ts']:
        trades[c] = pd.to_datetime(trades[c], utc=True, errors='coerce')
    trades = trades[(trades.timeframe=='4h') & (trades.rr=='R2') & (trades.resolved.astype(str).str.lower().isin(['true','1']))].copy()

    rows=[]
    for t in trades.itertuples(index=False):
        s_pos = int(idx.searchsorted(t.signal_ts, side='left'))
        if s_pos < 4 or s_pos >= len(z):
            continue
        # Only swings whose confirmation was available BEFORE signal bar began.
        last_sh = None; last_sl = None
        for k in range(1, s_pos-1):
            confirm_ts = idx[k+2] if k+2 < len(idx) else None
            if confirm_ts is None or confirm_ts > t.signal_ts:
                break
            if sh[k]: last_sh = k
            if sl[k]: last_sl = k
        if last_sh is None or last_sl is None:
            continue

        sh_px=float(hi[last_sh]); sl_px=float(lo[last_sl])
        sh_confirm=idx[last_sh+2]; sl_confirm=idx[last_sl+2]
        known_ts=max(sh_confirm, sl_confirm)
        a=int(idx.searchsorted(known_ts, side='left'))
        b=s_pos  # exclude signal breakout candle itself

        upper_tests=0; lower_tests=0; ambiguous_both=0
        seq=[]
        for j in range(a,b):
            up = hi[j] >= sh_px and cl[j] <= sh_px
            dn = lo[j] <= sl_px and cl[j] >= sl_px
            if up and dn:
                ambiguous_both += 1
            elif up:
                upper_tests += 1; seq.append('H')
            elif dn:
                lower_tests += 1; seq.append('L')

        # Collapse consecutive same-side tests into visits; count side-to-side switches.
        visits=[]
        for s in seq:
            if not visits or visits[-1] != s:
                visits.append(s)
        switches=max(0, len(visits)-1)
        true_swing_break = (t.side=='LONG' and cl[s_pos] > sh_px) or (t.side=='SHORT' and cl[s_pos] < sl_px)

        rows.append({
            'partition':t.partition,'side':t.side,'signal_ts':t.signal_ts,'net_pnl_usd':float(t.net_pnl_usd),
            'swing_high':sh_px,'swing_low':sl_px,'swing_high_ts':idx[last_sh],'swing_low_ts':idx[last_sl],
            'range_known_ts':known_ts,'upper_test_candles':upper_tests,'lower_test_candles':lower_tests,
            'total_test_candles':upper_tests+lower_tests,'ambiguous_both_candles':ambiguous_both,
            'side_visits':len(visits),'side_switches':switches,'visit_sequence':'-'.join(visits),
            'true_swing_breakout':bool(true_swing_break),
        })

    d=pd.DataFrame(rows)
    d.to_csv(OUT_CSV,index=False)

    md=['# B27C — 4H Swing High/Low “Tektok” Before Breakout','',
        f'Source coverage: **{coverage:.4%}**. Source trades: frozen B27A 4H R2. No trading rule changed.','',
        'Definition: latest causally-confirmed 3-bar swing high and swing low before the B27A signal candle. A test candle wicks to/through a swing boundary but closes back inside. Consecutive tests of the same side are collapsed into one side visit; `side_switches` counts H→L or L→H changes. The breakout candle itself is excluded from the pre-breakout count.','']

    # How often B27A prior-bar breakout is also a real swing-range breakout.
    md += ['## Does B27A actually break the latest swing range?','',
           '| Partition | B27A 4H R2 trades with swing context | True swing breakout | Share |','|---|---:|---:|---:|']
    for part in ['external','development','reference_validation','august']:
        g=d[d.partition==part]
        n=len(g); n2=int(g.true_swing_breakout.sum()) if n else 0
        md.append(f'| {part} | {n} | {n2} | {fmt_pct(n2/n) if n else "-"} |')

    # Distribution among true swing breakouts.
    e=d[d.true_swing_breakout].copy()
    e['switch_bucket']=pd.cut(e.side_switches, bins=[-1,0,1,2,3,10**9], labels=['0','1','2','3','4+'])
    md += ['','## True swing breakouts: result by pre-breakout side switches','',
           '| Partition | Switches | N | W | L | WR | Net PF | Net exp/trade | Total net | Median test candles | Median side visits |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for part in ['external','development','reference_validation','august']:
        for buck in ['0','1','2','3','4+']:
            g=e[(e.partition==part) & (e.switch_bucket.astype(str)==buck)]
            s=summarize(g)
            med_tests=float(g.total_test_candles.median()) if len(g) else np.nan
            med_vis=float(g.side_visits.median()) if len(g) else np.nan
            md.append(f'| {part} | {buck} | {s["n"]} | {s["w"]} | {s["l"]} | {fmt_pct(s["wr"])} | {fmt_num(s["pf"])} | ${fmt_num(s["exp"])} | ${fmt_num(s["total"])} | {fmt_num(med_tests,1)} | {fmt_num(med_vis,1)} |')

    # Validation raw distribution.
    v=e[e.partition=='reference_validation']
    md += ['','## Validation true swing breakouts: raw tektok distribution','',
           '| Metric | Value |','|---|---:|',
           f'| N | {len(v)} |',
           f'| Median upper-test candles | {fmt_num(v.upper_test_candles.median() if len(v) else np.nan,1)} |',
           f'| Median lower-test candles | {fmt_num(v.lower_test_candles.median() if len(v) else np.nan,1)} |',
           f'| Median total test candles | {fmt_num(v.total_test_candles.median() if len(v) else np.nan,1)} |',
           f'| Median side visits | {fmt_num(v.side_visits.median() if len(v) else np.nan,1)} |',
           f'| Median side switches | {fmt_num(v.side_switches.median() if len(v) else np.nan,1)} |',
           f'| 75th percentile side switches | {fmt_num(v.side_switches.quantile(.75) if len(v) else np.nan,1)} |']

    md += ['','Forensic only. Any apparently good switch-count subgroup is hindsight-discovered and is NOT a validated filter until tested in a new preregistered experiment.','','Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__=='__main__':
    main()
