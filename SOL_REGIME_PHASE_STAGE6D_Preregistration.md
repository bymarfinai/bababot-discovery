# SOL Regime + Phase V2 — Stage 6D DEV Future-Behavior Validation Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 6D tests whether the frozen Stage-6C outcome-blind phase scores actually separate subsequent SOL continuation quality.

No Stage-6B feature, Stage-6C calibration, score weight, or phase formula may be changed in Stage 6D.

## Data boundary
- Frozen scores/features: 2023-2024 only.
- Future prices: SOLUSDT perpetual futures 5m, entirely inside 2023-2024.
- 2025 and 2026 are NOT opened.
- 2023 was used only for outcome-blind marginal calibration in Stage 6C.
- 2024 receives special emphasis as internal temporal validation because Stage-6C calibration was frozen from 2023 before 2024 scoring.

## Frozen direction routing

Every valid 1H row receives exactly one directional side:

- if `bull_DirectionEvidence > bear_DirectionEvidence` -> BULL
- if `bear_DirectionEvidence > bull_DirectionEvidence` -> BEAR
- exact tie -> UNAVAILABLE

No minimum direction threshold is applied.

For the selected side, Stage 6D consumes unchanged:
- provisional directional phase
- ContinuationQualityScore
- RemainingEnergyScore
- ReversalRiskScore
- EarlyExpansionScore
- HealthyContinuationScore
- MatureTrendScore
- ExhaustionScore
- TransitionScore

This routing is frozen before future outcomes are calculated.

## Entry / future-behavior convention

For each selected 1H row:
- state/score is known at the completed 1H close,
- reference entry = SOLUSDT 5m open exactly at `decision_time` / next 1H open,
- future path begins from that open.

Horizons: 6H, 12H, 24H.

For each horizon:
- aligned forward return
- aligned MFE
- aligned MAE
- symmetric ±1% first-hit:
  - ALIGNED_FIRST
  - OPPOSITE_FIRST
  - AMBIGUOUS if both ±1% first touched inside the same 5m candle
  - UNRESOLVED if neither touched

AMBIGUOUS and UNRESOLVED are excluded from resolved directional hit-rate denominators.

## Frozen phase groups

### Continuation group
- EARLY_EXPANSION
- HEALTHY_CONTINUATION

### Late/Risk group
- EXHAUSTION
- TRANSITION

MATURE_TREND is reported separately and is not forced into either group.

## Threshold-free ranking metrics

On resolved 24H ±1% outcomes:
- AUC of ContinuationQualityScore for ALIGNED_FIRST
- AUC of RemainingEnergyScore for ALIGNED_FIRST
- AUC of ReversalRiskScore for ALIGNED_FIRST

AUC is computed from average ranks with ties handled by pandas rank(method="average").
No fitted probability model is used.

Expected:
- continuation / remaining-energy AUC > 0.50
- reversal-risk AUC < 0.50

## Frozen temporal blocks
- 2023-H1
- 2023-H2
- 2024-H1
- 2024-H2

## Mandatory Stage-6D gates

Technical:
1. Stage-6C status is SCORING_VALID.
2. Raw 5m coverage for 2023-2024 >=99.5%.
3. No scored future window crosses 2025-01-01.
4. Same-5m ambiguous 24H share <=2%.
5. Every five directional phases has >=200 eligible 24H selected-side observations across 2023-2024.

Phase separation:
6. HEALTHY_CONTINUATION combined 2023-2024 aligned 24H hit-rate >=55%.
7. EARLY_EXPANSION combined aligned 24H hit-rate >=53%.
8. EXHAUSTION combined aligned 24H hit-rate <=50%.
9. TRANSITION combined aligned 24H hit-rate <=52%.
10. HEALTHY_CONTINUATION minus EXHAUSTION aligned hit-rate >=7 percentage points.
11. Continuation group aligned hit-rate exceeds Late/Risk group by >=5 percentage points.
12. Continuation group median aligned forward 24H return > Late/Risk group median aligned forward 24H return.

Internal temporal validation:
13. On **2024 only**, Continuation group aligned hit-rate >=55%.
14. On **2024 only**, Continuation group exceeds Late/Risk group by >=5 percentage points.
15. Continuation group aligned hit-rate >50% in at least 3 of 4 half-year blocks.

Continuous-score validation:
16. Combined 2023-2024 ContinuationQualityScore AUC >=0.55.
17. Combined RemainingEnergyScore AUC >=0.53.
18. Combined ReversalRiskScore AUC <=0.47.
19. On 2024 only, ContinuationQualityScore AUC >=0.54.
20. On 2024 only, ReversalRiskScore AUC <=0.48.

Stage 6D passes only if **all** mandatory gates pass.

If Stage 6D fails, 2025 remains unopened and the current V2 phase scoring model is not promoted.
