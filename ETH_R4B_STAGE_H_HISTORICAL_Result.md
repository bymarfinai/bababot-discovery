# ETH R4b — Stage H Historical Energy-Regime Validation

**VALIDATION ONLY. FEATURES FIXED FROM STAGE G; THRESHOLDS FROZEN FROM 2022 DISTRIBUTION ONLY. NO PNL-OPTIMIZED CUTS. NO LIVE GATE PROMOTION.**

Dataset through frozen Stage-E cutoff: **2026-08-25T23:55:00+00:00**. Coverage **100.0000%**.
2022 unique entry timestamps used to freeze tertiles: **126**.
RV1H q33/q67: **0.008603 / 0.014205**.
ATR1H q33/q67: **0.004258 / 0.006810**.
Stage H status: **HISTORICAL_ENERGY_RELATIONSHIP_PARTIAL**.

## High-vs-low tertile directional support

| Period | Feature | Usable cells | High Exp > Low | Support | Median ΔExp |
|---|---|---:|---:|---:|---:|
| DEV_2022 | rv_60 | 5 | 5 | 100.00% | $+6.15 |
| DEV_2022 | atr_pct_60 | 5 | 5 | 100.00% | $+8.57 |
| TEST_2023 | rv_60 | 5 | 5 | 100.00% | $+6.83 |
| TEST_2023 | atr_pct_60 | 5 | 5 | 100.00% | $+7.24 |
| CONFIRM_2024 | rv_60 | 5 | 3 | 60.00% | $+0.76 |
| CONFIRM_2024 | atr_pct_60 | 5 | 5 | 100.00% | $+3.48 |
| FINAL_OOS_2025 | rv_60 | 5 | 2 | 40.00% | $-0.13 |
| FINAL_OOS_2025 | atr_pct_60 | 5 | 5 | 100.00% | $+0.67 |
| SHADOW_2026 | rv_60 | 0 | 0 | NA | NA |
| SHADOW_2026 | atr_pct_60 | 3 | 3 | 100.00% | $+6.18 |

## Validation gates

- TEST_2023: **PASS**
- CONFIRM_2024: **PASS**
- FINAL_OOS_2025: **FAIL**

## Canonical LB240/H360 composite-energy view

| Period | Bucket | N | WR | Exp | PF |
|---|---|---:|---:|---:|---:|
| DEV_2022 | LOW_ENERGY | 20 | 25.00% | $-5.16 | 0.265 |
| DEV_2022 | MIXED | 46 | 65.22% | $+4.12 | 1.942 |
| DEV_2022 | HIGH_ENERGY | 30 | 53.33% | $+0.68 | 1.118 |
| TEST_2023 | LOW_ENERGY | 57 | 56.14% | $+0.75 | 1.800 |
| TEST_2023 | MIXED | 21 | 57.14% | $-0.42 | 0.865 |
| TEST_2023 | HIGH_ENERGY | 12 | 58.33% | $+7.24 | 7.760 |
| CONFIRM_2024 | LOW_ENERGY | 54 | 55.56% | $+1.73 | 1.865 |
| CONFIRM_2024 | MIXED | 51 | 64.71% | $+1.73 | 1.590 |
| CONFIRM_2024 | HIGH_ENERGY | 17 | 47.06% | $+1.33 | 1.488 |
| FINAL_OOS_2025 | LOW_ENERGY | 28 | 60.71% | $+1.84 | 1.848 |
| FINAL_OOS_2025 | MIXED | 56 | 60.71% | $-0.66 | 0.864 |
| FINAL_OOS_2025 | HIGH_ENERGY | 23 | 73.91% | $+5.52 | 4.897 |
| SHADOW_2026 | LOW_ENERGY | 36 | 36.11% | $-1.84 | 0.446 |
| SHADOW_2026 | MIXED | 7 | 28.57% | $-2.41 | 0.357 |
| SHADOW_2026 | HIGH_ENERGY | 4 | 100.00% | $+6.43 | inf |

## Guardrails

- RV1H and ATR1H were nominated by Stage G; Stage H does not search additional features.
- q33/q67 thresholds come only from the 2022 feature distribution, never from outcomes.
- 2023, 2024, and 2025 are sequential historical validation periods for the energy hypothesis; 2026 is shadow context only.
- Composite-energy buckets are secondary diagnostics; the formal Stage-H verdict uses individual RV1H and ATR1H high-vs-low expectancy direction.
- No strategy parameter, entry, hold, TP/SL, hour, character rule, or risk rule is changed here.
- Even a PASS does not authorize a live regime gate; that requires a separate preregistered gate-validation stage.
