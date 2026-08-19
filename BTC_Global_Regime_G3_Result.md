# BTC Global/Pooled Regime Engine — G3 Relative SELL Lift

**Status: G3_SHADOW_GATE_FAILED**

Research only; live BBC untouched.

## Frozen rule
TRADE iff `pSELL >= causal training SELL prior` (SELL_LIFT >= 1.0).

## Historical Tuesday comparison
| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Always A5.11 | 126 | 100.00% | 65.87% | $+150.89 | $+1.1976 | 1.960 | $20.91 |
| G1 hard gate | 40 | 31.75% | 77.50% | $+94.81 | $+0.7525 | 4.287 | $6.25 |
| G2 conflict-only | 43 | 34.13% | 74.42% | $+92.86 | $+0.7369 | 3.998 | $8.21 |
| G3 relative lift | 76 | 60.32% | 65.79% | $+91.96 | $+0.7298 | 1.860 | $20.91 |

## Outcome attribution by relative SELL lift
| State | N | WR | PnL | Exp/trade | PF |
|---|---:|---:|---:|---:|---:|
| SELL_LIFT >= 1 | 76 | 65.79% | $+91.96 | $+1.2100 | 1.860 |
| SELL_LIFT < 1 | 50 | 66.00% | $+58.94 | $+1.1787 | 2.172 |

## Promotion gate
- PASS — `coverage_ge_35pct`
- FAIL — `exp_per_opportunity_improves`
- FAIL — `total_pnl_ge_baseline`
- FAIL — `trade_wr_improves`
- FAIL — `positive_delta_3_of_4_blocks`

## Four chronological blocks
| Block | Dates | Baseline PnL | G3 PnL | Delta |
|---:|---|---:|---:|---:|
| 1 | 2024-03-05 → 2024-10-08 | $+35.96 | $+22.24 | $-13.72 |
| 2 | 2024-10-15 → 2025-05-20 | $+19.97 | $+12.32 | $-7.64 |
| 3 | 2025-05-27 → 2025-12-23 | $+60.99 | $+27.83 | $-33.17 |
| 4 | 2025-12-30 → 2026-07-28 | $+33.97 | $+29.56 | $-4.40 |

## August 2026 — report only
Frozen historical SELL prior: **44.11%**.

| Date WIB | pSELL | SELL lift | Decision | A5.11 PnL | G3 realized |
|---|---:|---:|---|---:|---:|
| 2026-08-04 | 38.5% | 0.872 | WAIT | $-4.75 | $+0.00 |
| 2026-08-11 | 33.2% | 0.753 | WAIT | $-0.82 | $+0.00 |
| 2026-08-18 | 31.1% | 0.704 | WAIT | $-0.10 | $+0.00 |

August always trade: **$-5.68**; G3: **$+0.00**; delta **$+5.68**.

**Final G3 verdict: FAIL — preserve result; no threshold tuning inside G3.**

No live BBC changes were made.
