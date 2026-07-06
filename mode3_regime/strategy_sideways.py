"""
strategy_sideways.py — Sideways Tektok Strategy v0.1
======================================================
Standalone strategy khusus untuk regime ACCUMULATION / DISTRIBUTION / MID_RANGE.
Tektok VAH-VAL: semua touch dieksekusi, full size (baseline).

Layer 2+ (confidence scoring untuk adjust size) akan ditambah di Round 2
berdasarkan hasil Round 1.
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass
from enum import Enum

from .regime import Regime, RegimeState
from .microevent import MicroEvent


class SideEnum(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"


class SidewaysMode(Enum):
    BOUNCE_VAL = "bounce_val"          # LONG dari VAL touch
    REJECT_VAH = "reject_vah"          # SHORT dari VAH reject
    FAKE_BREAKDOWN = "fake_breakdown"  # LONG counter dari wick below VAL
    FAKE_BREAKOUT = "fake_breakout"    # SHORT counter dari wick above VAH


@dataclass
class SidewaysConfig:
    # Range detection (harus lebih strict dari default regime detector)
    range_max_width_pct: float = 0.03      # width < 3% qualify as tight range

    # Touch tolerance
    touch_tolerance: float = 0.003          # 0.3% dari level

    # Volume threshold
    volume_multiplier: float = 1.3          # candle volume > 1.3x avg

    # Cooldown
    cooldown_bars: int = 10

    # Regime filter — hanya trade kalau salah satu dari ini
    allowed_regimes: tuple = (
        Regime.ACCUMULATION,
        Regime.DISTRIBUTION,
        Regime.UNKNOWN,  # UNKNOWN sering = ambiguous sideways, tetap trade
    )


@dataclass
class SidewaysSignal:
    idx: int
    side: SideEnum
    mode: SidewaysMode
    price: float
    val: float
    vah: float
    poc: float
    regime: str
    confidence: float = 1.0  # Baseline v0.1: semua 1.0. Round 2+ akan variable.
    reason: str = ""


def generate_sideways_signals(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: SidewaysConfig,
) -> list[SidewaysSignal]:
    """
    Generate signals sideways tektok baseline.
    Baseline: semua touch VAL/VAH yang qualify dieksekusi, confidence = 1.0.
    """
    n = len(closes)
    signals: list[SidewaysSignal] = []

    # Volume average (20-bar rolling)
    vol_avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - 19)
        vol_avg[i] = float(np.mean(volumes[start:i + 1])) if i > start else 1.0

    last_long_bar = -9999
    last_short_bar = -9999

    for i in range(50, n):
        rs = regime_states[i]

        # Filter 1: harus di regime yang di-allow
        if rs.regime not in cfg.allowed_regimes:
            continue

        # Filter 2: range width harus qualify
        if rs.range_width_pct <= 0 or rs.range_width_pct >= cfg.range_max_width_pct:
            continue

        vah = rs.vah
        val = rs.val
        poc = rs.poc

        if vah <= 0 or val <= 0 or vah <= val:
            continue

        h, l, c = highs[i], lows[i], closes[i]
        v = volumes[i]
        vol_ok = v > vol_avg[i] * cfg.volume_multiplier

        # Cooldown
        cooldown_long_ok = (i - last_long_bar) >= cfg.cooldown_bars
        cooldown_short_ok = (i - last_short_bar) >= cfg.cooldown_bars

        # Touch detection
        touch_val = (l <= val * (1 + cfg.touch_tolerance)) and (l >= val * (1 - cfg.touch_tolerance))
        touch_vah = (h >= vah * (1 - cfg.touch_tolerance)) and (h <= vah * (1 + cfg.touch_tolerance))

        wick_below_val = l < val * (1 - cfg.touch_tolerance) and c > val
        wick_above_vah = h > vah * (1 + cfg.touch_tolerance) and c < vah

        # Candle direction
        bullish_candle = c > closes[i - 1] and c > (h + l) / 2
        bearish_candle = c < closes[i - 1] and c < (h + l) / 2

        # ─── ENTRY: LONG BOUNCE VAL ───
        if touch_val and bullish_candle and vol_ok and c > val and cooldown_long_ok:
            signals.append(SidewaysSignal(
                idx=i, side=SideEnum.LONG, mode=SidewaysMode.BOUNCE_VAL,
                price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                regime=rs.regime.value, confidence=1.0,
                reason="touch_val_bullish_vol_ok",
            ))
            last_long_bar = i
            continue

        # ─── ENTRY: LONG FAKE BREAKDOWN ───
        if wick_below_val and vol_ok and cooldown_long_ok:
            signals.append(SidewaysSignal(
                idx=i, side=SideEnum.LONG, mode=SidewaysMode.FAKE_BREAKDOWN,
                price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                regime=rs.regime.value, confidence=1.0,
                reason="wick_below_val_reclaim",
            ))
            last_long_bar = i
            continue

        # ─── ENTRY: SHORT REJECT VAH ───
        if touch_vah and bearish_candle and vol_ok and c < vah and cooldown_short_ok:
            signals.append(SidewaysSignal(
                idx=i, side=SideEnum.SHORT, mode=SidewaysMode.REJECT_VAH,
                price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                regime=rs.regime.value, confidence=1.0,
                reason="touch_vah_bearish_vol_ok",
            ))
            last_short_bar = i
            continue

        # ─── ENTRY: SHORT FAKE BREAKOUT ───
        if wick_above_vah and vol_ok and cooldown_short_ok:
            signals.append(SidewaysSignal(
                idx=i, side=SideEnum.SHORT, mode=SidewaysMode.FAKE_BREAKOUT,
                price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                regime=rs.regime.value, confidence=1.0,
                reason="wick_above_vah_rejection",
            ))
            last_short_bar = i
            continue

    return signals


__all__ = ["SideEnum", "SidewaysMode", "SidewaysConfig", "SidewaysSignal", "generate_sideways_signals"]
