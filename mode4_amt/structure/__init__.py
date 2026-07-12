"""structure/ — Swing detection, HH/HL/LH/LL, BOS/CHoCH, impulse legs."""

from .swing_detector import (
    Swing,
    SwingType,
    detect_swings,
    last_swing_before,
)
from .structure_labels import (
    LabeledSwing,
    StructureLabel,
    label_swings,
)
from .bos_choch import (
    StructureEvent,
    EventType,
    detect_structure_events,
)
from .impulse_leg import (
    ImpulseLeg,
    detect_impulse_legs,
)

__all__ = [
    "Swing", "SwingType", "detect_swings", "last_swing_before",
    "LabeledSwing", "StructureLabel", "label_swings",
    "StructureEvent", "EventType", "detect_structure_events",
    "ImpulseLeg", "detect_impulse_legs",
]
