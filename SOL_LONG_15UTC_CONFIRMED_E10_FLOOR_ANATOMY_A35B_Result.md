# SOL LONG 15:00 UTC Confirmed E10 Close-Floor Anatomy — A35B Result

Exact A35 DC10_C12 confirmed cohort; anatomy only.

| Role | Partition | N | Winners | Failures | Winner close<=E10 | Failure close<=E10 | Gap | Winner median min close | Failure median min close |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | 27 | 16 | 11 | 6.2% | 100.0% | 93.8% | 0.254R | -0.032R |
| CENTRAL | external | 19 | 10 | 9 | 10.0% | 100.0% | 90.0% | 0.192R | -0.045R |
| CENTRAL | reference_validation | 13 | 8 | 5 | 37.5% | 100.0% | 62.5% | 0.232R | -0.015R |
| CLOCK_SUPPORT | development | 34 | 15 | 19 | 6.7% | 100.0% | 93.3% | 0.197R | -0.032R |
| CLOCK_SUPPORT | external | 18 | 10 | 8 | 0.0% | 100.0% | 100.0% | 0.178R | -0.014R |
| CLOCK_SUPPORT | reference_validation | 21 | 11 | 10 | 27.3% | 100.0% | 72.7% | 0.180R | -0.035R |
| REF_SUPPORT | development | 27 | 13 | 14 | 7.7% | 100.0% | 92.3% | 0.214R | -0.029R |
| REF_SUPPORT | external | 17 | 9 | 8 | 11.1% | 100.0% | 88.9% | 0.172R | -0.070R |
| REF_SUPPORT | reference_validation | 14 | 8 | 6 | 25.0% | 100.0% | 75.0% | 0.232R | -0.035R |

## Decision

- Dev winner violation=6.2%, failure violation=100.0%; Central OOS gaps=90.0%/62.5%; support positive gaps=4/4.

**Status: SOL_LONG_15UTC_CONFIRMED_E10_FLOOR_A35B_SUPPORTED_FOR_A36**

Research only. Live Baba Bot remains unchanged.
