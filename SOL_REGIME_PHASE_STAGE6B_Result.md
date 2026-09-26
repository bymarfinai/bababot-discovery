# SOL Regime + Phase V2 — Stage 6B Feature Engine Result

Raw SOLUSDT 5m coverage (2022-12 through 2024): **100.0000%**.
Exported DEV 1H feature rows: **17,544**.
Feature columns: **165**.

## Causal event counts

| Event | Bull | Bear |
|---|---:|---:|
| IMPULSE | 918 | 857 |
| BREAK | 2834 | 2345 |
| RAW_SWITCH | 491 | 453 |
| RENEWAL | 750 | 523 |
| FAILED_RECLAIM | 565 | 849 |

## Mandatory audits

| Audit | Pass | Value |
|---|---|---|
| stage6a_taxonomy_frozen | PASS | True |
| stage2_feature_engine_valid | PASS | True |
| raw_5m_coverage_ge_99_5 | PASS | 1.0 |
| all_exported_1h_complete | PASS | 0 |
| dev_years_only | PASS | [2023, 2024] |
| raw_indicator_parity_stage2 | FAIL | 0.0027209904805481685 |
| event_clocks_nonnegative_and_reset | PASS | {'negative': {'bull_hours_since_impulse': 0, 'bull_hours_since_break': 0, 'bull_hours_since_raw_switch': 0, 'bull_hours_since_renewal': 0, 'bull_hours_since_fresh_extreme24': 0, 'bear_hours_since_impulse': 0, 'bear_hours_since_break': 0, 'bear_hours_since_raw_switch': 0, 'bear_hours_since_renewal': 0, 'bear_hours_since_fresh_extreme24': 0}, 'reset_bad': {'bull_impulse_event->bull_hours_since_impulse': 0, 'bear_impulse_event->bear_hours_since_impulse': 0, 'bull_break_event->bull_hours_since_break': 0, 'bear_break_event->bear_hours_since_break': 0, 'bull_raw_switch_event->bull_hours_since_raw_switch': 0, 'bear_raw_switch_event->bear_hours_since_raw_switch': 0, 'bull_renewal_event->bull_hours_since_renewal': 0, 'bear_renewal_event->bear_hours_since_renewal': 0}} |
| event_anchor_not_future | PASS | {'bull_hours_since_impulse': 0, 'bull_hours_since_break': 0, 'bull_hours_since_raw_switch': 0, 'bull_hours_since_renewal': 0, 'bull_hours_since_fresh_extreme24': 0, 'bear_hours_since_impulse': 0, 'bear_hours_since_break': 0, 'bear_hours_since_raw_switch': 0, 'bear_hours_since_renewal': 0, 'bear_hours_since_fresh_extreme24': 0} |
| pullback_ages_nonnegative | PASS | {'bull': 0, 'bear': 0} |
| post_reclaim_progress_not_early | FAIL | {'bull': {'1h_bad': 809, '3h_bad': 809}, 'bear': {'1h_bad': 742, '3h_bad': 742}} |
| prefix_causality_all_checkpoints | PASS | 4/4 |
| no_future_outcome_fields | PASS | [] |
| core_feature_coverage_ge_98pct | PASS | 0.9999424493554327 |
| single_symmetric_side_feature_function | PASS | side_features(z, side) |

## Prefix causality

| Checkpoint | Pass | Max numeric diff | Categorical mismatch |
|---|---|---:|---:|
| 2023-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2023-12-31 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2024-06-30 23:00:00+00:00 | PASS | 0.0 | 0 |
| 2024-12-30 23:00:00+00:00 | PASS | 0.0 | 0 |

## Decision

**Status: SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_REJECTED**

Failed audits: **['raw_indicator_parity_stage2', 'post_reclaim_progress_not_early']**.
Stage 6C is blocked until a technical repair passes the same frozen audits.
