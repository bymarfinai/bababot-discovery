# SOL LONG 15UTC Market Alignment Anatomy — A49 Result

A49 keeps the SOL parent frozen and studies only BTC/ETH state available before the SOL H fill.

BTC coverage **100.0000%**; ETH coverage **100.0000%**. Count reconciliation: **True**. Enriched **1219/1219**; errors **0**.

## Replicated market separators

| Family | Feature | Dev WIN med | Dev FAIL med | Dev effect | Dev sign blocks | Ext effect | RefVal effect | Strong |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| - | none | - | - | - | - | - | - | - |

## Strongest diagnostics

| Family | Feature | Dev effect | Dev sign blocks | Ext gap/effect | RefVal gap/effect | Replicated |
|---|---|---:|---:|---|---|---:|
| LATE | market_last120_breadth | 0.500 | 3/6 | -1.00000/0.500 | 1.00000/0.500 | NO |
| PREFILL | btc_prefill_return_pct | 0.240 | 5/6 | 0.00122/0.110 | 0.00015/0.022 | NO |
| PREFILL | market_prefill_mean_return_pct | 0.134 | 5/6 | 0.00071/0.055 | -0.00089/0.117 | NO |
| REF6 | btc_ref6_range_pct | 0.112 | 5/6 | -0.00278/0.139 | -0.00109/0.091 | NO |
| REF6 | eth_ref6_range_pct | 0.078 | 4/6 | -0.00506/0.185 | -0.00090/0.058 | NO |
| REF6 | btc_ref6_close_location | 0.070 | 3/6 | -0.03711/0.088 | 0.02792/0.060 | NO |
| PREFILL | btc_prefill_close_vs_refH_pct | 0.065 | 4/6 | -0.00174/0.109 | -0.00000/0.000 | NO |
| REF6 | eth_ref6_close_location | 0.063 | 4/6 | -0.01259/0.030 | -0.04392/0.103 | NO |
| LATE | eth_last120_return_pct | 0.061 | 3/6 | -0.00310/0.180 | 0.00144/0.121 | NO |
| LATE | btc_last60_return_pct | 0.057 | 3/6 | 0.00044/0.053 | 0.00007/0.012 | NO |
| LATE | eth_last60_return_pct | 0.049 | 2/6 | -0.00104/0.092 | 0.00054/0.060 | NO |
| REF6 | market_ref6_mean_return_pct | 0.031 | 4/6 | -0.00214/0.097 | -0.00065/0.052 | NO |

## Decision

Replicated features: **0**. Strong replicated: **0**.

**Status: SOL_LONG_15UTC_MARKET_ALIGNMENT_A49_INCONCLUSIVE**

Research only. Live Baba Bot remains unchanged.
