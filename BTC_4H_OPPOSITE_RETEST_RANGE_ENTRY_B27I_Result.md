# B27I — BTC 4H Opposite-Side Retest Entry Before Range Breakout

Source coverage: **100.0000%**. Frozen causal 4H swing range; retest tolerance ±0.20%; target-side visits >=2; entry from second-or-later opposite-side retest; next 4H open; retest-candle extreme SL; TP 2R.

Structural diagnostic = intended frozen boundary achieves a strict 4H close-through breakout before the 5m stop is first hit.

| Partition | Group | Resolved | W | L | WR | Net PF | Net exp/trade | Total net | Target breakout before SL | Median stop | Median hold min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | ALL | 1 | 0 | 1 | 0.00% | 0.00 | $-5.00 | $-5.00 | 0.00% | 0.92% | 60.0 |
| external | PRESSURE_2 | 1 | 0 | 1 | 0.00% | 0.00 | $-5.00 | $-5.00 | 0.00% | 0.92% | 60.0 |
| external | PRESSURE_3PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| external | LONG | 1 | 0 | 1 | 0.00% | 0.00 | $-5.00 | $-5.00 | 0.00% | 0.92% | 60.0 |
| external | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| development | ALL | 1 | 0 | 1 | 0.00% | 0.00 | $-6.66 | $-6.66 | 0.00% | 1.25% | 90.0 |
| development | PRESSURE_2 | 1 | 0 | 1 | 0.00% | 0.00 | $-6.66 | $-6.66 | 0.00% | 1.25% | 90.0 |
| development | PRESSURE_3PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| development | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| development | SHORT | 1 | 0 | 1 | 0.00% | 0.00 | $-6.66 | $-6.66 | 0.00% | 1.25% | 90.0 |
| reference_validation | ALL | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| reference_validation | PRESSURE_2 | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| reference_validation | PRESSURE_3PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| reference_validation | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| reference_validation | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| august | ALL | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| august | PRESSURE_2 | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| august | PRESSURE_3PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| august | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - |
| august | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - |

## Pre-registered verdict

**B27I: FAIL / INSUFFICIENT.**

PASS requires >=30 resolved trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.

Pressure-count and side rows are diagnostics only and are not promoted post hoc.

Research only; live BBC unchanged.
