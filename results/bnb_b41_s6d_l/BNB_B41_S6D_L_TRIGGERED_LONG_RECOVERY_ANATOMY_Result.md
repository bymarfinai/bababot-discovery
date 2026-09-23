# BNB B41-S6D-L — Triggered LONG Recovery Anatomy

**Status: BNB_B41_S6D_L_RECOVERY_MECHANISM_CANDIDATE_FOUND**

S6D-L signature: `fc4ec7581c282e2f61f578df00ace715451381b92d15c82453d56f369e33281a`

Cohort is frozen to R4_60_2OF3_Q85 alarms only. REF has only two false-stop winners, so REF is directional/descriptive rather than a promotion gate.

## DEV mechanism candidates

| After alarm | Feature | Kind | DEV strength | REF strength | REF direction consistent |
|---:|---|---|---:|---:|---|
| 15m | mfe_from_alarm | CONT | 0.708 | 0.375 | NO |
| 15m | no_new_low_after_alarm | BINARY | 66.7% | 25.0% | YES |
| 30m | close_above_alarm | BINARY | 41.7% | 12.5% | YES |
| 30m | close_break_pre15_high | BINARY | 54.2% | -25.0% | NO |
| 30m | mfe_from_alarm | CONT | 0.771 | 0.375 | NO |
| 30m | no_new_low_after_alarm | BINARY | 50.0% | 37.5% | YES |
| 45m | close_progress | CONT | 0.812 | 0.500 | NO |
| 45m | close_reclaim_wall | BINARY | 58.3% | 87.5% | YES |
| 45m | mfe_from_alarm | CONT | 0.708 | 0.438 | NO |
| 45m | no_new_low_after_alarm | BINARY | 50.0% | 37.5% | YES |
| 45m | recovery_ratio | CONT | 0.792 | 0.500 | NO |
| 45m | up_slope_3 | CONT | 0.833 | 0.500 | NO |
| 60m | close_break_pre15_high | BINARY | 54.2% | -25.0% | NO |
| 60m | close_progress | CONT | 0.979 | 0.750 | YES |
| 60m | close_reclaim_entry | BINARY | 66.7% | 0.0% | NO |
| 60m | close_reclaim_wall | BINARY | 58.3% | 37.5% | YES |
| 60m | mae_from_alarm | CONT | 0.708 | 0.375 | NO |
| 60m | mfe_from_alarm | CONT | 0.854 | 0.500 | NO |
| 60m | no_new_low_after_alarm | BINARY | 50.0% | -12.5% | NO |
| 60m | recovery_ratio | CONT | 0.979 | 0.562 | YES |
| 60m | touch_reclaim_entry | BINARY | 58.3% | 50.0% | YES |
| 60m | up_slope_3 | CONT | 0.979 | 0.625 | YES |

## Stable mechanism candidates

| After alarm | Feature | Kind | DEV | REF |
|---:|---|---|---:|---:|
| 15m | no_new_low_after_alarm | BINARY | 66.7% | 25.0% |
| 30m | close_above_alarm | BINARY | 41.7% | 12.5% |
| 30m | no_new_low_after_alarm | BINARY | 50.0% | 37.5% |
| 45m | close_reclaim_wall | BINARY | 58.3% | 87.5% |
| 45m | no_new_low_after_alarm | BINARY | 50.0% | 37.5% |
| 60m | close_progress | CONT | 0.979 | 0.750 |
| 60m | close_reclaim_wall | BINARY | 58.3% | 37.5% |
| 60m | recovery_ratio | CONT | 0.979 | 0.562 |
| 60m | touch_reclaim_entry | BINARY | 58.3% | 50.0% |
| 60m | up_slope_3 | CONT | 0.979 | 0.625 |

## Full cohort effects

| Period | After alarm | Feature | Kind | False-winner | True-loser | Recovery AUC / gap |
|---|---:|---|---|---:|---:|---:|
| DEV | 15m | close_progress | CONT | -0.017 | -0.049 | 0.542 |
| DEV | 15m | mfe_from_alarm | CONT | 0.100 | 0.053 | 0.708 |
| DEV | 15m | recovery_ratio | CONT | -0.033 | -0.333 | 0.625 |
| DEV | 15m | up_slope_3 | CONT | -0.049 | -0.008 | 0.458 |
| DEV | 15m | mae_from_alarm | CONT | 0.102 | 0.140 | 0.667 |
| DEV | 15m | close_above_alarm | BINARY | 50.0% | 37.5% | 12.5% |
| DEV | 15m | touch_reclaim_entry | BINARY | 16.7% | 0.0% | 16.7% |
| DEV | 15m | close_reclaim_entry | BINARY | 0.0% | 0.0% | 0.0% |
| DEV | 15m | touch_reclaim_wall | BINARY | 50.0% | 37.5% | 12.5% |
| DEV | 15m | close_reclaim_wall | BINARY | 33.3% | 37.5% | -4.2% |
| DEV | 15m | close_break_pre15_high | BINARY | 50.0% | 12.5% | 37.5% |
| DEV | 15m | no_new_low_after_alarm | BINARY | 66.7% | 0.0% | 66.7% |
| REF | 15m | close_progress | CONT | -0.061 | -0.007 | 0.500 |
| REF | 15m | mfe_from_alarm | CONT | 0.075 | 0.078 | 0.375 |
| REF | 15m | recovery_ratio | CONT | -0.099 | -0.017 | 0.500 |
| REF | 15m | up_slope_3 | CONT | -0.051 | -0.036 | 0.438 |
| REF | 15m | mae_from_alarm | CONT | 0.207 | 0.086 | 0.188 |
| REF | 15m | close_above_alarm | BINARY | 50.0% | 50.0% | 0.0% |
| REF | 15m | touch_reclaim_entry | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 15m | close_reclaim_entry | BINARY | 0.0% | 0.0% | 0.0% |
| REF | 15m | touch_reclaim_wall | BINARY | 100.0% | 62.5% | 37.5% |
| REF | 15m | close_reclaim_wall | BINARY | 100.0% | 12.5% | 87.5% |
| REF | 15m | close_break_pre15_high | BINARY | 0.0% | 12.5% | -12.5% |
| REF | 15m | no_new_low_after_alarm | BINARY | 50.0% | 25.0% | 25.0% |
| DEV | 30m | close_progress | CONT | 0.072 | -0.091 | 0.583 |
| DEV | 30m | mfe_from_alarm | CONT | 0.180 | 0.053 | 0.771 |
| DEV | 30m | recovery_ratio | CONT | 0.339 | -0.582 | 0.688 |
| DEV | 30m | up_slope_3 | CONT | 0.069 | -0.030 | 0.688 |
| DEV | 30m | mae_from_alarm | CONT | 0.149 | 0.159 | 0.646 |
| DEV | 30m | close_above_alarm | BINARY | 66.7% | 25.0% | 41.7% |
| DEV | 30m | touch_reclaim_entry | BINARY | 33.3% | 12.5% | 20.8% |
| DEV | 30m | close_reclaim_entry | BINARY | 16.7% | 12.5% | 4.2% |
| DEV | 30m | touch_reclaim_wall | BINARY | 83.3% | 37.5% | 45.8% |
| DEV | 30m | close_reclaim_wall | BINARY | 83.3% | 37.5% | 45.8% |
| DEV | 30m | close_break_pre15_high | BINARY | 66.7% | 12.5% | 54.2% |
| DEV | 30m | no_new_low_after_alarm | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 30m | close_progress | CONT | -0.059 | -0.103 | 0.562 |
| REF | 30m | mfe_from_alarm | CONT | 0.075 | 0.101 | 0.375 |
| REF | 30m | recovery_ratio | CONT | -0.208 | -0.327 | 0.562 |
| REF | 30m | up_slope_3 | CONT | 0.002 | -0.004 | 0.688 |
| REF | 30m | mae_from_alarm | CONT | 0.234 | 0.197 | 0.375 |
| REF | 30m | close_above_alarm | BINARY | 50.0% | 37.5% | 12.5% |
| REF | 30m | touch_reclaim_entry | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 30m | close_reclaim_entry | BINARY | 0.0% | 0.0% | 0.0% |
| REF | 30m | touch_reclaim_wall | BINARY | 100.0% | 62.5% | 37.5% |
| REF | 30m | close_reclaim_wall | BINARY | 100.0% | 12.5% | 87.5% |
| REF | 30m | close_break_pre15_high | BINARY | 0.0% | 25.0% | -25.0% |
| REF | 30m | no_new_low_after_alarm | BINARY | 50.0% | 12.5% | 37.5% |
| DEV | 45m | close_progress | CONT | 0.186 | -0.113 | 0.812 |
| DEV | 45m | mfe_from_alarm | CONT | 0.212 | 0.129 | 0.708 |
| DEV | 45m | recovery_ratio | CONT | 0.635 | -0.565 | 0.792 |
| DEV | 45m | up_slope_3 | CONT | 0.131 | -0.044 | 0.833 |
| DEV | 45m | mae_from_alarm | CONT | 0.149 | 0.212 | 0.667 |
| DEV | 45m | close_above_alarm | BINARY | 100.0% | 37.5% | 62.5% |
| DEV | 45m | touch_reclaim_entry | BINARY | 33.3% | 25.0% | 8.3% |
| DEV | 45m | close_reclaim_entry | BINARY | 33.3% | 0.0% | 33.3% |
| DEV | 45m | touch_reclaim_wall | BINARY | 83.3% | 37.5% | 45.8% |
| DEV | 45m | close_reclaim_wall | BINARY | 83.3% | 25.0% | 58.3% |
| DEV | 45m | close_break_pre15_high | BINARY | 66.7% | 37.5% | 29.2% |
| DEV | 45m | no_new_low_after_alarm | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 45m | close_progress | CONT | -0.129 | -0.149 | 0.500 |
| REF | 45m | mfe_from_alarm | CONT | 0.094 | 0.112 | 0.438 |
| REF | 45m | recovery_ratio | CONT | -0.388 | -0.486 | 0.500 |
| REF | 45m | up_slope_3 | CONT | -0.070 | -0.029 | 0.500 |
| REF | 45m | mae_from_alarm | CONT | 0.332 | 0.235 | 0.312 |
| REF | 45m | close_above_alarm | BINARY | 50.0% | 25.0% | 25.0% |
| REF | 45m | touch_reclaim_entry | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 45m | close_reclaim_entry | BINARY | 0.0% | 0.0% | 0.0% |
| REF | 45m | touch_reclaim_wall | BINARY | 100.0% | 62.5% | 37.5% |
| REF | 45m | close_reclaim_wall | BINARY | 100.0% | 12.5% | 87.5% |
| REF | 45m | close_break_pre15_high | BINARY | 0.0% | 25.0% | -25.0% |
| REF | 45m | no_new_low_after_alarm | BINARY | 50.0% | 12.5% | 37.5% |
| DEV | 60m | close_progress | CONT | 0.302 | -0.276 | 0.979 |
| DEV | 60m | mfe_from_alarm | CONT | 0.318 | 0.129 | 0.854 |
| DEV | 60m | recovery_ratio | CONT | 1.191 | -1.225 | 0.979 |
| DEV | 60m | up_slope_3 | CONT | 0.071 | -0.104 | 0.979 |
| DEV | 60m | mae_from_alarm | CONT | 0.149 | 0.356 | 0.708 |
| DEV | 60m | close_above_alarm | BINARY | 100.0% | 37.5% | 62.5% |
| DEV | 60m | touch_reclaim_entry | BINARY | 83.3% | 25.0% | 58.3% |
| DEV | 60m | close_reclaim_entry | BINARY | 66.7% | 0.0% | 66.7% |
| DEV | 60m | touch_reclaim_wall | BINARY | 83.3% | 37.5% | 45.8% |
| DEV | 60m | close_reclaim_wall | BINARY | 83.3% | 25.0% | 58.3% |
| DEV | 60m | close_break_pre15_high | BINARY | 66.7% | 12.5% | 54.2% |
| DEV | 60m | no_new_low_after_alarm | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 60m | close_progress | CONT | -0.004 | -0.130 | 0.750 |
| REF | 60m | mfe_from_alarm | CONT | 0.111 | 0.112 | 0.500 |
| REF | 60m | recovery_ratio | CONT | -0.165 | -0.414 | 0.562 |
| REF | 60m | up_slope_3 | CONT | 0.125 | 0.019 | 0.625 |
| REF | 60m | mae_from_alarm | CONT | 0.352 | 0.270 | 0.375 |
| REF | 60m | close_above_alarm | BINARY | 50.0% | 25.0% | 25.0% |
| REF | 60m | touch_reclaim_entry | BINARY | 50.0% | 0.0% | 50.0% |
| REF | 60m | close_reclaim_entry | BINARY | 0.0% | 0.0% | 0.0% |
| REF | 60m | touch_reclaim_wall | BINARY | 100.0% | 62.5% | 37.5% |
| REF | 60m | close_reclaim_wall | BINARY | 50.0% | 12.5% | 37.5% |
| REF | 60m | close_break_pre15_high | BINARY | 0.0% | 25.0% | -25.0% |
| REF | 60m | no_new_low_after_alarm | BINARY | 0.0% | 12.5% | -12.5% |

## Gate
- DEV mechanism candidates: **22**.
- REF-directionally-consistent candidates: **10**.
- Next step: **S6E-L preregistered recovery-test rule construction**.

No exit rule, EMA/Fibonacci, TP, WR optimization, PF, expectancy, leverage, or PnL optimization.
