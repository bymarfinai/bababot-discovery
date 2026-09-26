# SOL Regime Stage 3 — Detector V1

Date: 2026-09-26
Status: V1 candidate frozen
Branch: `sol-regime-forensic-1b`

## Objective

Build a causal detector from Stage 2 features, using DEV 2023-2024 only for construction.

Architecture:
1. directional evidence,
2. asymmetric BULL / BEAR heads,
3. SIDEWAYS only under strong low-volatility evidence,
4. otherwise TRANSITION.

No future values are used by the detector.

## Candidate search

Initial vote-based rules still produced too much TRANSITION contamination.

An asymmetric conjunction search was therefore run on DEV only with a minimum 1% support / ~90 observations.

Two candidates were frozen before VAL/OOS:
- V1-PRECISION
- V1-BALANCED

### V1-BALANCED final rules

BULL if all are true:
- rv24 > 1.1633509829
- ATR14% > 1.8851167596
- distance from 8H high <= -2.9087400396%

BEAR if all are true:
- accel4v12 >= 1.1012155401
- candle close-location >= 0.6260779195

If both BULL and BEAR fire: TRANSITION.

SIDEWAYS only if:
- rv8 < 0.4718633093
- ATR14% < 0.9798115352

Otherwise: TRANSITION.

## Results

### DEV 2023-2024
Base BULL = 17.51%
Base BEAR = 14.19%

BULL:
- precision 31.38%
- recall 11.93%
- lift 1.792x
- predicted n=631
- transition contamination 47.70%
- opposite-side contamination 6.66%

BEAR:
- precision 18.76%
- recall 7.88%
- lift 1.322x
- predicted n=565
- transition contamination 45.84%
- opposite-side contamination 15.93%

Directional coverage = 12.62%
Exact four-state match = 41.29%

### VAL 2025
Base BULL = 16.01%
Base BEAR = 15.66%

BULL:
- precision 22.02%
- recall 6.08%
- lift 1.375x
- predicted n=386
- transition contamination 45.08%
- opposite-side contamination 18.91%

BEAR:
- precision 16.87%
- recall 6.14%
- lift 1.077x
- predicted n=498
- transition contamination 46.79%
- opposite-side contamination 16.27%

Directional coverage = 10.12%
Exact four-state match = 39.77%

### OOS 2026 YTD
Base BULL = 11.04%
Base BEAR = 11.21%

BULL:
- precision 18.75%
- recall 1.70%
- lift 1.699x
- predicted n=64
- transition contamination 37.50%
- opposite-side contamination 14.06%

BEAR:
- precision 12.89%
- recall 3.49%
- lift 1.150x
- predicted n=194
- transition contamination 51.03%
- opposite-side contamination 10.31%

Directional coverage = 4.03%
Exact four-state match = 36.91%

## Comparison with legacy family

The main improvement is BULL selectivity:
- legacy EMA Cross Bull precision was approximately base-rate,
- V1-BALANCED produces a stable BULL lift >1 across DEV, VAL, and OOS,
- OOS BULL lift is ~1.70x.

BEAR remains weak:
- lift is >1 across all periods for V1-BALANCED,
- but only 1.08x in 2025 and 1.15x OOS,
- OOS BEAR transition contamination remains ~51%.

## Verdict

### PASS
- New feature architecture materially improves BULL identification.
- BULL lift remains >1 in DEV -> VAL -> OOS without retuning.
- Bear direction does not invert under V1-BALANCED.
- Detector abstains heavily instead of forcing every hour into BULL/BEAR.

### NOT YET PRODUCTION-READY
- BULL recall becomes very low OOS because absolute DEV volatility thresholds fire less often.
- BEAR head is still weak.
- Transition contamination remains too high, especially for BEAR.
- SIDEWAYS precision is still low (~25%).

Stage 3 therefore produces a valid **research V1 baseline**, not a final live regime engine.

Recommended next formal step:
Stage 4 robustness / forward validation and refinement tests should focus on:
1. volatility-normalized thresholds to recover OOS coverage,
2. improving the BEAR head,
3. adding 15m 30-minute momentum as a causal direction discriminator,
4. preserving the frozen Stage 1C ground truth and no-retune discipline.
