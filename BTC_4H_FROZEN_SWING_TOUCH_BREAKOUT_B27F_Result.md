# B27F — BTC 4H Frozen Swing-Level Repeated Touch Breakout

Source coverage: **100.0000%**. Frozen swing level remains active until close-through breakout; minor same-side pivots do not reset it. Entry next 4H open, breakout-candle opposite extreme SL, TP 2R.

| Partition | Prior touches | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | ALL | 33 | 31 | 2 | 14 | 19 | 42.42% | 1.21 | $2.77 | $91.25 | 3.65% | 2175.0 |
| external | 0 | 16 | 16 | 0 | 6 | 10 | 37.50% | 1.44 | $5.43 | $86.95 | 4.11% | 2582.5 |
| external | 1 | 11 | 9 | 2 | 5 | 6 | 45.45% | 0.67 | $-5.60 | $-61.56 | 2.46% | 925.0 |
| external | 2 | 5 | 5 | 0 | 2 | 3 | 40.00% | 1.44 | $3.95 | $19.76 | 2.72% | 960.0 |
| external | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 4+ | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $46.09 | $46.09 | 4.65% | 7165.0 |
| development | ALL | 23 | 14 | 9 | 11 | 12 | 47.83% | 1.90 | $7.95 | $182.94 | 3.39% | 1120.0 |
| development | 0 | 5 | 2 | 3 | 2 | 3 | 40.00% | 1.56 | $5.78 | $28.89 | 3.22% | 325.0 |
| development | 1 | 12 | 8 | 4 | 6 | 6 | 50.00% | 3.06 | $13.00 | $156.01 | 2.64% | 895.0 |
| development | 2 | 4 | 2 | 2 | 1 | 3 | 25.00% | 0.25 | $-14.23 | $-56.92 | 4.70% | 2425.0 |
| development | 3 | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $35.20 | $35.20 | 3.56% | 605.0 |
| development | 4+ | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $19.76 | $19.76 | 2.02% | 4615.0 |
| reference_validation | ALL | 16 | 9 | 7 | 5 | 11 | 31.25% | 0.60 | $-3.83 | $-61.21 | 2.22% | 730.0 |
| reference_validation | 0 | 7 | 6 | 1 | 2 | 5 | 28.57% | 0.28 | $-7.17 | $-50.20 | 1.14% | 675.0 |
| reference_validation | 1 | 4 | 1 | 3 | 2 | 2 | 50.00% | 1.95 | $6.63 | $26.50 | 2.76% | 1455.0 |
| reference_validation | 2 | 3 | 2 | 1 | 1 | 2 | 33.33% | 0.69 | $-2.53 | $-7.60 | 1.75% | 700.0 |
| reference_validation | 3 | 2 | 0 | 2 | 0 | 2 | 0.00% | 0.00 | $-14.95 | $-29.90 | 2.91% | 5262.5 |
| reference_validation | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | ALL | 2 | 2 | 1 | 1 | 1 | 50.00% | 4.37 | $7.47 | $14.95 | 1.39% | 11650.0 |
| august | 0 | 1 | 1 | 1 | 0 | 1 | 0.00% | 0.00 | $-4.44 | $-4.44 | 0.81% | 315.0 |
| august | 1 | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $19.38 | $19.38 | 1.98% | 22985.0 |
| august | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |

## Pre-registered repeatability verdict

- 0 prior touches: **FAIL / INSUFFICIENT**
- 1 prior touches: **FAIL / INSUFFICIENT**
- 2 prior touches: **FAIL / INSUFFICIENT**
- 3 prior touches: **FAIL / INSUFFICIENT**
- 4+ prior touches: **FAIL / INSUFFICIENT**

Gate: same bucket >=30 resolved, positive net expectancy, net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
