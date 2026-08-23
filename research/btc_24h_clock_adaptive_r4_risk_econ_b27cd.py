#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_MAE_MFE_B27CC_Detail.csv'
OUT_MD = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_R4_RISK_ECON_B27CD_Result.md'
OUT_TRADES = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_R4_RISK_ECON_B27CD_Trades.csv'
OUT_STOPS = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_R4_RISK_ECON_B27CD_Stops.csv'
OUT_STATUS = ROOT / 'BTC_24H_CLOCK_ADAPTIVE_R4_RISK_ECON_B27CD_Status.txt'

BAR5 = pd.Timedelta(minutes=5)
MAJOR = ('external','development','reference_validation')
OOS = ('external','reference_validation')
CLOCKS = ('00-04','04-08','08-12','12-16','16-20','20-00')
FROZEN_ENTRY = {'00-04':.05,'04-08':.05,'08-12':.10,'12-16':.05,'16-20':.05,'20-00':.05}
NOTIONAL = 500.0
FEE = 0.40


def as_bool(s: pd.Series) -> pd.Series:
    return s if s.dtype == bool else s.astype(str).str.lower().eq('true')


def fast_slice(x5: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    a = int(x5.index.searchsorted(start, side='left'))
    b = int(x5.index.searchsorted(end, side='left'))
    return x5.iloc[a:b]


def load_entries() -> pd.DataFrame:
    d = pd.read_csv(SRC)
    d['structural_winner'] = as_bool(d.structural_winner)
    for col in ('obs_start','obs_end','fill_ts'):
        d[col] = pd.to_datetime(d[col], utc=True, errors='coerce')
    d = d[d.partition.isin(MAJOR)].copy()
    expected = {'external':250,'development':380,'reference_validation':177}
    assert len(d) == 807, len(d)
    for p,n in expected.items():
        assert len(d[d.partition == p]) == n, (p, len(d[d.partition == p]), n)
    assert d.obs_start.notna().all() and d.obs_end.notna().all() and d.fill_ts.notna().all()
    assert not d.duplicated(['partition','obs_start']).any()
    for cb,f in FROZEN_ENTRY.items():
        q = d[d.clock_block == cb]
        assert len(q) > 0
        assert np.allclose(q.fraction.astype(float), f)
    return d.sort_values(['partition','obs_start']).reset_index(drop=True)


def derive_stops(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for cb in CLOCKS:
        g = d[(d.partition == 'development') & (d.clock_block == cb) & d.structural_winner & d.mae_r4.notna()].copy()
        assert len(g) >= 20, (cb, len(g))
        p75 = float(g.mae_r4.astype(float).quantile(.75))
        rounded = math.ceil((p75 - 1e-12) / .05) * .05
        rounded = round(rounded, 10)
        assert rounded >= p75 - 1e-12 and rounded > 0
        rows.append({'clock_block':cb,'entry_fraction':FROZEN_ENTRY[cb],
                     'development_winner_n':len(g),'development_mae_r4_p75':p75,
                     'frozen_stop_r4_fraction':rounded,'frozen_target_r4_fraction':rounded,
                     'nominal_rr':1.0})
    s = pd.DataFrame(rows)
    assert list(s.clock_block) == list(CLOCKS)
    return s


def eval_trade(x5: pd.DataFrame, r, stop_frac: float) -> dict:
    start = pd.Timestamp(r.obs_start); end = pd.Timestamp(r.obs_end); fill = pd.Timestamp(r.fill_ts)
    entry = float(r.entry_price); H = float(r.H); L = float(r.L); R4 = float(r.R4)
    assert R4 > 0 and start <= fill < end
    dist = stop_frac * R4
    stop = entry + dist
    target = entry - dist
    assert stop > entry > target

    q = fast_slice(x5, start, end)
    assert len(q) == 48 and q.index[0] == start and q.index[-1] == end - BAR5
    idx = int(q.index.searchsorted(fill, side='left'))
    assert idx < len(q) and q.index[idx] == fill
    fb = q.iloc[idx]
    assert float(fb.low) <= entry <= float(fb.high)

    reason = None; exit_ts = None; exit_px = None
    # Conservative fill-bar ambiguity: STOP can count, TP cannot be credited.
    if float(fb.high) >= stop:
        reason = 'STOP_FILL_BAR'; exit_ts = fill; exit_px = stop
    else:
        for i in range(idx + 1, len(q)):
            b = q.iloc[i]; ts = q.index[i]
            hs = float(b.high) >= stop
            ht = float(b.low) <= target
            if hs and ht:
                reason = 'STOP_SAME_BAR_BOTH'; exit_ts = ts; exit_px = stop; break
            if hs:
                reason = 'STOP'; exit_ts = ts; exit_px = stop; break
            if ht:
                reason = 'TP'; exit_ts = ts; exit_px = target; break
    if reason is None:
        reason = 'TIME'; exit_ts = end; exit_px = float(q.iloc[-1].close)

    gross_return = (entry - float(exit_px)) / entry
    net = gross_return * NOTIONAL - FEE
    return {
        'partition':str(r.partition),'regime':str(r.regime),'clock_block':str(r.clock_block),
        'obs_start':start,'obs_end':end,'fill_ts':fill,'entry_fraction':float(r.fraction),
        'entry_price':entry,'H':H,'L':L,'R4':R4,
        'stop_r4_fraction':stop_frac,'target_r4_fraction':stop_frac,'nominal_rr':1.0,
        'stop_price':stop,'target_price':target,'exit_ts':exit_ts,'exit_price':float(exit_px),
        'exit_reason':reason,'gross_return':gross_return,'net_pnl_usd':net,'win':bool(net > 0),
        'structural_winner':bool(r.structural_winner),
    }


def metrics(g: pd.DataFrame) -> dict:
    n = len(g)
    if n == 0:
        return {'n':0,'wr':np.nan,'pf':np.nan,'expectancy':np.nan,'total_net':0.0,'tp':0,'stop':0,'time':0}
    pnl = g.net_pnl_usd.astype(float)
    gp = float(pnl[pnl > 0].sum()); gl = float(-pnl[pnl < 0].sum())
    pf = math.inf if gl == 0 and gp > 0 else (gp / gl if gl > 0 else np.nan)
    return {'n':int(n),'wr':float((pnl > 0).mean()),'pf':pf,'expectancy':float(pnl.mean()),
            'total_net':float(pnl.sum()),'tp':int((g.exit_reason == 'TP').sum()),
            'stop':int(g.exit_reason.astype(str).str.startswith('STOP').sum()),
            'time':int((g.exit_reason == 'TIME').sum())}


def pct(v): return '-' if pd.isna(v) else f'{100*float(v):.1f}%'
def num(v):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.2f}'
def money(v): return '-' if pd.isna(v) else f'${float(v):+.2f}'


def main():
    d = load_entries()
    stops = derive_stops(d)
    stops.to_csv(OUT_STOPS,index=False)
    stop_map = {str(r.clock_block):float(r.frozen_stop_r4_fraction) for r in stops.itertuples(index=False)}

    x5,cov = b21.load5()
    assert len(x5) == 698112 and abs(float(cov)-1.0) < 1e-12
    trades = pd.DataFrame([eval_trade(x5,r,stop_map[str(r.clock_block)]) for r in d.itertuples(index=False)])
    assert len(trades) == 807 and int(trades.partition.isin(OOS).sum()) == 427
    trades.to_csv(OUT_TRADES,index=False)

    part = {p:metrics(trades[trades.partition == p]) for p in MAJOR}
    po = metrics(trades[trades.partition.isin(OOS)])
    pm = metrics(trades)
    n_ok = part['external']['n'] >= 100 and part['development']['n'] >= 150 and part['reference_validation']['n'] >= 60
    exp_ok = all(part[p]['expectancy'] > 0 for p in MAJOR)
    pf_ok = all(part[p]['pf'] >= 1.20 for p in MAJOR)
    wr_ok = all(part[p]['wr'] >= .50 for p in MAJOR)
    oos_ok = po['expectancy'] > 0 and po['pf'] >= 1.20
    supported = bool(n_ok and exp_ok and pf_ok and wr_ok and oos_ok)
    high70 = bool(supported and all(part[p]['wr'] >= .70 for p in MAJOR))
    verdict = 'B27CD_R4_RISK_ECON_SUPPORTED' if supported else 'B27CD_R4_RISK_ECON_NOT_SUPPORTED'
    OUT_STATUS.write_text(verdict + ('__HIGH_QUALITY_70' if high70 else '') + '\n')

    lines = ['# B27CD — BTC 24H Clock-Adaptive R4-Risk SHORT Economics — Result','',
             f'5m rows: **{len(x5):,}**; coverage **{100*float(cov):.4f}%**.','',
             '**Audit status: PASS.** Exact B27CC/B27CA adaptive filled-entry identity reproduced: external 250 / development 380 / validation 177. One anatomy-derived 1:1 rule only; no stop/target sweep.','',
             f'Illustrative economics: **${NOTIONAL:.0f} notional/trade, ${FEE:.2f} round-trip fee, no extra slippage**. Same-bar ambiguity is conservative: STOP wins; fill-bar TP is not credited.','',
             '## Development-only frozen R4 stops','',
             '| UTC block | Entry | Dev winner N | Dev MAE P75 %R4 | Frozen stop | Target | RR |',
             '|---|---|---:|---:|---:|---:|---:|']
    for r in stops.itertuples(index=False):
        lines.append(f'| {r.clock_block} | F{int(round(r.entry_fraction*100)):02d} | {int(r.development_winner_n)} | {pct(r.development_mae_r4_p75)} | {pct(r.frozen_stop_r4_fraction)} R4 | {pct(r.frozen_target_r4_fraction)} R4 | 1.00 |')

    lines += ['', '## Major partitions','',
              '| Partition | N | WR | PF | Exp/trade | Total net | TP | STOP | TIME |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for p in MAJOR:
        m=part[p]; lines.append(f'| {p} | {m["n"]} | {pct(m["wr"])} | {num(m["pf"])} | {money(m["expectancy"])} | {money(m["total_net"])} | {m["tp"]} | {m["stop"]} | {m["time"]} |')
    lines += ['', '## Pooled','',
              '| Scope | N | WR | PF | Exp/trade | Total net |',
              '|---|---:|---:|---:|---:|---:|',
              f'| POOLED_OOS | {po["n"]} | {pct(po["wr"])} | {num(po["pf"])} | {money(po["expectancy"])} | {money(po["total_net"])} |',
              f'| POOLED_MAJOR | {pm["n"]} | {pct(pm["wr"])} | {num(pm["pf"])} | {money(pm["expectancy"])} | {money(pm["total_net"])} |',
              '', '## Clock diagnostics','',
              '| UTC block | Stop %R4 | OOS N | OOS WR | OOS PF | OOS Exp | OOS Net | Major N | Major WR | Major PF |',
              '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for cb in CLOCKS:
        o=metrics(trades[(trades.clock_block==cb)&trades.partition.isin(OOS)])
        m=metrics(trades[trades.clock_block==cb])
        lines.append(f'| {cb} | {pct(stop_map[cb])} | {o["n"]} | {pct(o["wr"])} | {num(o["pf"])} | {money(o["expectancy"])} | {money(o["total_net"])} | {m["n"]} | {pct(m["wr"])} | {num(m["pf"])} |')

    lines += ['', '## Frozen gate','',
              f'- N gate: **{"PASS" if n_ok else "FAIL"}**.',
              f'- Positive expectancy in all major partitions: **{"PASS" if exp_ok else "FAIL"}**.',
              f'- PF >=1.20 in all major partitions: **{"PASS" if pf_ok else "FAIL"}**.',
              f'- WR >=50% in all major partitions: **{"PASS" if wr_ok else "FAIL"}**.',
              f'- Pooled-OOS PF >=1.20 and expectancy >0: **{"PASS" if oos_ok else "FAIL"}**.',
              f'- HIGH_QUALITY_70: **{"PASS" if high70 else "FAIL"}**.',
              '', f'**Frozen verdict: `{verdict}`.**','',
              'Research only. No live BBC change. No failed clock may be removed post hoc inside B27CD.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print('\n'.join(lines))

if __name__ == '__main__':
    main()
