# SOL LONG 15:00 UTC RC30_C2 Rescue Anatomy — A28 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A28 is forensic only and studies the exact A27 RC30_C2 trigger cohort.

## Central Development cohort

| Trigger N | Episode rescues | Recovery-win-not-rescue | Recovery fails | Rescue rate |
|---:|---:|---:|---:|---:|
| 114 | 43 | 1 | 70 | 37.7% |

## Loss-class rescue anatomy

| Loss class | N | Rescue rate | Recovery win rate | Median parent loss | Median signal delay |
|---|---:|---:|---:|---:|---:|
| L5_BREAK_FAIL_LATE | 10 | 50.0% | 50.0% | $0.35 | 18m |
| L3_BREAK_FAST_FAIL_10M | 26 | 38.5% | 38.5% | $0.57 | 15m |
| L4_BREAK_FAIL_30M | 32 | 37.5% | 37.5% | $0.40 | 12m |
| L2_BREAK_FAST_FAIL_5M | 42 | 35.7% | 38.1% | $0.74 | 15m |
| L1_NEVER_BREAK_TIME | 4 | 25.0% | 25.0% | $0.31 | 20m |

## Replicated causal separation

| Feature | Rescue median | Non-rescue median | Dev gap | External gap | RefVal gap | Support same dir |
|---|---:|---:|---:|---:|---:|---:|
| max_close_R_to_signal | 0.109 | 0.071 | 0.038 | 0.026 | 0.055 | 4/4 |
| parent_loss_return | 0.001 | 0.001 | -0.000 | -0.001 | -0.000 | 3/4 |
| running_mfe_R_to_signal | 0.142 | 0.126 | 0.016 | 0.013 | 0.042 | 4/4 |
| signal_body_R | 0.049 | 0.030 | 0.019 | 0.029 | 0.053 | 4/4 |
| signal_close_R | 0.098 | 0.057 | 0.041 | 0.035 | 0.072 | 4/4 |
| signal_close_location | 0.740 | 0.672 | 0.068 | 0.083 | 0.287 | 3/4 |

## Decision

Central replicated=6; strong replicated=6.

**Status: SOL_LONG_15UTC_RC30C2_RESCUE_A28_SUPPORTED_FOR_A29**

If supported, A29 may guard RC30_C2 using at most three robust causal features. No threshold grid and no OOS retuning.

Research only. Live Baba Bot remains unchanged.
