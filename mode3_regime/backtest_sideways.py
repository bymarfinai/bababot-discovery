"""
backtest_sideways.py — Backtest Engine untuk Sideways Tektok Strategy
======================================================================
Standalone backtest hanya untuk sideways strategy.
SL/TP config disesuaikan untuk range trading (tight SL, TP at levels).
"""

from __future__ import annotations
import time
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .regime import RegimeConfig, RegimeState, classify_regime_series
from .strategy_sideways import (
    SideEnum, SidewaysMode, SidewaysConfig, SidewaysSignal,
    generate_sideways_signals,
)


class ExitReasonSW(Enum):
    TP1 = "tp1"
    TP2 = "tp2"
    TP3 = "tp3"
    SL = "sl"
    SL_BE = "sl_breakeven"
    MAX_HOLD = "max_hold"
    CIRCUIT_BREAKER = "circuit_breaker"
    END = "end_of_data"


@dataclass
class SidewaysBTConfig:
    position_usd: float = 10.0
    leverage: float = 50.0
    fee_pct: float = 0.0004
    slippage_pct: float = 0.001
    candle_hours: float = 1.0

    # SL/TP untuk sideways: tight SL, TP at levels (POC, mid, VAH/VAL)
    sl_pct_from_level: float = 0.005      # 0.5% below VAL / above VAH
    tp1_ratio: float = 0.5                 # 50% close at POC
    tp2_ratio: float = 0.3                 # 30% close at mid
    tp3_ratio: float = 0.2                 # 20% close at opposite level
    move_sl_to_be_after_tp1: bool = True

    max_hold_candles: int = 12             # Max hold 12 candle di range trading

    # Circuit breakers
    max_consec_losses: int = 5
    max_drawdown_pct: float = 0.10
    cooldown_after_breaker: int = 48


@dataclass
class SidewaysTradeRecord:
    entry_idx: int
    exit_idx: int
    side: str
    mode: str
    reason: str
    regime: str
    confidence: float
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
class SidewaysBTStats:
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    total_pnl_net: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    max_drawdown_pct: float = 0.0
    max_drawdown_usd: float = 0.0
    trades_per_day: float = 0.0

    tp1_hit_rate: float = 0.0
    tp2_hit_rate: float = 0.0
    tp3_hit_rate: float = 0.0

    exit_by_reason: dict = field(default_factory=dict)
    by_regime: dict = field(default_factory=dict)
    by_mode: dict = field(default_factory=dict)
    runtime_sec: float = 0.0
    total_candles: int = 0


@dataclass
class SidewaysBTResult:
    stats: SidewaysBTStats
    trades: list[SidewaysTradeRecord]
    error: Optional[str] = None


def run_sideways_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: SidewaysBTConfig,
    regime_cfg: Optional[RegimeConfig] = None,
    strategy_cfg: Optional[SidewaysConfig] = None,
    warmup: int = 100,
) -> SidewaysBTResult:
    t0 = time.time()

    regime_cfg = regime_cfg or RegimeConfig()
    strategy_cfg = strategy_cfg or SidewaysConfig()

    n = len(closes)
    if n < warmup + 50:
        return SidewaysBTResult(
            stats=SidewaysBTStats(), trades=[],
            error=f"insufficient candles: {n}",
        )

    print(f"[SW BT] Classifying regime for {n} candles...")
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)

    print(f"[SW BT] Generating sideways signals...")
    signals = generate_sideways_signals(highs, lows, closes, volumes, regime_states, strategy_cfg)
    print(f"[SW BT] {len(signals)} signals generated")

    trades: list[SidewaysTradeRecord] = []
    equity = cfg.position_usd * 10
    starting_equity = equity
    peak_equity = equity
    max_dd = 0.0
    consec_losses = 0
    breaker_until = -1

    active_pos = None
    sig_iter = iter(signals)
    next_sig = next(sig_iter, None)

    for i in range(n):
        # Manage active position
        if active_pos is not None:
            h, l, c = highs[i], lows[i], closes[i]
            side = active_pos['side']
            entry = active_pos['entry_price']
            sl = active_pos['sl']
            tp1, tp2, tp3 = active_pos['tp1'], active_pos['tp2'], active_pos['tp3']
            notional = cfg.position_usd * cfg.leverage

            exit_reason = None
            exit_price = 0.0
            close_pos = False

            sl_hit = (side == 'long' and l <= sl) or (side == 'short' and h >= sl)

            if sl_hit:
                if active_pos['moved_to_be']:
                    exit_reason = ExitReasonSW.SL_BE
                else:
                    exit_reason = ExitReasonSW.SL
                exit_price = sl
                close_pos = True
            else:
                # TP1
                if not active_pos['tp1_hit']:
                    tp1_reached = (side == 'long' and h >= tp1) or (side == 'short' and l <= tp1)
                    if tp1_reached:
                        active_pos['tp1_hit'] = True
                        gross_pct = (tp1 - entry) / entry if side == 'long' else (entry - tp1) / entry
                        partial_notional = notional * cfg.tp1_ratio
                        partial_pnl = gross_pct * partial_notional
                        partial_fee = cfg.fee_pct * partial_notional
                        partial_slip = cfg.slippage_pct * partial_notional
                        active_pos['realized_pnl'] += partial_pnl - partial_fee - partial_slip
                        active_pos['remaining_ratio'] -= cfg.tp1_ratio
                        if cfg.move_sl_to_be_after_tp1:
                            active_pos['sl'] = entry
                            active_pos['moved_to_be'] = True

                # TP2
                if active_pos['tp1_hit'] and not active_pos['tp2_hit']:
                    tp2_reached = (side == 'long' and h >= tp2) or (side == 'short' and l <= tp2)
                    if tp2_reached:
                        active_pos['tp2_hit'] = True
                        gross_pct = (tp2 - entry) / entry if side == 'long' else (entry - tp2) / entry
                        partial_notional = notional * cfg.tp2_ratio
                        partial_pnl = gross_pct * partial_notional
                        partial_fee = cfg.fee_pct * partial_notional
                        partial_slip = cfg.slippage_pct * partial_notional
                        active_pos['realized_pnl'] += partial_pnl - partial_fee - partial_slip
                        active_pos['remaining_ratio'] -= cfg.tp2_ratio

                # TP3 (final)
                if active_pos['tp2_hit'] and not active_pos['tp3_hit']:
                    tp3_reached = (side == 'long' and h >= tp3) or (side == 'short' and l <= tp3)
                    if tp3_reached:
                        active_pos['tp3_hit'] = True
                        exit_reason = ExitReasonSW.TP3
                        exit_price = tp3
                        close_pos = True

                # Max hold
                if not close_pos and (i - active_pos['entry_idx']) >= cfg.max_hold_candles:
                    exit_reason = ExitReasonSW.MAX_HOLD
                    exit_price = c
                    close_pos = True

            if close_pos:
                remaining = active_pos['remaining_ratio']
                if remaining > 0:
                    gross_pct = (exit_price - entry) / entry if side == 'long' else (entry - exit_price) / entry
                    remaining_notional = notional * remaining
                    remaining_pnl = gross_pct * remaining_notional
                    remaining_fee = cfg.fee_pct * remaining_notional
                    remaining_slip = cfg.slippage_pct * remaining_notional
                    final_pnl = active_pos['realized_pnl'] + (remaining_pnl - remaining_fee - remaining_slip)
                else:
                    final_pnl = active_pos['realized_pnl']

                entry_fee = cfg.fee_pct * notional
                entry_slip = cfg.slippage_pct * notional
                final_pnl -= entry_fee + entry_slip

                trade = SidewaysTradeRecord(
                    entry_idx=active_pos['entry_idx'],
                    exit_idx=i,
                    side=side,
                    mode=active_pos['mode'],
                    reason=active_pos['reason'],
                    regime=active_pos['regime'],
                    confidence=active_pos['confidence'],
                    entry_price=entry,
                    exit_price=exit_price,
                    sl_price=active_pos['orig_sl'],
                    tp1_price=tp1, tp2_price=tp2, tp3_price=tp3,
                    tp1_hit=active_pos['tp1_hit'],
                    tp2_hit=active_pos['tp2_hit'],
                    tp3_hit=active_pos['tp3_hit'],
                    exit_reason=exit_reason.value,
                    pnl_net=final_pnl,
                    hold_candles=i - active_pos['entry_idx'],
                )
                trades.append(trade)
                equity += final_pnl

                if equity > peak_equity:
                    peak_equity = equity
                dd = peak_equity - equity
                if dd > max_dd:
                    max_dd = dd

                if final_pnl < 0:
                    consec_losses += 1
                elif final_pnl > 0:
                    consec_losses = 0

                if consec_losses >= cfg.max_consec_losses:
                    breaker_until = i + cfg.cooldown_after_breaker
                    consec_losses = 0
                if peak_equity > 0 and (peak_equity - equity) / peak_equity >= cfg.max_drawdown_pct:
                    breaker_until = i + cfg.cooldown_after_breaker

                active_pos = None

        if i < breaker_until:
            while next_sig is not None and next_sig.idx <= i:
                next_sig = next(sig_iter, None)
            continue

        while next_sig is not None and next_sig.idx < i:
            next_sig = next(sig_iter, None)

        if active_pos is None and next_sig is not None and next_sig.idx == i:
            sig = next_sig
            next_sig = next(sig_iter, None)

            entry_price = closes[i]
            if sig.side == SideEnum.LONG:
                entry_price = entry_price * (1 + cfg.slippage_pct)
            else:
                entry_price = entry_price * (1 - cfg.slippage_pct)

            side_str = 'long' if sig.side == SideEnum.LONG else 'short'

            # SL: 0.5% below VAL (LONG) or above VAH (SHORT)
            if side_str == 'long':
                sl = sig.val * (1 - cfg.sl_pct_from_level)
                # TP tiers: POC → mid(POC,VAH) → VAH
                tp1 = sig.poc
                tp2 = (sig.poc + sig.vah) / 2
                tp3 = sig.vah
            else:
                sl = sig.vah * (1 + cfg.sl_pct_from_level)
                tp1 = sig.poc
                tp2 = (sig.poc + sig.val) / 2
                tp3 = sig.val

            # Safety check
            if side_str == 'long' and (tp1 <= entry_price or sl >= entry_price):
                continue
            if side_str == 'short' and (tp1 >= entry_price or sl <= entry_price):
                continue

            active_pos = {
                'side': side_str,
                'mode': sig.mode.value,
                'reason': sig.reason,
                'regime': sig.regime,
                'confidence': sig.confidence,
                'entry_idx': i,
                'entry_price': entry_price,
                'sl': sl,
                'orig_sl': sl,
                'tp1': tp1, 'tp2': tp2, 'tp3': tp3,
                'tp1_hit': False, 'tp2_hit': False, 'tp3_hit': False,
                'realized_pnl': 0.0,
                'remaining_ratio': 1.0,
                'moved_to_be': False,
            }

    # Close open at end
    if active_pos is not None:
        side = active_pos['side']
        entry = active_pos['entry_price']
        exit_price = closes[-1]
        notional = cfg.position_usd * cfg.leverage
        remaining = active_pos['remaining_ratio']
        if remaining > 0:
            gross_pct = (exit_price - entry) / entry if side == 'long' else (entry - exit_price) / entry
            remaining_notional = notional * remaining
            remaining_pnl = gross_pct * remaining_notional - cfg.fee_pct * remaining_notional - cfg.slippage_pct * remaining_notional
            final_pnl = active_pos['realized_pnl'] + remaining_pnl
        else:
            final_pnl = active_pos['realized_pnl']
        final_pnl -= cfg.fee_pct * notional + cfg.slippage_pct * notional
        trades.append(SidewaysTradeRecord(
            entry_idx=active_pos['entry_idx'], exit_idx=n - 1,
            side=side, mode=active_pos['mode'], reason=active_pos['reason'],
            regime=active_pos['regime'], confidence=active_pos['confidence'],
            entry_price=entry, exit_price=exit_price,
            sl_price=active_pos['orig_sl'],
            tp1_price=active_pos['tp1'], tp2_price=active_pos['tp2'], tp3_price=active_pos['tp3'],
            tp1_hit=active_pos['tp1_hit'], tp2_hit=active_pos['tp2_hit'], tp3_hit=active_pos['tp3_hit'],
            exit_reason=ExitReasonSW.END.value, pnl_net=final_pnl,
            hold_candles=n - 1 - active_pos['entry_idx'],
        ))
        equity += final_pnl

    stats = SidewaysBTStats()
    stats.total_trades = len(trades)
    stats.total_candles = n
    stats.runtime_sec = time.time() - t0

    wins_pnl, losses_pnl = [], []
    tp1_hits, tp2_hits, tp3_hits = 0, 0, 0
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
        if t.tp1_hit:
            tp1_hits += 1
        if t.tp2_hit:
            tp2_hits += 1
        if t.tp3_hit:
            tp3_hits += 1

    if stats.wins + stats.losses > 0:
        stats.win_rate = stats.wins / (stats.wins + stats.losses)
    if wins_pnl:
        stats.avg_win = float(np.mean(wins_pnl))
    if losses_pnl:
        stats.avg_loss = float(np.mean(losses_pnl))

    if stats.total_trades > 0:
        stats.tp1_hit_rate = tp1_hits / stats.total_trades
        stats.tp2_hit_rate = tp2_hits / stats.total_trades
        stats.tp3_hit_rate = tp3_hits / stats.total_trades

    stats.max_drawdown_usd = max_dd
    stats.max_drawdown_pct = max_dd / starting_equity if starting_equity > 0 else 0.0

    days = (n * cfg.candle_hours) / 24.0
    stats.trades_per_day = stats.total_trades / days if days > 0 else 0.0

    return SidewaysBTResult(stats=stats, trades=trades)


__all__ = ["SidewaysBTConfig", "SidewaysTradeRecord", "SidewaysBTStats",
           "SidewaysBTResult", "run_sideways_backtest", "ExitReasonSW"]
