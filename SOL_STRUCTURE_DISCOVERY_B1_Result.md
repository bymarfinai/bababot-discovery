# SOL Structure Discovery B1 — Development Result

Development-only SOLUSDT 5m coverage: **99.5565%**.

B1 evaluated the nine preregistered dynamic-structure variants. No entry, TP, SL, clock, or OOS optimization was performed.

## Variant gates

| Family | Variant | N | Resolved | WR 4h | Mean R 4h | Median MFE/MAE | Min yearly R | Max clock | Verdict | Exact failure reasons |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| COMPRESSION_EXPANSION | COMPRESSION_EXPANSION_4 | 1660 | 1623 | 49.23% | -0.075R | 0.971 | -0.151R | 6.69% | **FAIL** | WR4h>55%;mean_close_R4h>0;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |
| COMPRESSION_EXPANSION | COMPRESSION_EXPANSION_6 | 1596 | 1559 | 48.75% | +0.005R | 0.934 | -0.028R | 8.02% | **FAIL** | WR4h>55%;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |
| COMPRESSION_EXPANSION | COMPRESSION_EXPANSION_8 | 1447 | 1414 | 50.35% | +0.010R | 1.038 | -0.081R | 8.22% | **FAIL** | WR4h>55%;median_MFE_MAE>=1.15;each_year_mean_R4h>0 |
| IMPULSE_PULLBACK | IMPULSE_PULLBACK_3 | 2834 | 2781 | 51.28% | -0.014R | 1.027 | -0.056R | 6.10% | **FAIL** | WR4h>55%;mean_close_R4h>0;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |
| IMPULSE_PULLBACK | IMPULSE_PULLBACK_4 | 2952 | 2914 | 51.85% | +0.068R | 1.055 | -0.002R | 5.66% | **FAIL** | WR4h>55%;median_MFE_MAE>=1.15;each_year_mean_R4h>0 |
| IMPULSE_PULLBACK | IMPULSE_PULLBACK_6 | 2674 | 2627 | 52.00% | +0.094R | 1.077 | -0.060R | 5.01% | **FAIL** | WR4h>55%;median_MFE_MAE>=1.15;each_year_mean_R4h>0 |
| SWEEP_RECLAIM | SWEEP_RECLAIM_8 | 3206 | 3159 | 48.31% | -0.025R | 0.941 | -0.135R | 5.02% | **FAIL** | WR4h>55%;mean_close_R4h>0;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |
| SWEEP_RECLAIM | SWEEP_RECLAIM_12 | 2772 | 2737 | 47.97% | -0.072R | 0.877 | -0.172R | 5.16% | **FAIL** | WR4h>55%;mean_close_R4h>0;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |
| SWEEP_RECLAIM | SWEEP_RECLAIM_20 | 2220 | 2185 | 48.01% | -0.077R | 0.900 | -0.268R | 5.77% | **FAIL** | WR4h>55%;mean_close_R4h>0;median_MFE_MAE>=1.15;3of4_horizons_positive;each_year_mean_R4h>0 |

## Family robustness

| Family | Passing neighbors | Robust | Representative |
|---|---:|---|---|
| COMPRESSION_EXPANSION | 0/3 | FAIL | — |
| IMPULSE_PULLBACK | 0/3 | FAIL | — |
| SWEEP_RECLAIM | 0/3 | FAIL | — |

## Decision

No family achieved 2-of-3 neighborhood robustness. Stop B1; do not repair thresholds or add variants post-result.

**Status: B1_NO_PASS**

Research only; no live-trading authorization.
