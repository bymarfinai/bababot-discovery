# SOL LONG 15:00 UTC Failure Early-Warning Validation — A52 Result

A52 uses only warning definitions frozen in A51. No new threshold or exit was optimized.

## Reconciliation

A51 source reconciled exactly: **1219 trades / 509 winners / 710 losses**, with M0=76, M1=95, M2=539.

## Development discrimination

| Mechanism | Warning | Bad hit | Winner hit | Gap | Ratio | Blocks | Lead | Candidate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| M0_REFERENCE_INVALIDATION | PRE_L25 | 89.2% | 3.7% | 85.5% | 24.18x | 6/6 | 40m | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_30M | 94.6% | 35.7% | 58.9% | 2.65x | 6/6 | -m | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_60M | 89.2% | 30.7% | 58.5% | 2.90x | 6/6 | -m | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_120M | 78.4% | 23.8% | 54.6% | 3.30x | 6/6 | -m | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_180M | 64.9% | 18.4% | 46.4% | 3.52x | 6/6 | -m | YES |
| M0_REFERENCE_INVALIDATION | PRE_L10 | 40.5% | 1.2% | 39.3% | 32.97x | 6/6 | 10m | no |
| M0_REFERENCE_INVALIDATION | NO_BREAK_240M | 48.6% | 15.6% | 33.1% | 3.12x | 6/6 | -m | no |
| M0_REFERENCE_INVALIDATION | NO_BREAK_360M | 24.3% | 9.8% | 14.5% | 2.47x | 5/6 | -m | no |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_120M | 87.9% | 23.8% | 64.2% | 3.70x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_60M | 94.8% | 30.7% | 64.1% | 3.09x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_30M | 98.3% | 35.7% | 62.6% | 2.76x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_180M | 75.9% | 18.4% | 57.4% | 4.11x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_240M | 72.4% | 15.6% | 56.8% | 4.65x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_360M | 58.6% | 9.8% | 48.8% | 5.96x | 6/6 | -m | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | PRE_L25 | 17.2% | 3.7% | 13.6% | 4.67x | 5/6 | -m | no |
| M1_TIME_NO_STRUCTURAL_FAIL | PRE_L10 | 5.2% | 1.2% | 3.9% | 4.21x | 3/6 | -m | no |
| M2_FAILED_BREAK | POST_H10 | 88.2% | 28.7% | 59.5% | 3.07x | 6/6 | 10m | YES |
| M2_FAILED_BREAK | POST_H05 | 69.5% | 15.2% | 54.3% | 4.58x | 6/6 | 5m | YES |
| M2_FAILED_BREAK | NO_EXT_010R_BY_10M | 34.0% | 0.8% | 33.1% | 41.44x | 6/6 | -m | no |
| M2_FAILED_BREAK | NO_EXT_005R_BY_5M | 9.5% | 0.4% | 9.1% | 23.28x | 6/6 | -m | no |

## OOS confirmation for Development candidates

| Mechanism | Warning | Partition | Bad hit | Winner hit | Gap | Ratio | Replicated |
|---|---|---|---:|---:|---:|---:|---:|
| M2_FAILED_BREAK | POST_H10 | external | 94.9% | 53.9% | 41.0% | 1.76x | YES |
| M2_FAILED_BREAK | POST_H10 | reference_validation | 95.0% | 36.0% | 59.0% | 2.64x | YES |
| M2_FAILED_BREAK | POST_H05 | external | 80.3% | 33.0% | 47.2% | 2.43x | YES |
| M2_FAILED_BREAK | POST_H05 | reference_validation | 75.7% | 21.3% | 54.4% | 3.55x | YES |
| M0_REFERENCE_INVALIDATION | PRE_L25 | external | 100.0% | 3.5% | 96.5% | 28.75x | YES |
| M0_REFERENCE_INVALIDATION | PRE_L25 | reference_validation | 92.3% | 4.0% | 88.3% | 23.08x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_30M | external | 100.0% | 22.6% | 77.4% | 4.42x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_30M | reference_validation | 96.2% | 38.0% | 58.2% | 2.53x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_60M | external | 92.3% | 19.1% | 73.2% | 4.83x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_60M | reference_validation | 88.5% | 32.7% | 55.8% | 2.71x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_120M | external | 92.3% | 13.9% | 78.4% | 6.63x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_120M | reference_validation | 73.1% | 27.3% | 45.7% | 2.67x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_180M | external | 84.6% | 10.4% | 74.2% | 8.11x | YES |
| M0_REFERENCE_INVALIDATION | NO_BREAK_180M | reference_validation | 57.7% | 20.7% | 37.0% | 2.79x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_30M | external | 93.8% | 22.6% | 71.1% | 4.15x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_30M | reference_validation | 95.2% | 38.0% | 57.2% | 2.51x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_60M | external | 87.5% | 19.1% | 68.4% | 4.57x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_60M | reference_validation | 95.2% | 32.7% | 62.6% | 2.92x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_120M | external | 81.2% | 13.9% | 67.3% | 5.84x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_120M | reference_validation | 85.7% | 27.3% | 58.4% | 3.14x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_180M | external | 81.2% | 10.4% | 70.8% | 7.79x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_180M | reference_validation | 76.2% | 20.7% | 55.5% | 3.69x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_240M | external | 75.0% | 10.4% | 64.6% | 7.19x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_240M | reference_validation | 76.2% | 15.3% | 60.9% | 4.97x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_360M | external | 68.8% | 7.0% | 61.8% | 9.88x | YES |
| M1_TIME_NO_STRUCTURAL_FAIL | NO_BREAK_360M | reference_validation | 71.4% | 12.7% | 58.8% | 5.64x | YES |

## M2 primary warning by legacy latency class

| Partition | Class | Warning | N | Hit | Lead |
|---|---|---|---:|---:|---:|
| development | L4_BREAK_FAIL_30M | POST_H10 | 66 | 93.9% | 15m |
| development | L4_BREAK_FAIL_30M | POST_H05 | 66 | 75.8% | 15m |
| development | L2_BREAK_FAST_FAIL_5M | POST_H10 | 115 | 84.3% | 5m |
| development | L2_BREAK_FAST_FAIL_5M | POST_H05 | 115 | 61.7% | 5m |
| development | L3_BREAK_FAST_FAIL_10M | POST_H10 | 54 | 83.3% | 10m |
| development | L3_BREAK_FAST_FAIL_10M | POST_H05 | 54 | 68.5% | 10m |
| development | L5_BREAK_FAIL_LATE | POST_H10 | 27 | 100.0% | 60m |
| development | L5_BREAK_FAIL_LATE | POST_H05 | 27 | 88.9% | 55m |
| external | L4_BREAK_FAIL_30M | POST_H10 | 36 | 97.2% | 15m |
| external | L4_BREAK_FAIL_30M | POST_H05 | 36 | 83.3% | 15m |
| external | L2_BREAK_FAST_FAIL_5M | POST_H10 | 51 | 94.1% | 5m |
| external | L2_BREAK_FAST_FAIL_5M | POST_H05 | 51 | 74.5% | 5m |
| external | L5_BREAK_FAIL_LATE | POST_H10 | 25 | 100.0% | 60m |
| external | L5_BREAK_FAIL_LATE | POST_H05 | 25 | 100.0% | 55m |
| external | L3_BREAK_FAST_FAIL_10M | POST_H10 | 25 | 88.0% | 10m |
| external | L3_BREAK_FAST_FAIL_10M | POST_H05 | 25 | 68.0% | 10m |
| reference_validation | L2_BREAK_FAST_FAIL_5M | POST_H10 | 68 | 92.6% | 5m |
| reference_validation | L2_BREAK_FAST_FAIL_5M | POST_H05 | 68 | 73.5% | 5m |
| reference_validation | L3_BREAK_FAST_FAIL_10M | POST_H10 | 29 | 93.1% | 10m |
| reference_validation | L3_BREAK_FAST_FAIL_10M | POST_H05 | 29 | 72.4% | 10m |
| reference_validation | L5_BREAK_FAIL_LATE | POST_H10 | 12 | 100.0% | 48m |
| reference_validation | L5_BREAK_FAIL_LATE | POST_H05 | 12 | 91.7% | 45m |
| reference_validation | L4_BREAK_FAIL_30M | POST_H10 | 31 | 100.0% | 15m |
| reference_validation | L4_BREAK_FAIL_30M | POST_H05 | 31 | 77.4% | 15m |

## Decision

Replicated fixed warnings: **13**.
Replicated warnings: **M2_FAILED_BREAK/POST_H10, M2_FAILED_BREAK/POST_H05, M0_REFERENCE_INVALIDATION/PRE_L25, M0_REFERENCE_INVALIDATION/NO_BREAK_30M, M0_REFERENCE_INVALIDATION/NO_BREAK_60M, M0_REFERENCE_INVALIDATION/NO_BREAK_120M, M0_REFERENCE_INVALIDATION/NO_BREAK_180M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_30M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_60M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_120M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_180M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_240M, M1_TIME_NO_STRUCTURAL_FAIL/NO_BREAK_360M**.

**Status: SOL_LONG_15UTC_FAILURE_WARNING_A52_SUPPORTED_FOR_A53**

A52 does not authorize an exit change. If supported, A53 must simulate only the replicated warning(s) as causal executable guards against the untouched parent and report raw + 5bps portfolio economics.

Research only. Live Baba Bot remains unchanged.
