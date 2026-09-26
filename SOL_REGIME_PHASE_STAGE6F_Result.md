# SOL Regime + Phase V2 — Stage 6F Predictive Feature Forensics

Stage 6F scanned individual causal Stage-6B features using **2023 discovery** and **2024 frozen-rule validation**. 2025/2026 were not opened.

- Candidates constructed: **92**.
- Eligible after support floors: **92**.
- STRONG_SURVIVOR: **0**.
- WATCHLIST: **0**.

## Top validated individual features

| Feature | Type | Direction | AUC23 | AUC24 | Hit23 | Lift23 | Hit24 | Lift24 | + blocks | Tier |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| SIDE:post_reclaim_progress_1h | CONTINUOUS | LOW | 0.502 | 0.522 | 50.6% | -1.1% | 51.2% | +0.4% | 3 | NO_EDGE |
| SHARED:h1_mean_cross_24 | CONTINUOUS | HIGH | 0.518 | 0.518 | 54.3% | +2.7% | 51.6% | +0.8% | 3 | NO_EDGE |
| SIDE:failed_fresh_break_count_24h | CONTINUOUS | LOW | 0.505 | 0.518 | 52.3% | +0.7% | 52.6% | +1.7% | 4 | NO_EDGE |
| SIDE:adverse_wick_frac | CONTINUOUS | HIGH | 0.511 | 0.516 | 53.1% | +1.4% | 53.0% | +2.1% | 4 | NO_EDGE |
| SHARED:h1_atr_norm | CONTINUOUS | LOW | 0.517 | 0.514 | 53.6% | +1.9% | 52.7% | +1.8% | 3 | NO_EDGE |
| SIDE:latest_reclaim_body_frac | CONTINUOUS | HIGH | 0.511 | 0.514 | 53.7% | +2.1% | 52.8% | +2.0% | 3 | NO_EDGE |
| SHARED:v1_regime_duration_hours | CONTINUOUS | HIGH | 0.510 | 0.513 | 53.3% | +1.6% | 52.4% | +1.6% | 4 | NO_EDGE |
| SIDE:favorable_excursion_3h | CONTINUOUS | LOW | 0.502 | 0.513 | 50.8% | -0.8% | 53.5% | +2.6% | 3 | NO_EDGE |
| SIDE:adverse_wick_3h | CONTINUOUS | HIGH | 0.508 | 0.513 | 51.1% | -0.5% | 51.4% | +0.6% | 3 | NO_EDGE |
| SIDE:distance_protected_atr | CONTINUOUS | HIGH | 0.503 | 0.512 | 53.8% | +2.2% | 51.1% | +0.3% | 3 | NO_EDGE |
| SIDE:pullback_depth_trend | CONTINUOUS | LOW | 0.505 | 0.512 | 53.2% | +1.6% | 51.9% | +1.0% | 3 | NO_EDGE |
| SIDE:adverse_wick_6h | CONTINUOUS | HIGH | 0.502 | 0.512 | 51.0% | -0.6% | 50.9% | +0.1% | 2 | NO_EDGE |
| SIDE:ema20_slope_atr | CONTINUOUS | HIGH | 0.504 | 0.512 | 53.0% | +1.3% | 50.9% | +0.1% | 3 | NO_EDGE |
| SHARED:h1_mean_cross_12 | CONTINUOUS | HIGH | 0.502 | 0.511 | 51.4% | -0.2% | 51.8% | +0.9% | 3 | NO_EDGE |
| SIDE:progress_path_12h | CONTINUOUS | HIGH | 0.505 | 0.511 | 52.9% | +1.3% | 49.3% | -1.6% | 2 | NO_EDGE |

## 2024 oriented-AUC distribution

{0.5: 0.5003439997543291, 0.75: 0.5038610213666438, 0.9: 0.5123691611627529, 0.95: 0.5141139956710896, 0.99: 0.5186322487295826}

## Survivors

**No feature met either frozen survivor gate.**

## Technical audits

| Audit | Pass | Value |
|---|---|---|
| stage6d_failed_status_present | PASS | True |
| stage6b_valid | PASS | True |
| dev_years_only | PASS | [2023, 2024] |
| no_2025_2026_loaded | PASS | [2023, 2024] |
| direction_routing_copied_from_6d | PASS | {'BULL': 9028, 'BEAR': 8515} |
| future_labels_copied_from_6d | PASS | {'source': 'Stage6D labels', 'relabel': False} |
| 2024_not_used_for_rule_fit | PASS | {'fit_year': 2023, 'validation_year': 2024} |
| at_least_50_eligible_candidates | PASS | 92 |
| candidate_names_no_future_fields | PASS | [] |
| promoted_rows_match_frozen_gates | PASS | [] |

## Decision

**Status: SOL_REGIME_PHASE_STAGE6F_NO_UNIVARIATE_EDGE**

No individual Stage-6B feature survived even the preregistered watchlist gate from 2023 into 2024.
This indicates the missing edge is unlikely to be a simple one-feature threshold and motivates interaction/event-sequence research rather than more single-score weighting.
