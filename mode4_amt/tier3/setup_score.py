"""
setup_score.py — Composite Setup Scoring (Tier 3 gate)
==========================================================
Design Doc reference: §7.3.

Composite score menggabungkan semua tier:

    setup_score = 0.30 × tier1_score           (sweep/breakout quality)
                + 0.25 × tier3_fvg_quality      (FVG mid + freshness)
                + 0.20 × liquidity_target_weight (weight BSL/SSL target TP)
                + 0.15 × structural_alignment   (BOS/CHoCH structural conf)
                + 0.10 × mtf_context            (4h alignment, from Mode 3)

Setup valid untuk entry jika setup_score >= threshold (default 0.65).

Sub-strategy-specific requirements (hard gate):
    Sub-4A: tier1_type == BREAKOUT, fvg_direction match leg
    Sub-4B: tier1_type == SWEEP, structural_confirm CHoCH match
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class SetupCandidate:
    """A trade setup candidate before scoring."""
    symbol: str
    sub_strategy: str          # "4A" or "4B"
    direction: str             # "LONG" or "SHORT"
    trigger_idx: int           # BOS/CHoCH trigger candle
    entry_price: float
    sl_price: float
    tp_prices: list = field(default_factory=list)   # multi-TP

    # Tier scores (all 0..1)
    tier1_score: float = 0.0
    tier1_type: str = ""              # "SWEEP" or "BREAKOUT"
    tier3_fvg_quality: float = 0.0
    liquidity_target_weight: float = 0.0
    structural_alignment: float = 0.0
    mtf_context: float = 0.0

    # Computed
    setup_score: float = 0.0
    passes_hard_gate: bool = False
    is_valid: bool = False


@dataclass
class SetupScore:
    """Result of scoring a setup."""
    setup_score: float
    passes_hard_gate: bool
    is_valid: bool
    weight_breakdown: Dict[str, float] = field(default_factory=dict)
    hard_gate_reasons: list = field(default_factory=list)


# Weights (Design Doc §7.3)
DEFAULT_WEIGHTS = {
    "tier1_score":              0.30,
    "tier3_fvg_quality":        0.25,
    "liquidity_target_weight":  0.20,
    "structural_alignment":     0.15,
    "mtf_context":              0.10,
}


def compute_setup_score(
    candidate: SetupCandidate,
    weights: Optional[Dict[str, float]] = None,
    min_score_threshold: float = 0.65,
    check_hard_gates: bool = True,
) -> SetupScore:
    """
    Compute composite setup score and validate hard gates.

    Hard gates (only applied if check_hard_gates=True):
        Sub-4A: tier1_type must be "BREAKOUT"
        Sub-4B: tier1_type must be "SWEEP", structural_alignment >= 0.3
        All: tier1_score >= 0.4, structural_alignment > 0.1

    Args:
        candidate: SetupCandidate with all tier scores populated
        weights: override default weight table
        min_score_threshold: min composite score to pass (default 0.65)
        check_hard_gates: apply sub-strategy hard gates

    Returns:
        SetupScore with is_valid = passes_hard_gate AND score >= threshold
    """
    w = weights or DEFAULT_WEIGHTS

    # Composite score
    score = (
        w["tier1_score"]              * candidate.tier1_score
        + w["tier3_fvg_quality"]      * candidate.tier3_fvg_quality
        + w["liquidity_target_weight"]* candidate.liquidity_target_weight
        + w["structural_alignment"]   * candidate.structural_alignment
        + w["mtf_context"]            * candidate.mtf_context
    )

    breakdown = {
        "tier1":       w["tier1_score"]             * candidate.tier1_score,
        "fvg":         w["tier3_fvg_quality"]       * candidate.tier3_fvg_quality,
        "liq_target":  w["liquidity_target_weight"] * candidate.liquidity_target_weight,
        "structural":  w["structural_alignment"]    * candidate.structural_alignment,
        "mtf":         w["mtf_context"]             * candidate.mtf_context,
    }

    # Hard gate checks
    passes_hard = True
    reasons = []

    if check_hard_gates:
        # Sub-strategy-specific requirement
        if candidate.sub_strategy == "4A":
            if candidate.tier1_type != "BREAKOUT":
                passes_hard = False
                reasons.append("Sub-4A requires tier1_type=BREAKOUT")
        elif candidate.sub_strategy == "4B":
            if candidate.tier1_type != "SWEEP":
                passes_hard = False
                reasons.append("Sub-4B requires tier1_type=SWEEP")
            if candidate.structural_alignment < 0.30:
                passes_hard = False
                reasons.append(f"Sub-4B needs structural_alignment>=0.30 (got {candidate.structural_alignment:.2f})")

        # Universal minimums
        if candidate.tier1_score < 0.40:
            passes_hard = False
            reasons.append(f"tier1_score too low ({candidate.tier1_score:.2f})")

        if candidate.structural_alignment <= 0.10 and candidate.sub_strategy != "4A":
            # Sub-4A can be more lenient (breakout alone gives structural evidence)
            passes_hard = False
            reasons.append("structural_alignment too low")

    is_valid = passes_hard and score >= min_score_threshold

    # Update candidate in place
    candidate.setup_score = float(score)
    candidate.passes_hard_gate = passes_hard
    candidate.is_valid = is_valid

    return SetupScore(
        setup_score=float(score),
        passes_hard_gate=passes_hard,
        is_valid=is_valid,
        weight_breakdown=breakdown,
        hard_gate_reasons=reasons,
    )


__all__ = ["SetupCandidate", "SetupScore", "compute_setup_score", "DEFAULT_WEIGHTS"]
