# SOL Regime + Phase V2 — Stage 6B Feature Engine Result

Raw SOLUSDT 5m coverage (2022-06 through 2024): **100.0000%**.
Exported DEV 1H feature rows: **17,544**.
Feature columns: **167**.

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
| raw_indicator_parity_stage2 | PASS | 9.985502008591496e-17 |
| event_clocks_nonnegative_and_reset | PASS | {'negative': {'bull_hours_since_impulse': 0, 'bull_hours_since_break': 0, 'bull_hours_since_raw_switch': 0, 'bull_hours_since_renewal': 0, 'bull_hours_since_fresh_extreme24': 0, 'bear_hours_since_impulse': 0, 'bear_hours_since_break': 0, 'bear_hours_since_raw_switch': 0, 'bear_hours_since_renewal': 0, 'bear_hours_since_fresh_extreme24': 0}, 'reset_bad': {'bull_impulse_event->bull_hours_since_impulse': 0, 'bear_impulse_event->bear_hours_since_impulse': 0, 'bull_break_event->bull_hours_since_break': 0, 'bear_break_event->bear_hours_since_break': 0, 'bull_raw_switch_event->bull_hours_since_raw_switch': 0, 'bear_raw_switch_event->bear_hours_since_raw_switch': 0, 'bull_renewal_event->bull_hours_since_renewal': 0, 'bear_renewal_event->bear_hours_since_renewal': 0}} |
| event_anchor_not_future | PASS | {'bull_hours_since_impulse': 0, 'bull_hours_since_break': 0, 'bull_hours_since_raw_switch': 0, 'bull_hours_since_renewal': 0, 'bull_hours_since_fresh_extreme24': 0, 'bear_hours_since_impulse': 0, 'bear_hours_since_break': 0, 'bear_hours_since_raw_switch': 0, 'bear_hours_since_renewal': 0, 'bear_hours_since_fresh_extreme24': 0} |
| pullback_ages_nonnegative | PASS | {'bull': 0, 'bear': 0} |
| post_reclaim_progress_not_early | PASS | {'bull': {'1h_bad': 0, '3h_bad': 0, 'reclaims': 3358, 'post1': 3358, 'post3': 3358}, 'bear': {'1h_bad': 0, '3h_bad': 0, 'reclaims': 3287, 'post1': 3287, 'post3': 3287}} |
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

**Status: SOL_REGIME_PHASE_STAGE6B_FEATURE_ENGINE_VALID**

The Stage-6B lifecycle / remaining-energy feature engine passed every frozen technical and causality audit.
No phase label or phase score has been created yet.
Stage 6C is authorized to construct phase evidence scores using 2023-2024 DEV only.
