# SOL LONG E10-Fail Trigger Anatomy — A15 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A15 is forensic only. It studies actual A14 CP_E10_5_FULL intervention triggers; no trade rule is changed.

## Trigger cohorts

| Role | Partition | Component | Outcome | N | Entry→E20 | E20 close | Trigger close | Trigger low | Peak→close giveback | MFE to trigger |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | PARENT | TRIGGERED_TRUE_STALLER | 46 | 10m | 0.118R | 0.045R | -0.015R | 0.221R | 0.244R |
| CENTRAL | development | PARENT | TRIGGERED_E40_RECOVERY | 30 | 30m | 0.138R | 0.033R | -0.004R | 0.224R | 0.264R |
| CENTRAL | external | PARENT | TRIGGERED_TRUE_STALLER | 23 | 5m | 0.156R | 0.034R | -0.007R | 0.193R | 0.232R |
| CENTRAL | external | PARENT | TRIGGERED_E40_RECOVERY | 12 | 15m | 0.137R | 0.082R | 0.036R | 0.168R | 0.237R |
| CENTRAL | reference_validation | PARENT | TRIGGERED_TRUE_STALLER | 24 | 5m | 0.132R | 0.051R | 0.017R | 0.203R | 0.255R |
| CENTRAL | reference_validation | PARENT | TRIGGERED_E40_RECOVERY | 14 | 35m | 0.064R | 0.045R | -0.022R | 0.232R | 0.238R |
| CLOCK_SUPPORT | external | PARENT | TRIGGERED_TRUE_STALLER | 19 | 10m | 0.126R | 0.030R | -0.012R | 0.201R | 0.248R |
| CLOCK_SUPPORT | external | PARENT | TRIGGERED_E40_RECOVERY | 8 | 10m | 0.158R | 0.039R | 0.020R | 0.195R | 0.235R |
| CLOCK_SUPPORT | reference_validation | PARENT | TRIGGERED_TRUE_STALLER | 28 | 5m | 0.118R | 0.069R | 0.022R | 0.191R | 0.233R |
| CLOCK_SUPPORT | reference_validation | PARENT | TRIGGERED_E40_RECOVERY | 14 | 15m | 0.117R | 0.055R | 0.019R | 0.189R | 0.232R |
| REF_SUPPORT | external | PARENT | TRIGGERED_E40_RECOVERY | 15 | 15m | 0.132R | 0.074R | 0.025R | 0.190R | 0.245R |
| REF_SUPPORT | external | PARENT | TRIGGERED_TRUE_STALLER | 22 | 5m | 0.155R | 0.030R | -0.013R | 0.219R | 0.231R |
| REF_SUPPORT | reference_validation | PARENT | TRIGGERED_E40_RECOVERY | 18 | 18m | 0.083R | 0.005R | -0.044R | 0.278R | 0.245R |
| REF_SUPPORT | reference_validation | PARENT | TRIGGERED_TRUE_STALLER | 28 | 5m | 0.121R | 0.058R | 0.017R | 0.204R | 0.259R |
| CENTRAL | development | REC_H2 | TRIGGERED_TRUE_STALLER | 5 | 10m | 0.146R | 0.075R | 0.051R | 0.173R | 0.229R |
| CENTRAL | development | REC_H2 | TRIGGERED_E40_RECOVERY | 1 | 0m | -0.048R | -0.280R | -0.396R | 0.626R | 0.346R |
| CENTRAL | external | REC_H2 | TRIGGERED_TRUE_STALLER | 8 | 20m | 0.173R | 0.058R | 0.023R | 0.197R | 0.235R |
| CENTRAL | external | REC_H2 | TRIGGERED_E40_RECOVERY | 1 | 10m | 0.203R | 0.089R | 0.047R | 0.135R | 0.225R |
| CENTRAL | reference_validation | REC_H2 | TRIGGERED_TRUE_STALLER | 9 | 50m | 0.150R | 0.065R | 0.039R | 0.158R | 0.219R |
| CENTRAL | reference_validation | REC_H2 | TRIGGERED_E40_RECOVERY | 3 | 5m | 0.156R | 0.077R | 0.013R | 0.175R | 0.212R |
| CLOCK_SUPPORT | external | REC_H2 | TRIGGERED_TRUE_STALLER | 8 | 10m | 0.149R | 0.064R | 0.036R | 0.168R | 0.229R |
| CLOCK_SUPPORT | external | REC_H2 | TRIGGERED_E40_RECOVERY | 2 | 140m | 0.195R | 0.076R | 0.067R | 0.211R | 0.287R |
| CLOCK_SUPPORT | reference_validation | REC_H2 | TRIGGERED_TRUE_STALLER | 5 | 20m | 0.119R | 0.087R | 0.048R | 0.135R | 0.226R |
| CLOCK_SUPPORT | reference_validation | REC_H2 | TRIGGERED_E40_RECOVERY | 2 | 2m | 0.127R | 0.048R | 0.011R | 0.180R | 0.228R |
| REF_SUPPORT | external | REC_H2 | TRIGGERED_TRUE_STALLER | 10 | 5m | 0.136R | 0.044R | -0.024R | 0.197R | 0.227R |
| REF_SUPPORT | external | REC_H2 | TRIGGERED_E40_RECOVERY | 1 | 20m | 0.116R | 0.032R | -0.063R | 0.175R | 0.207R |
| REF_SUPPORT | reference_validation | REC_H2 | TRIGGERED_TRUE_STALLER | 5 | 45m | 0.150R | 0.052R | 0.039R | 0.195R | 0.247R |
| REF_SUPPORT | reference_validation | REC_H2 | TRIGGERED_E40_RECOVERY | 1 | 60m | 0.156R | 0.077R | 0.013R | 0.125R | 0.202R |
| CENTRAL | development | POOLED | TRIGGERED_TRUE_STALLER | 51 | 10m | 0.128R | 0.048R | 0.003R | 0.213R | 0.243R |
| CENTRAL | development | POOLED | TRIGGERED_E40_RECOVERY | 31 | 25m | 0.137R | 0.033R | -0.005R | 0.225R | 0.265R |
| CENTRAL | external | POOLED | TRIGGERED_TRUE_STALLER | 31 | 5m | 0.156R | 0.047R | -0.004R | 0.196R | 0.232R |
| CENTRAL | external | POOLED | TRIGGERED_E40_RECOVERY | 13 | 15m | 0.142R | 0.082R | 0.040R | 0.165R | 0.229R |
| CENTRAL | reference_validation | POOLED | TRIGGERED_TRUE_STALLER | 33 | 5m | 0.133R | 0.052R | 0.018R | 0.198R | 0.245R |
| CENTRAL | reference_validation | POOLED | TRIGGERED_E40_RECOVERY | 17 | 25m | 0.075R | 0.050R | 0.000R | 0.190R | 0.238R |
| CLOCK_SUPPORT | external | POOLED | TRIGGERED_TRUE_STALLER | 27 | 10m | 0.133R | 0.046R | -0.004R | 0.197R | 0.244R |
| CLOCK_SUPPORT | external | POOLED | TRIGGERED_E40_RECOVERY | 10 | 15m | 0.166R | 0.058R | 0.039R | 0.205R | 0.241R |
| CLOCK_SUPPORT | reference_validation | POOLED | TRIGGERED_TRUE_STALLER | 33 | 5m | 0.119R | 0.069R | 0.038R | 0.174R | 0.232R |
| CLOCK_SUPPORT | reference_validation | POOLED | TRIGGERED_E40_RECOVERY | 16 | 10m | 0.117R | 0.055R | 0.019R | 0.189R | 0.232R |
| REF_SUPPORT | external | POOLED | TRIGGERED_E40_RECOVERY | 16 | 18m | 0.124R | 0.067R | 0.013R | 0.183R | 0.245R |
| REF_SUPPORT | external | POOLED | TRIGGERED_TRUE_STALLER | 32 | 5m | 0.139R | 0.032R | -0.013R | 0.200R | 0.231R |
| REF_SUPPORT | reference_validation | POOLED | TRIGGERED_E40_RECOVERY | 19 | 25m | 0.091R | 0.046R | -0.029R | 0.275R | 0.244R |
| REF_SUPPORT | reference_validation | POOLED | TRIGGERED_TRUE_STALLER | 33 | 5m | 0.131R | 0.056R | 0.020R | 0.203R | 0.255R |

## Central Development trigger-time separations

| Feature | Recovery N | Staller N | Recovery | Staller | Gap | Material |
|---|---:|---:|---:|---:|---:|---|
| entry_to_e20_min | 31 | 51 | 25.000 | 10.000 | 15.000 | YES |
| break_to_e20_min | 31 | 51 | 0.000 | 5.000 | -5.000 | YES |
| closes_gt_H_to_e20 | 31 | 51 | 1.000 | 2.000 | -1.000 | YES |
| running_mae_R_to_e20 | 31 | 51 | 0.322 | 0.226 | 0.095 | YES |
| trigger_traded_E30 | 31 | 51 | 0.097 | 0.039 | 0.058 | NO |
| trigger_body_R | 31 | 51 | 0.124 | 0.092 | 0.032 | YES |
| trigger_traded_E25 | 31 | 51 | 0.161 | 0.137 | 0.024 | NO |
| post_e20_peak_R | 31 | 51 | 0.265 | 0.243 | 0.022 | NO |
| running_mfe_R_to_trigger | 31 | 51 | 0.265 | 0.243 | 0.022 | NO |
| trigger_close_vs_E10_R | 31 | 51 | -0.067 | -0.052 | -0.016 | NO |
| trigger_close_R | 31 | 51 | 0.033 | 0.048 | -0.016 | NO |
| trigger_lower_wick_R | 31 | 51 | 0.051 | 0.037 | 0.014 | NO |
| giveback_peak_to_trigger_close_R | 31 | 51 | 0.225 | 0.213 | 0.012 | NO |
| e20_bar_close_R | 31 | 51 | 0.137 | 0.128 | 0.010 | NO |
| e20_bar_close_vs_E20_R | 31 | 51 | -0.063 | -0.072 | 0.010 | NO |
| trigger_low_R | 31 | 51 | -0.005 | 0.003 | -0.008 | NO |
| trigger_upper_wick_R | 31 | 51 | 0.042 | 0.034 | 0.008 | NO |
| trigger_high_R | 31 | 51 | 0.178 | 0.172 | 0.006 | NO |

## Replicated A16 guard dimensions

| Feature | Dev gap | External gap | RefVal gap | Support same/reversed |
|---|---:|---:|---:|---:|
| entry_to_e20_min | 15.000 | 10.000 | 20.000 | 4/0 |
| running_mae_R_to_e20 | 0.095 | 0.023 | 0.110 | 4/0 |

## Decision

- 2 trigger-time features replicate for an A16 guard.

**Status: SOL_LONG_E10_FAIL_TRIGGER_A15_SUPPORTED_FOR_A16**

If supported, A16 may test only a tiny false-positive guard derived from rounded Central Development quantiles/state values. OOS cannot choose the guard.

Research only. Live Baba Bot remains unchanged.
