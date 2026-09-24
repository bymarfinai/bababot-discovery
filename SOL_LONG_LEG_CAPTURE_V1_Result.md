# SOL Long Leg Capture V1 — Verified Result

Run ID: 35952772529
Head SHA: 7070cea89ae2647b47d4c7bf2e162554946b79b2
Status: SUCCESS
5m coverage: 99.76977%
Complete 15m bars: 208,004
Ex-post long legs (1% reversal segmentation): 4,430

## Weekly opportunity census

| Period | HL mean | HL median | Weeks HL>=15% | >=2% long legs mean/wk | >=3% long legs mean/wk | >=5% long legs mean/wk | Weeks with >=10% in >=2% long legs |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2023 | 25.83% | 19.84% | 69.8% | 54.72% | 39.89% | 23.61% | 96.2% |
| 2024 | 22.93% | 19.03% | 71.7% | 53.92% | 38.64% | 20.37% | 100.0% |
| 2025 | 21.76% | 18.51% | 73.6% | 45.69% | 32.47% | 15.36% | 100.0% |
| 2026 | 15.87% | 12.08% | 37.1% | 27.96% | 18.64% | 8.52% | 82.9% |

These are ex-post opportunity ceilings, not executable returns.

## Frozen causal detector transfer

| Target | Partition | WR | Trades/wk | Exp/trade | Mean weekly net | Median weekly net | Leg hit | Early hit | Oracle mean/wk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L2 TP2/SL1 | 2024 | 38.35% | 5.26 | +0.004% | +0.02% | -0.45% | 15.9% | 5.0% | 44.43% |
| L2 TP2/SL1 | 2025 | 39.08% | 5.36 | +0.035% | +0.19% | 0.00% | 19.9% | 8.5% | 35.95% |
| L2 TP2/SL1 | 2026 | 33.79% | 4.14 | -0.054% | -0.22% | -1.15% | 24.0% | 9.0% | 22.15% |
| L3 TP3/SL1 | 2024 | 28.22% | 3.08 | -0.021% | -0.07% | -0.05% | 16.3% | 4.7% | 35.65% |
| L3 TP3/SL1 | 2025 | 30.61% | 3.70 | +0.074% | +0.28% | 0.00% | 20.7% | 8.0% | 28.82% |
| L3 TP3/SL1 | 2026 | 21.88% | 2.74 | -0.248% | -0.68% | -1.15% | 27.9% | 8.1% | 17.59% |
| L5 TP5/SL1 | 2024 | 19.62% | 7.02 | +0.027% | +0.19% | -0.90% | 43.4% | 17.8% | 24.71% |
| L5 TP5/SL1 | 2025 | 18.32% | 6.08 | -0.024% | -0.15% | -2.05% | 53.5% | 24.6% | 20.96% |
| L5 TP5/SL1 | 2026 | 15.72% | 4.54 | -0.141% | -0.64% | -2.30% | 55.8% | 18.6% | 12.89% |

## Interpretation

The market-opportunity hypothesis is strongly supported: ex-post SOL LONG movement is abundant, and >=10% weekly aggregate LONG-leg movement exists in most weeks.

The causal target-outcome detector is not robust. Its most informative failure is timing: it often recognizes large legs after they are already underway. L5 hits 43-56% of large legs but only 18-25% early, while L2/L3 early-hit rates are mostly single digits.

Next experiment should train explicitly on leg onset / early-leg labels rather than on generic TP-before-SL labels.

VERDICT: NO_ROBUST_LEG_CAPTURE_YET__ONSET_IS_BOTTLENECK
