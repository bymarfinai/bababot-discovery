#!/usr/bin/env python3
from __future__ import annotations

import math
import sys
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / 'research'
for p in (str(ROOT), str(RESEARCH)):
    if p not in sys.path:
        sys.path.insert(0, p)

import bnb_session_native_london_ny_long_m1_structure_b27em as b27em

TARGET = 'BNBUSDT'
WIB = ZoneInfo('Asia/Jakarta')
UTC = ZoneInfo('UTC')
BAR5 = pd.Timedelta(minutes=5)
COMMON_START = datetime(2022, 1, 2).date()
COMMON_END = datetime(2024, 12, 31).date()
REF_START_HOUR = 1
REF_END_HOUR = 5
EXE_START_HOUR = 5
EXE_END_HOUR = 10
EXPECTED_SESSIONS = 1095
EXPECTED_LEAVES = 167
EXPECTED_H2 = 142
P10 = 0.10
NOTIONAL_USD = 500.0
FEE_RT = 0.0008
SLIPPAGE_BPS = [0, 2, 5, 10]
PFX = 'BNB_CAUSAL_P10_ENTRY_ECONOMICS_B27FR'
OUT_TRADES = ROOT / f'{PFX}_Trades.csv'
OUT_ECON = ROOT / f'{PFX}_Economics.csv'
OUT_YEARLY = ROOT / f'{PFX}_Yearly.csv'
OUT_EXIT = ROOT / f'{PFX}_Exit_Reasons.csv'
OUT_MD = ROOT / f'{PFX}_Result.md'
OUT_STATUS = ROOT / f'{PFX}_Status.txt'


def fs(x: pd.DataFrame, a: pd.Timestamp, z: pd.Timestamp) -> pd.DataFrame:
    i = int(x.index.searchsorted(a, side='left'))
    j = int(x.index.searchsorted(z, side='left'))
    return x.iloc[i:j]


def bounds_for_local_day(day):
    ref_start_local = datetime.combine(day, time(REF_START_HOUR, 0), tzinfo=WIB)
    ref_end_local = datetime.combine(day, time(REF_END_HOUR, 0), tzinfo=WIB)
    exe_start_local = datetime.combine(day, time(EXE_START_HOUR, 0), tzinfo=WIB)
    exe_end_local = datetime.combine(day, time(EXE_END_HOUR, 0), tzinfo=WIB)
    return tuple(pd.Timestamp(v.astimezone(UTC)) for v in (
        ref_start_local, ref_end_local, exe_start_local, exe_end_local
    ))


def build_sessions(x5: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for d in pd.date_range(COMMON_START, COMMON_END, freq='D'):
        day = d.date()
        ref_start, ref_end, exe_start, exe_end = bounds_for_local_day(day)
        ref = fs(x5, ref_start, ref_end)
        exe = fs(x5, exe_start, exe_end)
        if len(ref) != 48 or len(exe) != 60:
            raise AssertionError(
                f'incomplete B27FR session day={day}: ref={len(ref)}/48 exe={len(exe)}/60'
            )
        H = float(ref.high.max())
        L = float(ref.low.min())
        R = H - L
        if not R > 0:
            raise AssertionError(f'nonpositive range day={day}: H={H} L={L}')
        out = b27em.classify_long(exe, H, L)
        rows.append({
            'event_id': str(day),
            'local_date': str(day),
            'year': int(day.year),
            'weekday': day.strftime('%A'),
            'reference_start_utc': ref_start,
            'reference_end_utc': ref_end,
            'execution_start_utc': exe_start,
            'execution_end_utc': exe_end,
            'H': H,
            'L': L,
            'R': R,
            **out,
        })
    return pd.DataFrame(rows)


def max_losing_streak(pnls) -> int:
    best = 0
    cur = 0
    for p in pnls:
        if float(p) < 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def profile(frame: pd.DataFrame, slip_bps: int) -> dict:
    s = float(slip_bps) / 10000.0
    if frame.empty:
        return {
            'slippage_bps_per_side': slip_bps,
            'trade_n': 0,
            'wins': 0,
            'losses': 0,
            'breakeven': 0,
            'wr': np.nan,
            'profit_factor': np.nan,
            'expectancy_usd': np.nan,
            'net_pnl_usd': 0.0,
            'avg_win_usd': np.nan,
            'avg_loss_usd': np.nan,
            'max_loss_streak': 0,
        }

    entry_adj = frame.raw_entry_price.astype(float) * (1.0 + s)
    exit_adj = frame.raw_exit_price.astype(float) * (1.0 - s)
    gross_ret = exit_adj / entry_adj - 1.0
    net_ret = gross_ret - FEE_RT
    pnl = NOTIONAL_USD * net_ret

    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    be = pnl[pnl == 0]
    gp = float(wins.sum())
    gl = float(-losses.sum())
    pf = math.inf if gl == 0 and gp > 0 else (gp / gl if gl > 0 else np.nan)

    return {
        'slippage_bps_per_side': slip_bps,
        'trade_n': int(len(frame)),
        'wins': int(len(wins)),
        'losses': int(len(losses)),
        'breakeven': int(len(be)),
        'wr': float((pnl > 0).mean()),
        'profit_factor': float(pf),
        'expectancy_usd': float(pnl.mean()),
        'net_pnl_usd': float(pnl.sum()),
        'avg_win_usd': float(wins.mean()) if len(wins) else np.nan,
        'avg_loss_usd': float(losses.mean()) if len(losses) else np.nan,
        'max_loss_streak': max_losing_streak(pnl.tolist()),
    }


def yearly_profile(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for year, g in frame.sort_values('entry_time_utc').groupby('year'):
        p = profile(g, 0)
        rows.append({'year': int(year), **p})
    return pd.DataFrame(rows)


def fmt_pct(x, d=1):
    return '-' if pd.isna(x) else f'{100.0 * float(x):.{d}f}%'


def fmt_num(x, d=2):
    if pd.isna(x):
        return '-'
    if math.isinf(float(x)):
        return 'inf'
    return f'{float(x):.{d}f}'


def main():
    prereg = ROOT / f'{PFX}_Preregistration.md'
    if not prereg.exists():
        raise AssertionError('B27FR preregistration missing')

    x5, coverage = b27em.data_base.load5(TARGET)
    if coverage < .995:
        raise AssertionError(f'raw BNB coverage below gate: {coverage:.6%}')

    sessions = build_sessions(x5)
    if len(sessions) != EXPECTED_SESSIONS:
        raise AssertionError(f'session reproduction mismatch: {len(sessions)} != {EXPECTED_SESSIONS}')

    q = sessions[sessions.qualified.fillna(False).astype(bool)]
    leaves = q[q.leave.fillna(False).astype(bool)].copy()
    h2_count = int((leaves.terminal == 'H2_ARRIVAL').sum())
    if len(leaves) != EXPECTED_LEAVES or h2_count != EXPECTED_H2:
        raise AssertionError(
            f'B27FQ reproduction gate failed: leaves/H2={len(leaves)}/{h2_count}, '
            f'expected={EXPECTED_LEAVES}/{EXPECTED_H2}'
        )

    signal_count = 0
    skip_no_first = 0
    skip_not_p10 = 0
    skip_h2_on_signal_bar = 0
    skip_no_entry_bar = 0
    skip_entry_at_or_above_h = 0
    trades = []

    for _, r in leaves.iterrows():
        exe_start = pd.Timestamp(r.execution_start_utc)
        exe_end = pd.Timestamp(r.execution_end_utc)
        exe = fs(x5, exe_start, exe_end)
        leave_ts = pd.Timestamp(r.leave_ts)
        post = fs(x5, leave_ts, exe_end)

        if len(post) == 0 or pd.Timestamp(post.index[0]) != leave_ts:
            skip_no_first += 1
            continue

        first = post.iloc[0]
        first_start = pd.Timestamp(post.index[0])
        H = float(r.H)
        L = float(r.L)
        R = float(r.R)
        p10_level = H - P10 * R

        # Signal must be knowable after the completed first post-leave bar.
        if float(first.high) >= H:
            skip_h2_on_signal_bar += 1
            continue
        first_close = float(first.close)
        if not (p10_level <= first_close < H):
            skip_not_p10 += 1
            continue

        signal_count += 1

        if len(post) < 2:
            skip_no_entry_bar += 1
            continue

        entry_start = pd.Timestamp(post.index[1])
        if entry_start >= exe_end:
            skip_no_entry_bar += 1
            continue
        entry_px = float(post.iloc[1].open)
        if entry_px >= H:
            skip_entry_at_or_above_h += 1
            continue

        # Map entry timestamp into the full execution frame.
        entry_pos = int(exe.index.searchsorted(entry_start, side='left'))
        if entry_pos >= len(exe) or pd.Timestamp(exe.index[entry_pos]) != entry_start:
            raise AssertionError(f'entry timestamp missing from execution frame: {entry_start}')

        exit_reason = None
        raw_exit = None
        exit_time = None
        target_touched = False
        ambiguous_touch = False
        invalidation_signal_start = pd.NaT

        for i in range(entry_pos, len(exe)):
            bar = exe.iloc[i]
            bar_start = pd.Timestamp(exe.index[i])
            hit_h = float(bar.high) >= H
            inv = float(bar.close) < L

            if hit_h and inv:
                target_touched = True
                ambiguous_touch = True
                invalidation_signal_start = bar_start
                exit_reason = 'AMBIGUOUS_TARGET_INVALIDATION'
                if i + 1 < len(exe):
                    raw_exit = float(exe.iloc[i + 1].open)
                    exit_time = pd.Timestamp(exe.index[i + 1])
                else:
                    raw_exit = float(exe.iloc[-1].close)
                    exit_time = pd.Timestamp(exe.index[-1]) + BAR5
                break

            if hit_h:
                target_touched = True
                exit_reason = 'TARGET_H'
                raw_exit = H
                exit_time = bar_start
                break

            if inv:
                invalidation_signal_start = bar_start
                exit_reason = 'CLOSE_BELOW_L_NEXT_OPEN'
                if i + 1 < len(exe):
                    raw_exit = float(exe.iloc[i + 1].open)
                    exit_time = pd.Timestamp(exe.index[i + 1])
                else:
                    raw_exit = float(exe.iloc[-1].close)
                    exit_time = pd.Timestamp(exe.index[-1]) + BAR5
                break

        if exit_reason is None:
            exit_reason = 'SESSION_END_1000'
            raw_exit = float(exe.iloc[-1].close)
            exit_time = pd.Timestamp(exe.index[-1]) + BAR5

        raw_return = float(raw_exit / entry_px - 1.0)
        trades.append({
            'event_id': r.event_id,
            'local_date': r.local_date,
            'year': int(r.year),
            'weekday': r.weekday,
            'H': H,
            'L': L,
            'R': R,
            'P10_level': p10_level,
            'leave_ts': leave_ts,
            'signal_bar_start_utc': first_start,
            'signal_bar_close_utc': first_start + BAR5,
            'signal_first_high': float(first.high),
            'signal_first_close': first_close,
            'signal_close_depth_R': (H - first_close) / R,
            'entry_time_utc': entry_start,
            'raw_entry_price': entry_px,
            'exit_time_utc': exit_time,
            'raw_exit_price': raw_exit,
            'exit_reason': exit_reason,
            'target_touched': target_touched,
            'ambiguous_target_invalidation': ambiguous_touch,
            'invalidation_signal_start_utc': invalidation_signal_start,
            'raw_return_before_fee_slippage': raw_return,
        })

    trades_df = pd.DataFrame(trades)
    if not trades_df.empty:
        trades_df = trades_df.sort_values('entry_time_utc').reset_index(drop=True)
    trades_df.to_csv(OUT_TRADES, index=False)

    econ_rows = [profile(trades_df, bps) for bps in SLIPPAGE_BPS]
    econ = pd.DataFrame(econ_rows)
    econ.to_csv(OUT_ECON, index=False)

    yearly = yearly_profile(trades_df) if not trades_df.empty else pd.DataFrame()
    yearly.to_csv(OUT_YEARLY, index=False)

    if trades_df.empty:
        exits = pd.DataFrame(columns=['exit_reason', 'count', 'share'])
    else:
        exits = (
            trades_df.groupby('exit_reason', dropna=False)
            .size().rename('count').reset_index()
            .sort_values(['count', 'exit_reason'], ascending=[False, True])
        )
        exits['share'] = exits['count'] / len(trades_df)
    exits.to_csv(OUT_EXIT, index=False)

    base = econ[econ.slippage_bps_per_side == 0].iloc[0]
    stress5 = econ[econ.slippage_bps_per_side == 5].iloc[0]

    if (
        int(base.trade_n) >= 20
        and float(base.profit_factor) >= 1.25
        and float(base.expectancy_usd) > 0
        and float(base.net_pnl_usd) > 0
        and float(stress5.profit_factor) > 1.00
        and float(stress5.net_pnl_usd) > 0
    ):
        classification = 'ECONOMIC_EDGE_SUPPORTED'
    elif (
        int(base.trade_n) >= 20
        and float(base.profit_factor) >= 1.25
        and float(base.expectancy_usd) > 0
        and float(base.net_pnl_usd) > 0
    ):
        classification = 'ECONOMIC_EDGE_FRAGILE'
    else:
        classification = 'ECONOMIC_EDGE_NOT_SUPPORTED'

    structural_rate = h2_count / len(leaves)
    target_touch_n = int(trades_df.target_touched.fillna(False).sum()) if len(trades_df) else 0
    target_exit_n = int((trades_df.exit_reason == 'TARGET_H').sum()) if len(trades_df) else 0
    target_touch_rate = target_touch_n / len(trades_df) if len(trades_df) else np.nan
    target_exit_rate = target_exit_n / len(trades_df) if len(trades_df) else np.nan

    lines = [
        '# BNB Causal P10 Entry Economics — B27FR', '',
        f'- Raw loader coverage: {coverage:.4%}',
        f'- Frozen normalized universe: {COMMON_START} through {COMMON_END} inclusive',
        f'- Complete sessions: {len(sessions)}',
        f'- Frozen geometry: reference 01:00–05:00 WIB; execution 05:00–10:00 WIB',
        f'- B27FQ reproduction gate: PASS ({len(leaves)} causal leaves, {h2_count} H2)',
        f'- Structural H2/leave rate: {fmt_pct(structural_rate, 2)} — **not trading WR**',
        '- P10 and geometry were frozen before this runner; no holdout data used', '',
        '## Causal signal and execution funnel', '',
        f'- Causal leaves examined: {len(leaves)}',
        f'- Skipped because H2 already occurred on first post-leave bar: {skip_h2_on_signal_bar}',
        f'- Skipped because completed first close was outside P10 band: {skip_not_p10}',
        f'- Missing first post-leave bar: {skip_no_first}',
        f'- P10 causal signals after completed first post-leave bar: {signal_count}',
        f'- Skipped: no next bar for entry: {skip_no_entry_bar}',
        f'- Skipped: next-open entry >= H: {skip_entry_at_or_above_h}',
        f'- Entered trades: {len(trades_df)}',
        f'- Structural H target touched after entry: {target_touch_n}/{len(trades_df)} = {fmt_pct(target_touch_rate)}',
        f'- Unambiguous TARGET_H exits: {target_exit_n}/{len(trades_df)} = {fmt_pct(target_exit_rate)}', '',
        '## Exit reasons', '',
        '| Exit reason | Count | Share |',
        '|---|---:|---:|',
    ]
    for _, r in exits.iterrows():
        lines.append(f"| {r.exit_reason} | {int(r['count'])} | {fmt_pct(r['share'])} |")

    lines += ['', '## Trading economics', '',
              f'- Notional: ${NOTIONAL_USD:,.0f}/trade',
              '- Fee: 8 bps round trip ($0.40 on $500 before price PnL effects)',
              '- Slippage stress is adverse per side and applied to both entry and exit',
              '- **Trading WR below means net PnL > 0 after fee and stated slippage.**', '',
              '| Slippage/side | N | WR | PF | Expectancy $ | Net $ | Avg win $ | Avg loss $ | Max loss streak |',
              '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for _, r in econ.iterrows():
        lines.append(
            f"| {int(r.slippage_bps_per_side)} bps | {int(r.trade_n)} | {fmt_pct(r.wr)} | "
            f"{fmt_num(r.profit_factor)} | {fmt_num(r.expectancy_usd)} | {fmt_num(r.net_pnl_usd)} | "
            f"{fmt_num(r.avg_win_usd)} | {fmt_num(r.avg_loss_usd)} | {int(r.max_loss_streak)} |"
        )

    lines += ['', '## Yearly stability — fee included, 0 bps slippage', '',
              '| Year | N | WR | PF | Expectancy $ | Net $ | Max loss streak |',
              '|---:|---:|---:|---:|---:|---:|---:|']
    if yearly.empty:
        lines.append('| - | 0 | - | - | - | 0.00 | 0 |')
    else:
        for _, r in yearly.iterrows():
            lines.append(
                f"| {int(r.year)} | {int(r.trade_n)} | {fmt_pct(r.wr)} | {fmt_num(r.profit_factor)} | "
                f"{fmt_num(r.expectancy_usd)} | {fmt_num(r.net_pnl_usd)} | {int(r.max_loss_streak)} |"
            )

    lines += ['', '## Frozen classification', '',
              f'**{classification}**', '',
              'Classification gates were preregistered before the runner was committed.',
              'This is development-sample economics only. It is not independent holdout validation and does not authorize live trading.', '',
              '## Status', '',
              f'`B27FR_BNB_CAUSAL_P10_ENTRY_ECONOMICS_COMPLETE_{classification}`', '']

    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    OUT_STATUS.write_text(
        f'B27FR_BNB_CAUSAL_P10_ENTRY_ECONOMICS_COMPLETE_{classification}\n',
        encoding='utf-8'
    )

    print(f'coverage={coverage:.6%}')
    print(f'sessions={len(sessions)} leaves={len(leaves)} h2={h2_count} structural_rate={structural_rate:.6%}')
    print(f'signals={signal_count} trades={len(trades_df)} target_touches={target_touch_n}')
    for _, r in econ.iterrows():
        print(
            f"slip={int(r.slippage_bps_per_side)}bps N={int(r.trade_n)} WR={r.wr:.6%} "
            f"PF={r.profit_factor:.4f} exp=${r.expectancy_usd:.4f} net=${r.net_pnl_usd:.4f} "
            f"maxLS={int(r.max_loss_streak)}"
        )
    print(f'classification={classification}')


if __name__ == '__main__':
    main()
