# BNB Session-Native London→New York LONG M7 Entry Economics Anatomy — B27ES Result

Raw BNB 5m coverage: **100.0000%**.

Economics discovery uses **development only (2022-01-01 → 2025-01-01)** and all frozen B27EO eligible entries. External, reference-validation and August are not used for economics selection.

Cost model: **0.10% round-trip fee + 0.05% slippage = 0.15% total cost per trade**. Illustrative PnL uses **$500 notional** ($10 × 50x) with no funding/liquidation model.

Intrabar rule: entry at 5m open; TP/SL active on the entry bar; if both are touched in one bar, **SL wins**. Unresolved trades exit at NY session close.

## Entry / excursion anatomy

| Candidate | N | B27EO H2 | Med entry depth | Med MFE | Med MAE | Med max ext above H | + grid cells | + cells RR>=1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_NEXT_OPEN | 97 | 78.35% | 0.130R | 0.373R | 0.430R | 0.242R | 0/36 | 0/36 |
| E1_FIRST_BULL_CLOSE | 66 | 72.73% | 0.176R | 0.458R | 0.340R | 0.198R | 4/36 | 4/36 |
| E2_F95_RECLAIM | 21 | 95.24% | 0.036R | 0.243R | 0.337R | 0.197R | 0/36 | 0/36 |
| E3_F90_RECLAIM | 36 | 91.67% | 0.078R | 0.380R | 0.383R | 0.283R | 1/36 | 0/36 |
| E4_F85_RECLAIM | 38 | 81.58% | 0.114R | 0.367R | 0.347R | 0.247R | 0/36 | 0/36 |
| E5_MICRO_HL_BULL | 50 | 66.00% | 0.247R | 0.413R | 0.248R | 0.123R | 7/36 | 7/36 |

## Target reach from actual entry

| Candidate | H | H+0.05R | H+0.10R | H+0.20R | H+0.30R | H+0.50R |
|---|---:|---:|---:|---:|---:|---:|
| E0_NEXT_OPEN | 79.38% | 75.26% | 65.98% | 54.64% | 45.36% | 30.93% |
| E1_FIRST_BULL_CLOSE | 74.24% | 71.21% | 59.09% | 48.48% | 42.42% | 28.79% |
| E2_F95_RECLAIM | 95.24% | 90.48% | 61.90% | 47.62% | 38.10% | 23.81% |
| E3_F90_RECLAIM | 91.67% | 83.33% | 69.44% | 55.56% | 47.22% | 27.78% |
| E4_F85_RECLAIM | 81.58% | 78.95% | 65.79% | 52.63% | 47.37% | 34.21% |
| E5_MICRO_HL_BULL | 66.00% | 64.00% | 54.00% | 42.00% | 38.00% | 24.00% |

## Best development cell per candidate — unrestricted

| Candidate | TP extension | Stop | Net WR | Avg net/trade | Total PnL @ $500 | PF | Median RR |
|---|---:|---:|---:|---:|---:|---:|---:|
| E0_NEXT_OPEN | H+0.30R | 0.30R | 44.33% | -0.09% | $-41.75 | 0.79 | 1.43 |
| E1_FIRST_BULL_CLOSE | H+0.50R | 0.15R | 27.27% | 0.01% | $3.68 | 1.03 | 4.51 |
| E2_F95_RECLAIM | H+0.50R | 0.05R | 19.05% | -0.05% | $-5.63 | 0.76 | 10.72 |
| E3_F90_RECLAIM | H+0.30R | 0.50R | 52.78% | 0.00% | $0.63 | 1.01 | 0.76 |
| E4_F85_RECLAIM | H+0.50R | 0.50R | 44.74% | -0.11% | $-21.01 | 0.77 | 1.23 |
| E5_MICRO_HL_BULL | H+0.30R | 0.30R | 50.00% | 0.11% | $27.84 | 1.34 | 1.82 |

## Best development cell per candidate with median gross RR >= 1.0

| Candidate | TP extension | Stop | Net WR | Avg net/trade | Total PnL @ $500 | PF | Median RR |
|---|---:|---:|---:|---:|---:|---:|---:|
| E0_NEXT_OPEN | H+0.30R | 0.30R | 44.33% | -0.09% | $-41.75 | 0.79 | 1.43 |
| E1_FIRST_BULL_CLOSE | H+0.50R | 0.15R | 27.27% | 0.01% | $3.68 | 1.03 | 4.51 |
| E2_F95_RECLAIM | H+0.50R | 0.05R | 19.05% | -0.05% | $-5.63 | 0.76 | 10.72 |
| E3_F90_RECLAIM | H+0.30R | 0.15R | 33.33% | -0.03% | $-4.63 | 0.92 | 2.52 |
| E4_F85_RECLAIM | H+0.50R | 0.50R | 44.74% | -0.11% | $-21.01 | 0.77 | 1.23 |
| E5_MICRO_HL_BULL | H+0.30R | 0.30R | 50.00% | 0.11% | $27.84 | 1.34 | 1.82 |

## Development-only descriptive read

By preregistered robustness ordering, **E5_MICRO_HL_BULL** has the largest count of positive-expectancy grid cells with median gross RR >= 1.0: **7/36**.

This is **not a promoted setup**. Best-cell numbers are in-sample development economics and require a later frozen holdout test before being called validated trading WR/expectancy.

**Status: B27ES_BNB_ALL_ENTRY_ECONOMICS_DEV_COMPLETE**

STOP: no holdout economics reveal, no parameter retuning, no August, no H3/breakout-retest, no SHORT/live integration.
