# BTC Global/Pooled Regime Engine — G6 Weekly Regime Health

**Status: G6_WEEKLY_HEALTH_GATE_FAILED**

Research only; live BBC untouched.

## Frozen slow-state rule
Use exactly the 168 completed hourly pooled predictions before each Tuesday.

`WEEKLY_SELL_HEALTH = mean(pSELL - causal SELL prior)`

TRADE iff weekly health >= 0; otherwise WAIT.

## Historical Tuesday comparison
- Eligible opportunities: **125**
- Health mean / median: **-0.00959 / -0.00376**
- Health range: **-0.09980 → +0.05737**

| Policy | Trades | Coverage | WR | PnL | Exp/oppty | PF | Max DD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Always A5.11 | 125 | 100.00% | 66.40% | $+155.64 | $+1.2452 | 2.021 | $20.91 |
| G6 weekly health | 55 | 44.00% | 69.09% | $+103.94 | $+0.8316 | 2.483 | $13.64 |

## Outcome attribution
| Weekly state | N | WR | PnL | Exp/trade | PF |
|---|---:|---:|---:|---:|---:|
| health >= 0 | 55 | 69.09% | $+103.94 | $+1.8899 | 2.483 |
| health < 0 | 70 | 64.29% | $+51.70 | $+0.7386 | 1.628 |

## Acceptance gate
- PASS — `eligible_opportunities_ge_120`
- PASS — `coverage_ge_35pct`
- FAIL — `exp_per_opportunity_improves`
- FAIL — `total_pnl_ge_baseline`
- PASS — `trade_wr_improves`
- PASS — `max_dd_improves`
- FAIL — `positive_delta_3_of_4_blocks`

## Four chronological blocks
| Block | Dates | Baseline PnL | G6 PnL | Delta |
|---:|---|---:|---:|---:|
| 1 | 2024-03-12 → 2024-10-15 | $+46.71 | $+33.47 | $-13.25 |
| 2 | 2024-10-22 → 2025-05-20 | $+13.97 | $+17.42 | $+3.45 |
| 3 | 2025-05-27 → 2025-12-23 | $+60.99 | $+23.78 | $-37.21 |
| 4 | 2025-12-30 → 2026-07-28 | $+33.97 | $+29.28 | $-4.69 |

## August 2026 — report only
| Date WIB | Weekly health | Mean pSELL | Decision | A5.11 PnL | G6 realized |
|---|---:|---:|---|---:|---:|
| 2026-08-04 | -0.04655 | 39.46% | WAIT | $-4.75 | $+0.00 |
| 2026-08-11 | -0.10538 | 33.57% | WAIT | $-0.82 | $+0.00 |
| 2026-08-18 | -0.12001 | 32.11% | WAIT | $-0.10 | $+0.00 |

August baseline: **$-5.68**; G6: **$+0.00**.

**Final G6 verdict: FAIL — preserve result; no lookback or threshold tuning inside G6.**

No live BBC changes were made.
