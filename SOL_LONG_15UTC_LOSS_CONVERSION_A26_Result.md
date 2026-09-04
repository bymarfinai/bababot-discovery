# SOL LONG 15:00 UTC Loss Conversion Anatomy — A26 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A26 is forensic only. The A20 R360/15 parent is unchanged and A23 recovery remains rejected.

## Central Development loss opportunity

| Losers | Latent recoverable | True-failure proxy | Latent share | Latent loss-$ share | Median recovery | Median target visit | Post-exit reclaim | E40 after reclaim |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 357 | 175 | 182 | 49.0% | 29.9% | 125m | 2.0 | 100.0% | 100.0% |

## Central Development taxonomy

| Loss class | N | Gross loss | Latent→E40 | Median recovery | Median target visit | Reclaim | E40 after reclaim |
|---|---:|---:|---:|---:|---:|---:|---:|
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | 37 | $521.05 | 16.2% | 158m | 3.0 | 18.9% | 16.2% |
| L1_NEVER_BREAK_TIME | 58 | $369.71 | 39.7% | 305m | 4.0 | 56.9% | 39.7% |
| L2_BREAK_FAST_FAIL_5M | 115 | $176.07 | 53.9% | 95m | 2.0 | 85.2% | 53.9% |
| L4_BREAK_FAIL_30M | 66 | $81.24 | 57.6% | 98m | 2.0 | 87.9% | 57.6% |
| L3_BREAK_FAST_FAIL_10M | 54 | $52.19 | 50.0% | 70m | 2.0 | 88.9% | 50.0% |
| L5_BREAK_FAIL_LATE | 27 | $18.74 | 70.4% | 160m | 2.0 | 100.0% | 70.4% |

## Replicated causal separation

| Snap | Feature | Latent median | True-failure median | Dev gap | Ext gap | RefVal gap | Support same dir |
|---:|---|---:|---:|---:|---:|---:|---:|
| path | mfe_R | 0.173 | 0.154 | 0.019 | 0.030 | 0.053 | 6/4 |
| path | mae_R | 0.178 | 0.236 | -0.058 | -0.005 | -0.032 | 5/4 |
| +5m | close_R | -0.076 | -0.125 | 0.048 | 0.026 | 0.077 | 6/4 |
| +5m | running_mae_R | 0.131 | 0.186 | -0.055 | -0.003 | -0.038 | 4/4 |
| +10m | close_R | -0.063 | -0.160 | 0.096 | 0.084 | 0.048 | 6/4 |
| +10m | running_mfe_R | 0.023 | 0.000 | 0.023 | 0.020 | 0.026 | 6/4 |
| +10m | running_mae_R | 0.150 | 0.214 | -0.064 | -0.011 | -0.029 | 5/4 |
| +15m | close_R | -0.061 | -0.190 | 0.129 | 0.086 | 0.043 | 6/4 |
| +15m | running_mfe_R | 0.047 | 0.000 | 0.047 | 0.052 | 0.041 | 6/4 |
| +15m | running_mae_R | 0.161 | 0.257 | -0.096 | -0.033 | -0.025 | 5/4 |
| +30m | close_R | -0.036 | -0.198 | 0.162 | 0.144 | 0.118 | 6/4 |
| +30m | running_mfe_R | 0.097 | 0.000 | 0.097 | 0.103 | 0.096 | 6/4 |
| +30m | running_mae_R | 0.194 | 0.305 | -0.111 | -0.086 | -0.054 | 6/4 |
| +30m | closes_above_H | 2.000 | 0.000 | 2.000 | 2.000 | 1.000 | 6/4 |
| +30m | closes_le_H | 4.000 | 6.000 | -2.000 | -2.000 | -1.000 | 6/4 |
| +30m | reclaim_by_snapshot | 1.000 | 0.000 | 1.000 | 1.000 | 1.000 | 6/4 |
| +60m | close_R | 0.021 | -0.274 | 0.295 | 0.244 | 0.259 | 6/4 |
| +60m | running_mfe_R | 0.195 | 0.000 | 0.195 | 0.115 | 0.198 | 6/4 |
| +60m | running_mae_R | 0.226 | 0.388 | -0.162 | -0.129 | -0.134 | 6/4 |
| +60m | closes_above_H | 5.000 | 0.000 | 5.000 | 5.000 | 4.000 | 6/4 |

## Decision

Central replicated dimensions: **22**; strong replicated (>=3/4 supports): **22**.

**Status: SOL_LONG_15UTC_LOSS_CONVERSION_A26_SUPPORTED_FOR_A27**

If supported, A27 must convert the replicated anatomy into a small preregistered causal recovery-state family. No threshold grid and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
