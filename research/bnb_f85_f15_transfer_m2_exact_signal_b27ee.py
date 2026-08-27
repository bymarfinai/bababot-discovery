#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import bbc_f85_f15_signals as sig
import eth_f85_f15_transfer_m1_k1_opp0 as data_base
import btc_f85_long_f15_short20_raw_5m_signal_parity_b27dw as dw

PFX = 'BNB_F85_F15_TRANSFER_M2_EXACT_SIGNAL_B27EE'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
CONTROL = 'BTCUSDT'
MAJOR = ('external', 'development', 'reference_validation')
SOURCES = ('ALT_0330', 'RAW_0530', 'LONDON', 'RAW_2330', 'SHORT_2000')


def fs(x, a, z):
    return x.iloc[int(x.index.searchsorted(a)):int(x.index.searchsorted(z))]


def part_for(es):
    for name, (a, z) in data_base.PARTS.items():
        if a <= es < z:
            return name
    return None


def outcome_after_entry(x5, entry_ts, exec_end, side, H, L):
    q = fs(x5, pd.Timestamp(entry_ts), pd.Timestamp(exec_end))
    for ts, r in q.iterrows():
        if side == 'LONG':
            h2 = float(r.high) >= float(H)
            opp = float(r.close) < float(L)
        else:
            h2 = float(r.low) <= float(L)
            opp = float(r.close) > float(H)
        if h2 and opp:
            return 'AMBIGUOUS', pd.Timestamp(ts), np.nan
        if h2:
            mins = float((pd.Timestamp(ts) - pd.Timestamp(entry_ts)) / pd.Timedelta(minutes=1))
            return 'H2', pd.Timestamp(ts), mins
        if opp:
            return 'OPPOSITE_BREAK', pd.Timestamp(ts), np.nan
    return 'NO_H2_BY_END', pd.NaT, np.nan


def replay_symbol(symbol, x5):
    rows = []
    anchors = pd.date_range(x5.index.min().normalize(), x5.index.max().normalize(), freq='D', tz='UTC')
    for a in anchors:
        for source, cm in sig.LONG_ZONE_CLOCKS.items():
            rs = a + pd.Timedelta(minutes=cm)
            re = rs + sig.REF_DUR
            es = re
            ee = es + sig.EXEC_DUR
            p = part_for(es)
            if p is None or es.weekday() >= 5:
                continue
            ref, exe = fs(x5, rs, re), fs(x5, es, ee)
            if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
                continue
            adapter = sig.LongF85Session(source, a, ref)
            emitted = sig.replay_session(adapter, exe)
            for s in emitted:
                out, ots, mins = outcome_after_entry(x5, s.entry_ts, ee, s.side, s.H, s.L)
                rows.append(dict(symbol=symbol, partition=p, side=s.side, source=source,
                                 entry_ts=s.entry_ts, entry_px=s.entry_px,
                                 confirmation_bar_start=s.confirmation_bar_start,
                                 H=s.H, L=s.L, R=s.R, entry_level=s.entry_level,
                                 stop_level=s.stop_level, target_level=s.target_level,
                                 touch_elapsed_min=s.touch_elapsed_min,
                                 outcome=out, outcome_bar_start=ots, minutes_entry_to_h2=mins))

        cm = sig.SHORT20_CLOCK
        rs = a + pd.Timedelta(minutes=cm)
        re = rs + sig.REF_DUR
        es = re
        ee = es + sig.EXEC_DUR
        p = part_for(es)
        if p is None or es.weekday() >= 5:
            continue
        ref, exe = fs(x5, rs, re), fs(x5, es, ee)
        if len(ref) != sig.REF_BARS or len(exe) != sig.EXEC_BARS:
            continue
        adapter = sig.ShortF15Session(a, ref)
        emitted = sig.replay_session(adapter, exe)
        for s in emitted:
            out, ots, mins = outcome_after_entry(x5, s.entry_ts, ee, s.side, s.H, s.L)
            rows.append(dict(symbol=symbol, partition=p, side=s.side, source='SHORT_2000',
                             entry_ts=s.entry_ts, entry_px=s.entry_px,
                             confirmation_bar_start=s.confirmation_bar_start,
                             H=s.H, L=s.L, R=s.R, entry_level=s.entry_level,
                             stop_level=s.stop_level, target_level=s.target_level,
                             touch_elapsed_min=s.touch_elapsed_min,
                             outcome=out, outcome_bar_start=ots, minutes_entry_to_h2=mins))
    return pd.DataFrame(rows)


def metrics(q):
    n = len(q)
    h = int((q.outcome == 'H2').sum()) if n else 0
    o = int((q.outcome == 'OPPOSITE_BREAK').sum()) if n else 0
    a = int((q.outcome == 'AMBIGUOUS').sum()) if n else 0
    no = int((q.outcome == 'NO_H2_BY_END').sum()) if n else 0
    return dict(signals=n, h2=h, opposite=o, ambiguous=a, no_h2=no,
                h2_hit_rate=h/n if n else np.nan,
                resolved_h2_wr=h/(h+o) if h+o else np.nan,
                median_min_entry_to_h2=pd.to_numeric(q.loc[q.outcome=='H2','minutes_entry_to_h2'], errors='coerce').median() if h else np.nan)


def make_summary(detail):
    rows=[]
    for sym in (CONTROL, TARGET):
        for src in SOURCES:
            for p in (*data_base.PARTS.keys(), 'POOLED_MAJOR'):
                q=detail[(detail.symbol==sym)&(detail.source==src)]
                q=q[q.partition.isin(MAJOR)] if p=='POOLED_MAJOR' else q[q.partition==p]
                m=metrics(q); m.update(symbol=sym, source=src, side='SHORT' if src=='SHORT_2000' else 'LONG', partition=p)
                rows.append(m)
    return pd.DataFrame(rows)


def main():
    # Prerequisite lock.
    m1_status=(ROOT/'BNB_F85_F15_TRANSFER_M1_K1_OPP0_B27ED_Status.txt').read_text().strip()
    if m1_status != 'B27ED_BNB_M1_K1_OPP0_STRUCTURAL_REPLICATION_SUPPORTED':
        raise AssertionError(f'B27ED prerequisite not supported: {m1_status}')

    # Frozen adapter contract guards.
    assert sig.LONG_ZONE_CLOCKS == {'ALT_0330':210,'RAW_0530':330,'LONDON':480,'RAW_2330':1410}
    assert sig.SHORT20_CLOCK == 1200
    assert sig.REF_BARS == 66 and sig.EXEC_BARS == 78

    data={}; cov={}
    for sym in (CONTROL, TARGET):
        data[sym], cov[sym] = data_base.load5(sym)
        if cov[sym] < .995:
            raise AssertionError(f'{sym} coverage below gate: {cov[sym]:.6f}')

    # BTC raw adapter control must reproduce the corrected causal signal stream size.
    btc_control, _ = dw.replay_raw(data[CONTROL])
    detail = pd.concat([replay_symbol(CONTROL, data[CONTROL]), replay_symbol(TARGET, data[TARGET])], ignore_index=True)
    btc_detail=detail[detail.symbol==CONTROL]
    if len(btc_detail) != len(btc_control):
        raise AssertionError(f'BTC exact-adapter control count drift: diagnostic={len(btc_detail)} raw={len(btc_control)}')

    detail.to_csv(OUT_DETAIL, index=False)
    s=make_summary(detail)

    gates={}
    gate_reasons={}
    for src in SOURCES:
        bpool=s[(s.symbol==TARGET)&(s.source==src)&(s.partition=='POOLED_MAJOR')].iloc[0]
        cpool=s[(s.symbol==CONTROL)&(s.source==src)&(s.partition=='POOLED_MAJOR')].iloc[0]
        parts=s[(s.symbol==TARGET)&(s.source==src)&(s.partition.isin(MAJOR))]
        checks=[
            int(bpool.signals)>=20,
            bool((parts.signals>=5).all()),
            float(bpool.h2_hit_rate)>=.70,
            bool((parts.h2_hit_rate>=.60).all()),
            float(bpool.resolved_h2_wr)>=.75,
            float(bpool.h2_hit_rate)>=float(cpool.h2_hit_rate)-.10,
        ]
        gates[src]=all(checks)
        gate_reasons[src]=';'.join(['PASS' if x else 'FAIL' for x in checks])

    long_pass=sum(gates[x] for x in SOURCES if x!='SHORT_2000')
    overall=long_pass>=3 and gates['SHORT_2000']
    status='B27EE_BNB_M2_EXACT_SIGNAL_TRANSFER_SUPPORTED' if overall else 'B27EE_BNB_M2_EXACT_SIGNAL_TRANSFER_NOT_SUPPORTED'
    s['gate']=''
    for src,ok in gates.items():
        s.loc[(s.symbol==TARGET)&(s.source==src)&(s.partition=='POOLED_MAJOR'),'gate']='PASS' if ok else 'FAIL'
    s.to_csv(OUT_SUM,index=False)
    OUT_STATUS.write_text(status+'\n')

    lines=['# BNB F85/F15 Transfer — M2 Exact Frozen BTC Signal — B27EE Result','',
           f'Raw 5m coverage: BTC **{cov[CONTROL]:.4%}**, BNB **{cov[TARGET]:.4%}**.','',
           'Exact frozen BTC raw-5m signal adapters were reused unchanged. No BNB-specific tuning, no new clocks, no PnL optimization.','',
           '## Pooled-major exact-signal comparison','',
           '| Source | Side | BNB N | BNB H2 Hit | BNB Resolved H2 WR | BTC N | BTC H2 Hit | Gate |',
           '|---|---|---:|---:|---:|---:|---:|---|']
    for src in SOURCES:
        b=s[(s.symbol==TARGET)&(s.source==src)&(s.partition=='POOLED_MAJOR')].iloc[0]
        c=s[(s.symbol==CONTROL)&(s.source==src)&(s.partition=='POOLED_MAJOR')].iloc[0]
        lines.append(f'| {src} | {b.side} | {int(b.signals)} | {100*b.h2_hit_rate:.1f}% | {100*b.resolved_h2_wr:.1f}% | {int(c.signals)} | {100*c.h2_hit_rate:.1f}% | {"PASS" if gates[src] else "FAIL"} |')
    lines += ['', '## Major-partition BNB diagnostics','',
              '| Source | Partition | N | H2 Hit | Resolved H2 WR |', '|---|---|---:|---:|---:|']
    for src in SOURCES:
        for p in MAJOR:
            r=s[(s.symbol==TARGET)&(s.source==src)&(s.partition==p)].iloc[0]
            lines.append(f'| {src} | {p} | {int(r.signals)} | {100*r.h2_hit_rate:.1f}% | {100*r.resolved_h2_wr:.1f}% |')
    lines += ['',f'LONG habitat gates passed: **{long_pass}/4**.',f'SHORT_2000 gate: **{"PASS" if gates["SHORT_2000"] else "FAIL"}**.','',f'**Status: {status}**','',
              'B27EE stops here. No TP/SL/PnL milestone and no M3 is run automatically.']
    OUT_MD.write_text('\n'.join(lines)+'\n')
    print(OUT_MD.read_text())


if __name__=='__main__':
    main()
