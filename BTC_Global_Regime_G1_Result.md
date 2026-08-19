# BTC Global/Pooled Regime Engine — G1 Result

**Status: G1_POOLED_PASS_TUESDAY_SHADOW_FAIL**

Research only; live BBC untouched.

## Pooled embargoed walk-forward
- Pseudo-OOS states: **21,144**
- Accuracy: **46.17%** (prior baseline 43.49%)
- Balanced accuracy: **42.51%**
- Macro F1: **0.4361**
- Log loss: **0.907395** (prior 0.985771)
- Brier: **0.572877** (prior 0.601950)
- SELL-vs-rest AUC: **0.5690**
- Hard-predicted SELL coverage: **34.14%**
- Actual SELL rate overall: **44.08%**
- Actual SELL rate when model predicts SELL: **47.28%**
- SELL enrichment: **+3.21 pp**

### Pooled acceptance gate
- PASS — `predictions_ge_18000`
- PASS — `causal_embargo_all_months`
- PASS — `logloss_beats_prior`
- PASS — `brier_beats_prior`
- PASS — `sell_auc_ge_055`
- PASS — `sell_enrichment_ge_3pp`
- PASS — `predicted_sell_coverage_ge_20pct`
- PASS — `logloss_improves_3_of_4_blocks`

### Four chronological pooled blocks
| Block | Dates | Model LL | Prior LL | Improved | Model Brier | Prior Brier |
|---:|---|---:|---:|---|---:|---:|
| 1 | 2024-03-01 00:00:00+00:00 → 2024-10-07 05:00:00+00:00 | 0.85892 | 0.92485 | YES | 0.55425 | 0.57264 |
| 2 | 2024-10-07 06:00:00+00:00 → 2025-05-15 11:00:00+00:00 | 0.89297 | 0.95006 | YES | 0.56644 | 0.58492 |
| 3 | 2025-05-15 12:00:00+00:00 → 2025-12-21 17:00:00+00:00 | 0.96347 | 1.07486 | YES | 0.59699 | 0.64396 |
| 4 | 2025-12-21 18:00:00+00:00 → 2026-07-29 23:00:00+00:00 | 0.91422 | 0.99332 | YES | 0.57383 | 0.60629 |

## Frozen Tuesday A5.11 overlay
- Opportunities: **126**
- Always trade: WR **65.87%**, PnL **$+150.89**, exp/oppty **$+1.1976**, PF **1.960**, DD **$20.91**
- Regime gate: 40 trades / 86 waits (31.75% coverage), WR **77.50%**, PnL **$+94.81**, exp/oppty **$+0.7525**, PF **4.287**, DD **$6.25**
- PnL delta: **$-56.08**

### Tuesday shadow promotion gate
- FAIL — `coverage_ge_35pct`
- FAIL — `exp_per_opportunity_improves`
- FAIL — `total_pnl_ge_baseline`
- PASS — `trade_wr_improves`
- FAIL — `positive_delta_3_of_4_blocks`

### Tuesday chronological blocks
| Block | Dates | Baseline PnL | Gated PnL | Delta |
|---:|---|---:|---:|---:|
| 1 | 2024-03-05 → 2024-10-08 | $+35.96 | $+25.59 | $-10.37 |
| 2 | 2024-10-15 → 2025-05-20 | $+19.97 | $+44.32 | $+24.36 |
| 3 | 2025-05-27 → 2025-12-23 | $+60.99 | $+18.24 | $-42.76 |
| 4 | 2025-12-30 → 2026-07-28 | $+33.97 | $+6.66 | $-27.31 |

## August 2026 — report only
| Date WIB | pSELL | Predicted | Decision | Actual G0 regime | A5.11 PnL |
|---|---:|---|---|---|---:|
| 2026-08-04 | 38.5% | BUY_COMPATIBLE | WAIT | BUY_COMPATIBLE | $-4.75 |
| 2026-08-11 | 33.2% | NEUTRAL | WAIT | NEUTRAL | $-0.82 |
| 2026-08-18 | 31.1% | NEUTRAL | WAIT | NEUTRAL | $-0.10 |

**Pooled model gate: PASS. Tuesday shadow gate: FAIL.**

No result in this report changes live BBC automatically.
