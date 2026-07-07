"""
bull_tool.py — v1.4 with proper SL + TP1 at VAH
======================================================
Entry: LONG at EMA20 pullback reject (dari atas)
Exit priorities (v1.4):
1. SL kena (close < wick_low − buffer) → normal SL exit → back SIDEWAYS
2. TP1 hit (high >= vah_target) → partial exit 50%, move SL to BE
3. TP1 hit + SL to BE hit → break even exit
4. Trailing EMA20 (only after TP1 hit) → close < EMA20 → exit remainder
5. Max hold

Config additions:
- sl_buffer_pct: 0.001 (0.1% below wick low)
- tp1_partial_ratio: 0.5 (exit 50% at TP1)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema as compute_ema


class BullExitReason(Enum):
    SL = "sl"
    SL_BE = "sl_breakeven"
    TP1_TP3 = "tp"
    TRAILING_STOP = "trailing_stop"
    LL_BREACH = "ll_breach"
    MAX_HOLD = "max_hold"
    END = "end_of_data"


@dataclass
class BullConfig:
    ema_period: int = 20
    min_pullback_pct: float = 0.015
    require_close_confirm: bool = True
    lookback_recent_high: int = 20


@dataclass
class BullSignal:
    idx: int
    entry_price: float
    ema20_at_entry: float
    recent_high: float
    reason: str = ""


@dataclass
class BullTradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_low: float
    ema20_at_entry: float
    ema20_at_exit: float
    exit_reason: str
    pnl_net: float
    hold_candles: int
    state_signal: str
    tp1_hit: bool = False


def detect_bull_entry_signal(highs, lows, closes, opens, ema20, i, cfg):
    if i < cfg.lookback_recent_high or i >= len(closes):
        return None
    cur_ema = float(ema20[i])
    if cur_ema <= 0:
        return None
    h_i, l_i, c_i, o_i = float(highs[i]), float(lows[i]), float(closes[i]), float(opens[i])
    recent_high = float(np.max(highs[i - cfg.lookback_recent_high:i]))
    if recent_high <= cur_ema:
        return None
    pullback_pct = (recent_high - l_i) / recent_high
    if pullback_pct < cfg.min_pullback_pct:
        return None
    if l_i > cur_ema:
        return None
    if cfg.require_close_confirm and c_i <= cur_ema:
        return None
    if c_i <= o_i:
        return None
    return BullSignal(
        idx=i, entry_price=c_i, ema20_at_entry=cur_ema, recent_high=recent_high,
        reason=f"pullback_reject_ema20 pullback={pullback_pct*100:.2f}%",
    )


def run_bull_trade(
    highs, lows, closes, ema20, signal, entry_idx,
    entry_low_anchor: float,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    # v1.4 additions
    sl_buffer_pct: float = 0.001,        # SL = wick low × (1 - buffer)
    tp1_target: Optional[float] = None,  # e.g., VAH from orchestrator
    tp1_partial_ratio: float = 0.5,
    use_trailing_after_tp1: bool = True,
) -> BullTradeRecord:
    entry_price = signal.entry_price * (1 + slippage_pct)
    notional = position_usd * leverage
    n = len(closes)

    # v1.4: SL below wick low with buffer
    sl_level = entry_low_anchor * (1 - sl_buffer_pct)

    exit_idx = entry_idx
    exit_price = entry_price
    exit_reason = BullExitReason.END
    state_signal = "back_to_sideways"  # v1.4: all exits back to SIDEWAYS
    tp1_hit = False
    moved_to_be = False
    realized_pnl = 0.0
    remaining = 1.0

    for i in range(entry_idx + 1, min(entry_idx + max_hold, n)):
        c = float(closes[i])
        h = float(highs[i])
        cur_ema = float(ema20[i])

        # Priority 1: SL check (close-based confirm)
        if c <= sl_level:
            exit_reason = BullExitReason.SL_BE if moved_to_be else BullExitReason.SL
            exit_price = c
            exit_idx = i
            break

        # Priority 2: TP1 check (partial exit)
        if not tp1_hit and tp1_target is not None:
            if h >= tp1_target:
                tp1_hit = True
                # Partial exit at TP1
                pn = notional * tp1_partial_ratio
                gp = (tp1_target - entry_price) / entry_price
                realized_pnl += gp * pn - fee_pct * pn - slippage_pct * pn
                remaining -= tp1_partial_ratio
                # Move SL to BE
                sl_level = entry_price
                moved_to_be = True

        # Priority 3: Trailing stop (only after TP1 hit)
        if tp1_hit and use_trailing_after_tp1:
            if cur_ema > 0 and c < cur_ema:
                exit_reason = BullExitReason.TRAILING_STOP
                exit_price = c
                exit_idx = i
                break

        # Max hold
        if i - entry_idx >= max_hold - 1:
            exit_reason = BullExitReason.MAX_HOLD
            exit_price = c
            exit_idx = i
            break
    else:
        exit_idx = min(entry_idx + max_hold - 1, n - 1)
        exit_price = float(closes[exit_idx])
        exit_reason = BullExitReason.END

    # PnL for remaining portion
    if remaining > 0:
        gp = (exit_price - entry_price) / entry_price
        pn = notional * remaining
        realized_pnl += gp * pn - fee_pct * pn - slippage_pct * pn
    # Entry fee
    realized_pnl -= fee_pct * notional + slippage_pct * notional

    return BullTradeRecord(
        entry_idx=entry_idx, exit_idx=exit_idx,
        entry_price=entry_price, exit_price=exit_price,
        entry_low=entry_low_anchor,
        ema20_at_entry=signal.ema20_at_entry,
        ema20_at_exit=float(ema20[exit_idx]) if exit_idx < len(ema20) else 0.0,
        exit_reason=exit_reason.value,
        pnl_net=realized_pnl,
        hold_candles=exit_idx - entry_idx,
        state_signal=state_signal,
        tp1_hit=tp1_hit,
    )


def run_bull_backtest(
    highs, lows, closes, opens,
    cfg: Optional[BullConfig] = None,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    warmup: int = 50,
    sl_buffer_pct: float = 0.001,
    tp1_target_pct: float = 0.01,  # standalone: TP1 = 1% above entry
) -> dict:
    cfg = cfg or BullConfig()
    n = len(closes)
    if n < warmup + 50:
        return {"ok": False, "error": f"insufficient candles: {n}"}
    ema20_arr = compute_ema(closes, cfg.ema_period)
    trades: list[BullTradeRecord] = []
    i = warmup
    while i < n - 1:
        sig = detect_bull_entry_signal(highs, lows, closes, opens, ema20_arr, i, cfg)
        if sig is not None:
            tp1_target = sig.entry_price * (1 + tp1_target_pct)
            trade = run_bull_trade(
                highs, lows, closes, ema20_arr, sig, i,
                entry_low_anchor=float(lows[i]),
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
        "ok": True, "tool": "bull_v1.4",
        "config": {
            "ema_period": cfg.ema_period, "min_pullback_pct": cfg.min_pullback_pct,
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
                "entry_low": round(t.entry_low, 2),
                "exit_reason": t.exit_reason,
                "tp1_hit": t.tp1_hit,
                "pnl_net": round(t.pnl_net, 2), "hold": t.hold_candles,
            }
            for t in trades
        ],
    }


__all__ = [
    "BullConfig", "BullSignal", "BullTradeRecord", "BullExitReason",
    "detect_bull_entry_signal", "run_bull_trade", "run_bull_backtest",
]
