# SOL Regime Detector — Stage 3 Scoring Preregistration

**Status: FROZEN BEFORE RESULT-BEARING EXECUTION**

Stage 3 converts the valid Stage-2 causal feature engine into three competing raw evidence scores:

- BullScore
- BearScore
- SidewaysScore

No hysteresis is applied yet. No forward return, TP/SL, trade outcome, future MFE/MAE, or 2025/2026 information is used to construct or tune the scores.

## Data policy
- Input: Stage-2 causal feature rows.
- Stage-3 analysis window: 2023-01-01 through 2024-12-31 only.
- 2025 and 2026 are not scored, summarized, inspected, or used for calibration in Stage 3.
- No supervised labels exist in Stage 3.

## Design principle
Each score is an equal-concept evidence aggregation, not a fitted model.

Directional evidence is deliberately symmetric:
- Bull and Bear use mirror transforms.
- Sideways has its own positive balance evidence.
- MIXED structure is not treated automatically as Sideways.

## Frozen transforms

Let:
- `dir01(x,s) = 0.5 + 0.5*tanh(x/s)`
- `clip01(x) = min(max(x,0),1)`
- `ATRn = h1_ATR14 / close`

Directional features are normalized into ATR units where possible.

### Bull / Bear structure family
- BULL_SEQ: Bull=1.00, Bear=0.00, Sideways structural balance=0.15
- BEAR_SEQ: Bull=0.00, Bear=1.00, Sideways structural balance=0.15
- MIXED: Bull=0.25, Bear=0.25, Sideways structural balance=1.00
- INSUFFICIENT: all directional structure=0.25, Sideways structural balance=0.50

### Directional drift family
Bull drift = mean of:
1. `dir01(h1_ema20_slope3_atr, 0.60)`
2. `dir01((h1_ema_spread / ATRn), 1.00)`
3. `dir01((h1_ret_12 / ATRn), 2.50)`
4. `dir01((h1_ret_24 / ATRn), 4.00)`

Bear drift is the exact sign mirror.

### Directional efficiency family
`signed_eff = h1_eff_24 * (h1_upfrac_24 - h1_dnfrac_24)`

- Bull efficiency = `dir01(signed_eff, 0.25)`
- Bear efficiency = `dir01(-signed_eff, 0.25)`

### Acceptance / persistence family
`trend_persistence = mean(1-clip01(h1_mean_cross_24/8), 1-h1_overlap_24)`

`dist20_atr = h1_close_ema20_dist / ATRn`

- Bull acceptance = `0.70*dir01(dist20_atr,0.80) + 0.30*trend_persistence`
- Bear acceptance = exact sign mirror for distance plus the same persistence component.

### Fully-completed 4H context family
4H structure mapping:
- matching directional sequence = 1.00
- MIXED = 0.35
- opposing directional sequence = 0.00
- insufficient = 0.25

Bull 4H directional context = mean of:
1. 4H structure evidence
2. `dir01(h4_ret_6,0.06)`
3. `dir01(h4_ema_spread,0.02)`
4. `dir01(h4_close_ema20_dist,0.03)`

Bear context is the exact sign mirror.

### Bull / Bear total score
Frozen weights:
- Structure: 0.25
- Drift: 0.25
- Directional efficiency: 0.18
- Acceptance/persistence: 0.14
- 4H context: 0.18

Weights sum to 1.00.

## Sideways score
Positive balance evidence:

1. structural balance: weight 0.18
2. low directional efficiency `1-h1_eff_24`: weight 0.20
3. mean-cross intensity `clip01(h1_mean_cross_24/6)`: weight 0.18
4. candle overlap `h1_overlap_24`: weight 0.14
5. path containment `1-clip01(h1_range_path_24/0.80)`: weight 0.12
6. muted 24H drift `1-abs(tanh((h1_ret_24/ATRn)/4))`: weight 0.10
7. completed-4H balance: weight 0.08

4H balance = mean of:
- structure balance: MIXED=1.0, BULL_SEQ/BEAR_SEQ=0.15, insufficient=0.5
- muted 4H return: `1-abs(tanh(h4_ret_6/0.06))`
- muted 4H EMA spread: `1-abs(tanh(h4_ema_spread/0.02))`

Weights sum to 1.00.

## Raw provisional class
Before hysteresis:
- provisional regime = argmax(BullScore, BearScore, SidewaysScore)
- raw score margin = top score - second-highest score
- confidence_raw = 0.5*top_score + 0.5*score_margin

This provisional class is diagnostic only. Stage 4 will add persistence/hysteresis and transition handling.

## Mandatory audits
1. Stage-2 status must be VALID.
2. 2025/2026 rows must not appear in Stage-3 output.
3. Every finite score must be in [0,1].
4. Score coverage across 2023-2024 must be >=99.5%.
5. Directional mirror audit on synthetic sign-flipped rows must swap BullScore/BearScore within 1e-10.
6. SidewaysScore must be unchanged by directional sign mirroring within 1e-10.
7. No future/outcome/TP/SL/MFE/MAE fields may appear.
8. All three provisional classes must each occupy at least 5% of 2023-2024 rows; otherwise the score system is considered degenerate.
9. Each score standard deviation must exceed 0.03 on 2023-2024; otherwise it is considered non-informative.

Stage 3 passes only if all mandatory audits pass.
