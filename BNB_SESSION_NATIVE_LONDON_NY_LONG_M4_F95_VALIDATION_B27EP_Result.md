# BNB Session-Native London→New York LONG M4 Frozen F95 Validation — B27EP Result

Raw BNB 5m coverage: **100.0000%**.

Validation uses only **reference_validation (2025-01-01 → 2026-07-30)**.

The entry rule is frozen from B27EO: **F95 touch + close back above F95, then fill at the next 5m open**. No alternative entry was searched or retuned.

## Upstream integrity

- Causal leaves: **45 / 45**
- Upstream H2: **35 / 35**
- Upstream non-H2: **10 / 10**
- Structural H2 rate before entry condition: **77.8%**

## Frozen F95 validation

| Metric | Result |
|---|---:|
| Eligible F95 entries | **7/45 (15.6%)** |
| H2 after entry | **6/7** |
| H2-after-entry rate | **85.7%** |
| Wilson 95% interval | **48.7% – 97.4%** |
| Winner capture | **6/35 (17.1%)** |
| Median leave→entry | **25.0m** |
| Median entry→H2 | **5.0m** |
| Median entry depth | **0.043R** |
| Median post-entry MAE | **0.000R** |
| P75 post-entry MAE | **0.044R** |

## Frozen target check

- Predeclared target: **H2-after-entry >= 90.0%**
- Observed validation: **85.7%**
- Target result: **TARGET_NOT_MET**

The validation percentage must be interpreted together with eligible N and the Wilson interval. This milestone validates only the structural post-entry H2 event; it is **not yet a trading win rate** because no stop, TP, fees, slippage, or PnL model is active.

**Status: B27EP_BNB_F95_REFERENCE_VALIDATION_COMPLETE_TARGET_NOT_MET**

STOP: no F90/F85 comparison, retuning, TP/SL, economics, SHORT, August reveal, or live integration was run.
