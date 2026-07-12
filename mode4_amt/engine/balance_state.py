"""
balance_state.py — Balance State Machine (Mode 4 Core)
==========================================================
Design Doc reference: §4 (State Machine 5-state), §7.1.

5 states of market context based on price position vs Value Area + recent
Tier 1 events. State determines which sub-strategy applies.

    BALANCE_INSIDE:     price di dalam VA (VAL ≤ price ≤ VAH), no fresh Tier 1
                        → NO SETUP (market balanced, wait for imbalance)

    BALANCE_EDGE:       price near VAH atau VAL (within edge_atr_dist),
                        no fresh Tier 1 yet
                        → WATCH (about to leave balance)

    IMBALANCE_FRESH:    price recently broke out of VA (< N candles ago),
                        no confirmation yet
                        → SCAN Tier 1 (sweep or breakout)

    IMBALANCE_CONFIRMED: price sustained outside VA + Tier 1 BREAKOUT confirmed
                        (or BOS in direction of imbalance)
                        → Sub-4A active

    SWEEP_REVERSAL:     Tier 1 SWEEP detected + subsequent CHoCH toward opposite
                        → Sub-4B active

State transitions terjadi setiap candle berdasarkan input current.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List
import numpy as np


class BalanceState(str, Enum):
    BALANCE_INSIDE = "BALANCE_INSIDE"
    BALANCE_EDGE = "BALANCE_EDGE"
    IMBALANCE_FRESH = "IMBALANCE_FRESH"
    IMBALANCE_CONFIRMED = "IMBALANCE_CONFIRMED"
    SWEEP_REVERSAL = "SWEEP_REVERSAL"


class ImbalanceDirection(str, Enum):
    UP = "UP"        # price broke above VAH
    DOWN = "DOWN"    # price broke below VAL
    NONE = "NONE"


@dataclass
class BalanceStateResult:
    """Balance state at a specific candle."""
    state: BalanceState
    imbalance_direction: ImbalanceDirection = ImbalanceDirection.NONE
    candles_since_breakout: int = -1     # -1 = never broke out
    poc_distance_atr: float = 0.0        # abs(price - POC) / ATR
    va_position_pct: float = 0.0         # 0..1 position within VA (extrapolate outside)

    # References to trigger events
    active_sweep_idx: int = -1
    active_breakout_idx: int = -1

    # Reason text for logging
    reason: str = ""

    def is_actionable(self) -> bool:
        """True if state is one where entry engines should scan."""
        return self.state in (
            BalanceState.IMBALANCE_CONFIRMED,
            BalanceState.SWEEP_REVERSAL,
        )

    def __repr__(self):
        return (f"BalanceState({self.state.value} "
                f"dir={self.imbalance_direction.value} "
                f"since={self.candles_since_breakout})")


def compute_balance_state(
    current_idx: int,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    vah: Optional[float],
    val: Optional[float],
    poc: Optional[float],
    atr: float,
    recent_sweeps: Optional[List] = None,       # List of SweepEvent
    recent_breakouts: Optional[List] = None,    # List of BreakoutEvent
    recent_structure_events: Optional[List] = None,  # List of StructureEvent
    edge_atr_dist: float = 0.3,
    imbalance_max_age: int = 20,
    sweep_reversal_window: int = 10,
) -> BalanceStateResult:
    """
    Compute balance state at current candle.

    Args:
        current_idx: candle index
        highs/lows/closes: OHLC arrays
        vah, val, poc: Value Area + POC from Volume Profile (or None if not available)
        atr: current ATR
        recent_sweeps: sweeps detected in last N candles
        recent_breakouts: breakouts confirmed in last N candles
        recent_structure_events: BOS/CHoCH events
        edge_atr_dist: how close to VAH/VAL counts as EDGE (in ATR units)
        imbalance_max_age: max candles a breakout stays IMBALANCE_FRESH before EXPIRED
        sweep_reversal_window: candles after sweep to look for CHoCH

    Returns:
        BalanceStateResult with state + context.
    """
    price = float(closes[current_idx])
    result = BalanceStateResult(state=BalanceState.BALANCE_INSIDE)

    if vah is None or val is None or poc is None:
        result.reason = "no VP available"
        return result

    # Position metrics
    va_width = vah - val
    if va_width > 0:
        result.va_position_pct = (price - val) / va_width
    result.poc_distance_atr = abs(price - poc) / atr if atr > 0 else 0

    # === Priority 1: SWEEP_REVERSAL ===
    # If a sweep occurred recently AND a CHoCH followed in the OPPOSITE direction
    if recent_sweeps and recent_structure_events:
        for sw in recent_sweeps[-5:]:  # last 5 sweeps
            age = current_idx - sw.idx
            if age < 0 or age > sweep_reversal_window:
                continue
            # Look for CHoCH within window after sweep
            for ev in recent_structure_events:
                if ev.idx <= sw.idx or ev.idx > current_idx:
                    continue
                if ev.idx - sw.idx > sweep_reversal_window:
                    continue
                # BSL sweep (UP) + CHoCH_DOWN = bearish reversal
                # SSL sweep (DOWN) + CHoCH_UP = bullish reversal
                sw_dir = sw.direction.value if hasattr(sw.direction, 'value') else str(sw.direction)
                ev_type = ev.event_type.value if hasattr(ev.event_type, 'value') else str(ev.event_type)
                if sw_dir == "UP" and ev_type == "CHOCH_DOWN":
                    result.state = BalanceState.SWEEP_REVERSAL
                    result.imbalance_direction = ImbalanceDirection.DOWN
                    result.active_sweep_idx = sw.idx
                    result.reason = f"BSL sweep@{sw.idx} + CHoCH_DOWN@{ev.idx}"
                    return result
                if sw_dir == "DOWN" and ev_type == "CHOCH_UP":
                    result.state = BalanceState.SWEEP_REVERSAL
                    result.imbalance_direction = ImbalanceDirection.UP
                    result.active_sweep_idx = sw.idx
                    result.reason = f"SSL sweep@{sw.idx} + CHoCH_UP@{ev.idx}"
                    return result

    # === Priority 2: IMBALANCE_CONFIRMED ===
    # Breakout confirmed + price still on breakout side
    if recent_breakouts:
        for br in recent_breakouts[-5:]:
            age = current_idx - br.confirmation_idx
            if age < 0 or age > imbalance_max_age:
                continue
            br_dir = br.direction.value if hasattr(br.direction, 'value') else str(br.direction)
            if br_dir == "UP" and price > vah:
                result.state = BalanceState.IMBALANCE_CONFIRMED
                result.imbalance_direction = ImbalanceDirection.UP
                result.candles_since_breakout = age
                result.active_breakout_idx = br.idx
                result.reason = f"Breakout UP confirmed@{br.confirmation_idx}, price above VAH"
                return result
            if br_dir == "DOWN" and price < val:
                result.state = BalanceState.IMBALANCE_CONFIRMED
                result.imbalance_direction = ImbalanceDirection.DOWN
                result.candles_since_breakout = age
                result.active_breakout_idx = br.idx
                result.reason = f"Breakout DOWN confirmed@{br.confirmation_idx}, price below VAL"
                return result

    # === Priority 3: IMBALANCE_FRESH ===
    # Price recently broke out of VA but no Tier 1 confirmation yet
    if price > vah or price < val:
        # Check when price first broke out in current move
        breakout_dir = ImbalanceDirection.UP if price > vah else ImbalanceDirection.DOWN
        lookback = min(current_idx, imbalance_max_age)
        first_break = -1
        for k in range(current_idx, current_idx - lookback, -1):
            if k < 0: break
            c = float(closes[k])
            if breakout_dir == ImbalanceDirection.UP:
                if c <= vah:
                    first_break = k + 1
                    break
            else:
                if c >= val:
                    first_break = k + 1
                    break
        else:
            first_break = max(0, current_idx - lookback)

        age = current_idx - first_break
        if age <= imbalance_max_age:
            result.state = BalanceState.IMBALANCE_FRESH
            result.imbalance_direction = breakout_dir
            result.candles_since_breakout = age
            result.reason = f"Price outside VA {age} candles ago, no Tier 1 confirm yet"
            return result

    # === Priority 4: BALANCE_EDGE ===
    # Price near VAH or VAL
    edge_dist = edge_atr_dist * atr
    if val - edge_dist <= price <= val + edge_dist:
        result.state = BalanceState.BALANCE_EDGE
        result.reason = f"Price near VAL ({val:.4f})"
        return result
    if vah - edge_dist <= price <= vah + edge_dist:
        result.state = BalanceState.BALANCE_EDGE
        result.reason = f"Price near VAH ({vah:.4f})"
        return result

    # === Default: BALANCE_INSIDE ===
    result.state = BalanceState.BALANCE_INSIDE
    result.reason = f"Price inside VA at {result.va_position_pct*100:.0f}%"
    return result


__all__ = [
    "BalanceState", "ImbalanceDirection", "BalanceStateResult",
    "compute_balance_state",
]
