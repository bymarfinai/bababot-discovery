"""
bull_tool.py — v1.0 BULL market tool
======================================================
Entry: LONG at EMA20 pullback reject (dari atas)
- Bot must be in BULL state (confirmed HH breach earlier)
- Wait for price pullback to EMA20 from above
- Candle touches EMA20 and closes BACK ABOVE = reject → LONG entry

Exit: Trailing stop EMA20 (close-based)
- If candle close < EMA20 → full exit
- No fixed TP tiers, ride the trend

State exit triggers:
- LL breach: candle close breaks entry_low → force exit + signal BULL→BEAR
- Trailing stop: normal exit → signal BULL→SIDEWAYS

Config:
- ema_period: 20 (1h default, fallback 4h if noisy)
- min_pullback_pct: 0.005 (0.5% minimum pullback before valid entry)
- confirmation_candles: 1 (single candle close-confirm)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema as compute_ema


class BullExitReason(Enum):
    TRAILING_STOP = "trailing_stop"     # close < EMA20
    LL_BREACH = "ll_breach"             # force exit → BEAR switch
    END = "end_of_data"


class BullStateSignal(Enum):
    NONE = "none"
    STAY_BULL = "stay_bull"             # trailing exit, no LL breach
    SWITCH_BEAR = "switch_bear"         # LL breach detected


@dataclass
class BullConfig:
    ema_period: int = 20
    min_pullback_pct: float = 0.005      # min 0.5% pullback from recent high
    require_close_confirm: bool = True   # close above EMA required
    lookback_recent_high: int = 20       # window for detecting pullback


@dataclass
class BullSignal:
    idx: int
    entry_price: float
    ema20_at_entry: float
    recent_high: float                   # tracked for pullback validation
    reason: str = ""


@dataclass
class BullTradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_low: float                     # anchor for LL detection
    ema20_at_entry: float
    ema20_at_exit: float
    exit_reason: str
    pnl_net: float
    hold_candles: int
    state_signal: str                    # STAY_BULL or SWITCH_BEAR


def detect_bull_entry_signal(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    opens: np.ndarray,
    ema20: np.ndarray,
    i: int,
    cfg: BullConfig,
) -> Optional[BullSignal]:
    """
    Detect BULL entry signal at candle i:
    1. Price was above EMA20 recently (uptrend context)
    2. Current candle low <= EMA20 (pullback touched EMA)
    3. Current candle close > EMA20 (rejected back up)
    4. Minimum pullback met (from recent high)
    """
    if i < cfg.lookback_recent_high or i >= len(closes):
        return None

    cur_ema = float(ema20[i])
    if cur_ema <= 0:
        return None

    h_i = float(highs[i])
    l_i = float(lows[i])
    c_i = float(closes[i])
    o_i = float(opens[i])

    # Recent high in lookback window
    recent_high = float(np.max(highs[i - cfg.lookback_recent_high:i]))

    # Condition 1: recent high must be above EMA20 (context = uptrend)
    if recent_high <= cur_ema:
        return None

    # Condition 2: minimum pullback from recent high
    pullback_pct = (recent_high - l_i) / recent_high
    if pullback_pct < cfg.min_pullback_pct:
        return None

    # Condition 3: current candle touched EMA20 from above (low <= ema)
    if l_i > cur_ema:
        return None

    # Condition 4: current candle rejected back up (close > EMA20)
    if cfg.require_close_confirm:
        if c_i <= cur_ema:
            return None
    # Additional bullish candle check
    if c_i <= o_i:  # must be bullish candle (close > open)
        return None

    return BullSignal(
        idx=i,
        entry_price=c_i,
        ema20_at_entry=cur_ema,
        recent_high=recent_high,
        reason=f"pullback_reject_ema20 pullback={pullback_pct*100:.2f}%",
    )


def run_bull_trade(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    ema20: np.ndarray,
    signal: BullSignal,
    entry_idx: int,
    entry_low_anchor: float,   # from signal candle low, used for LL breach detection
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
) -> BullTradeRecord:
    """
    Manage BULL LONG position from entry until exit.
    Exit conditions:
    1. Close < EMA20 → trailing_stop → STAY_BULL signal
    2. Close < entry_low_anchor → ll_breach → SWITCH_BEAR signal (priority)
    """
    entry_price = signal.entry_price * (1 + slippage_pct)
    notional = position_usd * leverage
    n = len(closes)

    exit_idx = entry_idx
    exit_price = entry_price
    exit_reason = BullExitReason.END
    state_signal = BullStateSignal.STAY_BULL

    for i in range(entry_idx + 1, min(entry_idx + max_hold, n)):
        c = float(closes[i])
        cur_ema = float(ema20[i])

        # Priority 1: LL breach check (force exit + switch BEAR)
        if c < entry_low_anchor:
            exit_idx = i
            exit_price = c
            exit_reason = BullExitReason.LL_BREACH
            state_signal = BullStateSignal.SWITCH_BEAR
            break

        # Priority 2: trailing stop (close < EMA20)
        if cur_ema > 0 and c < cur_ema:
            exit_idx = i
            exit_price = c
            exit_reason = BullExitReason.TRAILING_STOP
            state_signal = BullStateSignal.STAY_BULL
            break

    # If loop ended without break, exit at end
    if exit_reason == BullExitReason.END:
        exit_idx = min(entry_idx + max_hold - 1, n - 1)
        exit_price = float(closes[exit_idx])

    # PnL calc
    gross_pct = (exit_price - entry_price) / entry_price
    gross_pnl = gross_pct * notional
    fee = fee_pct * notional * 2  # entry + exit
    slip = slippage_pct * notional  # entry slippage (exit slippage embedded)
    pnl_net = gross_pnl - fee - slip

    return BullTradeRecord(
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        entry_price=entry_price,
        exit_price=exit_price,
        entry_low=entry_low_anchor,
        ema20_at_entry=signal.ema20_at_entry,
        ema20_at_exit=float(ema20[exit_idx]) if exit_idx < len(ema20) else 0.0,
        exit_reason=exit_reason.value,
        pnl_net=pnl_net,
        hold_candles=exit_idx - entry_idx,
        state_signal=state_signal.value,
    )


def run_bull_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    opens: np.ndarray,
    cfg: Optional[BullConfig] = None,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    warmup: int = 50,
) -> dict:
    """
    Standalone BULL backtest — assumes we're in BULL state throughout.
    Real orchestrator would only invoke this while state=BULL.
    """
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
            trade = run_bull_trade(
                highs, lows, closes, ema20_arr, sig, i,
                entry_low_anchor=float(lows[i]),
                max_hold=max_hold, fee_pct=fee_pct, slippage_pct=slippage_pct,
                position_usd=position_usd, leverage=leverage,
            )
            trades.append(trade)
            i = trade.exit_idx + 1  # jump to after exit
        else:
            i += 1

    # Aggregate stats
    total = len(trades)
    wins = sum(1 for t in trades if t.pnl_net > 0.01)
    losses = sum(1 for t in trades if t.pnl_net < -0.01)
    pnl_total = sum(t.pnl_net for t in trades)
    wr = wins / max(wins + losses, 1)
    ll_breach_count = sum(1 for t in trades if t.state_signal == "switch_bear")
    trailing_count = sum(1 for t in trades if t.state_signal == "stay_bull")

    return {
        "ok": True,
        "tool": "bull_v1.0",
        "config": {
            "ema_period": cfg.ema_period,
            "min_pullback_pct": cfg.min_pullback_pct,
            "max_hold": max_hold,
        },
        "stats": {
            "total_trades": total,
            "wins": wins,
            "losses": losses,
            "win_rate": round(wr, 4),
            "total_pnl": round(pnl_total, 2),
            "avg_win": round(np.mean([t.pnl_net for t in trades if t.pnl_net > 0.01]), 2) if wins > 0 else 0.0,
            "avg_loss": round(np.mean([t.pnl_net for t in trades if t.pnl_net < -0.01]), 2) if losses > 0 else 0.0,
            "ll_breach_exits": ll_breach_count,
            "trailing_exits": trailing_count,
        },
        "trades": [
            {
                "entry_idx": t.entry_idx,
                "exit_idx": t.exit_idx,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "entry_low": round(t.entry_low, 2),
                "ema20_entry": round(t.ema20_at_entry, 2),
                "exit_reason": t.exit_reason,
                "state_signal": t.state_signal,
                "pnl_net": round(t.pnl_net, 2),
                "hold": t.hold_candles,
            }
            for t in trades
        ],
    }


__all__ = [
    "BullConfig", "BullSignal", "BullTradeRecord",
    "BullExitReason", "BullStateSignal",
    "detect_bull_entry_signal", "run_bull_trade", "run_bull_backtest",
]
