"""
structure_labels.py — HH/HL/LH/LL Labeling
============================================
Setelah swing terdeteksi, label mereka relative ke swing sebelumnya:
    HH = Higher High  (swing high > previous swing high)
    HL = Higher Low   (swing low  > previous swing low)
    LH = Lower High   (swing high < previous swing high)
    LL = Lower Low    (swing low  < previous swing low)

Design Doc reference: §3.1.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional

from .swing_detector import Swing, SwingType


class StructureLabel(str, Enum):
    HH = "HH"    # Higher High
    HL = "HL"    # Higher Low
    LH = "LH"    # Lower High
    LL = "LL"    # Lower Low
    UNDEFINED = "UNDEFINED"  # First swing of its type, no reference


@dataclass
class LabeledSwing:
    """Swing dengan label struktural."""
    swing: Swing
    label: StructureLabel

    @property
    def idx(self) -> int:
        return self.swing.idx

    @property
    def price(self) -> float:
        return self.swing.price

    @property
    def swing_type(self) -> SwingType:
        return self.swing.swing_type

    def __repr__(self):
        return (f"LabeledSwing({self.label.value} "
                f"{self.swing_type.value}@{self.idx}={self.price:.4f})")


def label_swings(swings: List[Swing]) -> List[LabeledSwing]:
    """
    Label setiap swing sebagai HH/HL/LH/LL relative ke swing terakhir dengan
    type yang sama (previous HIGH untuk HIGH, previous LOW untuk LOW).

    Swing pertama dari tiap type di-label UNDEFINED karena belum ada reference.

    Args:
        swings: list of Swing sorted by idx ascending (output dari detect_swings)

    Returns:
        List of LabeledSwing, order sama seperti input.

    Design Doc §3.1: is_HH, is_HL, is_LH, is_LL definitions.
    """
    labeled: List[LabeledSwing] = []
    last_high: Optional[Swing] = None
    last_low: Optional[Swing] = None

    for s in swings:
        if s.swing_type == SwingType.HIGH:
            if last_high is None:
                label = StructureLabel.UNDEFINED
            elif s.price > last_high.price:
                label = StructureLabel.HH
            else:
                label = StructureLabel.LH
            last_high = s
        else:  # LOW
            if last_low is None:
                label = StructureLabel.UNDEFINED
            elif s.price > last_low.price:
                label = StructureLabel.HL
            else:
                label = StructureLabel.LL
            last_low = s

        labeled.append(LabeledSwing(swing=s, label=label))

    return labeled


def count_recent_labels(
    labeled_swings: List[LabeledSwing],
    labels: List[StructureLabel],
    lookback: int = 10,
) -> int:
    """
    Hitung berapa swing terakhir (max `lookback`) yang memiliki label di
    daftar `labels`. Berguna untuk BOS/CHoCH validation.

    Contoh: count_recent_labels(swings, [HH], lookback=10) return jumlah HH
    di 10 swing terakhir.
    """
    recent = labeled_swings[-lookback:] if lookback > 0 else labeled_swings
    return sum(1 for ls in recent if ls.label in labels)


def get_trend_bias(
    labeled_swings: List[LabeledSwing],
    lookback: int = 6,
) -> str:
    """
    Simple trend bias dari N swing terakhir.

    Returns:
        "UPTREND" jika HH+HL dominan
        "DOWNTREND" jika LH+LL dominan
        "MIXED" jika campuran
        "UNDEFINED" jika data insufficient
    """
    if len(labeled_swings) < 2:
        return "UNDEFINED"

    recent = labeled_swings[-lookback:]
    hh_hl = sum(1 for ls in recent
                if ls.label in [StructureLabel.HH, StructureLabel.HL])
    lh_ll = sum(1 for ls in recent
                if ls.label in [StructureLabel.LH, StructureLabel.LL])

    if hh_hl >= lh_ll * 2 and hh_hl >= 2:
        return "UPTREND"
    if lh_ll >= hh_hl * 2 and lh_ll >= 2:
        return "DOWNTREND"
    return "MIXED"


__all__ = [
    "StructureLabel", "LabeledSwing", "label_swings",
    "count_recent_labels", "get_trend_bias",
]
