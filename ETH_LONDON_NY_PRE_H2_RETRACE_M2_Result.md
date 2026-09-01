# ETH London -> New York Pre-H2 Retrace — M2 Result

ETH raw 5m coverage: **100.0000%**.

Frozen structure: **London 08:00-13:30 UTC -> New York 13:30-20:00 UTC · LONG K1 OPP0 · causal leave · pre-H2 only**.

- Reused M1 ETH K1 identities: **382**; parity: **PASS**.
- Causal/geometry audit: **PASS**.

## Structural retracement grid

| Partition | Level | Setups | Clean windows | Fills | Fill/clean | H2 hits | H2 hit/fill | Median fill->H2 | Median MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | F95 | 120 | 79 | 36 | 45.6% | 34 | 94.4% | 15.0m | 0.116R |
| external | F90 | 120 | 79 | 56 | 70.9% | 47 | 83.9% | 20.0m | 0.166R |
| external | F85 | 120 | 79 | 56 | 70.9% | 46 | 82.1% | 27.5m | 0.156R |
| external | F80 | 120 | 79 | 45 | 57.0% | 34 | 75.6% | 40.0m | 0.225R |
| external | F75 | 120 | 79 | 42 | 53.2% | 31 | 73.8% | 40.0m | 0.211R |
| development | F95 | 173 | 121 | 43 | 35.5% | 37 | 86.0% | 10.0m | 0.175R |
| development | F90 | 173 | 121 | 65 | 53.7% | 55 | 84.6% | 20.0m | 0.216R |
| development | F85 | 173 | 121 | 70 | 57.9% | 58 | 82.9% | 25.0m | 0.216R |
| development | F80 | 173 | 121 | 69 | 57.0% | 54 | 78.3% | 30.0m | 0.180R |
| development | F75 | 173 | 121 | 65 | 53.7% | 48 | 73.8% | 35.0m | 0.223R |
| reference_validation | F95 | 85 | 50 | 19 | 38.0% | 15 | 78.9% | 20.0m | 0.282R |
| reference_validation | F90 | 85 | 50 | 30 | 60.0% | 24 | 80.0% | 20.0m | 0.303R |
| reference_validation | F85 | 85 | 50 | 34 | 68.0% | 26 | 76.5% | 20.0m | 0.303R |
| reference_validation | F80 | 85 | 50 | 35 | 70.0% | 26 | 74.3% | 20.0m | 0.274R |
| reference_validation | F75 | 85 | 50 | 31 | 62.0% | 22 | 71.0% | 20.0m | 0.335R |
| august | F95 | 4 | 3 | 1 | 33.3% | 0 | 0.0% | -m | 0.832R |
| august | F90 | 4 | 3 | 1 | 33.3% | 0 | 0.0% | -m | 0.782R |
| august | F85 | 4 | 3 | 1 | 33.3% | 0 | 0.0% | -m | 0.732R |
| august | F80 | 4 | 3 | 2 | 66.7% | 1 | 50.0% | 5.0m | 0.372R |
| august | F75 | 4 | 3 | 2 | 66.7% | 1 | 50.0% | 5.0m | 0.322R |
| POOLED_MAJOR | F95 | 378 | 250 | 98 | 39.2% | 86 | 87.8% | 15.0m | 0.171R |
| POOLED_MAJOR | F90 | 378 | 250 | 151 | 60.4% | 126 | 83.4% | 20.0m | 0.211R |
| POOLED_MAJOR | F85 | 378 | 250 | 160 | 64.0% | 130 | 81.2% | 25.0m | 0.213R |
| POOLED_MAJOR | F80 | 378 | 250 | 149 | 59.6% | 114 | 76.5% | 30.0m | 0.217R |
| POOLED_MAJOR | F75 | 378 | 250 | 138 | 55.2% | 101 | 73.2% | 35.0m | 0.226R |

## Frozen discovery screen

- F95: **NO**
- F90: **SCREEN_PASS**
- F85: **SCREEN_PASS**
- F80: **SCREEN_PASS**
- F75: **SCREEN_PASS**

**Supported family: F90, F85, F80, F75.**

No max-rate level is selected. Multiple passing levels remain a family; no intermediate fraction sweep is allowed here.

## Decision

**Status: ETH_LONDON_NY_M2_RETRACE_FAMILY_SUPPORTED**

- M2 contains no TP/SL/PF/PnL/runner/fee/slippage/portfolio optimization.
- Historical data are already inspected; this is structural calibration evidence, not pristine OOS promotion.
