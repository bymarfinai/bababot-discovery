# SOL Regime + Phase V2 — Stage 6D DEV Future-Behavior Validation

Stage 6D tested frozen Stage-6C scores on 2023-2024 only. **2025/2026 remain unopened.**

Raw SOLUSDT 5m coverage: **100.0000%**.

## Phase outcome separation — selected directional side

| Phase | Eligible 24H | Resolved | Aligned hit | Median aligned ret24 | MFE24 | MAE24 |
|---|---:|---:|---:|---:|---:|---:|
| EarlyExpansion | 5753 | 5737 | 50.3% | -0.212% | 2.897% | 2.872% |
| HealthyContinuation | 2814 | 2804 | 51.4% | -0.137% | 2.763% | 2.517% |
| MatureTrend | 2798 | 2791 | 53.3% | 0.038% | 2.742% | 2.505% |
| Exhaustion | 4849 | 4818 | 51.3% | -0.065% | 2.841% | 2.474% |
| Transition | 1305 | 1301 | 50.7% | 0.085% | 2.687% | 2.625% |

## Group separation

| Population | Continuation hit | Late/Risk hit | Gap | Continuation median ret | Risk median ret |
|---|---:|---:|---:|---:|---:|
| 2023-24 | 50.7% | 51.1% | -0.5% | -0.186% | -0.031% |
| 2024 only | 50.4% | 51.1% | -0.7% | -0.099% | 0.013% |

## Half-year robustness

| Block | Continuation hit | Late/Risk hit | Gap |
|---|---:|---:|---:|
| 2023-H1 | 50.2% | 52.5% | -2.3% |
| 2023-H2 | 51.6% | 49.8% | +1.8% |
| 2024-H1 | 50.4% | 51.7% | -1.3% |
| 2024-H2 | 50.3% | 50.4% | -0.1% |

## Threshold-free score ranking (AUC)

| Period | Continuation Quality | Remaining Energy | Reversal Risk |
|---|---:|---:|---:|
| 2023_24 | 0.501 | 0.502 | 0.503 |
| 2023 | 0.501 | 0.507 | 0.498 |
| 2024 | 0.501 | 0.497 | 0.508 |

## Mandatory gates

| Gate | Pass | Value |
|---|---|---|
| stage6c_valid | PASS | True |
| raw_5m_coverage_ge_99_5 | PASS | 1.0 |
| no_24h_window_crosses_2025 | PASS | 2024-12-30 23:00:00+00:00 |
| ambiguous_24h_share_le_2pct | PASS | 0.0007420514869570181 |
| each_phase_ge_200_eligible24 | PASS | {'EarlyExpansion': 5753, 'HealthyContinuation': 2814, 'MatureTrend': 2798, 'Exhaustion': 4849, 'Transition': 1305} |
| healthy_hit_ge_55pct | FAIL | 0.5139087018544936 |
| early_hit_ge_53pct | FAIL | 0.5030503747603277 |
| exhaustion_hit_le_50pct | FAIL | 0.5126608551266085 |
| transition_hit_le_52pct | PASS | 0.5065334358186011 |
| healthy_minus_exhaustion_ge_7pp | FAIL | 0.001247846727885027 |
| continuation_group_minus_risk_ge_5pp | FAIL | {'continuation': 0.5066151504507669, 'risk': 0.5113580650433077, 'gap': -0.004742914592540837} |
| continuation_median_ret_gt_risk | FAIL | {'continuation': -0.0018627886793249893, 'risk': -0.0003063202243818175, 'gap': -0.0015564684549431718} |
| 2024_continuation_hit_ge_55pct | FAIL | 0.5038150807899462 |
| 2024_continuation_minus_risk_ge_5pp | FAIL | {'continuation': 0.5038150807899462, 'risk': 0.5106822880771882, 'gap': -0.006867207287241994} |
| continuation_gt50_in_3of4_blocks | PASS | [{'block': '2023-H1', 'continuation_hit': 0.5022947475777665}, {'block': '2023-H2', 'continuation_hit': 0.5164783427495292}, {'block': '2024-H1', 'continuation_hit': 0.5043201455206913}, {'block': '2024-H2', 'continuation_hit': 0.5033229951262738}] |
| continuation_quality_auc_ge_055 | FAIL | 0.5008725401396853 |
| remaining_energy_auc_ge_053 | FAIL | 0.5015845798924716 |
| reversal_risk_auc_le_047 | FAIL | 0.5028706726995466 |
| 2024_continuation_quality_auc_ge_054 | FAIL | 0.5013834608031494 |
| 2024_reversal_risk_auc_le_048 | FAIL | 0.5076351898670748 |

## Decision

**Status: SOL_REGIME_PHASE_STAGE6D_DEV_VALIDATION_FAILED**

Failed gates: **['healthy_hit_ge_55pct', 'early_hit_ge_53pct', 'exhaustion_hit_le_50pct', 'healthy_minus_exhaustion_ge_7pp', 'continuation_group_minus_risk_ge_5pp', 'continuation_median_ret_gt_risk', '2024_continuation_hit_ge_55pct', '2024_continuation_minus_risk_ge_5pp', 'continuation_quality_auc_ge_055', 'remaining_energy_auc_ge_053', 'reversal_risk_auc_le_047', '2024_continuation_quality_auc_ge_054', '2024_reversal_risk_auc_le_048']**.
2025 remains unopened. The current frozen V2 phase model is not promoted to OOS.
