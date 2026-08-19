# BTC Global/Pooled Regime Engine — G4 Execution Compatibility

**Status: G4_POOLED_GATE_FAILED**

Research only; live BBC untouched.

## Mandatory A5.11 parity
- N: **139**
- Wins: **89**
- PnL: **$+130.328521**
- A5.2 actions: **7**
- FastMR actions: **12**
- Recoveries: **4**
- Max trade-level PnL delta vs canonical: **0**
- Verdict: **PASS**

## Pooled frozen-A5.11 labels
- Hourly states: **23,304**
- WIN rate: **40.59%**
- Aggregate hypothetical PnL: **$-17630.02**

## Embargoed pooled walk-forward
- Pseudo-OOS states: **21,144**
- Unconditional WIN rate: **40.81%**
- Accuracy: **59.08%** (prior 59.19%)
- Log loss: **0.677453** (prior 0.676520)
- Brier: **0.242167** (prior 0.241727)
- ROC AUC: **0.5117**
- p>=0.50 TRADE coverage: **0.73%**
- WIN rate among predicted TRADE: **42.58%**
- WIN-rate enrichment: **+1.77 pp**

### Pooled acceptance gate
- PASS — `predictions_ge_18000`
- PASS — `causal_embargo_all_months`
- FAIL — `logloss_beats_prior`
- FAIL — `brier_beats_prior`
- FAIL — `auc_ge_055`
- FAIL — `trade_coverage_ge_20pct`
- FAIL — `trade_wr_enrichment_ge_3pp`
- FAIL — `logloss_improves_3_of_4_blocks`

### Four chronological pooled blocks
| Block | Dates | Model LL | Prior LL | Improved | Model Brier | Prior Brier |
|---:|---|---:|---:|---|---:|---:|
| 1 | 2024-03-01 00:00:00+00:00 → 2024-10-07 05:00:00+00:00 | 0.67698 | 0.67544 | NO | 0.24190 | 0.24118 |
| 2 | 2024-10-07 06:00:00+00:00 → 2025-05-15 11:00:00+00:00 | 0.67633 | 0.67453 | NO | 0.24160 | 0.24075 |
| 3 | 2025-05-15 12:00:00+00:00 → 2025-12-21 17:00:00+00:00 | 0.67322 | 0.67395 | YES | 0.24012 | 0.24046 |
| 4 | 2025-12-21 18:00:00+00:00 → 2026-07-29 23:00:00+00:00 | 0.68328 | 0.68216 | NO | 0.24504 | 0.24452 |

## Frozen Tuesday A5.11 overlay
- Opportunities: **126**
- Always: WR **65.87%**, PnL **$+150.89**, exp/oppty **$+1.1976**, PF **1.960**, DD **$20.91**
- G4 gate: 1 trades / 125 waits (0.79%), WR **100.00%**, PnL **$+6.00**, exp/oppty **$+0.0476**, PF **999.000**, DD **$0.00**
- PnL delta: **$-144.89**

### Tuesday shadow promotion gate
- FAIL — `coverage_ge_35pct`
- FAIL — `exp_per_opportunity_improves`
- FAIL — `total_pnl_ge_baseline`
- PASS — `trade_wr_improves`
- FAIL — `positive_delta_3_of_4_blocks`

### Tuesday chronological blocks
| Block | Dates | Baseline PnL | G4 PnL | Delta |
|---:|---|---:|---:|---:|
| 1 | 2024-03-05 → 2024-10-08 | $+35.96 | $+6.00 | $-29.96 |
| 2 | 2024-10-15 → 2025-05-20 | $+19.97 | $+0.00 | $-19.97 |
| 3 | 2025-05-27 → 2025-12-23 | $+60.99 | $+0.00 | $-60.99 |
| 4 | 2025-12-30 → 2026-07-28 | $+33.97 | $+0.00 | $-33.97 |

## August 2026 — report only
| Date WIB | p(WIN) | Decision | A5.11 PnL |
|---|---:|---|---:|
| 2026-08-04 | 39.1% | WAIT | $-4.75 |
| 2026-08-11 | 35.8% | WAIT | $-0.82 |
| 2026-08-18 | 39.2% | WAIT | $-0.10 |

August always-trade: **$-5.68**; G4 gated: **$+0.00**.

**Pooled G4 gate: FAIL. Tuesday shadow gate: FAIL.**

No live BBC changes were made.
