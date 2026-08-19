# BTC Global/Pooled Regime Engine — G7 Weekly-Health Risk Governor

**Status: G7_WEEKLY_RISK_GOVERNOR_GATE_FAILED**

Research only; live BBC untouched.

## Frozen sizing rule
`WEIGHT = min(1.0, mean_pSELL_168h / mean_causal_SELL_prior_168h)`

Every eligible Tuesday remains a trade; G7 can only reduce exposure.

## Historical Tuesday economics
| Policy | N | Mean weight | Exposure | WR | PnL | PnL/exposure | Max DD | PnL/DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Always 1.0x | 125 | 1.000 | 125.00 | 66.40% | $+155.64 | $+1.2452 | $20.91 | 7.443 |
| G7 weekly governor | 125 | 0.958 | 119.71 | 66.40% | $+151.60 | $+1.2664 | $20.44 | 7.415 |
| G5 point governor (same subset) | 125 | 0.962 | 120.29 | 66.40% | $+151.08 | $+1.2559 | $20.91 | 7.225 |

G7 weight range: **0.773 → 1.000**, median **0.992**.

## Acceptance gate
- PASS — `eligible_ge_120`
- PASS — `mean_weight_lt_1`
- PASS — `capital_efficiency_improves`
- PASS — `max_dd_improves`
- FAIL — `pnl_over_dd_improves`
- PASS — `absolute_pnl_positive`
- PASS — `efficiency_improves_3_of_4_blocks`

## Four chronological blocks
| Block | Dates | Base exp | G7 exp | Base PnL/exp | G7 PnL/exp | Improved | Base DD | G7 DD |
|---:|---|---:|---:|---:|---:|---|---:|---:|
| 1 | 2024-03-12 → 2024-10-15 | 32.00 | 31.25 | $+1.4598 | $+1.4674 | YES | $15.45 | $14.90 |
| 2 | 2024-10-22 → 2025-05-20 | 31.00 | 30.11 | $+0.4506 | $+0.4459 | NO | $20.91 | $20.44 |
| 3 | 2025-05-27 → 2025-12-23 | 31.00 | 28.78 | $+1.9675 | $+2.0403 | YES | $6.54 | $5.93 |
| 4 | 2025-12-30 → 2026-07-28 | 31.00 | 29.57 | $+1.0958 | $+1.1362 | YES | $10.03 | $9.58 |

## August 2026 — report only
| Date WIB | Mean pSELL 168h | Weekly lift | Weight | A5.11 PnL | Weighted PnL |
|---|---:|---:|---:|---:|---:|
| 2026-08-04 | 39.46% | 0.894 | 0.894 | $-4.75 | $-4.25 |
| 2026-08-11 | 33.57% | 0.761 | 0.761 | $-0.82 | $-0.63 |
| 2026-08-18 | 32.11% | 0.728 | 0.728 | $-0.10 | $-0.08 |

August baseline: **$-5.68**; G7: **$-4.95**; loss reduction **$+0.73**.

**Final G7 verdict: FAIL — preserve result; no sizing retune inside G7.**

No live BBC changes were made.
