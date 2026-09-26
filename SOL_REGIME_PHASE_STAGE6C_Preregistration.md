# SOL Regime + Phase V2 — Stage 6C Scoring Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 6C converts the valid Stage-6B causal lifecycle features into outcome-blind phase evidence scores.

No forward return, TP/SL, future MFE/MAE, trade result, 2025 data, or 2026 data may be used.

## Data / calibration policy

- Input: frozen Stage-6B DEV features.
- 2023 = unsupervised marginal calibration only.
- 2024 = internal score-stability readout.
- 2025 remains the first frozen external holdout.
- 2026 remains final validation.
- No future-price target is used in calibration.

### Symmetric percentile calibration

For every directional feature suffix used by both BULL and BEAR:
- concatenate 2023 BULL-side and BEAR-side values,
- build one pooled empirical CDF,
- apply that exact same transform to both sides.

This prevents side-specific numeric tuning.

Shared balance/volatility features use their 2023 empirical CDF.

The empirical CDF is used only to place heterogeneous causal features on a common [0,1] evidence scale.

## Core derived evidence

For each side independently:

### DirectionEvidence
Equal mean of:
- signed efficiency 6H
- signed efficiency 12H
- aligned EMA20 slope
- aligned EMA spread / ATR
- aligned close fraction 6H
- aligned candle-body fraction 6H
- aligned close-location value

### RecencyEvidence
Equal mean of:
- recent impulse clock
- recent structure-break clock
- recent renewal clock

For an event clock:
- absent anchor = 0 evidence,
- otherwise recency = 1 - pooled percentile(hours_since_event).

### VolExpansionEvidence
Equal mean of:
- ATR slope 6H
- current range / ATR
- ATR vs 72H median

### StretchEvidence
Equal mean of:
- impulse age
- aligned move since impulse in ATR
- MFE since impulse in ATR
- aligned 24H displacement percentile
- distance from EMA20 in ATR
- same-side renewal count 72H

Missing impulse-dependent values contribute 0 rather than neutral evidence.

### RenewalEvidence
Equal mean of:
- renewal recency
- fresh-extreme count 6H
- acceptance beyond prior-24H boundary
- positive short-vs-long efficiency change
- latest reclaim body quality
- latest reclaim close-location quality
- positive post-reclaim progress 1H
- positive post-reclaim progress 3H

Missing reclaim-specific fields contribute 0.

### RejectionEvidence
Equal mean of:
- adverse wick 6H
- failed fresh-break count 6H
- failed reclaim count 24H
- negative marginal-progress quality
- increasing pullback-depth trend
- poor aligned close-location

### DeteriorationEvidence
Equal mean of:
- negative efficiency change 6H vs 24H
- low marginal-progress ratio 3H vs 12H
- increasing pullback depth
- failed fresh-break count 24H

### ControlledPullbackEvidence
Equal mean of:
- low latest completed pullback max depth
- good latest reclaim body
- good latest reclaim close-location
- positive post-reclaim 1H progress

If no completed pullback exists, pullback-specific terms contribute 0.

## Shared BalanceEvidence

Equal mean of:
- mean-cross 24H
- overlap 24H
- low range/path 24H
- boundary-touch count 12H
- failed escape count 24H
- low maximum of Bull DirectionEvidence / Bear DirectionEvidence

## Directional phase scores

All scores are clipped to [0,1].

### EarlyExpansionScore
- 25% RecencyEvidence
- 25% DirectionEvidence
- 20% VolExpansionEvidence
- 15% low StretchEvidence
- 15% fresh acceptance evidence

### HealthyContinuationScore
- 25% DirectionEvidence
- 30% RenewalEvidence
- 15% ControlledPullbackEvidence
- 15% low RejectionEvidence
- 15% mid-Stretch evidence

Mid-Stretch evidence peaks at StretchEvidence=0.50 and falls linearly toward 0 at the extremes.

### MatureTrendScore
- 30% DirectionEvidence
- 30% StretchEvidence
- 15% high impulse/break age evidence
- 15% renewal-count evidence
- 10% low RejectionEvidence

### ExhaustionScore
- 25% DirectionEvidence
- 35% StretchEvidence
- 25% RejectionEvidence
- 15% DeteriorationEvidence

### TransitionScore
- 25% RejectionEvidence
- 20% BalanceEvidence
- 20% low own DirectionEvidence
- 15% failed-reclaim evidence
- 20% opposite-side DirectionEvidence

## Auxiliary directional quality scores

### RemainingEnergyScore
- 30% DirectionEvidence
- 30% RenewalEvidence
- 20% low StretchEvidence
- 20% low RejectionEvidence

### ContinuationQualityScore
- 45% EarlyExpansionScore
- 55% HealthyContinuationScore
then multiplied by:
- `0.75 + 0.25*RemainingEnergyScore`

### ReversalRiskScore
- 55% ExhaustionScore
- 45% TransitionScore

## Sideways phase scores

### CompressionScore
- 25% low ATR percentile 168H
- 20% low compression 6H/24H ratio
- 15% low current range/ATR
- 15% overlap 24H
- 15% mean-cross 24H
- 10% low max directional evidence

### BalancedRangeScore
- 20% overlap 24H
- 20% mean-cross 24H
- 15% low range/path 24H
- 15% boundary-touch count
- 15% failed-escape count
- 15% low max directional evidence

### ExpansionAttemptScore
- 30% VolExpansionEvidence (shared)
- 25% max directional evidence
- 20% max recent impulse evidence
- 15% max recent break evidence
- 10% fresh boundary-acceptance evidence

## Diagnostic winners

Stage 6C may emit:
- BULL provisional directional phase winner
- BEAR provisional directional phase winner
- sideways provisional phase winner

These are diagnostics only, not a final routing state.

No hysteresis and no trading decision are applied in Stage 6C.

## Mandatory audits

1. Stage 6B status is FEATURE_ENGINE_VALID.
2. Input/output years are only 2023 and 2024.
3. Calibration reference contains only 2023 rows.
4. BULL/BEAR transforms use pooled symmetric calibration references.
5. Every finite score is within [0,1].
6. Score coverage after first 168H of 2023 is >=98%.
7. Synthetic BULL/BEAR column swap causes all directional phase/quality scores to swap exactly within 1e-10.
8. No output field contains forward/future/outcome/TP/SL/trade-result labels.
9. In 2024, every main directional score has standard deviation >=0.02.
10. In 2024 pooled BULL+BEAR provisional directional winners, each of the five phases has >=1% share.
11. In 2024 sideways provisional winners, each of the three sideways phases has >=1% share.
12. 2024 score generation uses the frozen 2023 calibration without refitting.

Stage 6C passes only if all mandatory audits pass.
