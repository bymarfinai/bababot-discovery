# B27J — BTC 4H Second Opposite-Side Retest Entry

Source coverage: **100.0000%**. Frozen causal 4H range, ±0.20% zones. LONG at second-or-later Low retest after >=1 known High visit; SHORT symmetric. Entry next 4H open; retest candle extreme SL; TP 2R.

| Partition | Group | Resolved | W | L | WR | Net PF | Net exp/trade | Total net | Target wick before SL | Target close-break before SL | Median stop | Median hold min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | ALL | 3 | 0 | 3 | 0.00% | 0.00 | $-3.10 | $-9.30 | 0.00% | 0.00% | 0.54% | 100.0 |
| external | TARGET_VISITS_1 | 3 | 0 | 3 | 0.00% | 0.00 | $-3.10 | $-9.30 | 0.00% | 0.00% | 0.54% | 100.0 |
| external | TARGET_VISITS_2PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| external | LONG | 1 | 0 | 1 | 0.00% | 0.00 | $-3.50 | $-3.50 | 0.00% | 0.00% | 0.62% | 75.0 |
| external | SHORT | 2 | 0 | 2 | 0.00% | 0.00 | $-2.90 | $-5.79 | 0.00% | 0.00% | 0.50% | 270.0 |
| development | ALL | 4 | 0 | 4 | 0.00% | 0.00 | $-3.23 | $-12.91 | 0.00% | 0.00% | 0.47% | 47.5 |
| development | TARGET_VISITS_1 | 3 | 0 | 3 | 0.00% | 0.00 | $-2.08 | $-6.25 | 0.00% | 0.00% | 0.27% | 5.0 |
| development | TARGET_VISITS_2PLUS | 1 | 0 | 1 | 0.00% | 0.00 | $-6.66 | $-6.66 | 0.00% | 0.00% | 1.25% | 90.0 |
| development | LONG | 1 | 0 | 1 | 0.00% | 0.00 | $-0.80 | $-0.80 | 0.00% | 0.00% | 0.08% | 0.0 |
| development | SHORT | 3 | 0 | 3 | 0.00% | 0.00 | $-4.04 | $-12.11 | 0.00% | 0.00% | 0.66% | 90.0 |
| reference_validation | ALL | 3 | 2 | 1 | 66.67% | 9.97 | $5.77 | $17.30 | 33.33% | 33.33% | 0.92% | 590.0 |
| reference_validation | TARGET_VISITS_1 | 3 | 2 | 1 | 66.67% | 9.97 | $5.77 | $17.30 | 33.33% | 33.33% | 0.92% | 590.0 |
| reference_validation | TARGET_VISITS_2PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| reference_validation | LONG | 2 | 1 | 1 | 50.00% | 5.40 | $4.24 | $8.48 | 50.00% | 50.00% | 0.69% | 3280.0 |
| reference_validation | SHORT | 1 | 1 | 0 | 100.00% | inf | $8.82 | $8.82 | 0.00% | 0.00% | 0.92% | 590.0 |
| august | ALL | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| august | TARGET_VISITS_1 | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| august | TARGET_VISITS_2PLUS | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| august | LONG | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |
| august | SHORT | 0 | 0 | 0 | - | - | $- | $- | - | - | - | - |

## Pre-registered verdict

**B27J: FAIL / INSUFFICIENT.**

PASS requires >=30 resolved trades, positive fee-sensitive expectancy, and PF >=1.20 in external, development, and reference_validation.

Subgroups are diagnostic only; no post-hoc promotion.

Research only; live BBC unchanged.
