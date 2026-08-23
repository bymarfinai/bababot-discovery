# B27DA — BTC 24H F05 SHORT Fresh Holdout Detector Confirmation — Result

Fresh window: **2026-08-21 00:00:00+00:00 -> 2026-08-23 00:00:00+00:00 (exclusive)**; fresh raw 5m rows: **576**.

**Audit status: PASS.** Historical B27CV models reproduced before fresh scoring: +10 AUC 0.8452298452; +15 AUC 0.8860088365. No fresh row entered fitting or threshold selection.

Fresh causal reconstruction: **11** complete 4H blocks with full +4h horizon -> **0** reclaimed source event(s) -> **0** executable F05 fill(s).

## Six clocks independently

| UTC / WIB | Blocks | Reclaimed | F05 fills | Detector | BAD caught | GOOD cut | OTHER | Precision |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| 00-04 / 07-11 | 2 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 00-04 / 07-11 | 2 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 00-04 / 07-11 | 2 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |
| 04-08 / 11-15 | 2 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 04-08 / 11-15 | 2 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 04-08 / 11-15 | 2 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |
| 08-12 / 15-19 | 2 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 08-12 / 15-19 | 2 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 08-12 / 15-19 | 2 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |
| 12-16 / 19-23 | 2 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 12-16 / 19-23 | 2 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 12-16 / 19-23 | 2 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |
| 16-20 / 23-03 | 2 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 16-20 / 23-03 | 2 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 16-20 / 23-03 | 2 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |
| 20-00 / 03-07 | 1 | 0 | 0 | GLOBAL_PLUS15_SAFE | 0/0 (-) | 0/0 (-) | 0 | - |
| 20-00 / 03-07 | 1 | 0 | 0 | PERSIST_10_15 | 0/0 (-) | 0/0 (-) | 0 | - |
| 20-00 / 03-07 | 1 | 0 | 0 | REFINED_BULL_IMPULSE | 0/0 (-) | 0/0 (-) | 0 | - |

## Pooled fresh holdout

| Detector | Fills | BAD | GOOD | OTHER | BAD caught | GOOD cut | Precision |
|---|---:|---:|---:|---:|---:|---:|---:|
| GLOBAL_PLUS15_SAFE | 0 | 0 | 0 | 0 | 0/0 (-) | 0/0 (-) | - |
| PERSIST_10_15 | 0 | 0 | 0 | 0 | 0/0 (-) | 0/0 (-) | - |
| REFINED_BULL_IMPULSE | 0 | 0 | 0 | 0 | 0/0 (-) | 0/0 (-) | - |

## Readiness

Required before detector confirmation: **>=10 BAD and >=30 GOOD**. Fresh holdout currently has **0 BAD and 0 GOOD**.

**Frozen status: `B27DA_FRESH_HOLDOUT_INSUFFICIENT`.**

Because B27DA is detector/anatomy confirmation only, trading WR/PF/expectancy/PnL for hypothetical early-abort exits are N/A. No live BBC change is authorized.
