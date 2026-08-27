#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

import eth_f85_f15_transfer_m1_k1_opp0 as base

ROOT = Path(__file__).resolve().parent.parent
PFX = 'BNB_F85_F15_TRANSFER_M1_K1_OPP0_B27ED'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_DETAIL = ROOT / f'{PFX}_Detail.csv'
OUT_SUM = ROOT / f'{PFX}_Summary.csv'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'

TARGET = 'BNBUSDT'
CONTROL = 'BTCUSDT'


def summarize(detail: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sym in (CONTROL, TARGET):
        for clock in base.CLOCKS:
            for p in (*base.PARTS.keys(), 'POOLED_MAJOR'):
                q = detail[(detail.symbol == sym) & (detail.clock == clock)]
                q = q[q.partition.isin(base.MAJOR)] if p == 'POOLED_MAJOR' else q[q.partition == p]
                complete = len(q)
                k = q[q.qualified.fillna(False).astype(bool)]
                lv = k[k.leave.fillna(False).astype(bool)] if len(k) else k
                h = int((lv.terminal == 'H2_ARRIVAL').sum()) if len(lv) else 0
                o = int((lv.terminal == 'OPPOSITE_BREAK_BEFORE_H2').sum()) if len(lv) else 0
                amb = int((lv.terminal == 'AMBIGUOUS_H2_VS_OPPOSITE_BREAK').sum()) if len(lv) else 0
                no = int((lv.terminal == 'NO_H2_BY_END').sum()) if len(lv) else 0
                rows.append({
                    'symbol': sym,
                    'clock': clock,
                    'side': base.SIDE[clock],
                    'partition': p,
                    'sessions': complete,
                    'k1_opp0': len(k),
                    'k1_rate': len(k) / complete if complete else np.nan,
                    'causal_leave': len(lv),
                    'leave_rate': len(lv) / len(k) if len(k) else np.nan,
                    'h2': h,
                    'opposite': o,
                    'ambiguous': amb,
                    'no_h2': no,
                    'h2_rate': h / len(lv) if len(lv) else np.nan,
                    'resolved_h2_wr': h / (h + o) if h + o else np.nan,
                    'median_min_to_h2': pd.to_numeric(
                        lv.loc[lv.terminal == 'H2_ARRIVAL', 'minutes_leave_to_h2'], errors='coerce'
                    ).median() if h else np.nan,
                })
    return pd.DataFrame(rows)


def main():
    # Frozen synthetic causal-state tests from the established ETH transfer M1 lineage.
    base.synth()

    # Guard against accidental clock/partition drift from the frozen transfer engine.
    assert base.CLOCKS == {
        'ALT_0330': 210,
        'RAW_0530': 330,
        'LONDON': 480,
        'RAW_2330': 1410,
        'SHORT_2000': 1200,
    }
    assert base.SIDE == {
        'ALT_0330': 'LONG',
        'RAW_0530': 'LONG',
        'LONDON': 'LONG',
        'RAW_2330': 'LONG',
        'SHORT_2000': 'SHORT',
    }
    assert base.START == pd.Timestamp('2020-01-01', tz='UTC')
    assert base.END == pd.Timestamp('2026-08-26', tz='UTC')

    data = {}
    coverage = {}
    for sym in (CONTROL, TARGET):
        data[sym], coverage[sym] = base.load5(sym)
        if coverage[sym] < 0.995:
            raise AssertionError(f'{sym} coverage below prereg gate: {coverage[sym]:.6f}')

    detail = pd.concat([base.run_symbol(sym, data[sym]) for sym in (CONTROL, TARGET)], ignore_index=True)
    if detail.empty:
        raise AssertionError('no M1 sessions generated')
    detail.to_csv(OUT_DETAIL, index=False)

    s = summarize(detail)
    gates = {}
    for clock in base.CLOCKS:
        bnb = s[(s.symbol == TARGET) & (s.clock == clock) & (s.partition == 'POOLED_MAJOR')].iloc[0]
        btc = s[(s.symbol == CONTROL) & (s.clock == clock) & (s.partition == 'POOLED_MAJOR')].iloc[0]
        ok = (
            bnb.k1_opp0 >= 30
            and bnb.causal_leave >= 25
            and bnb.h2_rate >= 0.60
            and bnb.resolved_h2_wr >= 0.65
            and bnb.h2_rate >= btc.h2_rate - 0.10
        )
        gates[clock] = bool(ok)

    overall = sum(gates[c] for c in ('ALT_0330', 'RAW_0530', 'LONDON', 'RAW_2330')) >= 3 and gates['SHORT_2000']
    status = (
        'B27ED_BNB_M1_K1_OPP0_STRUCTURAL_REPLICATION_SUPPORTED'
        if overall
        else 'B27ED_BNB_M1_K1_OPP0_STRUCTURAL_REPLICATION_NOT_SUPPORTED'
    )

    s['m1_replication'] = ''
    for clock, ok in gates.items():
        s.loc[
            (s.symbol == TARGET) & (s.clock == clock) & (s.partition == 'POOLED_MAJOR'),
            'm1_replication'
        ] = 'PASS' if ok else 'FAIL'
    s.to_csv(OUT_SUM, index=False)
    OUT_STATUS.write_text(status + '\n')

    lines = [
        '# BNB F85/F15 Transfer — M1 K1 OPP0 Structural Replication — B27ED Result',
        '',
        f'Raw 5m coverage: BTC **{coverage[CONTROL]:.4%}**, BNB **{coverage[TARGET]:.4%}**.',
        '',
        'M1 only: no F85/F15, no entry, no stop, no target, no PnL, and no BNB-specific tuning.',
        '',
        '## Pooled-major structural comparison',
        '',
        '| Clock | Side | BNB K1 | BNB Leave | BNB H2 Rate | BNB Resolved H2 WR | BTC H2 Rate | Gate |',
        '|---|---|---:|---:|---:|---:|---:|---|',
    ]
    for clock in base.CLOCKS:
        bnb = s[(s.symbol == TARGET) & (s.clock == clock) & (s.partition == 'POOLED_MAJOR')].iloc[0]
        btc = s[(s.symbol == CONTROL) & (s.clock == clock) & (s.partition == 'POOLED_MAJOR')].iloc[0]
        lines.append(
            f'| {clock} | {bnb.side} | {int(bnb.k1_opp0)} | {int(bnb.causal_leave)} | '
            f'{100 * bnb.h2_rate:.1f}% | {100 * bnb.resolved_h2_wr:.1f}% | '
            f'{100 * btc.h2_rate:.1f}% | {"PASS" if gates[clock] else "FAIL"} |'
        )

    lines += [
        '',
        f'LONG habitat gates passed: **{sum(gates[c] for c in ("ALT_0330", "RAW_0530", "LONDON", "RAW_2330"))}/4**.',
        f'SHORT_2000 gate: **{"PASS" if gates["SHORT_2000"] else "FAIL"}**.',
        '',
        f'**Status: {status}**',
        '',
        'Per preregistration, execution stops here. M2 is not run automatically.',
    ]
    OUT_MD.write_text('\n'.join(lines) + '\n')
    print(OUT_MD.read_text())


if __name__ == '__main__':
    main()
