# B27K — BTC 15m / 1H Second Opposite-Side Retest Entry

Source coverage: **100.0000%**. Exact B27J logic moved to 15m and 1H: frozen causal range, ±0.20% zones, LONG on second-or-later Low visit after >=1 High visit; SHORT symmetric; next-TF-open entry; retest-candle extreme SL; TP 2R.

| TF | Partition | Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Target wick before SL | Target close-break before SL | Median stop | Median hold min |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 15m | external | ALL | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 15m | external | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 15m | external | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 15m | development | ALL | 3 | 0 | 3 | 0.00% | 0.00 | $-0.88 | $-2.63 | 0.00% | 0.00% | 0.10% | 10.0 |
| 15m | development | LONG | 3 | 0 | 3 | 0.00% | 0.00 | $-0.88 | $-2.63 | 0.00% | 0.00% | 0.10% | 10.0 |
| 15m | development | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 15m | reference_validation | ALL | 4 | 1 | 3 | 25.00% | 0.08 | $-0.51 | $-2.04 | 0.00% | 0.00% | 0.06% | 0.0 |
| 15m | reference_validation | LONG | 2 | 1 | 1 | 50.00% | 0.25 | $-0.26 | $-0.51 | 0.00% | 0.00% | 0.06% | 0.0 |
| 15m | reference_validation | SHORT | 2 | 0 | 2 | 0.00% | 0.00 | $-0.76 | $-1.53 | 0.00% | 0.00% | 0.07% | 0.0 |
| 15m | august | ALL | 4 | 4 | 0 | 100.00% | 6.61 | $0.41 | $1.63 | 25.00% | 25.00% | 0.08% | 20.0 |
| 15m | august | LONG | 3 | 3 | 0 | 100.00% | 3.08 | $0.20 | $0.60 | 33.33% | 33.33% | 0.08% | 10.0 |
| 15m | august | SHORT | 1 | 1 | 0 | 100.00% | inf | $1.03 | $1.03 | 0.00% | 0.00% | 0.14% | 75.0 |
| 1h | external | ALL | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 1h | external | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 1h | external | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 1h | development | ALL | 10 | 4 | 6 | 40.00% | 0.82 | $-0.33 | $-3.31 | 40.00% | 20.00% | 0.24% | 15.0 |
| 1h | development | LONG | 6 | 1 | 5 | 16.67% | 0.56 | $-1.32 | $-7.91 | 16.67% | 16.67% | 0.46% | 10.0 |
| 1h | development | SHORT | 4 | 3 | 1 | 75.00% | 9.00 | $1.15 | $4.60 | 75.00% | 25.00% | 0.19% | 22.5 |
| 1h | reference_validation | ALL | 1 | 0 | 1 | 0.00% | 0.00 | $-2.21 | $-2.21 | 0.00% | 0.00% | 0.36% | 10.0 |
| 1h | reference_validation | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| 1h | reference_validation | SHORT | 1 | 0 | 1 | 0.00% | 0.00 | $-2.21 | $-2.21 | 0.00% | 0.00% | 0.36% | 10.0 |
| 1h | august | ALL | 3 | 1 | 2 | 33.33% | 0.17 | $-0.63 | $-1.88 | 33.33% | 0.00% | 0.08% | 50.0 |
| 1h | august | LONG | 2 | 1 | 1 | 50.00% | 0.58 | $-0.14 | $-0.29 | 50.00% | 0.00% | 0.07% | 45.0 |
| 1h | august | SHORT | 1 | 0 | 1 | 0.00% | 0.00 | $-1.60 | $-1.60 | 0.00% | 0.00% | 0.24% | 50.0 |

## Pre-registered verdict

- 15m: **FAIL / INSUFFICIENT**
- 1h: **FAIL / INSUFFICIENT**

PASS requires >=30 resolved trades, positive net expectancy, and net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
