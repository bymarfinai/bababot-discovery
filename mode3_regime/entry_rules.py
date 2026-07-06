"""
entry_rules.py — Adaptive Entry Rules per Regime
==================================================
Menghubungkan 3 layer (regime + transition + microevent + bias) ke
decision entry LONG/SHORT dengan alasan spesifik.

Rules per regime:
- BULL_MARKUP: LONG di pullback ke EMA20 (failed retest resistance)
- BEAR_MARKDOWN: SHORT di rally failed di EMA20
- ACCUMULATION: LONG bounce VAL, block SHORT
- DISTRIBUTION: SHORT reject VAH, block LONG
- UNKNOWN/ambiguous: allow both dengan bias filter
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .regime import Regime, RegimeState
from .transition import Transition, TransitionState
from .microevent import MicroEvent, Bias


class EntrySide(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"


class EntryMode(Enum):
    RANGE_BOUNCE = "range_bounce"      # Accumulation: bounce VAL
    RANGE_REJECT = "range_reject"      # Distribution: reject VAH
    RANGE_FAKE = "range_fake"           # Counter-trap
    TREND_PULLBACK = "trend_pullback"   # Bull: dip di EMA20 / Bear: rally di EMA20
    TREND_RETEST = "trend_retest"       # Retest old level after break
    TREND_FAILED_RALLY = "failed_rally" # Bear continuation di EMA20
    TREND_FAILED_DIP = "failed_dip"     # Bull continuation di EMA20


@dataclass
class EntryConfig:
    cooldown_bars: int = 10
    ema_touch_tolerance: float = 0.005    # 0.5% dari EMA20 = touching
    ema_reject_close_pct: float = 0.003   # close 0.3% below EMA = reject confirmed


@dataclass
class EntrySignal:
    idx: int
    side: EntrySide
    mode: EntryMode
    price: float
    reason: str
    regime: str
    bias: str


def generate_entry_signals(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    regime_states: list[RegimeState],
    events: list[MicroEvent],
    biases: list[Bias],
    cfg: EntryConfig,
) -> list[EntrySignal]:
    """
    Generate entry signals per bar dengan adaptif rules.
    """
    n = len(closes)
    signals: list[EntrySignal] = []
    last_long_bar = -9999
    last_short_bar = -9999

    for i in range(50, n):
        rs = regime_states[i]
        ev = events[i]
        bias = biases[i]

        cooldown_long_ok = (i - last_long_bar) >= cfg.cooldown_bars
        cooldown_short_ok = (i - last_short_bar) >= cfg.cooldown_bars

        entry_side = EntrySide.NONE
        entry_mode = EntryMode.RANGE_BOUNCE
        reason = ""

        # ─── ACCUMULATION regime ───
        if rs.regime == Regime.ACCUMULATION:
            # Allow LONG bounce, block SHORT
            if bias != Bias.BEARISH and cooldown_long_ok:
                if ev == MicroEvent.TRUE_BOUNCE and lows[i] <= rs.val * 1.003:
                    entry_side = EntrySide.LONG
                    entry_mode = EntryMode.RANGE_BOUNCE
                    reason = "accum_bounce_val"
                elif ev == MicroEvent.FAKE_BREAKDOWN:
                    entry_side = EntrySide.LONG
                    entry_mode = EntryMode.RANGE_FAKE
                    reason = "accum_fake_breakdown_counter"

        # ─── DISTRIBUTION regime ───
        elif rs.regime == Regime.DISTRIBUTION:
            if bias != Bias.BULLISH and cooldown_short_ok:
                if ev == MicroEvent.TRUE_BOUNCE and highs[i] >= rs.vah * 0.997:
                    entry_side = EntrySide.SHORT
                    entry_mode = EntryMode.RANGE_REJECT
                    reason = "distrib_reject_vah"
                elif ev == MicroEvent.FAKE_BREAKOUT:
                    entry_side = EntrySide.SHORT
                    entry_mode = EntryMode.RANGE_FAKE
                    reason = "distrib_fake_breakout_counter"

        # ─── BULL_MARKUP regime ───
        elif rs.regime == Regime.BULL_MARKUP:
            # LONG di pullback ke EMA20 dengan bounce
            if bias != Bias.BEARISH and cooldown_long_ok:
                ema_touch = lows[i] <= rs.ema_fast * (1 + cfg.ema_touch_tolerance) and lows[i] >= rs.ema_fast * (1 - cfg.ema_touch_tolerance)
                bullish_close = closes[i] > rs.ema_fast and closes[i] > closes[i - 1]
                if ema_touch and bullish_close:
                    entry_side = EntrySide.LONG
                    entry_mode = EntryMode.TREND_PULLBACK
                    reason = "bull_pullback_ema20"

        # ─── BEAR_MARKDOWN regime ───
        elif rs.regime == Regime.BEAR_MARKDOWN:
            # SHORT di failed rally at EMA20 (LU MINTA INI)
            if bias != Bias.BULLISH and cooldown_short_ok:
                ema_touch = highs[i] >= rs.ema_fast * (1 - cfg.ema_touch_tolerance) and highs[i] <= rs.ema_fast * (1 + cfg.ema_touch_tolerance)
                bearish_close = closes[i] < rs.ema_fast and closes[i] < closes[i - 1]
                if ema_touch and bearish_close:
                    entry_side = EntrySide.SHORT
                    entry_mode = EntryMode.TREND_FAILED_RALLY
                    reason = "bear_failed_rally_ema20"

        # ─── UNKNOWN / ambiguous ───
        else:
            # Fallback: allow both dengan strict bias filter
            if ev == MicroEvent.TRUE_BOUNCE and lows[i] <= rs.val * 1.003 and bias != Bias.BEARISH and cooldown_long_ok:
                entry_side = EntrySide.LONG
                entry_mode = EntryMode.RANGE_BOUNCE
                reason = "unknown_bounce_val"
            elif ev == MicroEvent.TRUE_BOUNCE and highs[i] >= rs.vah * 0.997 and bias != Bias.BULLISH and cooldown_short_ok:
                entry_side = EntrySide.SHORT
                entry_mode = EntryMode.RANGE_REJECT
                reason = "unknown_reject_vah"

        if entry_side != EntrySide.NONE:
            signals.append(EntrySignal(
                idx=i,
                side=entry_side,
                mode=entry_mode,
                price=float(closes[i]),
                reason=reason,
                regime=rs.regime.value,
                bias=bias.value,
            ))
            if entry_side == EntrySide.LONG:
                last_long_bar = i
            else:
                last_short_bar = i

    return signals


__all__ = ["EntrySide", "EntryMode", "EntryConfig", "EntrySignal", "generate_entry_signals"]
