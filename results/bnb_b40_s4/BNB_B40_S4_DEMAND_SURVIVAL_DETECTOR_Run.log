# BNB B40-S4 — Frozen Demand Survival Detector Validation

Primary detector: **SD1_CLOSE15_ABOVE_ANCHOR**
Signature: `c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0`
Rule: at +15m after first retest, PASS iff completed reaction window closes above the original touch anchor.

## Frozen +15m detector validation

| Detector | Period | Eligible | PASS | Survival precision | Base | Uplift | Survivor retention | Consumed rejection | False-pass consumed | Whole-parent survivor capture |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SD1_CLOSE15_ABOVE_ANCHOR | DEV | 532 | 286 (53.8%) | 235/286 (82.2%) | 73.5% | 8.7pp | 60.1% | 63.8% | 51/141 (36.2%) | 47.0% |
| SD1_CLOSE15_ABOVE_ANCHOR | REF | 307 | 160 (52.1%) | 137/160 (85.6%) | 74.3% | 11.4pp | 60.1% | 70.9% | 23/79 (29.1%) | 44.3% |
| B1_ALL3_ABOVE_ANCHOR | DEV | 532 | 158 (29.7%) | 134/158 (84.8%) | 73.5% | 11.3pp | 34.3% | 83.0% | 24/141 (17.0%) | 26.8% |
| B1_ALL3_ABOVE_ANCHOR | REF | 307 | 101 (32.9%) | 91/101 (90.1%) | 74.3% | 15.8pp | 39.9% | 87.3% | 10/79 (12.7%) | 29.4% |
| B2_BREAK_TOUCH_HIGH | DEV | 532 | 58 (10.9%) | 51/58 (87.9%) | 73.5% | 14.4pp | 13.0% | 95.0% | 7/141 (5.0%) | 10.2% |
| B2_BREAK_TOUCH_HIGH | REF | 307 | 43 (14.0%) | 39/43 (90.7%) | 74.3% | 16.4pp | 17.1% | 94.9% | 4/79 (5.1%) | 12.6% |

## Primary year stability

| Year | Eligible | PASS | Survival precision | Base | Uplift | Survivor retention | Consumed rejection |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 173 | 88 | 77.3% | 69.4% | 7.9pp | 56.7% | 62.3% |
| 2023 | 165 | 98 | 84.7% | 78.2% | 6.5pp | 64.3% | 58.3% |
| 2024 | 194 | 100 | 84.0% | 73.2% | 10.8pp | 59.2% | 69.2% |
| 2025 | 200 | 106 | 89.6% | 76.5% | 13.1pp | 62.1% | 76.6% |
| 2026 | 107 | 54 | 77.8% | 70.1% | 7.7pp | 56.0% | 62.5% |

## Operational state-recognition view

| Period | Fast survive already resolved | Fast consumed already resolved | SD1 pass S/C | SD1 reject S/C | Positive precision | Parent survivor recognition |
|---|---:|---:|---:|---:|---:|---:|
| DEV | 109 | 16 | 235/51 | 156/90 | 87.1% | 68.8% |
| REF | 81 | 15 | 137/23 | 91/56 | 90.5% | 70.6% |

## Interpretation boundary
S4 validates demand SURVIVAL only.
The strict benchmarks are reported but cannot replace the preregistered primary detector in this stage.
REF has already been inspected during B40 discovery, so it is confirmation data rather than pristine out-of-sample evidence.
No expansion, entry, SL, or TP conclusion is implied by a survival PASS.
