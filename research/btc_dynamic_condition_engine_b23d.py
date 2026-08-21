#!/usr/bin/env python3
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd

import btc_mtf_bull_cascade_b21 as b21
import btc_strong_uptrend_lifecycle_b22b as b22b

ROOT = Path(__file__).resolve().parent.parent
OUT_MD = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Result.md'
OUT_SUMMARY = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Summary.csv'
OUT_TRADES = ROOT / 'BTC_DYNAMIC_CONDITION_ENGINE_B23D_Trades.csv'

PARTS = b22b.PARTS
ANCHORS = {
    '5m': ('5min', pd.Timedelta(minutes=5), '5min', pd.Timedelta(minutes=5)),
    '15m': ('15min', pd.Timedelta(minutes=15), '5min', pd.Timedelta(minutes=5)),
    '1h': ('1h', pd.Timedelta(hours=1), '15min', pd.Timedelta(minutes=15)),
    '4h': ('4h', pd.Timedelta(hours=4), '1h', pd.Timedelta(hours=1)),
}
MARGIN = 10.0
LEVERAGE = 50.0
NOTIONAL = MARGIN * LEVERAGE
FEE_RT = 0.0008
FEE_USD = NOTIONAL * FEE_RT


def classify(z: pd.DataFrame) -> pd.DataFrame:
    x = z.copy()
    e20_up3 = x.ema20 > x.ema20.shift(3)
    e50_up3 = x.ema50 > x.ema50.shift(3)
    e50_nonneg3 = x.ema50 >= x.ema50.shift(3)
    spread_widen3 = x.spread > x.spread.shift(3)
    spread_narrow1 = x.spread < x.spread.shift(1)
    reversal = (
        (x.close < x.ema50)
        | (x.ema20 < x.ema50)
        | ((x.close < x.ema20) & (x.ema20 < x.ema20.shift(1)) & spread_narrow1)
    ).fillna(False)
    strong = (
        (x.ema20 > x.ema50)
        & e20_up3
        & e50_up3
        & spread_widen3
        & (x.close > x.ema20)
    ).fillna(False)
    healthy = (
        (x.ema20 > x.ema50)
        & e50_nonneg3
        & (x.close >= x.ema50)
        & (~reversal)
        & (~strong)
    ).fillna(False)
    strong_bear = (
        (x.ema20 < x.ema50)
        & (x.ema20 < x.ema20.shift(3))
        & (x.ema50 < x.ema50.shift(3))
        & (x.spread < x.spread.shift(3))
        & (x.close < x.ema20)
    ).fillna(False)
    state = np.select(
        [reversal.to_numpy(bool), strong.to_numpy(bool), healthy.to_numpy(bool)],
        ['REVERSAL', 'STRONG_BULL', 'HEALTHY_BULL'],
        default='TRANSITION',
    )
    x['state'] = state
    x['strong_bear'] = strong_bear
    x['fresh_strong'] = strong & (~strong.shift(1).fillna(False))
    return x


def causal_map(frame: pd.DataFrame, dur: pd.Timedelta, base_close: pd.DatetimeIndex):
    close_idx = frame.index + dur
    s_state = pd.Series(frame.state.to_numpy(object), index=close_idx)
    s_bear = pd.Series(frame.strong_bear.to_numpy(bool), index=close_idx)
    # Reindex only from completed candles; no look-ahead.
    state = s_state.reindex(base_close, method='ffill').to_numpy(object)
    bear = s_bear.reindex(base_close, method='ffill').fillna(False).to_numpy(bool)
    return state, bear


def profit_factor(vals) -> float:
    a = pd.Series(vals, dtype=float)
    pos = float(a[a > 0].sum())
    neg = float(-a[a < 0].sum())
    if neg == 0 and pos > 0:
        return float('inf')
    return pos / neg if neg > 0 else np.nan


def max_losing_streak(vals) -> int:
    best = cur = 0
    for v in vals:
        if v <= 0:
            cur += 1
            best = max(best, cur)
        else:
            cur = 0
    return int(best)


def simulate_anchor(x5: pd.DataFrame, anchor_name: str, anchor_rule: str, anchor_dur: pd.Timedelta,
                    risk_rule: str, risk_dur: pd.Timedelta) -> list[dict]:
    anchor = classify(b22b.enrich(b22b.resample_ohlc(x5, anchor_rule)))
    risk = classify(b22b.enrich(b22b.resample_ohlc(x5, risk_rule)))

    base_idx = x5.index
    base_close = base_idx + pd.Timedelta(minutes=5)
    a_state, _ = causal_map(anchor, anchor_dur, base_close)
    r_state, r_bear = causal_map(risk, risk_dur, base_close)

    opens = x5.open.to_numpy(float)
    highs = x5.high.to_numpy(float)
    lows = x5.low.to_numpy(float)
    closes = x5.close.to_numpy(float)

    onset_close_times = (anchor.index[anchor.fresh_strong.fillna(False)] + anchor_dur)
    rows: list[dict] = []

    for part, (start, end) in PARTS.items():
        lo = int(base_idx.searchsorted(start, side='left'))
        hi = int(base_idx.searchsorted(end, side='left'))
        if hi - lo < 5:
            continue

        eligible_onsets = [t for t in onset_close_times if t >= start and t < end]
        cursor = lo
        for onset_close in eligible_onsets:
            entry_i = int(base_idx.searchsorted(onset_close, side='left'))
            if entry_i < cursor or entry_i >= hi - 1:
                continue
            entry_px = float(opens[entry_i])
            exit_i = None
            exit_reason = None

            # Every completed 5m candle after execution is inspected.
            for j in range(entry_i, hi - 1):
                ast = str(a_state[j]) if a_state[j] is not None else 'NA'
                rst = str(r_state[j]) if r_state[j] is not None else 'NA'
                bear = bool(r_bear[j])
                uret = float(closes[j] / entry_px - 1.0)

                reason = None
                if ast == 'REVERSAL':
                    reason = 'ANCHOR_REVERSAL'
                elif uret <= 0 and bear:
                    reason = 'EMERGENCY_LOSS_CUT'
                elif uret > 0 and ast != 'STRONG_BULL' and (rst == 'REVERSAL' or bear):
                    reason = 'PROFIT_PROTECT'
                elif uret <= 0 and ast != 'STRONG_BULL' and rst == 'REVERSAL':
                    reason = 'TRANSITION_CUT'

                if reason is not None:
                    exit_i = j + 1
                    exit_reason = reason
                    break

            if exit_i is None or exit_i >= hi:
                exit_i = hi - 1
                exit_reason = 'PARTITION_FORCE_CLOSE'
            if exit_i <= entry_i:
                continue

            exit_px = float(opens[exit_i])
            path_hi = float(np.nanmax(highs[entry_i:exit_i]))
            path_lo = float(np.nanmin(lows[entry_i:exit_i]))
            ret = exit_px / entry_px - 1.0
            gross = ret * NOTIONAL
            net = gross - FEE_USD
            rows.append({
                'partition': part,
                'anchor_tf': anchor_name,
                'risk_tf': {'5m':'5m','15m':'5m','1h':'15m','4h':'1h'}[anchor_name],
                'onset_close_ts': onset_close,
                'entry_ts': base_idx[entry_i],
                'exit_ts': base_idx[exit_i],
                'entry_px': entry_px,
                'exit_px': exit_px,
                'return': ret,
                'mfe': path_hi / entry_px - 1.0,
                'mae': path_lo / entry_px - 1.0,
                'hold_5m_bars': int(exit_i - entry_i),
                'gross_pnl_usd': gross,
                'fee_sensitive_pnl_usd': net,
                'exit_reason': exit_reason,
            })
            cursor = exit_i
    return rows


def metrics(g: pd.DataFrame) -> dict:
    if g.empty:
        return {'n': 0}
    r = g['return'].astype(float)
    losers = r[r <= 0]
    winners = r[r > 0]
    mae = g.mae.astype(float)
    gross = g.gross_pnl_usd.astype(float)
    net = g.fee_sensitive_pnl_usd.astype(float)
    d = {
        'n': int(len(g)),
        'wr': float((r > 0).mean()),
        'pf': float(profit_factor(r)),
        'mean_ret': float(r.mean()),
        'median_ret': float(r.median()),
        'median_winner_ret': float(winners.median()) if len(winners) else np.nan,
        'median_loser_ret': float(losers.median()) if len(losers) else np.nan,
        'median_mfe': float(g.mfe.median()),
        'median_mae': float(mae.median()),
        'p10_mae': float(mae.quantile(.10)),
        'mean_gross_usd': float(gross.mean()),
        'mean_fee_sensitive_usd': float(net.mean()),
        'fee_sensitive_wr': float((net > 0).mean()),
        'fee_sensitive_pf': float(profit_factor(net)),
        'median_hold_5m_bars': float(g.hold_5m_bars.median()),
        'max_losing_streak': max_losing_streak(r),
        'mae_le_0p5': float((mae <= -.005).mean()),
        'mae_le_1p0': float((mae <= -.010).mean()),
        'mae_le_1p5': float((mae <= -.015).mean()),
        'mae_le_1p8': float((mae <= -.018).mean()),
    }
    counts = g.exit_reason.value_counts(normalize=True)
    for reason in ['ANCHOR_REVERSAL','EMERGENCY_LOSS_CUT','PROFIT_PROTECT','TRANSITION_CUT','PARTITION_FORCE_CLOSE']:
        d[f'exit_{reason.lower()}'] = float(counts.get(reason, 0.0))
    return d


def pct(v):
    return '-' if pd.isna(v) else f'{100*float(v):.2f}%'


def num(v, d=2):
    if pd.isna(v): return '-'
    if math.isinf(float(v)): return 'inf'
    return f'{float(v):.{d}f}'


def main():
    x5, coverage = b21.load5()
    all_rows = []
    for name, (arule, adur, rrule, rdur) in ANCHORS.items():
        all_rows.extend(simulate_anchor(x5, name, arule, adur, rrule, rdur))
    trades = pd.DataFrame(all_rows)
    trades.to_csv(OUT_TRADES, index=False)

    sums = []
    for key, g in trades.groupby(['partition','anchor_tf','risk_tf']):
        sums.append(dict(zip(['partition','anchor_tf','risk_tf'], key)) | metrics(g))
    s = pd.DataFrame(sums)
    s.to_csv(OUT_SUMMARY, index=False)

    md = [
        '# BTC Dynamic Condition Engine B23D — Result', '',
        f'5m source rows: **{len(x5):,}**; coverage: **{coverage:.4%}**', '',
        f'Position model: **${MARGIN:.0f} margin × {LEVERAGE:.0f}x = ${NOTIONAL:.0f} notional**. Fee sensitivity subtracts an illustrative **{FEE_RT:.2%} round trip = ${FEE_USD:.2f}/trade**.', '',
        'Entry is immediate at the first executable 5m open after a fresh image-like STRONG_BULL onset. No 1-bar/2-bar confirmation delay. Management is condition-based and inspected every 5m.', '',
        '| Partition | Anchor→Risk | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | Fee mean $ | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med hold min |',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|'
    ]
    order_tf = {'5m':0,'15m':1,'1h':2,'4h':3}
    s['ord'] = s.anchor_tf.map(order_tf)
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        md.append(
            f'| {r.partition} | {r.anchor_tf}→{r.risk_tf} | {r.n} | {pct(r.wr)} | {num(r.pf)} | {pct(r.mean_ret)} | {pct(r.median_winner_ret)} | {pct(r.median_loser_ret)} | {pct(r.median_mfe)} | {pct(r.median_mae)} | {pct(r.p10_mae)} | ${num(r.mean_gross_usd)} | {pct(r.fee_sensitive_wr)} | {num(r.fee_sensitive_pf)} | ${num(r.mean_fee_sensitive_usd)} | {pct(r.mae_le_0p5)} | {pct(r.mae_le_1p0)} | {pct(r.mae_le_1p5)} | {pct(r.mae_le_1p8)} | {num(r.median_hold_5m_bars*5,1)} |'
        )

    md += ['', '## Exit-reason mix', '',
           '| Partition | Anchor | Anchor reversal | Emergency loss cut | Profit protect | Transition cut | Forced close |',
           '|---|---|---:|---:|---:|---:|---:|']
    for r in s.sort_values(['partition','ord']).itertuples(index=False):
        md.append(f'| {r.partition} | {r.anchor_tf} | {pct(r.exit_anchor_reversal)} | {pct(r.exit_emergency_loss_cut)} | {pct(r.exit_profit_protect)} | {pct(r.exit_transition_cut)} | {pct(r.exit_partition_force_close)} |')

    md += ['', '## Frozen precision gates', '']
    for tf in ['5m','15m','1h','4h']:
        checks=[]; high=[]
        nmin={'5m':30,'15m':30,'1h':20,'4h':10}[tf]
        for part in ['external','reference_validation']:
            q=s[(s.partition==part)&(s.anchor_tf==tf)]
            if q.empty:
                checks.append(False); high.append(False); continue
            r=q.iloc[0]
            base=(int(r.n)>=nmin and float(r.wr)>=.80 and float(r.pf)>=1.20 and float(r.median_loser_ret)>-.003 and float(r.mae_le_1p5)<.05)
            checks.append(bool(base)); high.append(bool(base and float(r.wr)>=.90))
        md.append(f'- {tf}: HIGH_PRECISION_CLUE={"PASS" if all(checks) else "FAIL"}; 90PCT_WR_CLAIM={"PASS" if all(high) else "FAIL"}')

    md += ['', 'Important: a 50x position can be operationally unsafe before a candle-close condition fires. The <=-1.5% and <=-1.8% MAE columns are shown specifically to expose that risk; they are not exchange liquidation calculations.', '', 'Research only; live BBC unchanged.']
    OUT_MD.write_text('\n'.join(md)+'\n')

if __name__ == '__main__':
    main()
