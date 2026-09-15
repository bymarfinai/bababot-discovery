# BNB B29 B1 — Event-Conditioned Structural Transition Result

**Status: BNB_B29_B1_EVENT_TRANSITION_REJECT**

B1 tests fixed causal structural event sequences and forward direction only. No entry, TP, SL, leverage, fees, PnL or live orders are tested.

## Frozen A1 artifact integrity

- Accepted A1 artifact id: `10336102957`
- Fingerprint file SHA256: `eae8f278d45e7c3035b03900b30e315b16a241c1fbc5fda39231681390c25cfa`
- Exact frozen file hash: **PASS**
- Rows: 229,267 / expected 229,267
- Boundary/grid/schema: **PASS**
- Forward outcomes reconstructed only from frozen A1 ret_15: **YES**
- Total de-duplicated events (2022-2026 folds): 38,516

## Frozen family gate results

| Family | Dir | N | +60m hit | Wilson LCB | Median signed +60m | Folds + | Worst fold | 2025 | 2026 | Aux >=52% | Max era share | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SWEEP_LOW_RECLAIM | LONG | 8084 | 54.13% | 53.04% | 0.03% | 5 | 52.66% | 52.66% | 53.00% | 4 | 22.22% | REJECT |
| BREAK_LOW_FAIL | LONG | 5102 | 52.51% | 51.14% | 0.02% | 4 | 48.58% | 55.00% | 48.58% | 3 | 22.36% | REJECT |
| SWEEP_HIGH_REJECT | SHORT | 8534 | 51.50% | 50.44% | 0.01% | 4 | 48.11% | 48.11% | 52.91% | 0 | 22.02% | REJECT |
| BREAK_HIGH_FAIL | SHORT | 5547 | 49.88% | 48.57% | 0.00% | 2 | 48.94% | 49.68% | 50.71% | 0 | 23.31% | REJECT |
| PULLBACK_UP_RESUME | LONG | 4387 | 48.19% | 46.71% | -0.01% | 2 | 44.55% | 48.36% | 50.33% | 0 | 22.29% | REJECT |
| COMPRESSION_EXPAND_UP | LONG | 37 | 62.16% | 46.10% | 0.17% | 3 | 42.86% | 57.14% | 42.86% | 3 | 27.03% | REJECT |
| PULLBACK_DOWN_RESUME | SHORT | 4001 | 46.44% | 44.90% | -0.03% | 0 | 45.61% | 46.08% | 46.06% | 0 | 21.92% | REJECT |
| BREAK_HIGH_HOLD | LONG | 1576 | 47.34% | 44.88% | -0.02% | 0 | 45.30% | 46.52% | 48.03% | 1 | 27.09% | REJECT |
| BREAK_LOW_HOLD | SHORT | 1204 | 45.18% | 42.39% | -0.06% | 0 | 42.54% | 47.62% | 47.88% | 0 | 24.42% | REJECT |
| COMPRESSION_EXPAND_DOWN | SHORT | 44 | 45.45% | 31.71% | -0.10% | 2 | 37.50% | 42.86% | 66.67% | 0 | 36.36% | REJECT |

## Primary +60m fold detail

| Family | Fold | N | Hit | Median signed return |
|---|---:|---:|---:|---:|
| SWEEP_LOW_RECLAIM | 2022 | 1775 | 53.80% | 0.05% |
| SWEEP_LOW_RECLAIM | 2023 | 1670 | 54.07% | 0.03% |
| SWEEP_LOW_RECLAIM | 2024 | 1796 | 56.63% | 0.06% |
| SWEEP_LOW_RECLAIM | 2025 | 1728 | 52.66% | 0.02% |
| SWEEP_LOW_RECLAIM | 2026 | 1115 | 53.00% | 0.02% |
| SWEEP_HIGH_REJECT | 2022 | 1879 | 54.44% | 0.04% |
| SWEEP_HIGH_REJECT | 2023 | 1784 | 52.13% | 0.01% |
| SWEEP_HIGH_REJECT | 2024 | 1874 | 50.37% | 0.00% |
| SWEEP_HIGH_REJECT | 2025 | 1827 | 48.11% | -0.01% |
| SWEEP_HIGH_REJECT | 2026 | 1170 | 52.91% | 0.02% |
| BREAK_HIGH_HOLD | 2022 | 261 | 46.74% | -0.04% |
| BREAK_HIGH_HOLD | 2023 | 362 | 45.30% | -0.02% |
| BREAK_HIGH_HOLD | 2024 | 427 | 49.88% | 0.00% |
| BREAK_HIGH_HOLD | 2025 | 374 | 46.52% | -0.02% |
| BREAK_HIGH_HOLD | 2026 | 152 | 48.03% | -0.01% |
| BREAK_LOW_HOLD | 2022 | 228 | 42.54% | -0.13% |
| BREAK_LOW_HOLD | 2023 | 244 | 43.03% | -0.06% |
| BREAK_LOW_HOLD | 2024 | 273 | 45.05% | -0.05% |
| BREAK_LOW_HOLD | 2025 | 294 | 47.62% | -0.04% |
| BREAK_LOW_HOLD | 2026 | 165 | 47.88% | -0.03% |
| BREAK_HIGH_FAIL | 2022 | 1089 | 48.94% | -0.01% |
| BREAK_HIGH_FAIL | 2023 | 1231 | 50.93% | 0.01% |
| BREAK_HIGH_FAIL | 2024 | 1293 | 49.42% | -0.01% |
| BREAK_HIGH_FAIL | 2025 | 1234 | 49.68% | -0.00% |
| BREAK_HIGH_FAIL | 2026 | 700 | 50.71% | 0.01% |
| BREAK_LOW_FAIL | 2022 | 1035 | 52.85% | 0.03% |
| BREAK_LOW_FAIL | 2023 | 1141 | 51.88% | 0.01% |
| BREAK_LOW_FAIL | 2024 | 1135 | 52.69% | 0.03% |
| BREAK_LOW_FAIL | 2025 | 1120 | 55.00% | 0.05% |
| BREAK_LOW_FAIL | 2026 | 671 | 48.58% | -0.01% |
| COMPRESSION_EXPAND_UP | 2022 | 7 | 100.00% | 1.02% |
| COMPRESSION_EXPAND_UP | 2023 | 10 | 60.00% | 0.10% |
| COMPRESSION_EXPAND_UP | 2024 | 6 | 50.00% | 0.03% |
| COMPRESSION_EXPAND_UP | 2025 | 7 | 57.14% | 1.00% |
| COMPRESSION_EXPAND_UP | 2026 | 7 | 42.86% | -0.14% |
| COMPRESSION_EXPAND_DOWN | 2022 | 12 | 41.67% | -0.37% |
| COMPRESSION_EXPAND_DOWN | 2023 | 16 | 37.50% | -0.13% |
| COMPRESSION_EXPAND_DOWN | 2024 | 3 | 66.67% | 0.16% |
| COMPRESSION_EXPAND_DOWN | 2025 | 7 | 42.86% | -0.02% |
| COMPRESSION_EXPAND_DOWN | 2026 | 6 | 66.67% | 0.13% |
| PULLBACK_UP_RESUME | 2022 | 907 | 46.75% | -0.04% |
| PULLBACK_UP_RESUME | 2023 | 945 | 44.55% | -0.04% |
| PULLBACK_UP_RESUME | 2024 | 959 | 51.62% | 0.01% |
| PULLBACK_UP_RESUME | 2025 | 978 | 48.36% | -0.02% |
| PULLBACK_UP_RESUME | 2026 | 598 | 50.33% | 0.00% |
| PULLBACK_DOWN_RESUME | 2022 | 829 | 47.17% | -0.05% |
| PULLBACK_DOWN_RESUME | 2023 | 877 | 45.61% | -0.03% |
| PULLBACK_DOWN_RESUME | 2024 | 869 | 47.18% | -0.03% |
| PULLBACK_DOWN_RESUME | 2025 | 855 | 46.08% | -0.03% |
| PULLBACK_DOWN_RESUME | 2026 | 571 | 46.06% | -0.03% |

## Decision

**BNB_B29_B1_EVENT_TRANSITION_REJECT**

No fixed event family satisfies the preregistered promotion gate. Do not proceed to execution discovery from this B1 identity.

No live orders were placed.
