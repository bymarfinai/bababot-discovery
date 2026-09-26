"""SOL Regime Stage 4 V2 normalized candidate — REJECTED by OOS robustness.

Research artifact only. Do not use as production regime detector.

Frozen candidate rules were selected before 2025/2026 evaluation.
"""

from dataclasses import dataclass

@dataclass(frozen=True)
class Stage4V2:
    # 30-day rolling median normalization.
    vol_ratio: float = 1.3
    bull_pullback_atr: float = 1.0
    bull_m30_atr: float = 0.0
    bull_r2_atr_max: float = -0.5

    bear_vol_ratio: float = 1.5
    bear_vol_votes: int = 2
    bear_rally_atr: float = 1.5
    bear_m30_atr: float = 0.4
    bear_r4_atr_min: float = 0.0

    side_rv8_rel_max: float = 1.0
    side_atr_rel_max: float = 0.9

CFG = Stage4V2()

def vol_votes(f, q: float) -> int:
    return int(f["rv8_rel"] >= q) + int(f["rv24_rel"] >= q) + int(f["atr_rel"] >= q)

def classify_v2(f):
    # BULL V2-BALANCED
    bull = (
        vol_votes(f, CFG.vol_ratio) >= 1
        and f["pullback_atr"] >= CFG.bull_pullback_atr
        and f["m30_atr"] >= CFG.bull_m30_atr
        and f["r2_atr"] <= CFG.bull_r2_atr_max
    )

    # BEAR V2 candidate: overextended rally is still strong at detection time.
    bear = (
        vol_votes(f, CFG.bear_vol_ratio) >= CFG.bear_vol_votes
        and f["rally_atr"] >= CFG.bear_rally_atr
        and f["m30_atr"] >= CFG.bear_m30_atr
        and f["r4_atr"] >= CFG.bear_r4_atr_min
    )

    if bull and not bear:
        return "BULL"
    if bear and not bull:
        return "BEAR"

    if f["rv8_rel"] <= CFG.side_rv8_rel_max and f["atr_rel"] <= CFG.side_atr_rel_max:
        return "SIDEWAYS"

    return "TRANSITION"
