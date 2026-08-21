# BTC Dynamic Condition Engine B23D — Result

5m source rows: **698,112**; coverage: **100.0000%**

Position model: **$10 margin × 50x = $500 notional**. Fee sensitivity subtracts illustrative **0.08% round trip = $0.40/trade**.

**Corrected design:** each timeframe is independent. A 5m trade is monitored on 5m, 15m on 15m, 1h on 1h, and 4h on 4h. Higher-TF states are recorded only as context diagnostics and never manage the primary trade.

Entry is the next same-timeframe open after a fresh image-like STRONG_BULL onset. HOLD on STRONG_BULL or HEALTHY_BULL; exit next same-timeframe open on DETERIORATING or REVERSAL. No fixed TP/SL and no fixed bar horizon.

| Partition | TF | N | WR | PF | Mean ret | Median winner | Median loser | Median MFE | Median MAE | P10 MAE | Mean $ | Fee WR | Fee PF | Fee mean $ | <=-0.5 MAE | <=-1.0 | <=-1.5 | <=-1.8 | Med bars | Med time min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| august | 5m | 145 | 30.34% | 1.67 | 0.05% | 0.18% | -0.09% | 0.13% | -0.09% | -0.26% | $0.27 | 22.07% | 0.81 | $-0.13 | 0.69% | 0.00% | 0.00% | 0.00% | 9.0 | 45.0 |
| august | 15m | 53 | 35.85% | 1.78 | 0.10% | 0.19% | -0.16% | 0.17% | -0.14% | -0.43% | $0.49 | 26.42% | 1.10 | $0.09 | 5.66% | 0.00% | 0.00% | 0.00% | 9.0 | 135.0 |
| august | 1h | 11 | 54.55% | 5.82 | 1.08% | 0.19% | -0.40% | 0.85% | -0.49% | -0.53% | $5.38 | 54.55% | 4.84 | $4.98 | 27.27% | 0.00% | 0.00% | 0.00% | 10.0 | 600.0 |
| august | 4h | 2 | 50.00% | 98.08 | 6.40% | 12.94% | -0.13% | 7.58% | -0.46% | -0.52% | $32.02 | 50.00% | 60.68 | $31.62 | 50.00% | 0.00% | 0.00% | 0.00% | 22.0 | 5280.0 |
| development | 5m | 8628 | 26.23% | 0.99 | -0.00% | 0.21% | -0.13% | 0.16% | -0.15% | -0.42% | $-0.01 | 18.66% | 0.60 | $-0.41 | 7.13% | 1.17% | 0.37% | 0.23% | 7.0 | 35.0 |
| development | 15m | 2748 | 26.31% | 1.05 | 0.01% | 0.43% | -0.24% | 0.31% | -0.28% | -0.82% | $0.06 | 21.40% | 0.79 | $-0.34 | 26.02% | 6.40% | 2.44% | 1.53% | 7.0 | 105.0 |
| development | 1h | 603 | 28.52% | 1.23 | 0.13% | 1.21% | -0.61% | 0.86% | -0.72% | -2.03% | $0.66 | 26.37% | 1.08 | $0.26 | 65.34% | 34.83% | 17.74% | 12.94% | 8.0 | 480.0 |
| development | 4h | 135 | 32.59% | 1.47 | 0.53% | 2.33% | -1.40% | 1.92% | -1.61% | -3.79% | $2.64 | 29.63% | 1.38 | $2.24 | 85.93% | 74.81% | 54.07% | 42.96% | 11.0 | 2640.0 |
| external | 5m | 5731 | 26.64% | 1.02 | 0.00% | 0.33% | -0.19% | 0.25% | -0.21% | -0.64% | $0.02 | 21.50% | 0.70 | $-0.38 | 16.09% | 3.45% | 1.19% | 0.68% | 7.0 | 35.0 |
| external | 15m | 1822 | 27.99% | 1.13 | 0.05% | 0.74% | -0.34% | 0.52% | -0.40% | -1.15% | $0.23 | 24.75% | 0.92 | $-0.17 | 40.29% | 13.94% | 5.60% | 3.73% | 8.0 | 120.0 |
| external | 1h | 398 | 33.92% | 1.58 | 0.38% | 1.73% | -0.80% | 1.29% | -0.94% | -2.18% | $1.92 | 33.42% | 1.43 | $1.52 | 74.37% | 47.24% | 26.63% | 18.09% | 10.0 | 600.0 |
| external | 4h | 103 | 36.89% | 1.92 | 1.31% | 4.82% | -1.85% | 2.55% | -1.99% | -4.95% | $6.57 | 36.89% | 1.83 | $6.17 | 92.23% | 79.61% | 64.08% | 56.31% | 10.0 | 2400.0 |
| reference_validation | 5m | 4256 | 29.35% | 0.97 | -0.00% | 0.19% | -0.13% | 0.16% | -0.13% | -0.38% | $-0.02 | 21.22% | 0.53 | $-0.42 | 5.12% | 0.54% | 0.14% | 0.07% | 8.0 | 40.0 |
| reference_validation | 15m | 1389 | 28.51% | 0.96 | -0.01% | 0.38% | -0.22% | 0.29% | -0.25% | -0.68% | $-0.05 | 24.19% | 0.68 | $-0.45 | 20.52% | 3.46% | 1.01% | 0.65% | 8.0 | 120.0 |
| reference_validation | 1h | 319 | 31.35% | 0.84 | -0.08% | 0.90% | -0.59% | 0.67% | -0.64% | -1.51% | $-0.41 | 28.84% | 0.71 | $-0.81 | 62.07% | 26.02% | 10.34% | 6.27% | 8.0 | 480.0 |
| reference_validation | 4h | 82 | 30.49% | 0.84 | -0.16% | 2.03% | -1.26% | 1.33% | -1.29% | -2.85% | $-0.78 | 30.49% | 0.78 | $-1.18 | 82.93% | 63.41% | 41.46% | 29.27% | 7.0 | 1680.0 |

## Exit-reason mix

| Partition | TF | Deterioration cut | Reversal cut | Forced close |
|---|---|---:|---:|---:|
| august | 5m | 75.86% | 23.45% | 0.69% |
| august | 15m | 73.58% | 26.42% | 0.00% |
| august | 1h | 72.73% | 18.18% | 9.09% |
| august | 4h | 0.00% | 50.00% | 50.00% |
| development | 5m | 69.33% | 30.67% | 0.00% |
| development | 15m | 68.92% | 31.08% | 0.00% |
| development | 1h | 67.16% | 32.84% | 0.00% |
| development | 4h | 63.70% | 36.30% | 0.00% |
| external | 5m | 70.34% | 29.66% | 0.00% |
| external | 15m | 69.98% | 30.02% | 0.00% |
| external | 1h | 74.62% | 25.38% | 0.00% |
| external | 4h | 66.02% | 33.98% | 0.00% |
| reference_validation | 5m | 71.59% | 28.38% | 0.02% |
| reference_validation | 15m | 69.98% | 30.02% | 0.00% |
| reference_validation | 1h | 67.71% | 32.29% | 0.00% |
| reference_validation | 4h | 65.85% | 34.15% | 0.00% |

## Frozen precision gates

- 5m: HIGH_PRECISION_CLUE=FAIL; 90PCT_WR_CLAIM=FAIL
- 15m: HIGH_PRECISION_CLUE=FAIL; 90PCT_WR_CLAIM=FAIL
- 1h: HIGH_PRECISION_CLUE=FAIL; 90PCT_WR_CLAIM=FAIL
- 4h: HIGH_PRECISION_CLUE=FAIL; 90PCT_WR_CLAIM=FAIL

Important for 50x: monitoring at the selected timeframe means an adverse move can occur inside a candle before the condition-based exit becomes executable. MAE tails are reported to expose this explicitly; they are not liquidation-price calculations.

Research only; live BBC unchanged.
