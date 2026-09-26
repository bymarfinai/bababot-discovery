# SOL Regime Detector — Stage 3 Raw Scoring Result

Stage 3 used **2023–2024 only**. 2025/2026 were not scored or inspected.

## Mandatory audits

| Audit | Pass | Value |
|---|---|---|
| stage2_valid | PASS | True |
| no_2025_2026_rows | PASS | [2023, 2024] |
| all_scores_in_0_1 | PASS | 0 |
| score_coverage_ge_99_5 | PASS | 0.9985750113999088 |
| directional_mirror_swaps_bull_bear | PASS | 0.0 |
| sideways_mirror_invariant | PASS | 0.0 |
| no_future_outcome_fields | PASS | [] |
| nondegenerate_class_shares | PASS | {'BULL': 0.3040698670015412, 'BEAR': 0.25446657914264514, 'SIDEWAYS': 0.4414635538558137} |
| score_std_gt_0_03 | PASS | {'BullScore': 0.20072520401759625, 'BearScore': 0.1983499682197219, 'SidewaysScore': 0.14439815742572554} |

## Raw provisional regime distribution (no hysteresis)

| Period | Bull | Bear | Sideways |
|---|---:|---:|---:|
| 2023–24 combined | 30.4% | 25.4% | 44.1% |
| 2023 | 31.2% | 25.4% | 43.3% |
| 2024 | 29.6% | 25.5% | 44.9% |

## Score medians and separation

| Year | Bull median | Bear median | Sideways median | Margin median | Confidence median |
|---|---:|---:|---:|---:|---:|
| 2023 | 0.470 | 0.444 | 0.584 | 0.176 | 0.439 |
| 2024 | 0.472 | 0.451 | 0.587 | 0.171 | 0.437 |

## Raw run-length diagnostic before hysteresis

| Regime | Runs | Median consecutive hours | P90 hours |
|---|---:|---:|---:|
| BULL | 491 | 4.0 | 29.0 |
| BEAR | 453 | 4.0 | 27.0 |
| SIDEWAYS | 835 | 6.0 | 23.0 |

## Decision

**Status: SOL_REGIME_DETECTOR_STAGE3_RAW_SCORING_VALID**

The unsupervised BullScore / BearScore / SidewaysScore system passed all frozen technical and symmetry audits.
These raw argmax classes are **not the final detector**. Stage 4 must add hysteresis, minimum persistence, transition flags, and confidence handling before any forward-behavior validation.
No 2025/2026 data or trading result was used.
