# BNB B39-S4 — Frozen First-5m Expansion Detector Validation

Detector signature: `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
Frozen D1: `p5_close_r > 0.20335748322474653`

## Detector validation

| Detector | Period | Eligible | Signals | GE1R | Base | Uplift | Rel lift | 95% Wilson | >=1.5R | >=2R | Clean1R | Winner retention | Whole GE1R capture | Too-fast win |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| D1_FIRST5_DISPLACEMENT | DEV | 604 | 151 (25.0%) | 108/151 (71.5%) | 52.5% | 19.0pp | 1.36x | 63.9%–78.1% | 83/151 (55.0%) | 69/151 (45.7%) | 93/151 (61.6%) | 34.1% | 28.8% | 58 |
| D1_FIRST5_DISPLACEMENT | REF | 369 | 101 (27.4%) | 83/101 (82.2%) | 56.1% | 26.1pp | 1.46x | 73.6%–88.4% | 67/101 (66.3%) | 53/101 (52.5%) | 64/101 (63.4%) | 40.1% | 34.4% | 34 |
| B15_DISPLACEMENT_BENCHMARK | DEV | 498 | 125 (25.1%) | 101/125 (80.8%) | 53.8% | 27.0pp | 1.50x | 73.0%–86.7% | 77/125 (61.6%) | 60/125 (48.0%) | 86/125 (68.8%) | 37.7% | 26.9% | 107 |
| B15_DISPLACEMENT_BENCHMARK | REF | 309 | 80 (25.9%) | 64/80 (80.0%) | 55.3% | 24.7pp | 1.45x | 70.0%–87.3% | 51/80 (63.7%) | 46/80 (57.5%) | 56/80 (70.0%) | 37.4% | 26.6% | 70 |

## D1 year stability

| Year | Eligible | Signals | GE1R | Base | Uplift | >=1.5R | >=2R | Whole GE1R capture | Too-fast win |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 208 | 57 | 38/57 (66.7%) | 55.8% | 10.9pp | 28/57 (49.1%) | 21/57 (36.8%) | 27.1% | 24 |
| 2023 | 183 | 42 | 30/42 (71.4%) | 52.5% | 19.0pp | 23/42 (54.8%) | 19/42 (45.2%) | 26.1% | 19 |
| 2024 | 213 | 52 | 40/52 (76.9%) | 49.3% | 27.6pp | 32/52 (61.5%) | 29/52 (55.8%) | 33.3% | 15 |
| 2025 | 231 | 62 | 52/62 (83.9%) | 59.3% | 24.6pp | 41/62 (66.1%) | 32/62 (51.6%) | 31.5% | 28 |
| 2026 | 138 | 39 | 31/39 (79.5%) | 50.7% | 28.8pp | 26/39 (66.7%) | 21/39 (53.8%) | 40.8% | 6 |

## Market-at-signal lateness diagnostic

| Period | Signals | Med displacement | Med reward left to anchor+1R | Med risk to floor | Med implied R:R | IQR implied R:R |
|---|---:|---:|---:|---:|---:|---:|
| DEV | 151 | 0.360 event-R | 0.640 | 1.360 | 0.470 | 0.331–0.588 |
| REF | 101 | 0.410 event-R | 0.590 | 1.410 | 0.418 | 0.314–0.554 |

## Interpretation boundary
S4 validates the frozen D1 character only.
B15 is a timing benchmark and cannot be promoted from this test.
Market-at-signal R:R is diagnostic only; no entry policy is optimized here.
If D1 passes robustness but market entry is late, the next stage must discover entry geometry around the same frozen D1 character without changing its threshold.
