# BTC Global/Pooled Regime Engine — G5 Risk Governor

**Status: G5_RISK_GOVERNOR_GATE_FAILED**

Research only; live BBC untouched.

## Frozen sizing rule
`WEIGHT = min(1.0, pSELL / causal training SELL prior)`

Every Tuesday remains a trade; G5 can only reduce size and can never exceed baseline exposure.

## Historical Tuesday economics
| Policy | N | Mean weight | Exposure | WR | PnL | PnL/exposure | Max DD | PnL/DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Always 1.0x | 126 | 1.000 | 126.00 | 65.87% | $+150.89 | $+1.1976 | $20.91 | 7.216 |
| G5 governor | 126 | 0.963 | 121.29 | 65.87% | $+146.33 | $+1.2064 | $20.91 | 6.997 |

G5 weight range: **0.658 → 1.000**, median **1.000**.

## Acceptance gate
- PASS — `mean_weight_lt_1`
- PASS — `capital_efficiency_improves`
- FAIL — `drawdown_improves`
- FAIL — `pnl_over_dd_improves`
- PASS — `absolute_pnl_positive`
- PASS — `efficiency_improves_3_of_4_blocks`

## Four chronological blocks
| Block | Dates | Base exposure | G5 exposure | Base PnL/exposure | G5 PnL/exposure | Improved | Base DD | G5 DD |
|---:|---|---:|---:|---:|---:|---|---:|---:|
| 1 | 2024-03-05 → 2024-10-08 | 32.00 | 31.20 | $+1.1239 | $+1.0988 | NO | $15.45 | $15.24 |
| 2 | 2024-10-15 → 2025-05-20 | 32.00 | 31.13 | $+0.6240 | $+0.6525 | YES | $20.91 | $20.91 |
| 3 | 2025-05-27 → 2025-12-23 | 31.00 | 28.79 | $+1.9675 | $+2.0093 | YES | $6.54 | $6.03 |
| 4 | 2025-12-30 → 2026-07-28 | 31.00 | 30.17 | $+1.0958 | $+1.1230 | YES | $10.03 | $9.66 |

## August 2026 — report only
Frozen historical SELL prior: **44.11%**.

| Date WIB | pSELL | SELL lift | Weight | A5.11 PnL | Weighted PnL |
|---|---:|---:|---:|---:|---:|
| 2026-08-04 | 38.5% | 0.872 | 0.872 | $-4.75 | $-4.14 |
| 2026-08-11 | 33.2% | 0.753 | 0.753 | $-0.82 | $-0.62 |
| 2026-08-18 | 31.1% | 0.704 | 0.704 | $-0.10 | $-0.07 |

August baseline: **$-5.68**; G5: **$-4.84**; loss reduction **$+0.84**.

**Final G5 verdict: FAIL — preserve result; do not tune sizing inside G5.**

No live BBC changes were made.
