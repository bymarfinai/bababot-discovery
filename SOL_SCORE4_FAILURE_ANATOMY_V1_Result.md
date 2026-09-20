# SOL Score-4 Failure Anatomy V1 — Result

- 5m coverage: **99.769767%**
- Score 4 only; GAP25 entry; static RECLAIM_EXTREME SL.
- Primary exit analyzed: structural completion.
- All evidence through 2026-08-26 is retrospective.
- Post-cutoff data remained CLOSED.

## Period anatomy

| Period | N | Mean R | PF | Median MFE | Median giveback | SL hit | Touch 1.0R | Fixed 1.5R mean |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HIST_2020_2024 | 34 | 0.113 | 1.202 | 0.830 | 1.266 | 55.88% | 41.18% | 0.052 |
| RETRO_2025 | 12 | 0.451 | 2.082 | 0.930 | 0.844 | 41.67% | 50.00% | 0.194 |
| RETRO_2026_PRE | 10 | -0.368 | 0.455 | 0.631 | 1.227 | 60.00% | 30.00% | -0.321 |

## 2026 material feature shifts

| Feature | Hist median | 2025 shift | 2026 shift | Direction | Material |
|---|---:|---:|---:|---|---|
| structural_target_distance_range_units | 1.053 | 0.338 IQR | -0.704 IQR | DOWN | YES |
| reclaim_directional_body_range_units | 0.886 | -0.103 IQR | 0.528 IQR | UP | YES |

## 2026 side anatomy

| Side | N | Mean R | PF | Median MFE | Median giveback |
|---|---:|---:|---:|---:|---:|
| BUY_SIDE | 8 | -0.493 | 0.315 | 0.431 | 1.227 |
| SELL_SIDE | 2 | 0.133 | 1.265 | 1.037 | 0.904 |

## Failure cohorts

| Period | Cohort | N | Share | Median MFE | Median giveback | Positive-event rate |
|---|---|---:|---:|---:|---:|---:|
| HIST_2020_2024 | LARGE_LOSS | 19 | 55.88% | 0.479 | 1.479 | 10.53% |
| HIST_2020_2024 | SMALL_WIN | 2 | 5.88% | 0.671 | 0.245 | 100.00% |
| HIST_2020_2024 | STRONG_WIN | 13 | 38.24% | 1.516 | 0.250 | 100.00% |
| RETRO_2025 | LARGE_LOSS | 5 | 41.67% | 0.655 | 1.655 | 0.00% |
| RETRO_2025 | SMALL_WIN | 2 | 16.67% | 1.129 | 0.662 | 100.00% |
| RETRO_2025 | STRONG_WIN | 5 | 41.67% | 1.911 | 0.364 | 100.00% |
| RETRO_2026_PRE | LARGE_LOSS | 7 | 70.00% | 0.249 | 1.249 | 0.00% |
| RETRO_2026_PRE | STRONG_WIN | 3 | 30.00% | 1.450 | 0.670 | 66.67% |

## Frozen diagnosis

- **FAILURE_MODE_E_SIDE_CONCENTRATION**

**VERDICT: SCORE4_FAILURE_MODE_IDENTIFIED_RETROSPECTIVELY**

No filter, TP, or exit rule was created in this experiment. Any next rule must be preregistered separately and requires fresh future data for validation.

POST_CUTOFF_DATA=CLOSED
