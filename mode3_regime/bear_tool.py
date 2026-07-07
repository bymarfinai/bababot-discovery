"""
bear_tool.py — v1.0 BEAR market tool
======================================================
Entry: SHORT at EMA20 rally reject (dari bawah)
- Bot must be in BEAR state (confirmed LL breach earlier)
- Wait for price rally to EMA20 from below
- Candle touches EMA20 and closes BACK BELOW = reject → SHORT entry

Exit: Trailing stop EMA20 (close-based)
- If candle close > EMA20 → full exit
- No fixed TP tiers, ride the trend down

State exit triggers:
- HH breach: candle close breaks entry_high → force exit + signal BEAR→BULL
- Trailing stop: normal exit → signal BEAR→SIDEWAYS

Mirror of bull_tool.py.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .indicators import ema as compute_ema


class BearExitReason(Enum):
    TRAILING_STOP = "trailing_stop"     # close > EMA20
    HH_BREACH = "hh_breach"             # force exit → BULL switch
    END = "end_of_data"


class BearStateSignal(Enum):
    NONE = "none"
    STAY_BEAR = "stay_bear"             # trailing exit, no HH breach
    SWITCH_BULL = "switch_bull"         # HH breach detected


@dataclass
class BearConfig:
    ema_period: int = 20
    min_rally_pct: float = 0.005         # min 0.5% rally from recent low
    require_close_confirm: bool = True   # close below EMA required
    lookback_recent_low: int = 20        # window for detecting rally


@dataclass
class BearSignal:
    idx: int
    entry_price: float
    ema20_at_entry: float
    recent_low: float                    # tracked for rally validation
    reason: str = ""


@dataclass
class BearTradeRecord:
    entry_idx: int
    exit_idx: int
    entry_price: float
    exit_price: float
    entry_high: float                    # anchor for HH detection
    ema20_at_entry: float
    ema20_at_exit: float
    exit_reason: str
    pnl_net: float
    hold_candles: int
    state_signal: str                    # STAY_BEAR or SWITCH_BULL


def detect_bear_entry_signal(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    opens: np.ndarray,
    ema20: np.ndarray,
    i: int,
    cfg: BearConfig,
) -> Optional[BearSignal]:
    """
    Detect BEAR entry signal at candle i:
    1. Price was below EMA20 recently (downtrend context)
    2. Current candle high >= EMA20 (rally touched EMA)
    3. Current candle close < EMA20 (rejected back down)
    4. Minimum rally met (from recent low)
    """
    if i < cfg.lookback_recent_low or i >= len(closes):
        return None

    cur_ema = float(ema20[i])
    if cur_ema <= 0:
        return None

    h_i = float(highs[i])
    l_i = float(lows[i])
    c_i = float(closes[i])
    o_i = float(opens[i])

    # Recent low in lookback window
    recent_low = float(np.min(lows[i - cfg.lookback_recent_low:i]))

    # Condition 1: recent low must be below EMA20 (context = downtrend)
    if recent_low >= cur_ema:
        return None

    # Condition 2: minimum rally from recent low
    rally_pct = (h_i - recent_low) / recent_low
    if rally_pct < cfg.min_rally_pct:
        return None

    # Condition 3: current candle touched EMA20 from below (high >= ema)
    if h_i < cur_ema:
        return None

    # Condition 4: current candle rejected back down (close < EMA20)
    if cfg.require_close_confirm:
        if c_i >= cur_ema:
            return None
    # Additional bearish candle check
    if c_i >= o_i:  # must be bearish candle (close < open)
        return None

    return BearSignal(
        idx=i,
        entry_price=c_i,
        ema20_at_entry=cur_ema,
        recent_low=recent_low,
        reason=f"rally_reject_ema20 rally={rally_pct*100:.2f}%",
    )


def run_bear_trade(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    ema20: np.ndarray,
    signal: BearSignal,
    entry_idx: int,
    entry_high_anchor: float,   # from signal candle high, used for HH breach detection
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
) -> BearTradeRecord:
    """
    Manage BEAR SHORT position from entry until exit.
    Exit conditions:
    1. Close > entry_high_anchor → hh_breach → SWITCH_BULL signal (priority)
    2. Close > EMA20 → trailing_stop → STAY_BEAR signal
    """
    entry_price = signal.entry_price * (1 - slippage_pct)
    notional = position_usd * leverage
    n = len(closes)

    exit_idx = entry_idx
    exit_price = entry_price
    exit_reason = BearExitReason.END
    state_signal = BearStateSignal.STAY_BEAR

    for i in range(entry_idx + 1, min(entry_idx + max_hold, n)):
        c = float(closes[i])
        cur_ema = float(ema20[i])

        # Priority 1: HH breach check (force exit + switch BULL)
        if c > entry_high_anchor:
            exit_idx = i
            exit_price = c
            exit_reason = BearExitReason.HH_BREACH
            state_signal = BearStateSignal.SWITCH_BULL
            break

        # Priority 2: trailing stop (close > EMA20)
        if cur_ema > 0 and c > cur_ema:
            exit_idx = i
            exit_price = c
            exit_reason = BearExitReason.TRAILING_STOP
            state_signal = BearStateSignal.STAY_BEAR
            break

    # If loop ended without break, exit at end
    if exit_reason == BearExitReason.END:
        exit_idx = min(entry_idx + max_hold - 1, n - 1)
        exit_price = float(closes[exit_idx])

    # PnL calc (SHORT: profit when exit < entry)
    gross_pct = (entry_price - exit_price) / entry_price
    gross_pnl = gross_pct * notional
    fee = fee_pct * notional * 2
    slip = slippage_pct * notional
    pnl_net = gross_pnl - fee - slip

    return BearTradeRecord(
        entry_idx=entry_idx,
        exit_idx=exit_idx,
        entry_price=entry_price,
        exit_price=exit_price,
        entry_high=entry_high_anchor,
        ema20_at_entry=signal.ema20_at_entry,
        ema20_at_exit=float(ema20[exit_idx]) if exit_idx < len(ema20) else 0.0,
        exit_reason=exit_reason.value,
        pnl_net=pnl_net,
        hold_candles=exit_idx - entry_idx,
        state_signal=state_signal.value,
    )


def run_bear_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    opens: np.ndarray,
    cfg: Optional[BearConfig] = None,
    max_hold: int = 200,
    fee_pct: float = 0.0004,
    slippage_pct: float = 0.001,
    position_usd: float = 10.0,
    leverage: float = 50.0,
    warmup: int = 50,
) -> dict:
    """
    Standalone BEAR backtest — assumes we're in BEAR state throughout.
    Real orchestrator would only invoke this while state=BEAR.
    """
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
            trade = run_bear_trade(
                highs, lows, closes, ema20_arr, sig, i,
                entry_high_anchor=float(highs[i]),
                max_hold=max_hold, fee_pct=fee_pct, slippage_pct=slippage_pct,
                position_usd=position_usd, leverage=leverage,
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
    hh_breach_count = sum(1 for t in trades if t.state_signal == "switch_bull")
    trailing_count = sum(1 for t in trades if t.state_signal == "stay_bear")

    return {
        "ok": True,
        "tool": "bear_v1.0",
        "config": {
            "ema_period": cfg.ema_period,
            "min_rally_pct": cfg.min_rally_pct,
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
            "hh_breach_exits": hh_breach_count,
            "trailing_exits": trailing_count,
        },
        "trades": [
            {
                "entry_idx": t.entry_idx,
                "exit_idx": t.exit_idx,
                "entry_price": round(t.entry_price, 2),
                "exit_price": round(t.exit_price, 2),
                "entry_high": round(t.entry_high, 2),
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
    "BearConfig", "BearSignal", "BearTradeRecord",
    "BearExitReason", "BearStateSignal",
    "detect_bear_entry_signal", "run_bear_trade", "run_bear_backtest",
]
