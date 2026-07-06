"""
backtest.py — Phase D: Regime-based Backtest Engine
====================================================

Integrate 3 layer (regime + state machine + classifier) untuk full backtest:
- 3 entry mode: range (fixed 3-tier TP), retest (hybrid), trend (full trailing)
- Circuit breakers: consecutive loss, drawdown, dead market, max hold time
- Realistic cost model: fee 0.04%, slippage 0.1%, funding rate (per 8h)
- Position sizing: sesuai bias resolver (0.5x-1.0x)

Author: BabaBot team
Version: 0.1.0 (Phase D)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .regime import (
    Regime, RegimeConfig, RegimeState, ValueArea,
    classify_regime_series, compute_atr, is_dead_market,
)
from .state_machine import (
    SMState, StateMachineConfig, MachineState,
    run_state_machine,
)
from .classifier import (
    SidewaysBias, ClassifierConfig, SidewaysAnalysis,
    analyze_sideways, get_prior_regime, resolve_entry_bias,
)


# ═════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════

class EntryMode(Enum):
    """3 mode entry berdasarkan konteks regime."""
    RANGE = "range"        # Bounce dari VAL/VAH di accumulation/distribution
    RETEST = "retest"      # Retest old level post-breakout (regime change)
    TREND = "trend"        # Pullback di trending market (bull/bear markup)


class ExitReason(Enum):
    """Alasan exit position."""
    TP1 = "tp1"
    TP2 = "tp2"
    TP3 = "tp3"
    SL = "sl"
    TRAILING = "trailing"
    MAX_HOLD = "max_hold"
    CIRCUIT_BREAKER = "circuit_breaker"
    END_OF_DATA = "end_of_data"


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

@dataclass
class BacktestConfig:
    """Config untuk backtest engine (aligned dengan real trading lu)."""

    # Position sizing
    position_usd: float = 10.0           # $10 per trade
    leverage: float = 50.0               # 50x leverage → notional $500

    # Cost model
    fee_pct: float = 0.0004              # 0.04% maker fee (Binance futures)
    slippage_pct: float = 0.001          # 0.1% slippage per side
    funding_rate_8h: float = 0.0001      # 0.01% per 8h (avg)

    # Time constraints
    max_hold_candles: int = 8            # Max hold 8 candle di 1h TF = 8 jam
    candle_hours: float = 1.0            # Timeframe dalam jam (1h default)

    # TP tier ratios (range mode)
    tp1_ratio: float = 0.5               # 50% posisi exit at TP1 (POC)
    tp2_ratio: float = 0.3               # 30% at TP2 (VWAP+σ)
    tp3_ratio: float = 0.2               # 20% at TP3 (VAH/VAL)

    # SL
    sl_atr_multiplier: float = 1.5       # SL = 1.5 × ATR from entry

    # Trailing stop (trend & retest mode)
    trailing_activation_pct: float = 0.005   # Activate trailing after +0.5%
    trailing_atr_multiplier: float = 1.0     # Trail 1x ATR below high

    # Circuit breakers
    max_consecutive_losses: int = 5      # Pause after 5 losses
    max_drawdown_pct: float = 0.10       # Pause at -10% modal drawdown
    cooldown_after_breaker_candles: int = 48  # 2 days cooldown after breaker

    # Multi-tf confluence
    require_mtf_confluence: bool = False # Set True kalau higher TF data ada

    # ATR period
    atr_period: int = 14


# ═════════════════════════════════════════════════════════════
# TRADE + POSITION OBJECTS
# ═════════════════════════════════════════════════════════════

@dataclass
class Position:
    """Active position state."""
    entry_idx: int
    entry_price: float
    side: str                    # "long" or "short"
    mode: EntryMode
    size_usd: float              # Position size (bisa < position_usd karena bias)
    notional: float              # size_usd × leverage
    sl_price: float
    tp1_price: float
    tp2_price: float
    tp3_price: float

    # Partial exit tracking
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    remaining_ratio: float = 1.0    # Fraction of position still open

    # Trailing stop state
    trailing_active: bool = False
    trailing_stop_price: float = 0.0
    highest_price: float = 0.0       # Untuk trailing (LONG)
    lowest_price: float = 0.0        # Untuk trailing (SHORT)

    # Realized PnL from partial exits
    realized_pnl: float = 0.0


@dataclass
class TradeRecord:
    """Complete record dari 1 trade (untuk log)."""
    entry_idx: int
    exit_idx: int
    side: str
    mode: str
    entry_price: float
    exit_price: float               # Weighted average exit price
    size_usd: float
    tp1_hit: bool
    tp2_hit: bool
    tp3_hit: bool
    exit_reason: str
    pnl_gross_usd: float           # Sebelum fee
    pnl_fee_usd: float             # Total fee cost
    pnl_slippage_usd: float
    pnl_funding_usd: float
    pnl_net_usd: float             # Final net
    hold_candles: int


# ═════════════════════════════════════════════════════════════
# STATS
# ═════════════════════════════════════════════════════════════

@dataclass
class BacktestStats:
    """Aggregate stats dari backtest run."""
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0

    win_rate: float = 0.0
    total_pnl_net: float = 0.0
    total_pnl_gross: float = 0.0
    total_fees: float = 0.0

    max_drawdown_usd: float = 0.0
    max_drawdown_pct: float = 0.0

    avg_win_usd: float = 0.0
    avg_loss_usd: float = 0.0

    # Per mode
    range_trades: int = 0
    retest_trades: int = 0
    trend_trades: int = 0
    range_wr: float = 0.0
    retest_wr: float = 0.0
    trend_wr: float = 0.0

    # Per exit reason
    exit_by_reason: dict = field(default_factory=dict)

    # Runtime
    runtime_sec: float = 0.0
    total_candles: int = 0

    # Trade count per day
    trades_per_day: float = 0.0


@dataclass
class BacktestResult:
    """Full backtest result."""
    stats: BacktestStats
    trades: list[TradeRecord]
    equity_curve: list[float]
    error: Optional[str] = None


# ═════════════════════════════════════════════════════════════
# ENTRY MODE DETECTION
# ═════════════════════════════════════════════════════════════

def infer_entry_mode(
    regime_state: RegimeState,
    ms: MachineState,
) -> EntryMode:
    """Infer entry mode dari regime + state machine event."""
    # Retest: post-breakout regime change (TRUE_BREAKOUT / TRUE_BREAKDOWN)
    if ms.reason in ("true_breakout_vah", "true_breakdown_val"):
        return EntryMode.RETEST

    # Range: bouncing in accumulation/distribution
    if regime_state.regime in (Regime.ACCUMULATION, Regime.DISTRIBUTION):
        return EntryMode.RANGE

    # Trend: pullback di bull/bear markup
    return EntryMode.TREND


# ═════════════════════════════════════════════════════════════
# POSITION OPEN & TP/SL CALCULATION
# ═════════════════════════════════════════════════════════════

def open_position(
    idx: int,
    entry_price: float,
    side: str,
    mode: EntryMode,
    size_mult: float,
    va: ValueArea,
    atr: float,
    cfg: BacktestConfig,
) -> Optional[Position]:
    """Create Position dengan SL/TP calculated. Return None kalau trade invalid."""
    size_usd = cfg.position_usd * size_mult
    notional = size_usd * cfg.leverage

    # Apply slippage on entry (worse fill)
    if side == "long":
        actual_entry = entry_price * (1 + cfg.slippage_pct)
    else:
        actual_entry = entry_price * (1 - cfg.slippage_pct)

    # SL: ATR-based (safety stop)
    sl_distance = atr * cfg.sl_atr_multiplier
    if side == "long":
        sl_price = actual_entry - sl_distance
    else:
        sl_price = actual_entry + sl_distance

    # TP tiers depend on mode
    if mode == EntryMode.RANGE:
        # Range: 3-tier di POC, VWAP+σ, VAH (untuk LONG) atau kebalikan (SHORT)
        if side == "long":
            tp1 = va.poc
            tp2 = va.vwap_upper
            tp3 = va.vah
        else:
            tp1 = va.poc
            tp2 = va.vwap_lower
            tp3 = va.val

    elif mode == EntryMode.RETEST:
        range_width = va.vah - va.val
        if side == "long":
            tp1 = actual_entry + range_width * 0.5
            tp2 = actual_entry + range_width * 1.0
            tp3 = actual_entry + range_width * 1.5
        else:
            tp1 = actual_entry - range_width * 0.5
            tp2 = actual_entry - range_width * 1.0
            tp3 = actual_entry - range_width * 1.5

    else:  # TREND
        if side == "long":
            tp1 = actual_entry + atr * 1.5
            tp2 = actual_entry + atr * 3.0
            tp3 = actual_entry + atr * 5.0
        else:
            tp1 = actual_entry - atr * 1.5
            tp2 = actual_entry - atr * 3.0
            tp3 = actual_entry - atr * 5.0

    # Safety check: TP direction must match side
    if side == "long" and tp1 <= actual_entry:
        return None  # TP1 below entry for LONG = invalid trade
    if side == "short" and tp1 >= actual_entry:
        return None  # TP1 above entry for SHORT = invalid trade

    # Safety check: SL/TP distance ratio (avoid tiny RR)
    if side == "long":
        risk = actual_entry - sl_price
        reward = tp1 - actual_entry
    else:
        risk = sl_price - actual_entry
        reward = actual_entry - tp1
    if risk <= 0 or reward <= 0 or (reward / risk) < 0.5:
        return None  # RR < 0.5:1 = skip

    return Position(
        entry_idx=idx,
        entry_price=actual_entry,
        side=side,
        mode=mode,
        size_usd=size_usd,
        notional=notional,
        sl_price=sl_price,
        tp1_price=tp1,
        tp2_price=tp2,
        tp3_price=tp3,
        highest_price=actual_entry,
        lowest_price=actual_entry,
    )


# ═════════════════════════════════════════════════════════════
# POSITION MANAGEMENT (per candle)
# ═════════════════════════════════════════════════════════════

def manage_position(
    pos: Position,
    idx: int,
    high: float,
    low: float,
    close: float,
    atr: float,
    cfg: BacktestConfig,
) -> tuple[Position, Optional[ExitReason], float]:
    """
    Manage position selama 1 candle.

    Check: TP1/TP2/TP3 hit, SL hit, trailing stop hit, max hold expired.

    Returns:
        (updated_position, exit_reason_if_closed, exit_price_or_0)
    """
    # Track high/low untuk trailing
    if pos.side == "long":
        pos.highest_price = max(pos.highest_price, high)
    else:
        pos.lowest_price = min(pos.lowest_price, low)

    # Check SL hit first (worst case, conservative assumption)
    sl_hit = (pos.side == "long" and low <= pos.sl_price) or \
             (pos.side == "short" and high >= pos.sl_price)

    if sl_hit:
        return pos, ExitReason.SL, pos.sl_price

    # Check TP tiers (partial exits)
    if pos.mode == EntryMode.RANGE:
        # Full 3-tier fixed TP
        if not pos.tp1_hit:
            tp1_hit = (pos.side == "long" and high >= pos.tp1_price) or \
                      (pos.side == "short" and low <= pos.tp1_price)
            if tp1_hit:
                pos.tp1_hit = True
                # Realize partial PnL from TP1
                tp1_pnl = _compute_partial_pnl(pos, pos.tp1_price, cfg.tp1_ratio, cfg)
                pos.realized_pnl += tp1_pnl
                pos.remaining_ratio -= cfg.tp1_ratio
                # Move SL to break-even after TP1
                pos.sl_price = pos.entry_price

        if pos.tp1_hit and not pos.tp2_hit:
            tp2_hit = (pos.side == "long" and high >= pos.tp2_price) or \
                      (pos.side == "short" and low <= pos.tp2_price)
            if tp2_hit:
                pos.tp2_hit = True
                tp2_pnl = _compute_partial_pnl(pos, pos.tp2_price, cfg.tp2_ratio, cfg)
                pos.realized_pnl += tp2_pnl
                pos.remaining_ratio -= cfg.tp2_ratio

        if pos.tp2_hit and not pos.tp3_hit:
            tp3_hit = (pos.side == "long" and high >= pos.tp3_price) or \
                      (pos.side == "short" and low <= pos.tp3_price)
            if tp3_hit:
                pos.tp3_hit = True
                return pos, ExitReason.TP3, pos.tp3_price

    else:
        # RETEST or TREND: TP1 fixed, sisanya trailing
        if not pos.tp1_hit:
            tp1_hit = (pos.side == "long" and high >= pos.tp1_price) or \
                      (pos.side == "short" and low <= pos.tp1_price)
            if tp1_hit:
                pos.tp1_hit = True
                tp1_pnl = _compute_partial_pnl(pos, pos.tp1_price, cfg.tp1_ratio, cfg)
                pos.realized_pnl += tp1_pnl
                pos.remaining_ratio -= cfg.tp1_ratio
                # Activate trailing stop
                pos.trailing_active = True
                trail_distance = atr * cfg.trailing_atr_multiplier
                if pos.side == "long":
                    pos.trailing_stop_price = pos.highest_price - trail_distance
                else:
                    pos.trailing_stop_price = pos.lowest_price + trail_distance

        # Update trailing stop kalau active
        if pos.trailing_active:
            trail_distance = atr * cfg.trailing_atr_multiplier
            if pos.side == "long":
                new_trail = pos.highest_price - trail_distance
                if new_trail > pos.trailing_stop_price:
                    pos.trailing_stop_price = new_trail
                # Check trailing hit
                if low <= pos.trailing_stop_price:
                    return pos, ExitReason.TRAILING, pos.trailing_stop_price
            else:
                new_trail = pos.lowest_price + trail_distance
                if new_trail < pos.trailing_stop_price:
                    pos.trailing_stop_price = new_trail
                if high >= pos.trailing_stop_price:
                    return pos, ExitReason.TRAILING, pos.trailing_stop_price

    # Check max hold
    hold_candles = idx - pos.entry_idx
    if hold_candles >= cfg.max_hold_candles:
        return pos, ExitReason.MAX_HOLD, close

    return pos, None, 0.0


def _compute_partial_pnl(
    pos: Position,
    exit_price: float,
    ratio: float,
    cfg: BacktestConfig,
) -> float:
    """Compute PnL untuk partial exit (proporsi `ratio` dari total position)."""
    partial_notional = pos.notional * ratio

    if pos.side == "long":
        gross_pct = (exit_price - pos.entry_price) / pos.entry_price
    else:
        gross_pct = (pos.entry_price - exit_price) / pos.entry_price

    gross_pnl = gross_pct * partial_notional
    # Fee di exit (entry fee handled once di finalize)
    exit_fee = cfg.fee_pct * partial_notional
    # Slippage exit
    slippage = cfg.slippage_pct * partial_notional
    return gross_pnl - exit_fee - slippage


def close_position(
    pos: Position,
    exit_idx: int,
    exit_price: float,
    exit_reason: ExitReason,
    cfg: BacktestConfig,
) -> TradeRecord:
    """Close remaining position dan hitung final PnL."""
    # Compute PnL untuk remaining ratio
    remaining_pnl = 0.0
    if pos.remaining_ratio > 0:
        remaining_notional = pos.notional * pos.remaining_ratio
        if pos.side == "long":
            gross_pct = (exit_price - pos.entry_price) / pos.entry_price
        else:
            gross_pct = (pos.entry_price - exit_price) / pos.entry_price
        remaining_pnl = gross_pct * remaining_notional
        # Fees + slippage on remaining
        remaining_pnl -= cfg.fee_pct * remaining_notional
        remaining_pnl -= cfg.slippage_pct * remaining_notional

    # Entry fee (baru di-charge saat trade close)
    entry_fee = cfg.fee_pct * pos.notional

    # Funding rate (per 8h)
    hold_candles = exit_idx - pos.entry_idx
    hold_hours = hold_candles * cfg.candle_hours
    funding_periods = hold_hours / 8.0
    funding_cost = cfg.funding_rate_8h * pos.notional * funding_periods

    total_gross = pos.realized_pnl + remaining_pnl
    total_slippage = cfg.slippage_pct * pos.notional * 2  # Entry + exit
    total_fees = entry_fee + cfg.fee_pct * pos.notional  # Entry + exit fee (weighted)

    net_pnl = total_gross - entry_fee - funding_cost

    # Compute weighted avg exit price (untuk log)
    if pos.tp1_hit or pos.tp2_hit or pos.tp3_hit:
        # Simplification: pakai final exit price
        avg_exit_price = exit_price
    else:
        avg_exit_price = exit_price

    return TradeRecord(
        entry_idx=pos.entry_idx,
        exit_idx=exit_idx,
        side=pos.side,
        mode=pos.mode.value,
        entry_price=pos.entry_price,
        exit_price=avg_exit_price,
        size_usd=pos.size_usd,
        tp1_hit=pos.tp1_hit,
        tp2_hit=pos.tp2_hit,
        tp3_hit=pos.tp3_hit,
        exit_reason=exit_reason.value,
        pnl_gross_usd=total_gross + entry_fee,  # Add back to get gross
        pnl_fee_usd=total_fees,
        pnl_slippage_usd=total_slippage,
        pnl_funding_usd=funding_cost,
        pnl_net_usd=net_pnl,
        hold_candles=hold_candles,
    )


# ═════════════════════════════════════════════════════════════
# CIRCUIT BREAKER
# ═════════════════════════════════════════════════════════════

@dataclass
class CircuitBreakerState:
    """State tracker untuk circuit breakers."""
    consecutive_losses: int = 0
    triggered_until_idx: int = -1     # Cooldown until this idx
    peak_equity: float = 0.0
    triggered_reason: str = ""

    def is_paused(self, current_idx: int) -> bool:
        return current_idx < self.triggered_until_idx


def check_circuit_breakers(
    cb: CircuitBreakerState,
    current_equity: float,
    current_idx: int,
    cfg: BacktestConfig,
) -> tuple[CircuitBreakerState, bool]:
    """
    Check semua circuit breakers, trigger pause kalau ada yang kena.

    Returns:
        (updated_cb, is_triggered_now)
    """
    if current_equity > cb.peak_equity:
        cb.peak_equity = current_equity

    triggered = False

    # Breaker 1: consecutive losses
    if cb.consecutive_losses >= cfg.max_consecutive_losses:
        cb.triggered_until_idx = current_idx + cfg.cooldown_after_breaker_candles
        cb.triggered_reason = f"{cb.consecutive_losses} consecutive losses"
        cb.consecutive_losses = 0  # Reset after trigger
        triggered = True

    # Breaker 2: drawdown
    if cb.peak_equity > 0:
        drawdown_pct = (cb.peak_equity - current_equity) / cb.peak_equity
        if drawdown_pct >= cfg.max_drawdown_pct:
            cb.triggered_until_idx = current_idx + cfg.cooldown_after_breaker_candles
            cb.triggered_reason = f"drawdown {drawdown_pct*100:.1f}%"
            triggered = True

    return cb, triggered


# ═════════════════════════════════════════════════════════════
# MAIN BACKTEST LOOP
# ═════════════════════════════════════════════════════════════

def run_regime_backtest(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    cfg: BacktestConfig,
    regime_cfg: Optional[RegimeConfig] = None,
    sm_cfg: Optional[StateMachineConfig] = None,
    cls_cfg: Optional[ClassifierConfig] = None,
    higher_tf_closes: Optional[np.ndarray] = None,
    warmup: int = 100,
) -> BacktestResult:
    """
    Full backtest engine.

    Steps per candle:
    1. Classify regime (Layer 1)
    2. Run state machine transition (Layer 2/3)
    3. Manage active position (TP/SL/timeout)
    4. If ENTER signal + no active position + not paused, open new position
    5. Check circuit breakers

    Returns BacktestResult dengan stats + trades + equity curve.
    """
    import time
    t_start = time.time()

    regime_cfg = regime_cfg or RegimeConfig()
    sm_cfg = sm_cfg or StateMachineConfig()
    cls_cfg = cls_cfg or ClassifierConfig()

    n = len(closes)
    if n < warmup + 50:
        return BacktestResult(
            stats=BacktestStats(),
            trades=[],
            equity_curve=[],
            error=f"Insufficient data: {n} candles, need >= {warmup + 50}",
        )

    # Pre-compute ATR
    atr_array = compute_atr(highs, lows, closes, period=cfg.atr_period)
    atr_median = float(np.median(atr_array[cfg.atr_period:])) if n > cfg.atr_period else 0.0

    # Pre-compute regime + state machine
    regime_states = classify_regime_series(highs, lows, closes, volumes, regime_cfg, warmup=warmup)
    ms_list = run_state_machine(highs, lows, closes, volumes, regime_states, sm_cfg, warmup=warmup)

    # Backtest state
    trades: list[TradeRecord] = []
    equity = cfg.position_usd * 10  # Start with 10x position_usd as bankroll ($100)
    starting_equity = equity
    equity_curve: list[float] = [equity]
    active_pos: Optional[Position] = None
    cb = CircuitBreakerState(peak_equity=equity)

    for idx in range(n):
        if idx < warmup:
            equity_curve.append(equity)
            continue

        # 1. Manage active position
        if active_pos is not None:
            active_pos, exit_reason, exit_price = manage_position(
                active_pos, idx,
                highs[idx], lows[idx], closes[idx],
                atr_array[idx], cfg,
            )
            if exit_reason is not None:
                # Close position
                trade = close_position(active_pos, idx, exit_price, exit_reason, cfg)
                trades.append(trade)
                equity += trade.pnl_net_usd

                # Update consecutive loss counter
                if trade.pnl_net_usd < 0:
                    cb.consecutive_losses += 1
                elif trade.pnl_net_usd > 0:
                    cb.consecutive_losses = 0

                active_pos = None

        # 2. Check circuit breakers
        cb, breaker_triggered = check_circuit_breakers(cb, equity, idx, cfg)

        # 3. Check dead market
        atr_now = atr_array[idx] if idx < len(atr_array) else 0.0
        dead = is_dead_market(atr_now, atr_median, regime_cfg)

        # 4. Try to open new position kalau tidak ada position aktif dan tidak paused
        if active_pos is None and not cb.is_paused(idx) and not dead:
            ms = ms_list[idx]
            if ms.sm_state == SMState.ENTER_LONG or ms.sm_state == SMState.ENTER_SHORT:
                side = "long" if ms.sm_state == SMState.ENTER_LONG else "short"
                regime = regime_states[idx]

                # Determine entry mode
                mode = infer_entry_mode(regime, ms)

                # Determine size mult via bias resolver
                size_mult = 1.0
                if regime.regime in (Regime.ACCUMULATION, Regime.DISTRIBUTION):
                    if regime.current_va is not None and regime.range_start_idx >= 0:
                        # Analyze sideways
                        prior_regime = get_prior_regime(regime_states, regime.range_start_idx)
                        analysis = analyze_sideways(
                            highs, lows, closes, volumes, regime.current_va,
                            start_idx=regime.range_start_idx,
                            end_idx=idx,
                            prior_regime=prior_regime,
                            cfg=cls_cfg,
                            higher_tf_closes=higher_tf_closes,
                        )
                        allowed, size_mult = resolve_entry_bias(analysis, prior_regime, side)
                        if not allowed:
                            equity_curve.append(equity)
                            continue

                # Open position kalau ATR valid
                if atr_now > 0 and regime.current_va is not None:
                    new_pos = open_position(
                        idx=idx,
                        entry_price=closes[idx],
                        side=side,
                        mode=mode,
                        size_mult=size_mult,
                        va=regime.current_va,
                        atr=atr_now,
                        cfg=cfg,
                    )
                    if new_pos is not None:  # None kalau trade invalid (skip)
                        active_pos = new_pos

        equity_curve.append(equity)

    # Close any active position at end
    if active_pos is not None:
        trade = close_position(active_pos, n - 1, closes[-1], ExitReason.END_OF_DATA, cfg)
        trades.append(trade)
        equity += trade.pnl_net_usd
        equity_curve.append(equity)

    # Compute stats
    stats = _compute_stats(trades, equity_curve, starting_equity, cfg, n)
    stats.runtime_sec = time.time() - t_start
    stats.total_candles = n

    return BacktestResult(
        stats=stats,
        trades=trades,
        equity_curve=equity_curve,
    )


# ═════════════════════════════════════════════════════════════
# STATS COMPUTATION
# ═════════════════════════════════════════════════════════════

def _compute_stats(
    trades: list[TradeRecord],
    equity_curve: list[float],
    starting_equity: float,
    cfg: BacktestConfig,
    n_candles: int,
) -> BacktestStats:
    """Compute aggregate stats dari list of trades."""
    if not trades:
        return BacktestStats()

    stats = BacktestStats()
    stats.total_trades = len(trades)

    wins_pnl = []
    losses_pnl = []
    for t in trades:
        if t.pnl_net_usd > 0.01:
            stats.wins += 1
            wins_pnl.append(t.pnl_net_usd)
        elif t.pnl_net_usd < -0.01:
            stats.losses += 1
            losses_pnl.append(t.pnl_net_usd)
        else:
            stats.breakeven += 1

        stats.total_pnl_net += t.pnl_net_usd
        stats.total_pnl_gross += t.pnl_gross_usd
        stats.total_fees += t.pnl_fee_usd

        # Per mode
        if t.mode == "range":
            stats.range_trades += 1
        elif t.mode == "retest":
            stats.retest_trades += 1
        elif t.mode == "trend":
            stats.trend_trades += 1

        # Per exit reason
        reason = t.exit_reason
        stats.exit_by_reason[reason] = stats.exit_by_reason.get(reason, 0) + 1

    denominator = stats.wins + stats.losses
    if denominator > 0:
        stats.win_rate = stats.wins / denominator

    if wins_pnl:
        stats.avg_win_usd = float(np.mean(wins_pnl))
    if losses_pnl:
        stats.avg_loss_usd = float(np.mean(losses_pnl))

    # Per-mode WR
    for mode_name in ("range", "retest", "trend"):
        mode_trades = [t for t in trades if t.mode == mode_name]
        if mode_trades:
            wins = sum(1 for t in mode_trades if t.pnl_net_usd > 0.01)
            losses = sum(1 for t in mode_trades if t.pnl_net_usd < -0.01)
            if wins + losses > 0:
                wr = wins / (wins + losses)
                if mode_name == "range":
                    stats.range_wr = wr
                elif mode_name == "retest":
                    stats.retest_wr = wr
                elif mode_name == "trend":
                    stats.trend_wr = wr

    # Max drawdown
    peak = starting_equity
    max_dd = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
    stats.max_drawdown_usd = max_dd
    stats.max_drawdown_pct = max_dd / starting_equity if starting_equity > 0 else 0.0

    # Trades per day
    days = (n_candles * cfg.candle_hours) / 24.0
    stats.trades_per_day = stats.total_trades / days if days > 0 else 0.0

    return stats


# ═════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════

__all__ = [
    "EntryMode",
    "ExitReason",
    "BacktestConfig",
    "Position",
    "TradeRecord",
    "BacktestStats",
    "BacktestResult",
    "CircuitBreakerState",
    "open_position",
    "manage_position",
    "close_position",
    "check_circuit_breakers",
    "infer_entry_mode",
    "run_regime_backtest",
]
