"""
liquidity_map.py — BSL/SSL Registry
=====================================
Design Doc reference: §7.2.1 (liquidity ranking table) dan §3.2.

Menggabungkan semua liquidity level jadi 1 registry, sorted by weight_score
descending. Setiap level punya:
- category (7 kategori)
- weight_score (dari tabel Design Doc §7.2.1)
- price
- side (BSL di atas current price, SSL di bawah)
- reference (swing idx / equal cluster / session ref)
- state (UNTOUCHED / SWEPT / BROKEN)

Categories dan weight:
    LEVEL_EQUAL_HL      1.00  (Equal Highs / Equal Lows 2+ instances)
    LEVEL_SWING_4H      0.90  (Swing High/Low 4h TF, untouched)
    LEVEL_VAH_VAL       0.85  (Volume Profile 4h VAH/VAL)
    LEVEL_PDH_PDL       0.80  (Previous Day High/Low)
    LEVEL_SESSION_HL    0.70  (Session Asia/London/NY H/L)
    LEVEL_SWING_1H      0.60  (Swing High/Low 1h TF, untouched)
    LEVEL_ROUND         0.50  (Round Number)
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict
import numpy as np

from ..structure.swing_detector import Swing, SwingType
from .session_levels import SessionLevel
from .equal_levels import EqualLevel


class LevelCategory(str, Enum):
    EQUAL_HL = "EQUAL_HL"
    SWING_4H = "SWING_4H"
    VAH_VAL = "VAH_VAL"
    PDH_PDL = "PDH_PDL"
    SESSION_HL = "SESSION_HL"
    SWING_1H = "SWING_1H"
    ROUND = "ROUND"


class LevelSide(str, Enum):
    BSL = "BSL"    # Buy-Side Liquidity (above price, short SLs)
    SSL = "SSL"    # Sell-Side Liquidity (below price, long SLs)


class LevelState(str, Enum):
    UNTOUCHED = "UNTOUCHED"    # Not yet approached
    APPROACHED = "APPROACHED"  # Price within 0.5×ATR of level, no touch yet
    SWEPT = "SWEPT"            # Wick tembus + close-back (liquidity taken)
    BROKEN = "BROKEN"          # Sustained close beyond (level invalidated)


# Weight table (Design Doc §7.2.1)
DEFAULT_WEIGHTS: Dict[LevelCategory, float] = {
    LevelCategory.EQUAL_HL: 1.00,
    LevelCategory.SWING_4H: 0.90,
    LevelCategory.VAH_VAL: 0.85,
    LevelCategory.PDH_PDL: 0.80,
    LevelCategory.SESSION_HL: 0.70,
    LevelCategory.SWING_1H: 0.60,
    LevelCategory.ROUND: 0.50,
}


@dataclass
class LiquidityLevel:
    """Satu level liquidity di map."""
    price: float
    category: LevelCategory
    side: LevelSide
    weight_score: float
    state: LevelState = LevelState.UNTOUCHED

    # Reference metadata
    source_idx: int = -1              # Candle idx where level originated
    reference: str = ""               # Human-readable ref ("swing@42", "Asia@2026-07-08")
    timeframe: str = ""               # "1h" / "4h" / "session"

    # Stats
    distance_from_current: float = 0.0
    distance_atr: float = 0.0

    def __repr__(self):
        return (f"LiquidityLevel({self.side.value} {self.category.value} "
                f"@{self.price:.4f} w={self.weight_score:.2f} "
                f"{self.state.value})")


@dataclass
class LiquidityMap:
    """Registry semua liquidity level, sorted by weight_score desc."""
    levels: List[LiquidityLevel] = field(default_factory=list)
    current_price: float = 0.0
    current_atr: float = 0.0

    def bsl_levels(self, min_weight: float = 0.0) -> List[LiquidityLevel]:
        """Return BSL (above current price), filtered by weight."""
        return [l for l in self.levels
                if l.side == LevelSide.BSL and l.weight_score >= min_weight]

    def ssl_levels(self, min_weight: float = 0.0) -> List[LiquidityLevel]:
        """Return SSL (below current price), filtered by weight."""
        return [l for l in self.levels
                if l.side == LevelSide.SSL and l.weight_score >= min_weight]

    def nearest_bsl(self) -> Optional[LiquidityLevel]:
        """Return BSL terdekat dari current price."""
        bsl = self.bsl_levels()
        if not bsl:
            return None
        return min(bsl, key=lambda l: l.price - self.current_price)

    def nearest_ssl(self) -> Optional[LiquidityLevel]:
        """Return SSL terdekat dari current price."""
        ssl = self.ssl_levels()
        if not ssl:
            return None
        return min(ssl, key=lambda l: self.current_price - l.price)

    def levels_within(self, max_atr_distance: float) -> List[LiquidityLevel]:
        """Return levels dalam jarak max_atr_distance × ATR dari current price."""
        max_dist = max_atr_distance * self.current_atr
        return [l for l in self.levels if abs(l.distance_from_current) <= max_dist]

    def summary(self) -> str:
        n_bsl = sum(1 for l in self.levels if l.side == LevelSide.BSL)
        n_ssl = sum(1 for l in self.levels if l.side == LevelSide.SSL)
        return (f"LiquidityMap(price={self.current_price:.4f} atr={self.current_atr:.4f} "
                f"BSL={n_bsl} SSL={n_ssl} total={len(self.levels)})")


def build_liquidity_map(
    current_price: float,
    current_atr: float,
    swings_1h: List[Swing] = None,
    swings_4h: List[Swing] = None,
    equal_highs: List[EqualLevel] = None,
    equal_lows: List[EqualLevel] = None,
    session_levels: List[SessionLevel] = None,
    vah: Optional[float] = None,
    val: Optional[float] = None,
    prev_day_high: Optional[float] = None,
    prev_day_low: Optional[float] = None,
    round_number_step: Optional[float] = None,
    weights: Optional[Dict[LevelCategory, float]] = None,
) -> LiquidityMap:
    """
    Build liquidity map dari semua sumber.

    Args:
        current_price: harga saat ini (untuk klasifikasi BSL vs SSL)
        current_atr: ATR saat ini (untuk distance normalization)
        swings_1h, swings_4h: swing points dari respective TF
        equal_highs, equal_lows: equal level clusters
        session_levels: session H/L
        vah, val: volume profile boundaries
        prev_day_high, prev_day_low: PDH/PDL
        round_number_step: e.g. 1000 for BTC (BSL/SSL di round numbers terdekat)
        weights: override default weight table

    Returns:
        LiquidityMap sorted by weight desc, then by distance asc.

    Level UNTOUCHED filtering: hanya level yang belum tembus final oleh current
    price yang dimasukkan (untuk BSL: price > current, untuk SSL: price < current).
    Level yang sudah broken (harga jauh melampaui) di-skip.
    """
    w = weights or DEFAULT_WEIGHTS
    levels: List[LiquidityLevel] = []

    def add_level(price, category, source_idx=-1, ref="", tf=""):
        """Add level, classifying BSL/SSL by price vs current."""
        if abs(price - current_price) < 1e-9:
            return  # exact match, skip
        side = LevelSide.BSL if price > current_price else LevelSide.SSL
        dist = price - current_price
        dist_atr = dist / current_atr if current_atr > 0 else 0.0
        levels.append(LiquidityLevel(
            price=float(price),
            category=category,
            side=side,
            weight_score=w[category],
            source_idx=source_idx,
            reference=ref,
            timeframe=tf,
            distance_from_current=float(dist),
            distance_atr=float(dist_atr),
        ))

    # 1. Equal Highs → BSL, Equal Lows → SSL
    if equal_highs:
        for eq in equal_highs:
            if eq.price_avg > current_price:  # only untouched BSL
                add_level(eq.price_avg, LevelCategory.EQUAL_HL,
                          source_idx=eq.swing_indices[-1],
                          ref=f"eqh(n={eq.num_equals})", tf="1h")
    if equal_lows:
        for eq in equal_lows:
            if eq.price_avg < current_price:
                add_level(eq.price_avg, LevelCategory.EQUAL_HL,
                          source_idx=eq.swing_indices[-1],
                          ref=f"eql(n={eq.num_equals})", tf="1h")

    # 2. Swings 4h
    if swings_4h:
        for s in swings_4h:
            if s.swing_type == SwingType.HIGH and s.price > current_price:
                add_level(s.price, LevelCategory.SWING_4H,
                          source_idx=s.idx, ref=f"sw4h@{s.idx}", tf="4h")
            elif s.swing_type == SwingType.LOW and s.price < current_price:
                add_level(s.price, LevelCategory.SWING_4H,
                          source_idx=s.idx, ref=f"sw4h@{s.idx}", tf="4h")

    # 3. VAH/VAL
    if vah is not None and vah > current_price:
        add_level(vah, LevelCategory.VAH_VAL, ref="VAH_4h", tf="4h")
    if val is not None and val < current_price:
        add_level(val, LevelCategory.VAH_VAL, ref="VAL_4h", tf="4h")

    # 4. PDH/PDL
    if prev_day_high is not None and prev_day_high > current_price:
        add_level(prev_day_high, LevelCategory.PDH_PDL, ref="PDH", tf="1d")
    if prev_day_low is not None and prev_day_low < current_price:
        add_level(prev_day_low, LevelCategory.PDH_PDL, ref="PDL", tf="1d")

    # 5. Session H/L
    if session_levels:
        for sl in session_levels:
            if sl.high > current_price:
                add_level(sl.high, LevelCategory.SESSION_HL,
                          source_idx=sl.high_idx,
                          ref=f"{sl.session.value}_H@{sl.date}", tf="session")
            if sl.low < current_price:
                add_level(sl.low, LevelCategory.SESSION_HL,
                          source_idx=sl.low_idx,
                          ref=f"{sl.session.value}_L@{sl.date}", tf="session")

    # 6. Swings 1h
    if swings_1h:
        for s in swings_1h:
            if s.swing_type == SwingType.HIGH and s.price > current_price:
                add_level(s.price, LevelCategory.SWING_1H,
                          source_idx=s.idx, ref=f"sw1h@{s.idx}", tf="1h")
            elif s.swing_type == SwingType.LOW and s.price < current_price:
                add_level(s.price, LevelCategory.SWING_1H,
                          source_idx=s.idx, ref=f"sw1h@{s.idx}", tf="1h")

    # 7. Round numbers (nearest above and below)
    if round_number_step is not None and round_number_step > 0:
        above = np.ceil(current_price / round_number_step) * round_number_step
        below = np.floor(current_price / round_number_step) * round_number_step
        if above > current_price:
            add_level(float(above), LevelCategory.ROUND, ref=f"round({round_number_step})")
        if below < current_price:
            add_level(float(below), LevelCategory.ROUND, ref=f"round({round_number_step})")

    # Deduplicate near-identical levels (within 0.05% price)
    dedup = _deduplicate_levels(levels, tolerance_pct=0.0005)

    # Sort: weight desc, then distance asc
    dedup.sort(key=lambda l: (-l.weight_score, abs(l.distance_from_current)))

    return LiquidityMap(
        levels=dedup,
        current_price=current_price,
        current_atr=current_atr,
    )


def _deduplicate_levels(
    levels: List[LiquidityLevel],
    tolerance_pct: float = 0.0005,
) -> List[LiquidityLevel]:
    """
    Merge levels yang harganya sangat dekat (<= tolerance_pct).
    Keep yang weight-nya tertinggi.
    """
    if not levels:
        return []
    # Sort by price
    sorted_levels = sorted(levels, key=lambda l: l.price)
    dedup = [sorted_levels[0]]
    for l in sorted_levels[1:]:
        prev = dedup[-1]
        if abs(l.price - prev.price) / max(prev.price, 1e-9) <= tolerance_pct:
            # Same effective level — keep higher weight
            if l.weight_score > prev.weight_score:
                dedup[-1] = l
        else:
            dedup.append(l)
    return dedup


__all__ = [
    "LevelCategory", "LevelSide", "LevelState",
    "LiquidityLevel", "LiquidityMap",
    "DEFAULT_WEIGHTS", "build_liquidity_map",
]
