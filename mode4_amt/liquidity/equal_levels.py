"""
equal_levels.py — Equal Highs/Lows Detection
==============================================
Design Doc reference: §3.2 (Equal Highs) dan §7.2.1 (BSL-1 kategori).

Definisi Equal Highs:
    Dua atau lebih swing high yang berjarak minimal 5 candle satu sama lain,
    dengan level high yang sama dalam toleransi 0.1%.

Equal Highs adalah SL cluster paling tebal (2 kelompok trader dengan level
target sama), sehingga jadi liquidity magnet berkualitas tinggi (weight 1.0).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple

from ..structure.swing_detector import Swing, SwingType


@dataclass
class EqualLevel:
    """Cluster equal high atau equal low."""
    is_high: bool                     # True = Equal Highs, False = Equal Lows
    price_avg: float                  # Average of the equal points
    price_min: float                  # Min price of cluster
    price_max: float                  # Max price of cluster
    swing_indices: List[int] = field(default_factory=list)  # Idx swing yang match
    tolerance_pct: float = 0.001

    @property
    def num_equals(self) -> int:
        return len(self.swing_indices)

    def __repr__(self):
        kind = "EQH" if self.is_high else "EQL"
        return (f"EqualLevel({kind} avg={self.price_avg:.4f} "
                f"n={self.num_equals} idxs={self.swing_indices})")


def _detect_equal(
    swings: List[Swing],
    swing_type: SwingType,
    tolerance_pct: float = 0.001,
    min_distance: int = 5,
) -> List[EqualLevel]:
    """
    Internal: cluster equal points among swings of given type.

    Two swings are 'equal' when their price difference is within tolerance
    dan idx distance minimal `min_distance`.

    Args:
        swings: list of Swing sorted by idx
        swing_type: HIGH atau LOW
        tolerance_pct: 0.001 = 0.1% price tolerance
        min_distance: minimum candle distance between pairs

    Returns:
        List of EqualLevel clusters (each has >= 2 equal points).
    """
    typed = [s for s in swings if s.swing_type == swing_type]
    if len(typed) < 2:
        return []

    # Union-find style clustering: for each pair, check equal; then group.
    # For simplicity, use greedy clustering: sort by price, group nearby.
    n = len(typed)
    # Mark which swings are grouped together
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # Compare all pairs
    for i in range(n):
        for j in range(i + 1, n):
            price_i = typed[i].price
            price_j = typed[j].price
            avg = (price_i + price_j) / 2
            price_diff = abs(price_i - price_j) / max(avg, 1e-9)
            idx_diff = abs(typed[i].idx - typed[j].idx)
            if price_diff <= tolerance_pct and idx_diff >= min_distance:
                union(i, j)

    # Group by root
    clusters: dict = {}
    for i in range(n):
        root = find(i)
        clusters.setdefault(root, []).append(i)

    # Build EqualLevel objects only for clusters size >= 2
    results: List[EqualLevel] = []
    for members in clusters.values():
        if len(members) < 2:
            continue
        member_swings = [typed[m] for m in members]
        prices = [s.price for s in member_swings]
        indices = sorted([s.idx for s in member_swings])
        results.append(EqualLevel(
            is_high=(swing_type == SwingType.HIGH),
            price_avg=float(sum(prices) / len(prices)),
            price_min=float(min(prices)),
            price_max=float(max(prices)),
            swing_indices=indices,
            tolerance_pct=tolerance_pct,
        ))

    # Sort by earliest swing_indices
    results.sort(key=lambda x: x.swing_indices[0])
    return results


def detect_equal_highs(
    swings: List[Swing],
    tolerance_pct: float = 0.001,
    min_distance: int = 5,
) -> List[EqualLevel]:
    """Detect Equal Highs clusters."""
    return _detect_equal(swings, SwingType.HIGH, tolerance_pct, min_distance)


def detect_equal_lows(
    swings: List[Swing],
    tolerance_pct: float = 0.001,
    min_distance: int = 5,
) -> List[EqualLevel]:
    """Detect Equal Lows clusters."""
    return _detect_equal(swings, SwingType.LOW, tolerance_pct, min_distance)


__all__ = [
    "EqualLevel", "detect_equal_highs", "detect_equal_lows",
]
