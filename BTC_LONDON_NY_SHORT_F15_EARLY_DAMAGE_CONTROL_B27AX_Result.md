# B27AX — BTC London->NY SHORT F15 Early Damage-Control Threshold Map — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27AT E20 baseline reproduced exactly before any early-exit candidate was interpreted.

Frozen pooled-major baseline: N=163, E20 activated=92, total **$-15.058**.

Each candidate is one independent decision at 5m, 10m, or 15m after the fill bar; if H2 had already occurred or the baseline trade had exited, that trade cannot be early-cut.

## Pooled-major map

| Candidate | Feature | Horizon | Threshold | At risk | Cuts | Cut baseline winners | Cut baseline E20 | WR | PF | Exp/trade $ | Total $ | Delta vs baseline | Eligible |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| AC_H05_T05 | adverse_close_r | 5m | 0.05R | 125 | 59 | 23 | 25 | 39.3% | 0.798 | -0.272 | -44.344 | -29.285 | NO |
| AC_H05_T10 | adverse_close_r | 5m | 0.10R | 125 | 39 | 16 | 16 | 43.6% | 0.822 | -0.265 | -43.190 | -28.131 | NO |
| AC_H05_T15 | adverse_close_r | 5m | 0.15R | 125 | 24 | 9 | 9 | 47.9% | 0.914 | -0.139 | -22.645 | -7.586 | NO |
| AC_H05_T20 | adverse_close_r | 5m | 0.20R | 125 | 10 | 2 | 2 | 52.1% | 0.973 | -0.044 | -7.239 | 7.820 | NO |
| AC_H05_T25 | adverse_close_r | 5m | 0.25R | 125 | 7 | 1 | 1 | 52.8% | 0.964 | -0.061 | -9.955 | 5.103 | NO |
| AC_H10_T05 | adverse_close_r | 10m | 0.05R | 107 | 71 | 27 | 31 | 37.4% | 0.736 | -0.346 | -56.397 | -41.339 | NO |
| AC_H10_T10 | adverse_close_r | 10m | 0.10R | 107 | 52 | 18 | 19 | 42.9% | 0.846 | -0.209 | -34.132 | -19.074 | NO |
| AC_H10_T15 | adverse_close_r | 10m | 0.15R | 107 | 41 | 14 | 15 | 45.4% | 0.851 | -0.219 | -35.646 | -20.587 | NO |
| AC_H10_T20 | adverse_close_r | 10m | 0.20R | 107 | 17 | 5 | 5 | 50.3% | 0.861 | -0.231 | -37.644 | -22.586 | NO |
| AC_H10_T25 | adverse_close_r | 10m | 0.25R | 107 | 9 | 2 | 2 | 52.1% | 0.864 | -0.229 | -37.398 | -22.340 | NO |
| AC_H15_T05 | adverse_close_r | 15m | 0.05R | 89 | 69 | 26 | 29 | 38.7% | 0.705 | -0.400 | -65.270 | -50.211 | NO |
| AC_H15_T10 | adverse_close_r | 15m | 0.10R | 89 | 53 | 17 | 18 | 43.6% | 0.831 | -0.234 | -38.221 | -23.162 | NO |
| AC_H15_T15 | adverse_close_r | 15m | 0.15R | 89 | 41 | 15 | 16 | 44.8% | 0.782 | -0.330 | -53.824 | -38.766 | NO |
| AC_H15_T20 | adverse_close_r | 15m | 0.20R | 89 | 23 | 6 | 6 | 49.7% | 0.849 | -0.243 | -39.611 | -24.553 | NO |
| AC_H15_T25 | adverse_close_r | 15m | 0.25R | 89 | 18 | 5 | 5 | 50.3% | 0.829 | -0.284 | -46.350 | -31.292 | NO |
| WI_H05_T05 | wick_imbalance_r | 5m | 0.05R | 125 | 67 | 29 | 32 | 36.2% | 0.749 | -0.325 | -52.946 | -37.887 | NO |
| WI_H05_T10 | wick_imbalance_r | 5m | 0.10R | 125 | 49 | 21 | 22 | 40.5% | 0.759 | -0.347 | -56.574 | -41.515 | NO |
| WI_H05_T15 | wick_imbalance_r | 5m | 0.15R | 125 | 35 | 15 | 15 | 44.2% | 0.817 | -0.279 | -45.453 | -30.395 | NO |
| WI_H05_T20 | wick_imbalance_r | 5m | 0.20R | 125 | 20 | 7 | 7 | 49.1% | 0.925 | -0.125 | -20.388 | -5.329 | NO |
| WI_H05_T25 | wick_imbalance_r | 5m | 0.25R | 125 | 15 | 5 | 5 | 50.3% | 0.946 | -0.090 | -14.691 | 0.368 | NO |
| WI_H10_T05 | wick_imbalance_r | 10m | 0.05R | 107 | 63 | 24 | 26 | 39.3% | 0.842 | -0.201 | -32.787 | -17.729 | NO |
| WI_H10_T10 | wick_imbalance_r | 10m | 0.10R | 107 | 52 | 18 | 20 | 42.9% | 0.877 | -0.165 | -26.896 | -11.838 | NO |
| WI_H10_T15 | wick_imbalance_r | 10m | 0.15R | 107 | 42 | 15 | 17 | 44.8% | 0.857 | -0.206 | -33.606 | -18.547 | NO |
| WI_H10_T20 | wick_imbalance_r | 10m | 0.20R | 107 | 32 | 12 | 14 | 46.0% | 0.795 | -0.339 | -55.304 | -40.246 | NO |
| WI_H10_T25 | wick_imbalance_r | 10m | 0.25R | 107 | 19 | 8 | 8 | 48.5% | 0.837 | -0.273 | -44.530 | -29.471 | NO |
| WI_H15_T05 | wick_imbalance_r | 15m | 0.05R | 89 | 64 | 22 | 25 | 40.5% | 0.773 | -0.307 | -50.069 | -35.011 | NO |
| WI_H15_T10 | wick_imbalance_r | 15m | 0.10R | 89 | 53 | 18 | 20 | 42.9% | 0.797 | -0.286 | -46.582 | -31.523 | NO |
| WI_H15_T15 | wick_imbalance_r | 15m | 0.15R | 89 | 43 | 15 | 17 | 44.2% | 0.778 | -0.336 | -54.715 | -39.657 | NO |
| WI_H15_T20 | wick_imbalance_r | 15m | 0.20R | 89 | 33 | 11 | 12 | 46.6% | 0.776 | -0.365 | -59.570 | -44.512 | NO |
| WI_H15_T25 | wick_imbalance_r | 15m | 0.25R | 89 | 21 | 7 | 7 | 49.1% | 0.854 | -0.235 | -38.294 | -23.236 | NO |

## Best diagnostic candidate and formal selection

Diagnostic best pooled total: **AC_H05_T20** (adverse_close_r, 5m, threshold 0.20R) → total **$-7.239**, delta **$+7.820** vs baseline.

Formal selected candidate under the preregistered cross-partition gate: **NONE**.

No candidate satisfied the frozen requirement of positive pooled expectancy plus non-negative expectancy and PF>=1.0 in every major partition.

No thresholds outside the preregistered coarse grid were tested. No feature combination, regime filter, F15/F65/E20 change, runner change, or live BBC change was made.

**Status:** `B27AX_SELECTED_NONE__DIAGNOSTIC_BEST_AC_H05_T20`
