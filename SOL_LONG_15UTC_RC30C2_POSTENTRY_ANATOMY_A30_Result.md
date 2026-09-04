# SOL LONG 15:00 UTC RC30_C2 Post-Entry Anatomy — A30 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A30 is forensic only. It explains the payoff failure of the otherwise WR-improving RC30_C2 mechanism.

## Central Development outcomes

| Outcome | N | Episode rescue | Entry R | Reward/H-risk | MFE after entry | MAE after entry | Parent loss | Required episode-BE exit R | Hold | E10 hit | E20 hit | E30 hit | E40 hit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| REC_TARGET | 44 | 97.7% | 0.099R | 3.00 | 0.378R | 0.064R | $0.59 | 0.146R | 12m | 100.0% | 100.0% | 100.0% | 100.0% |
| REC_FAIL | 70 | 0.0% | 0.058R | 5.88 | 0.073R | 0.160R | $0.55 | 0.086R | 20m | 60.0% | 34.3% | 11.4% | 0.0% |

## RC30_C2 failures: lower target conversion opportunity

| Level | Failure touch rate | Failure episode-rescue-if-hit rate |
|---|---:|---:|
| E10 | 60.0% | 24.3% |
| E20 | 34.3% | 24.3% |
| E30 | 11.4% | 11.4% |
| E40 | 0.0% | 0.0% |

## Central-OOS replicated winner vs failure separation

| Snapshot | Feature | Winner median | Failure median | Dev gap | External gap | RefVal gap |
|---|---|---:|---:|---:|---:|---:|
| entry/path | entry_R | 0.099 | 0.058 | 0.041 | 0.039 | 0.072 |
| entry/path | mae_from_entry_R | 0.064 | 0.160 | -0.097 | -0.126 | -0.068 |
| entry/path | mfe_from_entry_R | 0.378 | 0.073 | 0.306 | 0.281 | 0.327 |
| entry/path | remaining_E40_R | 0.301 | 0.342 | -0.041 | -0.039 | -0.072 |
| entry/path | required_exit_R_to_episode_be | 0.146 | 0.086 | 0.060 | 0.054 | 0.063 |
| entry/path | reward_to_Hrisk | 3.000 | 5.883 | -2.883 | -3.437 | -3.600 |
| entry/path | risk_to_H_R | 0.099 | 0.058 | 0.041 | 0.039 | 0.072 |
| +5m | close_R | 0.163 | 0.036 | 0.128 | 0.109 | 0.122 |
| +5m | running_mae_from_entry_R | 0.045 | 0.069 | -0.025 | -0.024 | -0.022 |
| +5m | running_mfe_from_entry_R | 0.117 | 0.046 | 0.071 | 0.027 | 0.055 |
| +10m | close_R | 0.200 | 0.031 | 0.169 | 0.230 | 0.260 |
| +10m | running_mae_from_entry_R | 0.050 | 0.096 | -0.046 | -0.041 | -0.052 |
| +10m | running_mfe_from_entry_R | 0.174 | 0.059 | 0.116 | 0.141 | 0.135 |
| +15m | close_R | 0.250 | 0.018 | 0.231 | 0.164 | 0.188 |
| +15m | closes_above_H | 3.000 | 2.000 | 1.000 | 1.000 | 1.000 |
| +15m | closes_le_H | 0.000 | 1.000 | -1.000 | -1.000 | -1.000 |
| +15m | running_mae_from_entry_R | 0.073 | 0.122 | -0.049 | -0.049 | -0.045 |
| +15m | running_mfe_from_entry_R | 0.185 | 0.066 | 0.119 | 0.155 | 0.119 |

## Decision

Anatomy-indicated next route: **TARGET**.

**Status: SOL_LONG_15UTC_RC30C2_POSTENTRY_A30_SUPPORTED_FOR_A31**

A31 may test only the fixed intervention family directly indicated above. No threshold grid or OOS retuning.

Research only. Live Baba Bot remains unchanged.
