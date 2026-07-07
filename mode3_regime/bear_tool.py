"""
bear_tool.py — v1.6: multi-candle rally + EMA20 reject (mirror bull)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema as compute_ema


class BearExitReason(Enum):
    SL = "sl"
    SL_BE = "sl_breakeven"
    TP1_TP3 = "tp"
    TRAILING_STOP = "trailing_stop"
    HH_BREACH = "hh_breach"
    MAX_HOLD = "max_hold"
    END = "end_of_data"


@dataclass
class BearConfig:
    ema_period: int = 20
    min_rally_pct: float = 0.015
    require_close_confirm: bool = True
    lookback_recent_low: int = 20
    trough_min_distance: int = 2  # v1.6: trough must be N candles before current


@dataclass
class BearSignal:
    idx: int
    entry_price: float
    ema20_at_entry: float
    recent_low: float
    reason: str = ""


@dataclass
class BearTradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_high: float
    ema20_at_entry: float
    ema20_at_exit: float
    exit_reason: str
    pnl_net: float
    hold_candles: int
    state_signal: str
    tp1_hit: bool = False


def detect_bear_entry_signal(highs, lows, closes, opens, ema20, i, cfg):
    """
    v1.6: multi-candle rally from trough + EMA20 rally reject
    - Trough must be at least trough_min_distance candles BEFORE current
    - Rally = (highest_since_trough - trough_low) / trough_low
    - Current candle: touch EMA20 from below + close below (reject)
    """
    min_lookback = cfg.lookback_recent_low + cfg.trough_min_distance
    if i < min_lookback or i >= len(closes):
        return None

    cur_ema = float(ema20[i])
    if cur_ema <= 0:
        return None

    trough_end = i - cfg.trough_min_distance
    trough_start = i - cfg.lookback_recent_low
    if trough_end <= trough_start:
        return None

    trough_window = lows[trough_start:trough_end]
    recent_low = float(np.min(trough_window))
    trough_offset = int(np.argmin(trough_window))
    trough_idx = trough_start + trough_offset

    if recent_low >= cur_ema:
        return None

    if trough_idx + 1 > i:
        return None
    highest_since_trough = float(np.max(highs[trough_idx + 1:i + 1]))
    rally_pct = (highest_since_trough - recent_low) / recent_low
    if rally_pct < cfg.min_rally_pct:
        return None

    h_i = float(highs[i])
    l_i = float(lows[i])
    c_i = float(closes[i])
    o_i = float(opens[i])

    if h_i < cur_ema:
        return None
    if cfg.require_close_confirm and c_i >= cur_ema:
        return None
    if c_i >= o_i:
        return None

    return BearSignal(
        idx=i, entry_price=c_i, ema20_at_entry=cur_ema,
        recent_low=recent_low,
        reason=f"trough_at_{i-trough_idx}c_ago rally={rally_pct*100:.2f}%",
    )


def run_bear_trade(
    highs, lows, closes, ema20, signal, entry_idx,
    entry_high_anchor: float,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    sl_buffer_pct: float = 0.001,
    tp1_target: Optional[float] = None,
    tp1_partial_ratio: float = 0.5,
    use_trailing_after_tp1: bool = True,
) -> BearTradeRecord:
    entry_price = signal.entry_price * (1 - slippage_pct)
    notional = position_usd * leverage
    n = len(closes)
    sl_level = entry_high_anchor * (1 + sl_buffer_pct)

    exit_idx = entry_idx
    exit_price = entry_price
    exit_reason = BearExitReason.END
    state_signal = "back_to_sideways"
    tp1_hit = False
    moved_to_be = False
    realized_pnl = 0.0
    remaining = 1.0

    for i in range(entry_idx + 1, min(entry_idx + max_hold, n)):
        c = float(closes[i])
        l = float(lows[i])
        cur_ema = float(ema20[i])

        if c >= sl_level:
            exit_reason = BearExitReason.SL_BE if moved_to_be else BearExitReason.SL
            exit_price = c
            exit_idx = i
            break

        if not tp1_hit and tp1_target is not None:
            if l <= tp1_target:
                tp1_hit = True
                pn = notional * tp1_partial_ratio
                gp = (entry_price - tp1_target) / entry_price
                realized_pnl += gp * pn - fee_pct * pn - slippage_pct * pn
                remaining -= tp1_partial_ratio
                sl_level = entry_price
                moved_to_be = True

        if tp1_hit and use_trailing_after_tp1:
            if cur_ema > 0 and c > cur_ema:
                exit_reason = BearExitReason.TRAILING_STOP
                exit_price = c
                exit_idx = i
                break

        if i - entry_idx >= max_hold - 1:
            exit_reason = BearExitReason.MAX_HOLD
            exit_price = c
            exit_idx = i
            break
    else:
        exit_idx = min(entry_idx + max_hold - 1, n - 1)
        exit_price = float(closes[exit_idx])
        exit_reason = BearExitReason.END

    if remaining > 0:
        gp = (entry_price - exit_price) / entry_price
        pn = notional * remaining
        realized_pnl += gp * pn - fee_pct * pn - slippage_pct * pn
    realized_pnl -= fee_pct * notional + slippage_pct * notional

    return BearTradeRecord(
        entry_idx=entry_idx, exit_idx=exit_idx,
        entry_price=entry_price, exit_price=exit_price,
        entry_high=entry_high_anchor,
        ema20_at_entry=signal.ema20_at_entry,
        ema20_at_exit=float(ema20[exit_idx]) if exit_idx < len(ema20) else 0.0,
        exit_reason=exit_reason.value,
        pnl_net=realized_pnl,
        hold_candles=exit_idx - entry_idx,
        state_signal=state_signal,
        tp1_hit=tp1_hit,
    )


def run_bear_backtest(
    highs, lows, closes, opens,
    cfg: Optional[BearConfig] = None,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    warmup: int = 50,
    sl_buffer_pct: float = 0.001,
    tp1_target_pct: float = 0.01,
) -> dict:
    cfg = cfg or BearConfig()
    n = len(closes)
    if n < warmup + 50:
        return {"ok": False, "error": f"insufficient candles: {n}"}
    ema20_arr = compute_ema(closes, cfg.ema_period)
    trades: list[BearTradeRecord] = []
    i = warmup
    while i < n - 1:
        sig = detect_bear_entry_signal(highs, lows, closes, opens, ema20_arr, i, cfg)
        if sig is not None:
            tp1_target = sig.entry_price * (1 - tp1_target_pct)
            trade = run_bear_trade(
                highs, lows, closes, ema20_arr, sig, i,
                entry_high_anchor=float(highs[i]),
                max_hold=max_hold, fee_pct=fee_pct, slippage_pct=slippage_pct,
                position_usd=position_usd, leverage=leverage,
                sl_buffer_pct=sl_buffer_pct,
                tp1_target=tp1_target,
            )
            trades.append(trade)
            i = trade.exit_idx + 1
        else:
            i += 1
    total = len(trades)
    wins = sum(1 for t in trades if t.pnl_net > 0.01)
    losses = sum(1 for t in trades if t.pnl_net < -0.01)
    pnl_total = sum(t.pnl_net for t in trades)
    wr = wins / max(wins + losses, 1)
    tp1_hits = sum(1 for t in trades if t.tp1_hit)
    return {
        "ok": True, "tool": "bear_v1.6",
        "config": {
            "ema_period": cfg.ema_period, "min_rally_pct": cfg.min_rally_pct,
            "trough_min_distance": cfg.trough_min_distance,
            "sl_buffer_pct": sl_buffer_pct, "tp1_target_pct": tp1_target_pct,
        },
        "stats": {
            "total_trades": total, "wins": wins, "losses": losses,
            "win_rate": round(wr, 4), "total_pnl": round(pnl_total, 2),
            "avg_win": round(np.mean([t.pnl_net for t in trades if t.pnl_net > 0.01]), 2) if wins > 0 else 0.0,
            "avg_loss": round(np.mean([t.pnl_net for t in trades if t.pnl_net < -0.01]), 2) if losses > 0 else 0.0,
            "tp1_hits": tp1_hits,
        },
        "trades": [
            {
                "entry_idx": t.entry_idx, "exit_idx": t.exit_idx,
                "entry_price": round(t.entry_price, 2), "exit_price": round(t.exit_price, 2),
                "entry_high": round(t.entry_high, 2),
                "exit_reason": t.exit_reason,
                "tp1_hit": t.tp1_hit,
                "pnl_net": round(t.pnl_net, 2), "hold": t.hold_candles,
            }
            for t in trades
        ],
    }


__all__ = [
    "BearConfig", "BearSignal", "BearTradeRecord", "BearExitReason",
    "detect_bear_entry_signal", "run_bear_trade", "run_bear_backtest",
]
