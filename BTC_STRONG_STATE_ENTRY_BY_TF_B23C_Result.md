# BTC Strong-State Entry by Timeframe B23C — Result

5m source rows: **698,112**; coverage: **100.0000%**

Position model: **$10 margin × 50x = $500 notional**. Gross PnL excludes fees/slippage/funding. Fee-sensitive columns subtract an illustrative **0.08% round trip = $0.40/trade**, not a claim about the user account fee.

Entry universe is every fresh STRONG onset, not pullback-only. Exit is dynamic: inspect every completed candle and exit next open on the first candle that is no longer STRONG.

## Development entry comparison

| TF | Variant | N | Gross WR | PF | Median loser | P10 MAE | Gross mean $ | Fee-sens WR | Fee-sens mean $ | Median bars |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5m | E0_ONSET | 9881 | 28.27% | 1.02 | -0.12% | -0.40% | $0.01 | 19.33% | $-0.39 | 6.0 |
| 5m | E1_CONFIRM1 | 8507 | 28.89% | 1.03 | -0.12% | -0.41% | $0.02 | 19.96% | $-0.38 | 6.0 |
| 5m | E2_CONFIRM2 | 7454 | 29.73% | 1.05 | -0.12% | -0.42% | $0.03 | 20.65% | $-0.37 | 6.0 |
| 15m | E0_ONSET | 3191 | 28.27% | 1.03 | -0.22% | -0.77% | $0.03 | 22.59% | $-0.37 | 6.0 |
| 15m | E1_CONFIRM1 | 2756 | 29.64% | 1.05 | -0.22% | -0.82% | $0.06 | 23.33% | $-0.34 | 6.0 |
| 15m | E2_CONFIRM2 | 2396 | 29.13% | 1.10 | -0.23% | -0.81% | $0.11 | 23.04% | $-0.29 | 6.0 |
| 1h | E0_ONSET | 721 | 30.37% | 1.19 | -0.54% | -1.85% | $0.48 | 27.60% | $0.08 | 6.0 |
| 1h | E1_CONFIRM1 | 624 | 33.65% | 1.28 | -0.54% | -1.77% | $0.67 | 30.93% | $0.27 | 6.0 |
| 1h | E2_CONFIRM2 | 550 | 33.27% | 1.19 | -0.55% | -1.89% | $0.47 | 29.82% | $0.07 | 7.0 |
| 4h | E0_ONSET | 168 | 38.10% | 1.42 | -1.10% | -3.91% | $2.07 | 35.71% | $1.67 | 7.0 |
| 4h | E1_CONFIRM1 | 146 | 39.04% | 1.44 | -1.33% | -4.01% | $2.21 | 36.99% | $1.81 | 8.0 |
| 4h | E2_CONFIRM2 | 129 | 40.31% | 1.41 | -1.41% | -3.55% | $2.13 | 39.53% | $1.73 | 8.0 |

## Precision-first selection and replication

| TF | Selected entry | Partition | N | Gross WR | PF | Median loser | P10 MAE | Gross mean $ | Fee-sens WR | Fee-sens PF | Fee-sens mean $ | <=-0.5% MAE | <=-1.0% | <=-1.5% |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 5m | E2_CONFIRM2 | external | 5148 | 30.61% | 1.01 | -0.18% | -0.62% | $0.01 | 23.04% | 0.67 | $-0.39 | 15.46% | 3.44% | 1.20% |
| 5m | E2_CONFIRM2 | development | 7454 | 29.73% | 1.05 | -0.12% | -0.42% | $0.03 | 20.65% | 0.60 | $-0.37 | 6.80% | 1.23% | 0.39% |
| 5m | E2_CONFIRM2 | reference_validation | 3893 | 32.11% | 1.00 | -0.11% | -0.36% | $0.00 | 21.09% | 0.52 | $-0.40 | 4.26% | 0.59% | 0.10% |
| 5m | E2_CONFIRM2 | august | 153 | 29.41% | 1.32 | -0.07% | -0.23% | $0.11 | 16.34% | 0.56 | $-0.29 | 1.31% | 0.00% | 0.00% |
| 15m | E1_CONFIRM1 | external | 1856 | 31.14% | 1.15 | -0.31% | -1.13% | $0.24 | 26.40% | 0.91 | $-0.16 | 39.12% | 12.61% | 5.44% |
| 15m | E1_CONFIRM1 | development | 2756 | 29.64% | 1.05 | -0.22% | -0.82% | $0.06 | 23.33% | 0.76 | $-0.34 | 23.62% | 6.35% | 2.47% |
| 15m | E1_CONFIRM1 | reference_validation | 1466 | 30.70% | 0.95 | -0.21% | -0.68% | $-0.05 | 24.15% | 0.65 | $-0.45 | 18.01% | 3.27% | 0.75% |
| 15m | E1_CONFIRM1 | august | 52 | 34.62% | 1.46 | -0.15% | -0.39% | $0.29 | 23.08% | 0.88 | $-0.11 | 5.77% | 0.00% | 0.00% |
| 1h | E1_CONFIRM1 | external | 444 | 37.39% | 1.53 | -0.64% | -2.13% | $1.49 | 35.59% | 1.36 | $1.09 | 70.27% | 42.12% | 22.07% |
| 1h | E1_CONFIRM1 | development | 624 | 33.65% | 1.28 | -0.54% | -1.77% | $0.67 | 30.93% | 1.10 | $0.27 | 59.94% | 29.65% | 16.19% |
| 1h | E1_CONFIRM1 | reference_validation | 332 | 31.93% | 0.85 | -0.48% | -1.47% | $-0.32 | 28.92% | 0.71 | $-0.72 | 56.02% | 24.10% | 9.64% |
| 1h | E1_CONFIRM1 | august | 16 | 25.00% | 4.07 | -0.23% | -0.65% | $3.15 | 25.00% | 3.07 | $2.75 | 25.00% | 0.00% | 0.00% |
| 4h | E2_CONFIRM2 | external | 122 | 35.25% | 1.51 | -1.22% | -4.04% | $2.89 | 34.43% | 1.42 | $2.49 | 89.34% | 72.95% | 58.20% |
| 4h | E2_CONFIRM2 | development | 129 | 40.31% | 1.41 | -1.41% | -3.55% | $2.13 | 39.53% | 1.32 | $1.73 | 82.95% | 66.67% | 48.84% |
| 4h | E2_CONFIRM2 | reference_validation | 67 | 43.28% | 1.41 | -1.09% | -2.98% | $1.55 | 37.31% | 1.29 | $1.15 | 74.63% | 49.25% | 31.34% |
| 4h | E2_CONFIRM2 | august | 4 | 50.00% | 15.95 | -0.39% | -0.79% | $14.70 | 50.00% | 13.08 | $14.30 | 50.00% | 0.00% | 0.00% |

## Gates

- 5m: selected **E2_CONFIRM2**; REPLICATED_PRECISION_CLUE=FAIL; HIGH_PRECISION_CLUE=FAIL
- 15m: selected **E1_CONFIRM1**; REPLICATED_PRECISION_CLUE=FAIL; HIGH_PRECISION_CLUE=FAIL
- 1h: selected **E1_CONFIRM1**; REPLICATED_PRECISION_CLUE=FAIL; HIGH_PRECISION_CLUE=FAIL
- 4h: selected **E2_CONFIRM2**; REPLICATED_PRECISION_CLUE=FAIL; HIGH_PRECISION_CLUE=FAIL

Interpretation rules:
- A high STRONG-state survival rate is not automatically a high trading WR; entry price versus first non-STRONG exit determines realized PnL.
- No hard SL is used here. MAE tails show whether 50x would be operationally dangerous even if the dynamic signal later exits.
- Fee-sensitive results are intentionally shown because small-timeframe edges can be consumed by transaction costs.
- Research only; live BBC unchanged.
