# SOL LONG 15UTC Participation Anatomy — A48 Result

A48 keeps the A20 E0/E40 parent frozen and studies only volume/trade/taker-buy participation available before the H fill.

Extended 5m coverage: **99.7671%**. Count reconciliation: **True**. Enriched rows: **1219/1219**. Errors: **0**.

## Replicated participation separators

| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| - | none | - | - | - | - | - | - | - |

## Strongest diagnostics

| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |
|---|---|---:|---:|---|---|---:|
| UPPER_PARTICIPATION | upper80_quotevol_share | 0.231 | 4/6 | 0.002/0.022 | 0.004/0.041 | NO |
| PREFILL_PARTICIPATION | prefill_last30_trades_vs_refavg | 0.167 | 5/6 | 0.029/0.062 | 0.007/0.013 | NO |
| PREFILL_PARTICIPATION | prefill_last30_quotevol_vs_refavg | 0.151 | 5/6 | -0.006/0.013 | -0.018/0.024 | NO |
| PREFILL_PARTICIPATION | prefill_trades_perbar_vs_ref | 0.121 | 5/6 | 0.079/0.217 | 0.084/0.127 | NO |
| REF_VS_PRE6 | ref_trades_perbar_vs_pre6 | 0.112 | 6/6 | -0.003/0.007 | -0.030/0.054 | NO |
| REF_VS_PRE6 | ref_quotevol_perbar_vs_pre6 | 0.106 | 4/6 | -0.041/0.072 | -0.075/0.098 | NO |
| REF_VS_PRE6 | ref_basevol_perbar_vs_pre6 | 0.095 | 4/6 | -0.047/0.082 | -0.086/0.115 | NO |
| PREFILL_PARTICIPATION | prefill_lastbar_trades_vs_refavg | 0.086 | 5/6 | 0.039/0.053 | 0.085/0.117 | NO |
| LATE_REF | ref_last30_taker_buy_ratio | 0.085 | 3/6 | 0.015/0.244 | 0.001/0.018 | NO |
| PREFILL_PARTICIPATION | prefill_last30_taker_buy_ratio | 0.084 | 4/6 | 0.003/0.044 | -0.009/0.134 | NO |
| PREFILL_PARTICIPATION | prefill_quotevol_perbar_vs_ref | 0.076 | 4/6 | 0.058/0.134 | 0.094/0.127 | NO |
| REF_VS_PRE6 | pre6_taker_buy_ratio | 0.075 | 3/6 | 0.002/0.086 | 0.006/0.216 | NO |

## Decision

Replicated features: **0**. Strong replicated: **0**.

**Status: SOL_LONG_15UTC_PARTICIPATION_A48_INCONCLUSIVE**

Research only. Live Baba Bot remains unchanged.
