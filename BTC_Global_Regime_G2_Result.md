# BTC Global/Pooled Regime Engine — G2 Conflict-Only Veto

**Status: G2_SHADOW_GATE_FAILED**

Research only; live BBC untouched.

## Frozen policy
- SELL_COMPATIBLE => TRADE
- NEUTRAL => TRADE
- BUY_COMPATIBLE => WAIT

## Historical Tuesday comparison
| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Always A5.11 | 126 | 100.00% | 65.87% | $+150.89 | $+1.1976 | 1.960 | $20.91 |
| G1 hard gate | 40 | 31.75% | 77.50% | $+94.81 | $+0.7525 | 4.287 | $6.25 |
| G2 conflict-only | 43 | 34.13% | 74.42% | $+92.86 | $+0.7369 | 3.998 | $8.21 |

## Outcome by predicted G1 class
| Predicted class | N | WR | PnL | Exp/trade | PF |
|---|---:|---:|---:|---:|---:|
| SELL_COMPATIBLE | 40 | 77.50% | $+94.81 | $+2.3703 | 4.28674291670712 |
| NEUTRAL | 3 | 33.33% | $-1.96 | $-0.6521 | 0.08067155079877743 |
| BUY_COMPATIBLE | 83 | 61.45% | $+58.04 | $+0.6993 | 1.4598375472585163 |

## Promotion gate
- FAIL — `coverage_ge_35pct`
- FAIL — `exp_per_opportunity_improves`
- FAIL — `total_pnl_ge_baseline`
- PASS — `trade_wr_improves`
- FAIL — `positive_delta_3_of_4_blocks`

## Four chronological blocks
| Block | Dates | Baseline PnL | G2 PnL | Delta |
|---:|---|---:|---:|---:|
| 1 | 2024-03-05 → 2024-10-08 | $+35.96 | $+25.59 | $-10.37 |
| 2 | 2024-10-15 → 2025-05-20 | $+19.97 | $+44.32 | $+24.36 |
| 3 | 2025-05-27 → 2025-12-23 | $+60.99 | $+16.28 | $-44.71 |
| 4 | 2025-12-30 → 2026-07-28 | $+33.97 | $+6.66 | $-27.31 |

## August 2026 — report only
| Date WIB | G1 predicted | G2 decision | A5.11 PnL | G2 realized |
|---|---|---|---:|---:|
| 2026-08-04 | BUY_COMPATIBLE | WAIT | $-4.75 | $+0.00 |
| 2026-08-11 | NEUTRAL | TRADE | $-0.82 | $-0.82 |
| 2026-08-18 | NEUTRAL | TRADE | $-0.10 | $-0.10 |

August always trade: **$-5.68**; G2: **$-0.93**; delta **$+4.75**.

**Final G2 verdict: FAIL — keep result; do not tune this mapping inside G2.**

No live BBC changes were made.
