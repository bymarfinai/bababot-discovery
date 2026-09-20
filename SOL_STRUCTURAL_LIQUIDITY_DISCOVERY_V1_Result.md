# SOL Structural Liquidity Discovery V1 — Result

- 5m coverage: **99.769767%**
- H1 bars: **52,001**
- Liquidity candidate instances: **17,940**
- Direct first-sweep events: **14,450**
- 2020-2022 descriptive discovery; 2023-2024 frozen confirmation.
- 2025+ CLOSED.
- No entry, TP, SL, PnL, session, or indicator filter.

## Candidate-family scorecard

| Family | Side | Candidates | Fully observed | Sweeps | Sweep rate | Reclaim | Structural event / sweep | Structural event / reclaim | Median age |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H1_EQUAL_CLUSTER | BUY_SIDE | 775 | 765 | 703 | 91.24% | 63.87% | 16.79% | 26.28% | 6.0h |
| H1_EQUAL_CLUSTER | SELL_SIDE | 710 | 704 | 645 | 91.19% | 69.15% | 16.12% | 23.32% | 7.0h |
| H1_SWING | BUY_SIDE | 5132 | 5087 | 4686 | 91.55% | 68.29% | 17.88% | 26.19% | 6.0h |
| H1_SWING | SELL_SIDE | 5182 | 5139 | 4675 | 90.33% | 71.49% | 17.35% | 24.27% | 6.0h |
| H4_SWING | BUY_SIDE | 1272 | 1261 | 1051 | 82.95% | 64.51% | 13.42% | 20.80% | 20.0h |
| H4_SWING | SELL_SIDE | 1303 | 1291 | 1054 | 81.10% | 71.06% | 12.71% | 17.89% | 20.0h |
| PREVIOUS_DAY | BUY_SIDE | 1563 | 1563 | 732 | 46.90% | 67.21% | 14.75% | 21.95% | 5.0h |
| PREVIOUS_DAY | SELL_SIDE | 1563 | 1563 | 687 | 43.95% | 72.78% | 15.43% | 21.20% | 5.0h |
| PREVIOUS_WEEK | BUY_SIDE | 220 | 219 | 113 | 51.60% | 62.83% | 7.08% | 11.27% | 27.0h |
| PREVIOUS_WEEK | SELL_SIDE | 220 | 219 | 95 | 43.38% | 69.47% | 8.42% | 12.12% | 27.0h |

## Frozen enrichment audit — 2023-2024

Each non-baseline family is compared with H1_SWING on the same side.

| Family | Side | N | Event rate | H1 swing | Lift | Event/reclaim | H1 swing event/reclaim | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| H1_EQUAL_CLUSTER | BUY_SIDE | 353 | 17.85% | 18.35% | -0.50 pp | 28.25% | 26.32% | **NOT_ENRICHED_AS_DEFINED** |
| H1_EQUAL_CLUSTER | SELL_SIDE | 305 | 17.38% | 17.83% | -0.45 pp | 23.35% | 24.25% | **NOT_ENRICHED_AS_DEFINED** |
| H4_SWING | BUY_SIDE | 534 | 13.67% | 18.35% | -4.67 pp | 20.86% | 26.32% | **NOT_ENRICHED_AS_DEFINED** |
| H4_SWING | SELL_SIDE | 483 | 12.63% | 17.83% | -5.20 pp | 17.58% | 24.25% | **NOT_ENRICHED_AS_DEFINED** |
| PREVIOUS_DAY | BUY_SIDE | 356 | 15.45% | 18.35% | -2.90 pp | 21.83% | 26.32% | **NOT_ENRICHED_AS_DEFINED** |
| PREVIOUS_DAY | SELL_SIDE | 302 | 18.87% | 17.83% | 1.05 pp | 25.33% | 24.25% | **NOT_ENRICHED_AS_DEFINED** |
| PREVIOUS_WEEK | BUY_SIDE | 58 | 8.62% | 18.35% | -9.72 pp | 13.51% | 26.32% | **NOT_ENRICHED_AS_DEFINED** |
| PREVIOUS_WEEK | SELL_SIDE | 40 | 2.50% | 17.83% | -15.33 pp | 3.57% | 24.25% | **NOT_ENRICHED_AS_DEFINED** |

## Enrichment gate audit

### H1_EQUAL_CLUSTER | BUY_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- PASS — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

### H1_EQUAL_CLUSTER | SELL_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- PASS — year_2024_above_h1_swing

### H4_SWING | BUY_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

### H4_SWING | SELL_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

### PREVIOUS_DAY | BUY_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

### PREVIOUS_DAY | SELL_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- PASS — year_2023_above_h1_swing
- PASS — year_2024_above_h1_swing

### PREVIOUS_WEEK | BUY_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

### PREVIOUS_WEEK | SELL_SIDE — NOT_ENRICHED_AS_DEFINED
- PASS — confirmation_sweep_n_ge_30
- FAIL — event_rate_lift_ge_8pp
- FAIL — reclaimed_event_rate_lift_ge_8pp
- FAIL — year_2023_above_h1_swing
- FAIL — year_2024_above_h1_swing

## Interpretation

STRUCTURAL_LIQUIDITY_EVENT is an observed consequence label: a causally-known level was first swept, reclaimed, and followed by an opposite H1 structural break before the sweep extreme was accepted again.
It is not a claim that hidden orders were directly observed.

ENRICHED_FAMILIES=NONE
2025_PLUS=CLOSED
