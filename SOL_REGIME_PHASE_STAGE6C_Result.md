# SOL Regime + Phase V2 — Stage 6C Outcome-Blind Scoring Result

Stage 6C used **2023 only for unsupervised marginal calibration** and produced scores for 2023-2024 without using future price outcomes.

## Mandatory audits

| Audit | Pass | Value |
|---|---|---|
| stage6b_valid | PASS | True |
| dev_years_only | PASS | [2023, 2024] |
| calibration_2023_only | PASS | [2023] |
| pooled_symmetric_pair_calibration | PASS | {'pair_refs': 30, 'method': 'pooled bull+bear 2023'} |
| all_scores_in_0_1 | PASS | 0 |
| score_coverage_ge_98pct | PASS | 1.0 |
| synthetic_bull_bear_swap_exact | PASS | 0.0 |
| no_future_outcome_fields | PASS | [] |
| 2024_main_score_std_ge_0_02 | PASS | {'bull_EarlyExpansionScore': 0.11703802465016704, 'bull_HealthyContinuationScore': 0.10272657639078378, 'bull_MatureTrendScore': 0.09694486455883013, 'bull_ExhaustionScore': 0.10522865236961446, 'bull_TransitionScore': 0.0985454358755225, 'bear_EarlyExpansionScore': 0.12078063083773002, 'bear_HealthyContinuationScore': 0.10445264612689514, 'bear_MatureTrendScore': 0.09905489547153545, 'bear_ExhaustionScore': 0.10161599265166313, 'bear_TransitionScore': 0.10040364855119879, 'CompressionScore': 0.13139176203596958, 'BalancedRangeScore': 0.10125212920799967, 'ExpansionAttemptScore': 0.11060261841195722} |
| 2024_each_directional_phase_winner_ge_1pct | PASS | {'EarlyExpansion': 0.18419854280510017, 'HealthyContinuation': 0.08498406193078324, 'MatureTrend': 0.08709016393442623, 'Exhaustion': 0.14879326047358835, 'Transition': 0.494933970856102} |
| 2024_each_sideways_phase_winner_ge_1pct | PASS | {'Compression': 0.1567622950819672, 'BalancedRange': 0.12249544626593807, 'ExpansionAttempt': 0.7207422586520947} |
| 2024_uses_frozen_2023_calibration | PASS | {'refit_2024': False} |

## 2024 provisional directional phase winners

| Context | Early | Healthy | Mature | Exhaustion | Transition |
|---|---:|---:|---:|---:|---:|
| BULL | 19.4% | 9.6% | 9.2% | 14.3% | 47.5% |
| BEAR | 17.4% | 7.4% | 8.2% | 15.5% | 51.5% |

## 2024 provisional sideways phase winners

| Compression | Balanced Range | Expansion Attempt |
|---:|---:|---:|
| 15.7% | 12.2% | 72.1% |

## 2024 auxiliary score medians

| Side | Remaining Energy | Continuation Quality | Reversal Risk |
|---|---:|---:|---:|
| BULL | 0.471 | 0.451 | 0.561 |
| BEAR | 0.455 | 0.432 | 0.566 |

## Decision

**Status: SOL_REGIME_PHASE_STAGE6C_SCORING_VALID**

The outcome-blind phase scoring engine passed all frozen range, symmetry, coverage, calibration, and non-degeneracy audits.
These scores are not yet claimed to predict +1%/-1% outcomes.
Stage 6D is authorized to test whether phase / remaining-energy scores actually separate future continuation quality on 2023-2024 DEV, with 2025 still untouched.
