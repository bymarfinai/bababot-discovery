"""
backtest.py — Backtest Engine
================================
Integrate semua layer + eksekusi trade dengan SL/TP + circuit breakers.
"""

from __future__ import annotations
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .indicators import atr
from .regime import RegimeConfig, classify_regime_series
from .transition import TransitionConfig, classify_transitions
from .microevent import MicroEventConfig, BiasConfig, detect_micro_events, compute_bias_series
from .entry_rules import EntryConfig, EntrySide, EntryMode, generate_entry_signals


class ExitReason(Enum):
    TP1 = "tp1"
    TP2 = "tp2"
    TP3 = "tp3"
    SL = "sl"
    MAX_HOLD = "max_hold"
    CIRCUIT_BREAKER = "circuit_breaker"
    END = "end_of_data"


@dataclass
class BacktestConfig:
    position_usd: float = 10.0
    leverage: float = 50.0
    fee_pct: float = 0.0004
    slippage_pct: float = 0.001
    max_hold_candles: int = 8
    candle_hours: float = 1.0

    sl_atr_mult: float = 1.5
    tp1_ratio: float = 0.5
    tp2_ratio: float = 0.3
    tp3_ratio: float = 0.2
    trailing_atr_mult: float = 1.0

    max_consec_losses: int = 5
    max_drawdown_pct: float = 0.10
    cooldown_after_breaker: int = 48


@dataclass
class TradeRecord:
    entry_idx: int
    exit_idx: int
    side: str
    mode: str
    reason: str
    regime: str
    bias: str
    entry_price: float
    exit_price: float
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    exit_reason: str
    pnl_net: float
    hold_candles: int


@dataclass
class BacktestStats:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    total_pnl_net: float = 0.0
    total_fees: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    trades_per_day: float = 0.0
    exit_by_reason: dict = field(default_factory=dict)
    by_regime: dict = field(default_factory=dict)
    by_mode: dict = field(default_factory=dict)
    runtime_sec: float = 0.0
    total_candles: int = 0


@dataclass
class BacktestResult:
    stats: BacktestStats
    trades: list[TradeRecord]
    error: Optional[str] = None


def run_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: BacktestConfig,
    regime_cfg: Optional[RegimeConfig] = None,
    trans_cfg: Optional[TransitionConfig] = None,
    event_cfg: Optional[MicroEventConfig] = None,
    bias_cfg: Optional[BiasConfig] = None,
    entry_cfg: Optional[EntryConfig] = None,
    warmup: int = 100,
) -> BacktestResult:
    """Run full backtest with all layers."""
    t0 = time.time()

    regime_cfg = regime_cfg or RegimeConfig()
    trans_cfg = trans_cfg or TransitionConfig()
    event_cfg = event_cfg or MicroEventConfig()
    bias_cfg = bias_cfg or BiasConfig()
    entry_cfg = entry_cfg or EntryConfig()

    n = len(closes)
    if n < warmup + 50:
        return BacktestResult(
            stats=BacktestStats(),
            trades=[],
            error=f"Insufficient data: {n} candles",
        )

    # Compute all layers
    print(f"[BT] Classifying regime for {n} candles...")
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)

    print(f"[BT] Classifying transitions...")
    transitions = classify_transitions(highs, lows, closes, volumes, regime_states, trans_cfg)

    print(f"[BT] Detecting micro events...")
    events = detect_micro_events(highs, lows, closes, volumes, regime_states, event_cfg)

    print(f"[BT] Computing bias series...")
    biases = compute_bias_series(highs, lows, closes, volumes, regime_states, bias_cfg)

    print(f"[BT] Generating entry signals...")
    signals = generate_entry_signals(highs, lows, closes, regime_states, events, biases, entry_cfg)
    print(f"[BT] Generated {len(signals)} signals")

    # ATR for SL
    atr_arr = atr(highs, lows, closes, 14)

    # Backtest execution
    trades: list[TradeRecord] = []
    equity = cfg.position_usd * 10  # $100 modal
    starting_equity = equity
    peak_equity = equity
    max_dd = 0.0
    consec_losses = 0
    breaker_until = -1

    active_pos = None
    signals_iter = iter(signals)
    next_signal = next(signals_iter, None)

    for i in range(n):
        # Manage active position
        if active_pos is not None:
            h, l, c = highs[i], lows[i], closes[i]
            side = active_pos['side']
            entry = active_pos['entry_price']
            sl = active_pos['sl']
            tp1 = active_pos['tp1']
            tp2 = active_pos['tp2']
            tp3 = active_pos['tp3']

            exit_reason = None
            exit_price = 0.0

            # SL check first (worst case)
            if side == 'long' and l <= sl:
                exit_reason = ExitReason.SL
                exit_price = sl
            elif side == 'short' and h >= sl:
                exit_reason = ExitReason.SL
                exit_price = sl
            else:
                # Sequential TP hits
                if not active_pos['tp1_hit']:
                    if (side == 'long' and h >= tp1) or (side == 'short' and l <= tp1):
                        active_pos['tp1_hit'] = True
                        active_pos['sl'] = entry  # Move to breakeven
                if active_pos['tp1_hit'] and not active_pos['tp2_hit']:
                    if (side == 'long' and h >= tp2) or (side == 'short' and l <= tp2):
                        active_pos['tp2_hit'] = True
                if active_pos['tp2_hit'] and not active_pos['tp3_hit']:
                    if (side == 'long' and h >= tp3) or (side == 'short' and l <= tp3):
                        active_pos['tp3_hit'] = True
                        exit_reason = ExitReason.TP3
                        exit_price = tp3

                # Max hold
                if exit_reason is None and (i - active_pos['entry_idx']) >= cfg.max_hold_candles:
                    exit_reason = ExitReason.MAX_HOLD
                    exit_price = c

            if exit_reason is not None:
                # Compute PnL
                notional = cfg.position_usd * cfg.leverage
                if side == 'long':
                    gross_pct = (exit_price - entry) / entry
                else:
                    gross_pct = (entry - exit_price) / entry
                gross_pnl = gross_pct * notional
                fees = cfg.fee_pct * notional * 2  # Entry + exit
                slippage_cost = cfg.slippage_pct * notional * 2
                net_pnl = gross_pnl - fees - slippage_cost

                trade = TradeRecord(
                    entry_idx=active_pos['entry_idx'],
                    exit_idx=i,
                    side=side,
                    mode=active_pos['mode'],
                    reason=active_pos['reason'],
                    regime=active_pos['regime'],
                    bias=active_pos['bias'],
                    entry_price=entry,
                    exit_price=exit_price,
                    sl_price=active_pos['orig_sl'],
                    tp1_price=tp1,
                    tp2_price=tp2,
                    tp3_price=tp3,
                    tp1_hit=active_pos['tp1_hit'],
                    tp2_hit=active_pos['tp2_hit'],
                    tp3_hit=active_pos['tp3_hit'],
                    exit_reason=exit_reason.value,
                    pnl_net=net_pnl,
                    hold_candles=i - active_pos['entry_idx'],
                )
                trades.append(trade)
                equity += net_pnl

                # Update DD
                if equity > peak_equity:
                    peak_equity = equity
                dd = peak_equity - equity
                if dd > max_dd:
                    max_dd = dd

                # Consecutive losses tracking
                if net_pnl < 0:
                    consec_losses += 1
                elif net_pnl > 0:
                    consec_losses = 0

                # Circuit breaker
                if consec_losses >= cfg.max_consec_losses:
                    breaker_until = i + cfg.cooldown_after_breaker
                    consec_losses = 0
                if peak_equity > 0 and (peak_equity - equity) / peak_equity >= cfg.max_drawdown_pct:
                    breaker_until = i + cfg.cooldown_after_breaker

                active_pos = None

        # Skip if breaker active
        if i < breaker_until:
            # Advance signals past current
            while next_signal is not None and next_signal.idx <= i:
                next_signal = next(signals_iter, None)
            continue

        # Consume signals
        while next_signal is not None and next_signal.idx < i:
            next_signal = next(signals_iter, None)

        if active_pos is None and next_signal is not None and next_signal.idx == i:
            sig = next_signal
            next_signal = next(signals_iter, None)

            if atr_arr[i] > 0:
                entry_price = closes[i]
                # Slippage on entry
                if sig.side == EntrySide.LONG:
                    entry_price = entry_price * (1 + cfg.slippage_pct)
                else:
                    entry_price = entry_price * (1 - cfg.slippage_pct)

                atr_now = atr_arr[i]
                sl = entry_price - atr_now * cfg.sl_atr_mult if sig.side == EntrySide.LONG else entry_price + atr_now * cfg.sl_atr_mult

                # TP tiers: range mode uses POC + VAH, trend mode uses ATR-based
                rs = regime_states[i]
                if sig.mode in (EntryMode.RANGE_BOUNCE, EntryMode.RANGE_REJECT, EntryMode.RANGE_FAKE):
                    if sig.side == EntrySide.LONG:
                        tp1 = rs.poc
                        tp2 = (rs.poc + rs.vah) / 2
                        tp3 = rs.vah
                    else:
                        tp1 = rs.poc
                        tp2 = (rs.poc + rs.val) / 2
                        tp3 = rs.val
                else:
                    # Trend mode: ATR-based
                    if sig.side == EntrySide.LONG:
                        tp1 = entry_price + atr_now * 1.5
                        tp2 = entry_price + atr_now * 3.0
                        tp3 = entry_price + atr_now * 5.0
                    else:
                        tp1 = entry_price - atr_now * 1.5
                        tp2 = entry_price - atr_now * 3.0
                        tp3 = entry_price - atr_now * 5.0

                # Safety check: reject invalid trade
                if sig.side == EntrySide.LONG and tp1 <= entry_price:
                    continue
                if sig.side == EntrySide.SHORT and tp1 >= entry_price:
                    continue

                active_pos = {
                    'side': 'long' if sig.side == EntrySide.LONG else 'short',
                    'mode': sig.mode.value,
                    'reason': sig.reason,
                    'regime': sig.regime,
                    'bias': sig.bias,
                    'entry_idx': i,
                    'entry_price': entry_price,
                    'sl': sl,
                    'orig_sl': sl,
                    'tp1': tp1,
                    'tp2': tp2,
                    'tp3': tp3,
                    'tp1_hit': False,
                    'tp2_hit': False,
                    'tp3_hit': False,
                }

    # Close any open position
    if active_pos is not None:
        notional = cfg.position_usd * cfg.leverage
        side = active_pos['side']
        entry = active_pos['entry_price']
        exit_price = closes[-1]
        gross_pct = (exit_price - entry) / entry if side == 'long' else (entry - exit_price) / entry
        net_pnl = gross_pct * notional - cfg.fee_pct * notional * 2 - cfg.slippage_pct * notional * 2
        trades.append(TradeRecord(
            entry_idx=active_pos['entry_idx'], exit_idx=n - 1,
            side=side, mode=active_pos['mode'], reason=active_pos['reason'],
            regime=active_pos['regime'], bias=active_pos['bias'],
            entry_price=entry, exit_price=exit_price,
            sl_price=active_pos['orig_sl'],
            tp1_price=active_pos['tp1'], tp2_price=active_pos['tp2'], tp3_price=active_pos['tp3'],
            tp1_hit=active_pos['tp1_hit'], tp2_hit=active_pos['tp2_hit'], tp3_hit=active_pos['tp3_hit'],
            exit_reason=ExitReason.END.value, pnl_net=net_pnl,
            hold_candles=n - 1 - active_pos['entry_idx'],
        ))
        equity += net_pnl

    # Compute stats
    stats = BacktestStats()
    stats.total_trades = len(trades)
    stats.total_candles = n
    stats.runtime_sec = time.time() - t0

    wins_pnl = []
    losses_pnl = []
    for t in trades:
        stats.total_pnl_net += t.pnl_net
        if t.pnl_net > 0.01:
            stats.wins += 1
            wins_pnl.append(t.pnl_net)
        elif t.pnl_net < -0.01:
            stats.losses += 1
            losses_pnl.append(t.pnl_net)
        else:
            stats.breakeven += 1

        stats.exit_by_reason[t.exit_reason] = stats.exit_by_reason.get(t.exit_reason, 0) + 1
        stats.by_regime[t.regime] = stats.by_regime.get(t.regime, 0) + 1
        stats.by_mode[t.mode] = stats.by_mode.get(t.mode, 0) + 1

    if stats.wins + stats.losses > 0:
        stats.win_rate = stats.wins / (stats.wins + stats.losses)
    if wins_pnl:
        stats.avg_win = float(np.mean(wins_pnl))
    if losses_pnl:
        stats.avg_loss = float(np.mean(losses_pnl))

    stats.max_drawdown_usd = max_dd
    stats.max_drawdown_pct = max_dd / starting_equity if starting_equity > 0 else 0.0

    days = (n * cfg.candle_hours) / 24.0
    stats.trades_per_day = stats.total_trades / days if days > 0 else 0.0

    return BacktestResult(stats=stats, trades=trades)


__all__ = ["BacktestConfig", "TradeRecord", "BacktestStats", "BacktestResult", "run_backtest", "ExitReason"]
