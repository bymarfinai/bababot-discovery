# SOL Structural Liquidity Detector V3 — Actionability Audit

## Purpose

Audit the already-frozen `SCORE >= 3` detector for a stricter live-actionable interpretation.

The original V3 allowed a structural outcome to be resolved on the same H1 candle that completed the reclaim. Such rows are valid contemporaneous classifications at reclaim close, but they are not actionable for an entry placed **after** reclaim close.

This audit therefore removes any row where:
`resolution_i_h1 == reclaim_i_h1`

No detector threshold, anatomy definition, score rule, side logic, or outcome window is changed.

## Frozen detector

Keep exactly:
- A <= 2.073485713625842
- B <= 1.4084118083030879
- C >= 0.4999999999999881
- D >= 0.6013241386375646
- detector = anatomy_score >= 3

## Populations

- Construction audit: 2020-2024.
- Frozen validation audit: 2025.
- Exclude all same-reclaim-bar resolved outcomes from BOTH baseline and detector cohorts.
- Keep unresolved-window negatives.
- 2026+ remains CLOSED in this audit.

## Gates

Use the original V3 validation gates on the stricter actionable population:

1. selected 2025 N >= 50;
2. selected 2025 structural-event rate >= 45%;
3. lift vs actionable 2025 baseline >= 15 percentage points;
4. Wilson 95% lower bound >= 35%;
5. BUY_SIDE selected rate > actionable BUY_SIDE baseline;
6. SELL_SIDE selected rate > actionable SELL_SIDE baseline.

If all pass:
`VALIDATED_ACTIONABLE_STRUCTURAL_LIQUIDITY_DETECTOR`

Otherwise:
`ACTIONABLE_DETECTOR_NOT_VALIDATED_AS_DEFINED`

## Interpretation

This audit does not re-discover or rescue the detector.
It asks only whether the already-frozen detector remains strong when every signal must still have an unresolved future structural consequence at the moment the reclaim candle closes.

Only a passing actionable detector may advance to Adaptive Entry.

2026_PLUS=CLOSED
