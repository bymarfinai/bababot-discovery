"""
strategy_sideways.py — Sideways Tektok Strategy v0.4
======================================================
v0.4 changes (MTF Container Integration):
- Accept optional mtf_classifications parameter (from mtf_container.classify_mtf)
- PRIMARY filter: skip signals where mtf.inside_confidence < min_mtf_confidence
- PRIMARY sizing: position size = f(mtf.inside_confidence)
  * 3/3 (inside all 3 containers) -> full size (1.0)
  * 2/3 -> half size (0.5)
  * 1/3 -> skip (unless enable_low_conf_quarter=True, then quarter)
  * 0/3 -> skip (definitive break)
- v0.3 5-signal scoring DISABLED by default (isolate MTF effect)
- Backward compat: works without mtf_classifications
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .regime import Regime, RegimeState
from .microevent import MicroEvent
from .indicators import ema


class SideEnum(Enum):
    NONE = "none"
    LONG = "long"
    SHORT = "short"


class SidewaysMode(Enum):
    BOUNCE_VAL = "bounce_val"
    REJECT_VAH = "reject_vah"
    FAKE_BREAKDOWN = "fake_breakdown"
    FAKE_BREAKOUT = "fake_breakout"


def _default_allowed_regimes():
    return (Regime.ACCUMULATION, Regime.DISTRIBUTION, Regime.UNKNOWN)


@dataclass
class SidewaysConfig:
    range_max_width_pct: float = 0.03
    touch_tolerance: float = 0.003
    volume_multiplier: float = 1.3
    cooldown_bars: int = 10

    allowed_regimes: tuple = field(default_factory=_default_allowed_regimes)

    skip_regime_filter: bool = False
    skip_range_width_filter: bool = False

    # v0.3 confidence scoring - DISABLED by default in v0.4
    enable_confidence_scoring: bool = False
    structure_lookback: int = 10
    wick_ratio_threshold: float = 1.5
    volume_divergence_lookback: int = 20
    ema_period: int = 20
    multi_touch_lookback: int = 20
    multi_touch_penalty_threshold: int = 4
    full_size_min_score: int = 4
    half_size_min_score: int = 2

    # v0.4: MTF Container filter (PRIMARY)
    use_mtf_filter: bool = True
    min_mtf_confidence: int = 2
    enable_low_conf_quarter: bool = False


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
    confidence: float = 1.0
    score: int = 0
    mtf_confidence: int = -1
    signals_detail: dict = field(default_factory=dict)
    reason: str = ""


def _mtf_conf_to_size(mtf_conf: int, cfg: SidewaysConfig) -> float:
    """Map MTF confidence 0-3 to position size multiplier 0.0-1.0."""
    if mtf_conf >= 3:
        return 1.0
    elif mtf_conf == 2:
        return 0.5
    elif mtf_conf == 1:
        return 0.25 if cfg.enable_low_conf_quarter else 0.0
    else:
        return 0.0


def generate_sideways_signals(
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray,
    regime_states: list[RegimeState],
    cfg: SidewaysConfig,
    mtf_classifications: Optional[list] = None,
) -> list[SidewaysSignal]:
    """
    Generate signals sideways tektok.
    v0.4: MTF filter/sizing PRIMARY when mtf_classifications provided.
    """
    n = len(closes)
    signals: list[SidewaysSignal] = []

    vol_avg = np.zeros(n)
    for i in range(n):
        start = max(0, i - 19)
        vol_avg[i] = float(np.mean(volumes[start:i + 1])) if i > start else 1.0

    ema_arr = ema(closes, cfg.ema_period) if cfg.enable_confidence_scoring else np.zeros(n)

    last_long_bar = -9999
    last_short_bar = -9999

    for i in range(50, n):
        rs = regime_states[i]

        if not cfg.skip_regime_filter:
            if rs.regime not in cfg.allowed_regimes:
                continue

        if not cfg.skip_range_width_filter:
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

        cooldown_long_ok = (i - last_long_bar) >= cfg.cooldown_bars
        cooldown_short_ok = (i - last_short_bar) >= cfg.cooldown_bars

        touch_val = (l <= val * (1 + cfg.touch_tolerance)) and (l >= val * (1 - cfg.touch_tolerance))
        touch_vah = (h >= vah * (1 - cfg.touch_tolerance)) and (h <= vah * (1 + cfg.touch_tolerance))

        wick_below_val = l < val * (1 - cfg.touch_tolerance) and c > val
        wick_above_vah = h > vah * (1 + cfg.touch_tolerance) and c < vah

        bullish_candle = c > closes[i - 1]
        bearish_candle = c < closes[i - 1]

        # v0.4: MTF confidence at this candle
        mtf_conf = -1
        if cfg.use_mtf_filter and mtf_classifications is not None and i < len(mtf_classifications):
            mtf_cls = mtf_classifications[i]
            mtf_conf = int(mtf_cls.inside_confidence) if mtf_cls.range_4h_high is not None else -1
            if mtf_conf >= 0 and mtf_conf < cfg.min_mtf_confidence:
                continue
            if mtf_conf < 0:
                continue  # warmup

        def build_signal(side: SideEnum, mode: SidewaysMode, reason: str):
            if cfg.use_mtf_filter and mtf_conf >= 0:
                size_mult = _mtf_conf_to_size(mtf_conf, cfg)
                if size_mult <= 0.0:
                    return None
                confidence = size_mult
                score = mtf_conf
                details = {"mtf_confidence": mtf_conf, "mtf_used": True}
            elif cfg.enable_confidence_scoring:
                score, details = 0, {}
                confidence = 1.0
            else:
                confidence = 1.0
                score = 0
                details = {}

            return SidewaysSignal(
                idx=i, side=side, mode=mode,
                price=float(c), val=float(val), vah=float(vah), poc=float(poc),
                regime=rs.regime.value,
                confidence=confidence, score=score, mtf_confidence=mtf_conf,
                signals_detail=details, reason=reason,
            )

        if touch_val and bullish_candle and vol_ok and c > val and cooldown_long_ok:
            sig = build_signal(SideEnum.LONG, SidewaysMode.BOUNCE_VAL, "touch_val_bullish_vol_ok")
            if sig is not None:
                signals.append(sig)
                last_long_bar = i
            continue

        if wick_below_val and vol_ok and cooldown_long_ok:
            sig = build_signal(SideEnum.LONG, SidewaysMode.FAKE_BREAKDOWN, "wick_below_val_reclaim")
            if sig is not None:
                signals.append(sig)
                last_long_bar = i
            continue

        if touch_vah and bearish_candle and vol_ok and c < vah and cooldown_short_ok:
            sig = build_signal(SideEnum.SHORT, SidewaysMode.REJECT_VAH, "touch_vah_bearish_vol_ok")
            if sig is not None:
                signals.append(sig)
                last_short_bar = i
            continue

        if wick_above_vah and vol_ok and cooldown_short_ok:
            sig = build_signal(SideEnum.SHORT, SidewaysMode.FAKE_BREAKOUT, "wick_above_vah_rejection")
            if sig is not None:
                signals.append(sig)
                last_short_bar = i
            continue

    return signals


__all__ = ["SideEnum", "SidewaysMode", "SidewaysConfig", "SidewaysSignal", "generate_sideways_signals"]
