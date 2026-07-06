"""
state_machine.py — Phase B: 3-way Confirmation State Machine
=============================================================

State machine untuk decide entry setelah price touch level (VAH/VAL).
Setiap kali level touched, bot masuk WATCHING state, lalu evaluate
2-5 candle berikutnya untuk classify:
  - True bounce → ENTER counter (LONG di VAL, SHORT di VAH)
  - True breakdown/breakout → ENTER searah break (regime change)
  - Fake break → ENTER counter-trap (aggressive)
  - Undecided → ABANDON setelah timeout

Context-aware filter:
  - Kalau bot baru exit LONG → filter ketat (transisi risk tinggi)
  - Kalau range confirmed → filter longgar
  - Kalau ambiguous → medium filter

Author: BabaBot team
Version: 0.1.0 (Phase B)
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from .regime import Regime, RegimeConfig, ValueArea, RegimeState


# ═════════════════════════════════════════════════════════════
# ENUMS
# ═════════════════════════════════════════════════════════════

class SMState(Enum):
    """State machine states."""
    FLAT = "flat"                          # Idle, watching for setup
    WATCHING_VAL = "watching_val"          # Price touched VAL, evaluating
    WATCHING_VAH = "watching_vah"          # Price touched VAH, evaluating
    TENTATIVE_LONG = "tentative_long"      # Bias LONG, need +1 candle
    TENTATIVE_SHORT = "tentative_short"    # Bias SHORT, need +1 candle
    ENTER_LONG = "enter_long"              # Confirmed, trigger entry
    ENTER_SHORT = "enter_short"            # Confirmed, trigger entry
    ABANDON = "abandon"                    # Timeout / clarity gone


class BreakType(Enum):
    """Klasifikasi break event."""
    NONE = "none"                          # No break yet
    TRUE_BOUNCE = "true_bounce"            # Reclaim level, buyer stepping in
    TRUE_BREAKDOWN = "true_breakdown"      # Continue beyond level, regime change
    TRUE_BREAKOUT = "true_breakout"        # Break VAH up, regime change bull
    FAKE_BREAKDOWN = "fake_breakdown"      # Wick beyond VAL, close back inside
    FAKE_BREAKOUT = "fake_breakout"        # Wick beyond VAH, close back inside
    UNDECIDED = "undecided"                # Hover, no clarity


class BotContext(Enum):
    """Context bot saat ini — untuk adaptive filter."""
    FLAT_RANGE_CONFIRMED = "flat_range"          # Bot flat, range udah lama confirmed
    FLAT_RECENT_LONG_EXIT = "flat_after_long"    # Baru exit LONG (regime change risk)
    FLAT_RECENT_SHORT_EXIT = "flat_after_short"  # Baru exit SHORT (regime change risk)
    FLAT_DEFAULT = "flat_default"                # Default flat state
    IN_POSITION = "in_position"                  # Sudah punya position (trailing handle)


# ═════════════════════════════════════════════════════════════
# CONFIG
# ═════════════════════════════════════════════════════════════

@dataclass
class StateMachineConfig:
    """Tunable parameters untuk state machine."""

    # Confirmation window
    watching_max_candles: int = 5              # Timeout ABANDON kalau 5 candle nggak clarity
    confirmation_candles: int = 2              # Consecutive candles butuh untuk CONFIRMED

    # Reclaim thresholds (untuk true bounce detection)
    reclaim_buffer_pct: float = 0.001          # 0.1% buffer di atas VWAP-1σ untuk reclaim
    reclaim_volume_multiplier: float = 1.2     # Volume butuh 1.2x average untuk valid reclaim

    # Fake break detection
    fake_break_max_candles: int = 1            # Max 1 candle beyond level untuk qualify as fake
    fake_break_close_recovery: float = 0.005   # Close balik 0.5% dari extreme = fake

    # True break detection
    breakdown_confirmation_candles: int = 2    # 2 candle close beyond level = true break
    breakdown_volume_multiplier: float = 1.5   # Volume 1.5x avg = strong break

    # Context-aware buffer multipliers
    context_range_confirmed_multiplier: float = 0.5   # Longgar (buffer × 0.5)
    context_recent_exit_multiplier: float = 2.0       # Ketat (buffer × 2.0)
    context_default_multiplier: float = 1.0           # Normal

    # Cooldown after ABANDON
    cooldown_candles: int = 3                  # Wait 3 candle sebelum re-enter WATCHING

    # Level touch detection
    touch_tolerance_pct: float = 0.002         # 0.2% tolerance untuk "touch"


# ═════════════════════════════════════════════════════════════
# STATE OBJECT
# ═════════════════════════════════════════════════════════════

@dataclass
class MachineState:
    """Current state of the machine at a specific candle."""
    sm_state: SMState = SMState.FLAT
    bot_context: BotContext = BotContext.FLAT_DEFAULT

    # Watching tracking
    watching_start_idx: int = -1               # Candle idx saat masuk WATCHING
    watching_touch_price: float = 0.0          # Price saat touch level
    watching_level_side: str = ""              # "val" or "vah"

    # Tentative tracking
    tentative_start_idx: int = -1
    tentative_confirmation_count: int = 0

    # Cooldown
    cooldown_until_idx: int = -1               # Idx kapan cooldown expire

    # History for context
    last_exit_side: str = ""                   # "long" or "short" (untuk context)
    last_exit_idx: int = -1

    # Detected event (current candle)
    detected_break: BreakType = BreakType.NONE

    # For debug / log
    reason: str = ""


# ═════════════════════════════════════════════════════════════
# BREAK CLASSIFIER
# ═════════════════════════════════════════════════════════════

def classify_break(
    candles_high: np.ndarray,
    candles_low: np.ndarray,
    candles_close: np.ndarray,
    candles_volume: np.ndarray,
    watching_idx: int,       # Idx saat WATCHING start
    current_idx: int,        # Idx sekarang
    level_price: float,      # VAL atau VAH price
    level_side: str,         # "val" or "vah"
    va: ValueArea,           # Current value area
    cfg: StateMachineConfig,
    volume_avg: float,       # Rolling average volume untuk comparison
) -> BreakType:
    """
    Classify break type dari candle sequence sejak WATCHING mulai.

    Logic:
    - Ambil candles dari watching_idx sampai current_idx (inclusive)
    - Analyze:
        * Close reclaim vwap_lower/upper? → true_bounce
        * Consecutive close beyond level? → true_breakdown/breakout
        * Wick beyond + close inside? → fake_break
        * None of above → undecided
    """
    if current_idx <= watching_idx:
        return BreakType.NONE

    slice_len = current_idx - watching_idx + 1
    if slice_len < 2:
        return BreakType.UNDECIDED

    slice_close = candles_close[watching_idx:current_idx + 1]
    slice_high = candles_high[watching_idx:current_idx + 1]
    slice_low = candles_low[watching_idx:current_idx + 1]
    slice_volume = candles_volume[watching_idx:current_idx + 1]

    current_close = candles_close[current_idx]
    current_volume = candles_volume[current_idx]

    volume_ok_reclaim = current_volume >= volume_avg * cfg.reclaim_volume_multiplier
    volume_ok_break = current_volume >= volume_avg * cfg.breakdown_volume_multiplier

    if level_side == "val":
        # ─── Watching VAL (support test) ───
        vwap_lower = va.vwap_lower
        reclaim_threshold = vwap_lower * (1 + cfg.reclaim_buffer_pct)

        # Check true bounce: close naik reclaim vwap_lower with volume
        if current_close >= reclaim_threshold and volume_ok_reclaim:
            # Also check trajectory: consecutive candles moving up
            if slice_len >= 2 and slice_close[-1] > slice_close[-2]:
                return BreakType.TRUE_BOUNCE

        # Check true breakdown: consecutive closes below VAL
        below_val_count = int(np.sum(slice_close < level_price))
        if below_val_count >= cfg.breakdown_confirmation_candles and volume_ok_break:
            # Additional check: latest close is lowest in slice
            if slice_close[-1] <= float(np.min(slice_close[:-1])) * 1.001:
                return BreakType.TRUE_BREAKDOWN

        # Check fake breakdown: wick beyond VAL but close back above
        wicks_below = slice_low < level_price
        closes_above = slice_close >= level_price
        # Look for pattern: wick down, then close back inside
        for i in range(slice_len - 1):
            if wicks_below[i] and closes_above[i + 1] if i + 1 < slice_len else False:
                # Fake break detected
                recovery_pct = (
                    (slice_close[i + 1] - float(np.min(slice_low[:i + 1])))
                    / level_price
                )
                if recovery_pct >= cfg.fake_break_close_recovery:
                    return BreakType.FAKE_BREAKDOWN

    else:  # level_side == "vah"
        # ─── Watching VAH (resistance test) ───
        vwap_upper = va.vwap_upper
        reject_threshold = vwap_upper * (1 - cfg.reclaim_buffer_pct)

        # Check true rejection (bounce down from VAH)
        if current_close <= reject_threshold and volume_ok_reclaim:
            if slice_len >= 2 and slice_close[-1] < slice_close[-2]:
                return BreakType.TRUE_BOUNCE

        # Check true breakout: consecutive closes above VAH
        above_vah_count = int(np.sum(slice_close > level_price))
        if above_vah_count >= cfg.breakdown_confirmation_candles and volume_ok_break:
            if slice_close[-1] >= float(np.max(slice_close[:-1])) * 0.999:
                return BreakType.TRUE_BREAKOUT

        # Check fake breakout
        wicks_above = slice_high > level_price
        closes_below = slice_close <= level_price
        for i in range(slice_len - 1):
            if wicks_above[i] and closes_below[i + 1] if i + 1 < slice_len else False:
                recovery_pct = (
                    (float(np.max(slice_high[:i + 1])) - slice_close[i + 1])
                    / level_price
                )
                if recovery_pct >= cfg.fake_break_close_recovery:
                    return BreakType.FAKE_BREAKOUT

    return BreakType.UNDECIDED


# ═════════════════════════════════════════════════════════════
# CONTEXT DETECTION
# ═════════════════════════════════════════════════════════════

def determine_context(
    ms: MachineState,
    current_idx: int,
    regime_state: RegimeState,
) -> BotContext:
    """
    Determine current bot context untuk adaptive filter.

    Priority:
    1. In position → IN_POSITION
    2. Baru exit LONG dalam 10 candle → FLAT_RECENT_LONG_EXIT
    3. Baru exit SHORT dalam 10 candle → FLAT_RECENT_SHORT_EXIT
    4. Range confirmed regime → FLAT_RANGE_CONFIRMED
    5. Default → FLAT_DEFAULT
    """
    # Priority 1: in position (handled elsewhere, but include for completeness)
    if ms.sm_state in (SMState.ENTER_LONG, SMState.ENTER_SHORT):
        return BotContext.IN_POSITION

    # Priority 2 & 3: recent exit
    if ms.last_exit_idx >= 0 and (current_idx - ms.last_exit_idx) <= 10:
        if ms.last_exit_side == "long":
            return BotContext.FLAT_RECENT_LONG_EXIT
        elif ms.last_exit_side == "short":
            return BotContext.FLAT_RECENT_SHORT_EXIT

    # Priority 4: range confirmed
    if regime_state.regime in (Regime.ACCUMULATION, Regime.DISTRIBUTION):
        if regime_state.current_va is not None and regime_state.current_va.is_anchored:
            return BotContext.FLAT_RANGE_CONFIRMED

    return BotContext.FLAT_DEFAULT


def context_buffer_multiplier(ctx: BotContext, cfg: StateMachineConfig) -> float:
    """Return buffer multiplier untuk given context."""
    if ctx == BotContext.FLAT_RANGE_CONFIRMED:
        return cfg.context_range_confirmed_multiplier
    elif ctx in (BotContext.FLAT_RECENT_LONG_EXIT, BotContext.FLAT_RECENT_SHORT_EXIT):
        return cfg.context_recent_exit_multiplier
    else:
        return cfg.context_default_multiplier


# ═════════════════════════════════════════════════════════════
# LEVEL TOUCH DETECTION
# ═════════════════════════════════════════════════════════════

def detect_level_touch(
    price_high: float,
    price_low: float,
    va: ValueArea,
    cfg: StateMachineConfig,
    context_multiplier: float = 1.0,
) -> Optional[str]:
    """
    Detect kalau candle touch VAL atau VAH.

    Returns:
        "val" kalau touch VAL
        "vah" kalau touch VAH
        None kalau nggak touch
    """
    tolerance = cfg.touch_tolerance_pct * context_multiplier

    # VAL touch: low candle mencapai VAL range
    val_upper = va.val * (1 + tolerance)
    val_lower = va.val * (1 - tolerance)
    if price_low <= val_upper and price_low >= val_lower:
        return "val"

    # VAH touch: high candle mencapai VAH range
    vah_upper = va.vah * (1 + tolerance)
    vah_lower = va.vah * (1 - tolerance)
    if price_high >= vah_lower and price_high <= vah_upper:
        return "vah"

    return None


# ═════════════════════════════════════════════════════════════
# STATE MACHINE TRANSITION
# ═════════════════════════════════════════════════════════════

def transition_state(
    ms: MachineState,
    idx: int,
    candles_high: np.ndarray,
    candles_low: np.ndarray,
    candles_close: np.ndarray,
    candles_volume: np.ndarray,
    regime_state: RegimeState,
    cfg: StateMachineConfig,
    volume_avg: float,
) -> MachineState:
    """
    Advance state machine dari current state ke next state di candle idx.

    Return new MachineState (immutable transition).
    """
    # Copy state (biar nggak mutate)
    new_state = MachineState(
        sm_state=ms.sm_state,
        bot_context=ms.bot_context,
        watching_start_idx=ms.watching_start_idx,
        watching_touch_price=ms.watching_touch_price,
        watching_level_side=ms.watching_level_side,
        tentative_start_idx=ms.tentative_start_idx,
        tentative_confirmation_count=ms.tentative_confirmation_count,
        cooldown_until_idx=ms.cooldown_until_idx,
        last_exit_side=ms.last_exit_side,
        last_exit_idx=ms.last_exit_idx,
    )

    # Determine current context
    new_state.bot_context = determine_context(ms, idx, regime_state)
    ctx_mult = context_buffer_multiplier(new_state.bot_context, cfg)

    # Skip if in cooldown
    if idx < ms.cooldown_until_idx:
        new_state.sm_state = SMState.FLAT
        new_state.reason = "cooldown_active"
        return new_state

    va = regime_state.current_va
    if va is None:
        # No VA available yet (warmup) — stay FLAT
        new_state.sm_state = SMState.FLAT
        new_state.reason = "no_value_area"
        return new_state

    current_high = candles_high[idx]
    current_low = candles_low[idx]

    # ─── FLAT → WATCHING transition ───
    if ms.sm_state == SMState.FLAT:
        touch = detect_level_touch(current_high, current_low, va, cfg, ctx_mult)
        if touch == "val":
            new_state.sm_state = SMState.WATCHING_VAL
            new_state.watching_start_idx = idx
            new_state.watching_touch_price = va.val
            new_state.watching_level_side = "val"
            new_state.reason = "touched_val"
        elif touch == "vah":
            new_state.sm_state = SMState.WATCHING_VAH
            new_state.watching_start_idx = idx
            new_state.watching_touch_price = va.vah
            new_state.watching_level_side = "vah"
            new_state.reason = "touched_vah"
        else:
            new_state.reason = "no_touch"
        return new_state

    # ─── WATCHING → TENTATIVE / CONFIRMED / ABANDON ───
    if ms.sm_state in (SMState.WATCHING_VAL, SMState.WATCHING_VAH):
        candles_since_watching = idx - ms.watching_start_idx

        # Timeout check
        if candles_since_watching >= cfg.watching_max_candles:
            new_state.sm_state = SMState.ABANDON
            new_state.cooldown_until_idx = idx + cfg.cooldown_candles
            new_state.reason = "watching_timeout"
            new_state.detected_break = BreakType.UNDECIDED
            return new_state

        # Classify break
        break_type = classify_break(
            candles_high, candles_low, candles_close, candles_volume,
            watching_idx=ms.watching_start_idx,
            current_idx=idx,
            level_price=ms.watching_touch_price,
            level_side=ms.watching_level_side,
            va=va,
            cfg=cfg,
            volume_avg=volume_avg,
        )
        new_state.detected_break = break_type

        if break_type == BreakType.TRUE_BOUNCE:
            if ms.watching_level_side == "val":
                new_state.sm_state = SMState.ENTER_LONG
                new_state.reason = "true_bounce_val"
            else:
                new_state.sm_state = SMState.ENTER_SHORT
                new_state.reason = "true_reject_vah"
        elif break_type == BreakType.TRUE_BREAKDOWN:
            new_state.sm_state = SMState.ENTER_SHORT
            new_state.reason = "true_breakdown_val"
        elif break_type == BreakType.TRUE_BREAKOUT:
            new_state.sm_state = SMState.ENTER_LONG
            new_state.reason = "true_breakout_vah"
        elif break_type == BreakType.FAKE_BREAKDOWN:
            # Aggressive counter-trap: enter LONG
            new_state.sm_state = SMState.ENTER_LONG
            new_state.reason = "fake_breakdown_counter"
        elif break_type == BreakType.FAKE_BREAKOUT:
            new_state.sm_state = SMState.ENTER_SHORT
            new_state.reason = "fake_breakout_counter"
        else:
            # UNDECIDED — stay watching
            new_state.sm_state = ms.sm_state
            new_state.reason = "still_watching"

        return new_state

    # ─── TENTATIVE (unused in simple version, kept for future) ───
    # In this simplified state machine, we skip TENTATIVE and go directly
    # from WATCHING to ENTER when confidence is high.

    # ─── ABANDON → FLAT ───
    if ms.sm_state == SMState.ABANDON:
        new_state.sm_state = SMState.FLAT
        new_state.reason = "reset_after_abandon"
        return new_state

    # ─── ENTER_* → FLAT (single-tick entry) ───
    if ms.sm_state in (SMState.ENTER_LONG, SMState.ENTER_SHORT):
        # Entry sudah dieksekusi di previous tick, reset ke FLAT
        # (position management handled outside state machine)
        new_state.sm_state = SMState.FLAT
        new_state.reason = "post_entry_reset"
        return new_state

    return new_state


# ═════════════════════════════════════════════════════════════
# BATCH RUNNER
# ═════════════════════════════════════════════════════════════

def run_state_machine(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: StateMachineConfig,
    volume_window: int = 24,
    warmup: int = 100,
) -> list[MachineState]:
    """
    Run state machine untuk full series.

    Returns list of MachineState per candle.
    """
    n = len(closes)
    ms_list: list[MachineState] = []
    current_state = MachineState()

    for idx in range(n):
        if idx < warmup:
            ms_list.append(MachineState(reason="warmup"))
            continue

        # Compute rolling volume average
        vol_start = max(0, idx - volume_window)
        volume_avg = float(np.mean(volumes[vol_start:idx + 1])) if idx > vol_start else 1.0

        # Transition
        new_state = transition_state(
            current_state,
            idx=idx,
            candles_high=highs,
            candles_low=lows,
            candles_close=closes,
            candles_volume=volumes,
            regime_state=regime_states[idx],
            cfg=cfg,
            volume_avg=volume_avg,
        )
        ms_list.append(new_state)
        current_state = new_state

    return ms_list


# ═════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════

__all__ = [
    "SMState",
    "BreakType",
    "BotContext",
    "StateMachineConfig",
    "MachineState",
    "classify_break",
    "determine_context",
    "context_buffer_multiplier",
    "detect_level_touch",
    "transition_state",
    "run_state_machine",
]
