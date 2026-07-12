"""tier3/ — Confirmation layer (FVG, retracement zones, structural, setup score)."""

from .fvg_detector import (
    FVG,
    FVGDirection,
    FVGState,
    detect_fvgs,
    update_fvg_states,
)
from .retracement_zone import (
    RetracementZone,
    compute_retracement_zone,
    fvg_in_zone,
)
from .structural_confirm import (
    StructuralConfirmation,
    check_structural_confirmation,
)
from .setup_score import (
    SetupScore,
    SetupCandidate,
    compute_setup_score,
)

__all__ = [
    "FVG", "FVGDirection", "FVGState", "detect_fvgs", "update_fvg_states",
    "RetracementZone", "compute_retracement_zone", "fvg_in_zone",
    "StructuralConfirmation", "check_structural_confirmation",
    "SetupScore", "SetupCandidate", "compute_setup_score",
]
