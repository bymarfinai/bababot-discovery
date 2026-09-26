# SOL Regime Detector — Stage 5 Forward-Behavior Validation

Stage 5 validated the **frozen Stage-4 states** on 2023-2024 future price behavior only. No 2025/2026 data were used.

Raw SOLUSDT 5m DEV coverage: **100.0000%**.

## 24H ±1% first-hit behavior

| Regime | Eligible | Resolved | Resolved rate | +1 first | -1 first | +1 share resolved | Aligned hit | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| BULL | 3750 | 3725 | 99.3% | 1798 | 1927 | 48.3% | 48.3% | 0.11% |
| BEAR | 3815 | 3801 | 99.6% | 1919 | 1882 | 50.5% | 49.5% | 0.10% |
| SIDEWAYS | 9954 | 9925 | 99.7% | 4892 | 5033 | 49.3% | — | 0.05% |

## Forward return / excursion

| Regime | Median 6H ret | Median 12H ret | Median 24H ret | Median MFE24 | Median MAE24 |
|---|---:|---:|---:|---:|---:|
| BULL | -0.016% | -0.012% | 0.147% | 2.923% | 2.840% |
| BEAR | 0.158% | 0.202% | 0.269% | 2.665% | 2.773% |
| SIDEWAYS | 0.018% | 0.028% | -0.017% | 2.692% | 2.619% |

## Temporal robustness — aligned 24H ±1% hit rate

| Block | Bull | Bear |
|---|---:|---:|
| 2023-H1 | 47.7% | 48.0% |
| 2023-H2 | 46.3% | 49.3% |
| 2024-H1 | 47.2% | 54.2% |
| 2024-H2 | 51.5% | 45.3% |

## Transition diagnostic

- CLEAN directional states: **49.4%** aligned, n=3944.
- TRANSITION directional states: **48.4%** aligned, n=3582.
- CLEAN minus TRANSITION: **1.0%**.

## Mandatory gates

| Gate | Pass | Value |
|---|---|---|
| stage4_valid | PASS | True |
| raw_5m_coverage_ge_99_5 | PASS | 1.0 |
| no_scored_24h_window_crosses_2025 | PASS | 2024-12-30 23:00:00+00:00 |
| each_regime_at_least_1000_24h_obs | PASS | {'BULL': 3750, 'BEAR': 3815, 'SIDEWAYS': 9954} |
| each_regime_resolved_rate_ge_60pct | PASS | {'BULL': 0.9933333333333333, 'BEAR': 0.9963302752293578, 'SIDEWAYS': 0.9970865983524211} |
| bull_aligned_hit_ge_55pct | FAIL | 0.48268456375838925 |
| bear_aligned_hit_ge_55pct | FAIL | 0.49513285977374377 |
| bull_vs_bear_pos_first_gap_ge_10pp | FAIL | -0.022182576467866977 |
| sideways_pos_first_45_to_55pct | PASS | 0.49289672544080604 |
| median_ret_order_bull_side_bear | FAIL | {'BULL': 0.001467495912714778, 'BEAR': 0.0026908369919274033, 'SIDEWAYS': -0.00017006023633053813} |
| bull_positive_bear_negative_median_ret | FAIL | {'BULL': 0.001467495912714778, 'BEAR': 0.0026908369919274033, 'SIDEWAYS': -0.00017006023633053813} |
| directional_excursion_medians | PASS | {'mfe': {'BULL': 0.029234187574954773, 'BEAR': 0.02665028587629359, 'SIDEWAYS': 0.02692033396164417}, 'mae': {'BULL': 0.02840131725659245, 'BEAR': 0.027734246874886126, 'SIDEWAYS': 0.026185774882145352}} |
| bull_gt50_in_3of4_blocks | FAIL | [{'block': '2023-H1', 'aligned_hit_rate': 0.4766269477543538}, {'block': '2023-H2', 'aligned_hit_rate': 0.4631979695431472}, {'block': '2024-H1', 'aligned_hit_rate': 0.472}, {'block': '2024-H2', 'aligned_hit_rate': 0.5149330587023687}] |
| bear_gt50_in_3of4_blocks | FAIL | [{'block': '2023-H1', 'aligned_hit_rate': 0.47964250248262164}, {'block': '2023-H2', 'aligned_hit_rate': 0.4927536231884058}, {'block': '2024-H1', 'aligned_hit_rate': 0.5418943533697632}, {'block': '2024-H2', 'aligned_hit_rate': 0.4530663329161452}] |
| clean_beats_transition_by_2pp | FAIL | {'clean': 0.4936612576064909, 'transition': 0.48380792853154664, 'gap': 0.00985332907494424, 'n': {'CLEAN': {'n': 3944, 'aligned_rate': 0.4936612576064909}, 'TRANSITION': {'n': 3582, 'aligned_rate': 0.48380792853154664}}} |
| ambiguous_share_le_2pct | PASS | {'BULL': 0.0010666666666666667, 'BEAR': 0.0010484927916120576, 'SIDEWAYS': 0.0005023106288929073} |
| stage4_states_not_recomputed | PASS | [] |

## Decision

**Status: SOL_REGIME_DETECTOR_STAGE5_REGIME_VALIDATION_FAILED**

Failed gates: **['bull_aligned_hit_ge_55pct', 'bear_aligned_hit_ge_55pct', 'bull_vs_bear_pos_first_gap_ge_10pp', 'median_ret_order_bull_side_bear', 'bull_positive_bear_negative_median_ret', 'bull_gt50_in_3of4_blocks', 'bear_gt50_in_3of4_blocks', 'clean_beats_transition_by_2pp']**.
The current detector is not promoted to Stage 6 OOS as a validated regime detector. Any redesign must be preregistered separately; Stage-5 outcomes may not be used retroactively while claiming a pristine validation.
