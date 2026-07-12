"""
retracement_zone.py — Fibonacci Retracement Zones (Tier 3 helper)
==================================================================
Design Doc reference: §3.6, §7.2.3.

Zona entry Sub-4A:
    Zona 38.2%: [end - 0.382 × range, end - 0.5 × range]     — "safe" pullback
    Zona OTE:   [end - 0.618 × range, end - 0.79 × range]    — "optimal" (deeper)

Untuk bullish leg (start=low, end=high):
    38.2% zone = [end - 0.5×rng, end - 0.382×rng]
    OTE zone = [end - 0.79×rng, end - 0.618×rng]

Untuk bearish leg (start=high, end=low): mirrored.

FVG in Zone: high-quality confirmation adalah FVG yang midprice-nya JATUH di
salah satu Fib zone. Ini menandakan zona demand institusional + area untraded
= confluence.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional

from ..structure.impulse_leg import ImpulseLeg, ImpulseDirection
from .fvg_detector import FVG, FVGDirection


@dataclass
class RetracementZone:
    """One Fibonacci retracement zone."""
    zone_low: float
    zone_high: float
    fib_low: float           # e.g. 0.5
    fib_high: float          # e.g. 0.382
    name: str = ""           # "38.2%" or "OTE"

    @property
    def mid(self) -> float:
        return (self.zone_low + self.zone_high) / 2

    def contains(self, price: float) -> bool:
        return self.zone_low <= price <= self.zone_high

    def overlap_size(self, other_low: float, other_high: float) -> float:
        """Size of overlap between this zone and [other_low, other_high]."""
        lo = max(self.zone_low, other_low)
        hi = min(self.zone_high, other_high)
        return max(0.0, hi - lo)

    def __repr__(self):
        return f"RetracementZone({self.name} [{self.zone_low:.4f}-{self.zone_high:.4f}])"


def compute_retracement_zone(
    leg: ImpulseLeg,
    zone_type: str = "38.2%",
) -> RetracementZone:
    """
    Compute retracement zone dari impulse leg.

    Args:
        zone_type: "38.2%" atau "OTE" (0.618-0.79)

    Returns:
        RetracementZone with zone_low < zone_high.
    """
    rng = leg.range()
    if zone_type == "38.2%":
        fib_low, fib_high = 0.5, 0.382
    elif zone_type == "OTE":
        fib_low, fib_high = 0.79, 0.618
    else:
        raise ValueError(f"Unknown zone_type: {zone_type}")

    if leg.direction == ImpulseDirection.BULLISH:
        # Retracement dari end (high) ke bawah
        z_high = leg.end_price - rng * fib_high  # closer to end
        z_low = leg.end_price - rng * fib_low    # deeper
    else:
        # Retracement dari end (low) ke atas
        z_low = leg.end_price + rng * fib_high   # closer to end
        z_high = leg.end_price + rng * fib_low   # deeper

    return RetracementZone(
        zone_low=float(min(z_low, z_high)),
        zone_high=float(max(z_low, z_high)),
        fib_low=fib_low, fib_high=fib_high,
        name=zone_type,
    )


def fvg_in_zone(fvg: FVG, zone: RetracementZone, min_overlap_pct: float = 0.30) -> bool:
    """
    Check if FVG has significant overlap with retracement zone.

    Args:
        min_overlap_pct: minimum overlap sebagai fraction dari FVG size.
                         0.3 = min 30% dari FVG overlaps dengan zona.

    Returns True jika overlap sufficient.
    """
    if fvg.gap_size <= 0:
        return False
    overlap = zone.overlap_size(fvg.gap_low, fvg.gap_high)
    return (overlap / fvg.gap_size) >= min_overlap_pct


def best_fvg_for_leg(
    fvgs: List[FVG],
    leg: ImpulseLeg,
    prefer_zone: str = "OTE",
) -> Optional[FVG]:
    """
    Find best FVG for entering pullback of `leg`. Prioritas:
        1. FVG direction sesuai leg (bullish leg → bullish FVG for support)
        2. FVG formed AFTER leg started
        3. FVG overlap dengan Fib zone
        4. Higher quality_score wins

    Returns best FVG or None.
    """
    if leg.direction == ImpulseDirection.BULLISH:
        target_dir = FVGDirection.BULLISH
    else:
        target_dir = FVGDirection.BEARISH

    zone = compute_retracement_zone(leg, prefer_zone)

    candidates = []
    for fvg in fvgs:
        if fvg.direction != target_dir:
            continue
        if fvg.idx < leg.start_idx or fvg.idx > leg.end_idx:
            continue
        if not fvg_in_zone(fvg, zone, min_overlap_pct=0.20):
            continue
        candidates.append(fvg)

    if not candidates:
        return None
    return max(candidates, key=lambda f: f.quality_score)


__all__ = [
    "RetracementZone", "compute_retracement_zone",
    "fvg_in_zone", "best_fvg_for_leg",
]
