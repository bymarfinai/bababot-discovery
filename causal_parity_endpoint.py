"""
Causal parity BBC backtest.

This keeps the legacy Mode3 BBC Switcher, state machine, SIDEWAYS behavior,
body ratios, TP/SL and 1H OHLC exit model. The only execution change is that
the old same-hour 15m MTF candidate is not booked retroactively: after the
completed 1H signal, entry is scheduled at the next 15m candle open.
"""

import os
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from mode3_bbc import Mode3BBCConfig, Switcher, Position
from causal_bbc_endpoint import (
    _load_rows, _ema_series, _value_area, _close_trade, _summary,
    CausalPosition, _sync_state_after_exit,
)

router = APIRouter(prefix="/mode3_bbc", tags=["mode3_bbc_parity"])

HOUR_MS = 60 * 60 * 1000
M15_MS = 15 * 60 * 1000


def _causal_mtf_arrays(rows1h, rows15, vah, val, mtf_period=20):
    """Find current-hour MTF triggers, but replace price with next 15m open."""
    n = len(rows1h)
    bull_close = [None] * n
    bull_low = [None] * n
    bear_close = [None] * n
    bear_high = [None] * n
    sw_short_close = [None] * n
    sw_short_high = [None] * n
    sw_long_close = [None] * n
    sw_long_low = [None] * n
    if not rows15:
        return (bull_close, bull_low, bear_close, bear_high,
                sw_short_close, sw_short_high, sw_long_close, sw_long_low)

    closes15 = [float(r[4]) for r in rows15]
    ema15 = _ema_series(closes15, mtf_period)
    idx = {int(r[0]): i for i, r in enumerate(rows15)}

    for i, row in enumerate(rows1h):
        t = int(row[0])
        candidate_bull = None
        candidate_bear = None
        candidate_sw_short = None
        candidate_sw_long = None
        for k in range(4):
            j = idx.get(t + k * M15_MS)
            if j is None:
                continue
            c15 = rows15[j]
            o = float(c15[1])
            h = float(c15[2])
            l = float(c15[3])
            c = float(c15[4])
            if candidate_bull is None and l <= ema15[j] and c > ema15[j] and c > o:
                candidate_bull = c15
            if candidate_bear is None and h >= ema15[j] and c < ema15[j] and c < o:
                candidate_bear = c15
            if vah[i] is not None and candidate_sw_short is None:
                if h >= vah[i] and c <= vah[i]:
                    candidate_sw_short = c15
            if val[i] is not None and candidate_sw_long is None:
                if l <= val[i] and c >= val[i]:
                    candidate_sw_long = c15

        # The first executable bar after the 1H close is the next 15m open.
        next_bar = rows15[idx[t + 4 * M15_MS]] if idx.get(t + 4 * M15_MS) is not None else None
        if next_bar is None:
            continue
        next_open = float(next_bar[1])
        if candidate_bull is not None:
            bull_close[i] = next_open
            bull_low[i] = float(candidate_bull[3])
        if candidate_bear is not None:
            bear_close[i] = next_open
            bear_high[i] = float(candidate_bear[2])
        if candidate_sw_short is not None:
            sw_short_close[i] = next_open
            sw_short_high[i] = float(candidate_sw_short[2])
        if candidate_sw_long is not None:
            sw_long_close[i] = next_open
            sw_long_low[i] = float(candidate_sw_long[3])

    return (
        bull_close, bull_low, bear_close, bear_high,
        sw_short_close, sw_short_high, sw_long_close, sw_long_low,
    )


def _dummy_position(pos: CausalPosition):
    """Keep Switcher in holding mode while external 15m-aware exits are absent."""
    if pos.side == "LONG":
        sl = 0.0
        tp = float("inf")
    else:
        sl = float("inf")
        tp = 0.0
    return Position(
        tool=pos.tool,
        side=pos.side,
        entry_price=pos.entry_price,
        entry_bar=pos.entry_hour,
        entry_high=pos.peak_high,
        entry_low=pos.trough_low,
        sl_level=sl,
        tp_level=tp,
        peak_high=pos.peak_high,
        trough_low=pos.trough_low,
        ema_at_entry=0.0,
        entry_trigger="causal_parity_hold",
        be_triggered=True,
        original_sl=sl,
    )


def _make_external_position(p, next_bar, hour_index):
    return CausalPosition(
        tool=p["tool"],
        side=p["side"],
        entry_price=float(p["entry_price"]),
        sl=float(p["sl"]),
        tp=float(p["tp"]),
        entry_hour=hour_index,
        entry_time=int(next_bar[0]),
        peak_high=float(next_bar[2]),
        trough_low=float(next_bar[3]),
    )


@router.get("/causal-parity-backtest")
def causal_parity_backtest(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    mtf_ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.0, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    sideways_tp_pct: float = Query(0.015, ge=0.0, le=0.10),
    sideways_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    direct_transition_enabled: bool = Query(True),
    enable_sideways_trades: bool = Query(True),
    bull_body_ratio_min: float = Query(0.5, ge=0.0, le=1.0),
    bear_body_ratio_min: float = Query(0.6, ge=0.0, le=1.0),
    sideways_body_ratio_min: float = Query(0.6, ge=0.0, le=1.0),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    fee_pct: float = Query(0.001, ge=0.0, le=0.10),
    slippage_pct: float = Query(0.0005, ge=0.0, le=0.10),
    include_trades: bool = Query(False),
):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ms = now_ms - end_days_ago * 86400 * 1000
    start_ms = end_ms - days * 86400 * 1000
    rows = _load_rows(symbol, timeframe, start_ms, end_ms)
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if len(rows) < va_window + 5:
        return {"error": f"Not enough 1H candles: {len(rows)}", "trades": []}
    if not rows15:
        return {"error": "15m data is required", "trades": []}

    cfg = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        bear_tp_pct=bear_tp_pct,
        bear_sl_pct=bear_sl_pct,
        sideways_tp_pct=sideways_tp_pct,
        sideways_sl_pct=sideways_sl_pct,
        direct_transition_enabled=direct_transition_enabled,
        enable_sideways_trades=enable_sideways_trades,
        bull_mtf_15m_enabled=True,
        bear_mtf_15m_enabled=True,
        sideways_mtf_15m_enabled=True,
        bull_body_ratio_min=bull_body_ratio_min,
        bear_body_ratio_min=bear_body_ratio_min,
        sideways_body_ratio_min=sideways_body_ratio_min,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
    )

    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    vah, val, poc = _value_area(rows, va_window)
    mtf = _causal_mtf_arrays(rows, rows15, vah, val, mtf_ema_period)
    (
        mtf_bull_close, mtf_bull_low, mtf_bear_close, mtf_bear_high,
        mtf_sw_short_close, mtf_sw_short_high,
        mtf_sw_long_close, mtf_sw_long_low,
    ) = mtf

    switcher = Switcher(cfg)
    switcher.mtf_bull_entry_close = mtf_bull_close
    switcher.mtf_bull_entry_low = mtf_bull_low
    switcher.mtf_bear_entry_close = mtf_bear_close
    switcher.mtf_bear_entry_high = mtf_bear_high
    switcher.mtf_sideways_short_entry_close = mtf_sw_short_close
    switcher.mtf_sideways_short_entry_high = mtf_sw_short_high
    switcher.mtf_sideways_long_entry_close = mtf_sw_long_close
    switcher.mtf_sideways_long_entry_low = mtf_sw_long_low

    by_hour = {}
    for row in rows15:
        by_hour.setdefault(int(row[0]) // HOUR_MS, []).append(row)
    for bars in by_hour.values():
        bars.sort(key=lambda r: int(r[0]))

    active: Optional[CausalPosition] = None
    scheduled = {}
    trades = []
    candidate_bull = sum(x is not None for x in mtf_bull_close)
    candidate_bear = sum(x is not None for x in mtf_bear_close)
    candidate_sw = sum(
        x is not None for x in mtf_sw_short_close
    ) + sum(x is not None for x in mtf_sw_long_close)
    blocked_same_hour_exit = 0

    for i, row in enumerate(rows):
        hour_key = int(row[0]) // HOUR_MS
        bars = by_hour.get(hour_key, [])
        if len(bars) < 4:
            continue
        bars = bars[:4]

        # Realize an entry scheduled by the previous completed 1H candle.
        first_time = int(bars[0][0])
        if first_time in scheduled and active is None:
            active = _make_external_position(
                scheduled.pop(first_time), bars[0], i
            )

        # Legacy exit model: evaluate the completed 1H OHLC before processing
        # this 1H signal. The entry itself occurred at the next 15m open.
        exited_this_hour = False
        if active is not None:
            active.peak_high = max(active.peak_high, float(row[2]))
            active.trough_low = min(active.trough_low, float(row[3]))
            if active.side == "LONG":
                if float(row[3]) < active.sl:
                    trades.append(_close_trade(active, active.sl, int(row[0]), "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                    exited_this_hour = True
                elif float(row[2]) >= active.tp:
                    trades.append(_close_trade(active, active.tp, int(row[0]), "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
                    exited_this_hour = True
            else:
                if float(row[2]) > active.sl:
                    trades.append(_close_trade(active, active.sl, int(row[0]), "SL", cfg))
                    _sync_state_after_exit(switcher, active, "SL")
                    active = None
                    exited_this_hour = True
                elif float(row[3]) <= active.tp:
                    trades.append(_close_trade(active, active.tp, int(row[0]), "TP", cfg))
                    _sync_state_after_exit(switcher, active, "TP")
                    active = None
                    exited_this_hour = True

        previous_position = active
        if active is not None:
            switcher.position = _dummy_position(active)
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            switcher.position = None
            continue

        # If a legacy position exited on this same 1H candle, preserve the
        # switcher's no-reentry-on-exit-bar behavior.
        if exited_this_hour and trades:
            blocker = _dummy_position(
                CausalPosition(
                    tool=trades[-1].tool,
                    side=trades[-1].side,
                    entry_price=trades[-1].entry_price,
                    sl=0.0 if trades[-1].side == "LONG" else float("inf"),
                    tp=float("inf") if trades[-1].side == "LONG" else 0.0,
                    entry_hour=i,
                    entry_time=int(row[0]),
                    peak_high=float(row[2]),
                    trough_low=float(row[3]),
                )
            )
            switcher.position = blocker
            switcher.process_candle(
                i, float(row[1]), float(row[2]), float(row[3]),
                float(row[4]), ema1h[i], vah[i], val[i], poc[i]
            )
            switcher.position = None
            blocked_same_hour_exit += 1
            continue

        switcher.process_candle(
            i, float(row[1]), float(row[2]), float(row[3]),
            float(row[4]), ema1h[i], vah[i], val[i], poc[i]
        )
        if switcher.position is not None:
            p = switcher.position
            # The MTF arrays contain the next 15m open for this completed 1H.
            next_key = int(row[0]) + 4 * M15_MS
            next_bars = by_hour.get(next_key // HOUR_MS, [])
            next_bar = next_bars[0] if next_bars and int(next_bars[0][0]) == next_key else None
            if next_bar is not None:
                scheduled[int(next_bar[0])] = {
                    "tool": p.tool,
                    "side": p.side,
                    "entry_price": float(p.entry_price),
                    "sl": float(p.sl_level),
                    "tp": float(p.tp_level),
                }
            switcher.position = None

    if active is not None:
        last = rows[-1]
        trades.append(_close_trade(active, float(last[4]), int(last[0]), "END", cfg))

    summary, per_tool = _summary(trades)
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "end_days_ago": end_days_ago,
        "causal": True,
        "parity": True,
        "legacy_engine": "mode3_bbc.Switcher v2.5",
        "entry_timing": "next_15m_open_after_completed_1h_signal",
        "exit_model": "legacy_1h_ohlc",
        "main_1h_ema_period": ema_period,
        "mtf_15m_ema_period": mtf_ema_period,
        "config": asdict(cfg),
        "mtf_candidate_hours": {
            "bull": candidate_bull,
            "bear": candidate_bear,
            "sideways": candidate_sw,
        },
        "blocked_same_hour_exit": blocked_same_hour_exit,
        "summary": summary,
        "per_tool": per_tool,
    }
    if include_trades:
        result["trades"] = [asdict(t) for t in trades]
    return result


@router.get("/health-parity")
def causal_parity_health():
    return {"status": "ok", "module": "mode3_bbc_parity", "causal": True, "parity": True}


# ══════════════════════════════════════════════════════════════════════════════
# FROZEN-SIGNAL BRIDGE DIAGNOSTIC
# ══════════════════════════════════════════════════════════════════════════════

def _bridge_mtf_candidates(rows1h, rows15, period=20):
    """Return legacy MTF prices plus the first qualifying 15m index per hour."""
    n = len(rows1h)
    bull = [None] * n
    bear = [None] * n
    bull_k = [None] * n
    bear_k = [None] * n
    closes = [float(r[4]) for r in rows15]
    ema15 = _ema_series(closes, period)
    idx = {int(r[0]): j for j, r in enumerate(rows15)}
    for i, row in enumerate(rows1h):
        t = int(row[0])
        for k in range(4):
            j = idx.get(t + k * M15_MS)
            if j is None:
                continue
            r = rows15[j]
            o, h, l, c = map(float, r[1:5])
            if bull[i] is None and l <= ema15[j] and c > ema15[j] and c > o:
                bull[i] = c
                bull_k[i] = k
            if bear[i] is None and h >= ema15[j] and c < ema15[j] and c < o:
                bear[i] = c
                bear_k[i] = k
    return bull, bull_k, bear, bear_k



def _bridge_entry_levels(rows1h, rows15, ema1h, bull_k, bear_k, period=20):
    """Build directional reference prices for the frozen entry schedule."""
    n = len(rows1h)
    closes15 = [float(r[4]) for r in rows15]
    ema15 = _ema_series(closes15, period)
    idx = {int(r[0]): j for j, r in enumerate(rows15)}
    levels = {
        "one_hour_ema": {
            "LONG": [float(x) for x in ema1h],
            "SHORT": [float(x) for x in ema1h],
        },
        "one_hour_low_high": {
            "LONG": [float(r[3]) for r in rows1h],
            "SHORT": [float(r[2]) for r in rows1h],
        },
        "one_hour_close": {
            "LONG": [float(r[4]) for r in rows1h],
            "SHORT": [float(r[4]) for r in rows1h],
        },
        "mtf_ema": {"LONG": [None] * n, "SHORT": [None] * n},
        "mtf_low_high": {"LONG": [None] * n, "SHORT": [None] * n},
    }
    for i, row in enumerate(rows1h):
        t = int(row[0])
        if bull_k[i] is not None:
            j = idx.get(t + bull_k[i] * M15_MS)
            if j is not None:
                levels["mtf_ema"]["LONG"][i] = float(ema15[j])
                levels["mtf_low_high"]["LONG"][i] = float(rows15[j][3])
        if bear_k[i] is not None:
            j = idx.get(t + bear_k[i] * M15_MS)
            if j is not None:
                levels["mtf_ema"]["SHORT"][i] = float(ema15[j])
                levels["mtf_low_high"]["SHORT"][i] = float(rows15[j][2])
    return levels


def _bridge_first_hit(rows, start_idx, side, entry_price, tp_pct, sl_pct):
    """Legacy 1H wick model: SL is checked before TP on each candle."""
    if side == "LONG":
        sl = entry_price * (1.0 - sl_pct)
        tp = entry_price * (1.0 + tp_pct)
    else:
        sl = entry_price * (1.0 + sl_pct)
        tp = entry_price * (1.0 - tp_pct)
    for j in range(max(0, start_idx), len(rows)):
        h = float(rows[j][2])
        l = float(rows[j][3])
        if side == "LONG":
            if l < sl:
                return j, sl, "SL"
            if h >= tp:
                return j, tp, "TP"
        else:
            if h > sl:
                return j, sl, "SL"
            if l <= tp:
                return j, tp, "TP"
    last = float(rows[-1][4])
    return len(rows) - 1, last, "END"


def _bridge_variant(
    legacy_trades, rows, rows15, entry_mode, tp_pct, sl_pct,
    fee_pct, slippage_pct, notional, entry_levels=None,
):
    """Replay the frozen legacy entry ledger with one alternate entry price."""
    by_time = {int(r[0]): r for r in rows15}
    records = []
    for p in legacy_trades:
        b = int(p.entry_bar)
        signal_time = int(rows[b][0])
        filled = True
        if entry_mode == "legacy_candidate_close":
            entry = float(p.entry_price)
        elif entry_mode == "one_hour_close":
            entry = float(rows[b][4])
        elif entry_mode in (
            "one_hour_ema",
            "one_hour_low_high",
            "one_hour_close",
            "mtf_ema",
            "mtf_low_high",
        ):
            if entry_levels is None:
                raise ValueError("entry_levels required for reference-price variant")
            entry = entry_levels[entry_mode][p.side][b]
            if entry is None:
                filled = False
                entry = float(p.entry_price)
        elif entry_mode == "next_15m_limit":
            next_bar = by_time.get(signal_time + HOUR_MS)
            if next_bar is None:
                continue
            limit_price = float(p.entry_price)
            o15, h15, l15 = map(float, next_bar[1:4])
            if p.side == "LONG":
                if l15 > limit_price:
                    filled = False
                    entry = limit_price
                else:
                    entry = o15 if o15 <= limit_price else limit_price
            else:
                if h15 < limit_price:
                    filled = False
                    entry = limit_price
                else:
                    entry = o15 if o15 >= limit_price else limit_price
        elif entry_mode == "next_15m_open" or entry_mode.startswith("blend_"):
            next_bar = by_time.get(signal_time + HOUR_MS)
            if next_bar is None:
                continue
            next_open = float(next_bar[1])
            if entry_mode == "next_15m_open":
                entry = next_open
            else:
                fraction = float(entry_mode.split("_")[1]) / 100.0
                entry = float(p.entry_price) + fraction * (next_open - float(p.entry_price))
        else:
            raise ValueError(f"unknown bridge entry mode: {entry_mode}")
        if not filled:
            continue
        exit_bar, exit_price, exit_type = _bridge_first_hit(
            rows, b + 1, p.side, entry, tp_pct,
            sl_pct,
        )
        if p.side == "LONG":
            raw = (exit_price - entry) / entry
        else:
            raw = (entry - exit_price) / entry
        net = raw - (fee_pct + slippage_pct)
        records.append({
            "legacy_entry_bar": b,
            "side": p.side,
            "tool": p.tool,
            "entry_price": entry,
            "legacy_entry_price": float(p.entry_price),
            "exit_bar": exit_bar,
            "exit_type": exit_type,
            "pnl_pct": net,
            "pnl_usd": net * notional,
            "legacy_exit_type": p.exit_type,
        })
    wins = [r for r in records if r["pnl_usd"] > 0]
    flips = [r for r in records if r["exit_type"] != r["legacy_exit_type"]]
    return {
        "entry_mode": entry_mode,
        "signals": len(legacy_trades),
        "trades": len(records),
        "fill_rate_pct": round(
            100.0 * len(records) / len(legacy_trades), 2
        ) if legacy_trades else 0.0,
        "wins": len(wins),
        "losses": len(records) - len(wins),
        "wr_pct": round(100.0 * len(wins) / len(records), 2) if records else 0.0,
        "pnl_usd": round(sum(r["pnl_usd"] for r in records), 2),
        "exit_type_breakdown": {
            kind: sum(r["exit_type"] == kind for r in records)
            for kind in ("TP", "SL", "END")
            if any(r["exit_type"] == kind for r in records)
        },
        "exit_type_flips_vs_legacy": len(flips),
        "legacy_tp_to_alt_sl": sum(
            r["legacy_exit_type"] == "TP" and r["exit_type"] == "SL"
            for r in records
        ),
        "alt_exit_after_next_frozen_entry": sum(
            i + 1 < len(records)
            and records[i]["exit_bar"] >= records[i + 1]["legacy_entry_bar"]
            for i in range(len(records))
        ),
        "records": records,
    }


@router.get("/bridge-backtest")
def bridge_backtest(
    symbol: str = Query("BTCUSDT"),
    timeframe: str = Query("1h"),
    days: int = Query(971, ge=30, le=2000),
    end_days_ago: int = Query(0, ge=0, le=2000),
    va_window: int = Query(50, ge=20, le=200),
    ema_period: int = Query(7, ge=5, le=100),
    mtf_ema_period: int = Query(20, ge=5, le=100),
    tp_pct: float = Query(0.013, ge=0.001, le=0.10),
    sl_pct: float = Query(0.013, ge=0.0, le=0.10),
    bear_tp_pct: float = Query(0.0, ge=0.0, le=0.10),
    bear_sl_pct: float = Query(0.0, ge=0.0, le=0.10),
    direct_transition_enabled: bool = Query(True),
    enable_sideways_trades: bool = Query(False),
    bull_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    bear_body_ratio_min: float = Query(0.7, ge=0.0, le=1.0),
    entry_usd: float = Query(10.0, gt=0),
    leverage: float = Query(50.0, gt=0),
    fee_pct: float = Query(0.001, ge=0.0, le=0.10),
    slippage_pct: float = Query(0.0005, ge=0.0, le=0.10),
    include_trades: bool = Query(False),
):
    now_ms = int(datetime.utcnow().timestamp() * 1000)
    end_ms = now_ms - end_days_ago * 86400 * 1000
    start_ms = end_ms - days * 86400 * 1000
    rows = _load_rows(symbol, timeframe, start_ms, end_ms)
    rows15 = _load_rows(symbol, "15m", start_ms, end_ms)
    if len(rows) < va_window + 5:
        return {"error": f"Not enough 1H candles: {len(rows)}"}
    if not rows15:
        return {"error": "15m data is required"}

    cfg = Mode3BBCConfig(
        va_window=va_window,
        ema_period=ema_period,
        tp_pct=tp_pct,
        sl_pct=sl_pct,
        bear_tp_pct=bear_tp_pct,
        bear_sl_pct=bear_sl_pct,
        direct_transition_enabled=direct_transition_enabled,
        enable_sideways_trades=enable_sideways_trades,
        bull_mtf_15m_enabled=True,
        bear_mtf_15m_enabled=True,
        sideways_mtf_15m_enabled=True,
        bull_body_ratio_min=bull_body_ratio_min,
        bear_body_ratio_min=bear_body_ratio_min,
        entry_usd=entry_usd,
        leverage=leverage,
        fee_pct_roundtrip=fee_pct,
        slippage_pct=slippage_pct,
    )
    ema1h = _ema_series([float(r[4]) for r in rows], ema_period)
    vah, val, poc = _value_area(rows, va_window)
    bull_mtf, bull_k, bear_mtf, bear_k = _bridge_mtf_candidates(
        rows, rows15, mtf_ema_period
    )
    entry_levels = _bridge_entry_levels(
        rows, rows15, ema1h, bull_k, bear_k, mtf_ema_period
    )
    switcher = Switcher(cfg)
    switcher.mtf_bull_entry_close = bull_mtf
    row15_by_time = {int(r[0]): r for r in rows15}
    switcher.mtf_bull_entry_low = [
        float(row15_by_time[int(rows[i][0]) + (bull_k[i] or 0) * M15_MS][3])
        if bull_k[i] is not None
        and int(rows[i][0]) + (bull_k[i] or 0) * M15_MS in row15_by_time
        else None
        for i in range(len(rows))
    ]
    switcher.mtf_bear_entry_close = bear_mtf
    switcher.mtf_bear_entry_high = [
        float(row15_by_time[int(rows[i][0]) + (bear_k[i] or 0) * M15_MS][2])
        if bear_k[i] is not None
        and int(rows[i][0]) + (bear_k[i] or 0) * M15_MS in row15_by_time
        else None
        for i in range(len(rows))
    ]
    for i, row in enumerate(rows):
        switcher.process_candle(
            i, float(row[1]), float(row[2]), float(row[3]),
            float(row[4]), ema1h[i], vah[i], val[i], poc[i]
        )
    legacy_trades = list(switcher.trades)
    variants = {}
    for mode in (
        "legacy_candidate_close",
        "one_hour_ema",
        "one_hour_low_high",
        "one_hour_close",
        "mtf_ema",
        "mtf_low_high",
        "blend_25",
        "blend_50",
        "blend_75",
        "blend_80",
        "blend_82",
        "blend_85",
        "blend_90",
        "blend_95",
        "next_15m_open",
        "next_15m_limit",
        "one_hour_close",
    ):
        variants[mode] = _bridge_variant(
            legacy_trades, rows, rows15, mode,
            tp_pct if tp_pct > 0 else cfg.tp_pct,
            (sl_pct if sl_pct > 0 else cfg.sl_pct),
            fee_pct, slippage_pct, cfg.notional(), entry_levels,
        )
        if not include_trades:
            variants[mode].pop("records", None)

    deltas = []
    for p in legacy_trades:
        b = int(p.entry_bar)
        signal_time = int(rows[b][0])
        next_bar = {int(r[0]): r for r in rows15}.get(
            signal_time + HOUR_MS
        )
        if next_bar is not None:
            deltas.append((float(next_bar[1]) / float(p.entry_price) - 1.0) * 100.0)
    deltas_sorted = sorted(deltas)
    stats = {}
    if deltas_sorted:
        stats = {
            "count": len(deltas_sorted),
            "mean_pct": round(sum(deltas_sorted) / len(deltas_sorted), 4),
            "median_pct": round(deltas_sorted[len(deltas_sorted) // 2], 4),
            "p10_pct": round(deltas_sorted[int(0.10 * (len(deltas_sorted) - 1))], 4),
            "p90_pct": round(deltas_sorted[int(0.90 * (len(deltas_sorted) - 1))], 4),
            "min_pct": round(deltas_sorted[0], 4),
            "max_pct": round(deltas_sorted[-1], 4),
        }
    return {
        "symbol": symbol,
        "timeframe": timeframe,
        "days": days,
        "frozen_signal_engine": "legacy Switcher v2.5",
        "frozen_entry_count": len(legacy_trades),
        "legacy_summary": {
            "trades": len(legacy_trades),
            "wins": sum(float(p.pnl_usd) > 0 for p in legacy_trades),
            "wr_pct": round(
                100.0 * sum(float(p.pnl_usd) > 0 for p in legacy_trades)
                / len(legacy_trades), 2
            ) if legacy_trades else 0.0,
            "pnl_usd": round(sum(float(p.pnl_usd) for p in legacy_trades), 2),
        },
        "next_open_delta_pct": stats,
        "entry_price_definitions": {
            "one_hour_ema": f"EMA{ema_period} on the signal 1H candle",
            "one_hour_low_high": "1H low for LONG / 1H high for SHORT",
            "one_hour_close": "signal 1H close",
            "mtf_ema": f"EMA{mtf_ema_period} on the first qualifying 15m candidate",
            "mtf_low_high": "candidate 15m low for LONG / 15m high for SHORT",
            "legacy_candidate_close": "first qualifying 15m candidate close",
        },
        "variants": variants,
    }
