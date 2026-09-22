# SOL Derivatives Liquidity Layer V1 — Result

**Status: DERIVATIVES_INFORMATION_WEAK_OR_UNSTABLE**

## Coverage

- Frozen SOL trades: **279**
- Causal feature rows available: **188 (67.38%)**
- Covered years: **2021, 2023, 2024, 2025, 2026**
- Archive days HTTP 200: **392**
- Archive days HTTP 404: **81**

## Pooled frozen-feature results

| Feature | N | Winner median | Loser median | AUC | Spearman R | All gates |
|---|---:|---:|---:|---:|---:|---:|
| global_account_ratio | 188 | 2.548654 | 2.847898 | 0.422 | -0.105 | FAIL |
| global_log | 188 | 0.935565 | 1.046581 | 0.422 | -0.105 | FAIL |
| top_account_ratio | 188 | 2.636891 | 2.986917 | 0.428 | -0.107 | FAIL |
| oi_trap_interaction_1h | 188 | 0.000061 | -0.000045 | 0.548 | 0.019 | FAIL |
| taker_ratio | 188 | 0.992068 | 1.027717 | 0.457 | -0.038 | FAIL |
| taker_log | 188 | -0.007964 | 0.027340 | 0.457 | -0.038 | FAIL |
| sweep_crowd_pressure | 188 | -0.216214 | -0.304695 | 0.537 | 0.068 | FAIL |
| oi_value | 188 | 744932833.840000 | 864759998.553000 | 0.470 | -0.000 | FAIL |
| sweep_top_position_pressure | 188 | -0.045021 | -0.055218 | 0.525 | 0.034 | FAIL |
| top_position_ratio | 188 | 1.785667 | 1.803911 | 0.483 | 0.008 | FAIL |
| top_position_log | 188 | 0.579792 | 0.589957 | 0.483 | 0.008 | FAIL |
| oi_change_1h | 188 | 0.002509 | 0.002621 | 0.485 | -0.002 | FAIL |
| oi_change_4h | 188 | -0.001100 | 0.000299 | 0.488 | -0.017 | FAIL |
| sweep_taker_pressure | 188 | -0.276329 | -0.317516 | 0.491 | -0.047 | FAIL |

## Gate-passing information signals

- None.

## Interpretation

V1 tests derivatives metrics only as an information layer over the already-frozen SOL detector.
No threshold, entry filter, WR optimization, TP change, or live rule is promoted from this run.

If a feature passes all frozen gates, the next experiment must preregister a fixed usage rule before testing economics.
If no feature passes, this futures-derivatives proxy is not used to modify the SOL detector.

This result does not validate or invalidate the options-IV method shown in the video; exact historical option-chain IV snapshots are a separate data problem.
