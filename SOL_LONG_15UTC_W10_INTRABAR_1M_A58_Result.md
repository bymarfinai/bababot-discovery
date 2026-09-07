# SOL LONG 15:00 UTC W10 Intrabar 1m Decomposition — A58 Result

Frozen SOL 5m source coverage: **99.7671%**.

A58 conditionally decomposes the first W10 5m warning candle into completed 1m states K1–K4. Cohort membership is future-known within the 5m candle, so any supported motif requires A59 live-opportunity revalidation before execution.

## Reconciliation and 1m feasibility

Frozen W10 rows: **676**. 1m state rows: **2704**. Duplicate used 1m rows: **0**. Fetch errors: **0**.

| Partition | W10 | 5x1m available | Availability | OHLC parity | Parity rate |
|---|---:|---:|---:|---:|---:|
| development | 300 | 300 | 100.0% | 300 | 100.0% |
| external | 192 | 192 | 100.0% | 192 | 100.0% |
| reference_validation | 184 | 184 | 100.0% | 184 | 100.0% |

## Replicated conditional 1m motifs

| K | Motif | Dev fail/target | Gap | Ratio | External fail/target | Gap | RefVal fail/target | Gap |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| - | No motif passed Development + both OOS gates | - | - | - | - | - | - | - |

## Strongest Development binary motifs

| K | Motif | Fail hit | Target hit | Gap | Ratio | Blocks | Dev supported | Replicated |
|---:|---|---:|---:|---:|---:|---:|---|---|
| K4 | ANY_CLOSE_LE_H_BY_K | 76.0% | 65.1% | 10.9pp | 1.17x | 5/6 | False | False |
| K3 | ANY_CLOSE_LE_H_BY_K | 73.8% | 63.5% | 10.3pp | 1.16x | 5/6 | False | False |
| K4 | NO_HIGH_ABOVE_H10_BY_K | 57.9% | 47.6% | 10.3pp | 1.22x | 4/6 | False | False |
| K4 | TWO_PLUS_NEAR_H05_BY_K | 29.2% | 19.0% | 10.1pp | 1.53x | 6/6 | False | False |
| K3 | TWO_PLUS_NEAR_H10_BY_K | 30.5% | 20.6% | 9.8pp | 1.48x | 6/6 | False | False |
| K3 | H_LOSS_THEN_RECLAIM_BY_K | 31.8% | 22.2% | 9.5pp | 1.43x | 5/6 | False | False |
| K2 | NO_HIGH_ABOVE_H10_BY_K | 73.0% | 63.5% | 9.5pp | 1.15x | 4/6 | False | False |
| K4 | CURRENT_CLOSE_LE_H | 30.0% | 20.6% | 9.4pp | 1.46x | 5/6 | False | False |
| K4 | NO_CLOSE_ABOVE_H10_BY_K | 76.8% | 68.3% | 8.6pp | 1.13x | 4/6 | False | False |
| K3 | TWO_PLUS_NEAR_H05_BY_K | 14.6% | 6.3% | 8.2pp | 2.30x | 5/6 | False | False |
| K4 | CURRENT_BEARISH | 42.9% | 34.9% | 8.0pp | 1.23x | 3/6 | False | False |
| K3 | NO_CLOSE_ABOVE_H10_BY_K | 79.4% | 71.4% | 8.0pp | 1.11x | 5/6 | False | False |
| K2 | NO_CLOSE_ABOVE_H10_BY_K | 84.1% | 76.2% | 7.9pp | 1.10x | 6/6 | False | False |
| K1 | ANY_CLOSE_LE_H_BY_K | 68.2% | 60.3% | 7.9pp | 1.13x | 5/6 | False | False |
| K1 | CURRENT_CLOSE_LE_H | 68.2% | 60.3% | 7.9pp | 1.13x | 5/6 | False | False |
| K2 | ANY_CLOSE_LE_H_BY_K | 70.8% | 63.5% | 7.3pp | 1.12x | 5/6 | False | False |
| K4 | LAST2_LOWER_CLOSES | 41.2% | 34.9% | 6.3pp | 1.18x | 3/6 | False | False |
| K3 | NO_HIGH_ABOVE_H10_BY_K | 63.1% | 57.1% | 5.9pp | 1.10x | 3/6 | False | False |

## Report-only continuous path anatomy

| Partition | K | Feature | Fail median | E40 median | Gap |
|---|---:|---|---:|---:|---:|
| development | K1 | latest_close_H_R | -0.037 | -0.033 | -0.005 |
| development | K1 | cum_max_high_H_R | -0.015 | -0.007 | -0.008 |
| development | K1 | cum_min_low_H_R | -0.088 | -0.086 | -0.002 |
| development | K1 | cum_rejection_R | 0.019 | 0.036 | -0.016 |
| development | K2 | latest_close_H_R | -0.008 | -0.011 | 0.002 |
| development | K2 | cum_max_high_H_R | 0.019 | 0.048 | -0.028 |
| development | K2 | cum_min_low_H_R | -0.094 | -0.096 | 0.002 |
| development | K2 | cum_rejection_R | 0.030 | 0.037 | -0.006 |
| development | K3 | latest_close_H_R | 0.017 | 0.016 | 0.001 |
| development | K3 | cum_max_high_H_R | 0.060 | 0.081 | -0.021 |
| development | K3 | cum_min_low_H_R | -0.094 | -0.097 | 0.003 |
| development | K3 | cum_rejection_R | 0.042 | 0.050 | -0.007 |
| development | K4 | latest_close_H_R | 0.025 | 0.047 | -0.022 |
| development | K4 | cum_max_high_H_R | 0.076 | 0.105 | -0.029 |
| development | K4 | cum_min_low_H_R | -0.094 | -0.097 | 0.003 |
| development | K4 | cum_rejection_R | 0.046 | 0.055 | -0.009 |
| external | K1 | latest_close_H_R | -0.034 | -0.017 | -0.018 |
| external | K1 | cum_max_high_H_R | -0.015 | 0.004 | -0.020 |
| external | K1 | cum_min_low_H_R | -0.069 | -0.069 | -0.000 |
| external | K1 | cum_rejection_R | 0.016 | 0.019 | -0.003 |
| external | K2 | latest_close_H_R | -0.019 | -0.023 | 0.004 |
| external | K2 | cum_max_high_H_R | 0.007 | 0.028 | -0.021 |
| external | K2 | cum_min_low_H_R | -0.077 | -0.075 | -0.002 |
| external | K2 | cum_rejection_R | 0.018 | 0.029 | -0.011 |
| external | K3 | latest_close_H_R | 0.005 | 0.004 | 0.001 |
| external | K3 | cum_max_high_H_R | 0.030 | 0.046 | -0.016 |
| external | K3 | cum_min_low_H_R | -0.077 | -0.080 | 0.003 |
| external | K3 | cum_rejection_R | 0.025 | 0.023 | 0.002 |
| external | K4 | latest_close_H_R | 0.024 | 0.035 | -0.011 |
| external | K4 | cum_max_high_H_R | 0.056 | 0.071 | -0.014 |
| external | K4 | cum_min_low_H_R | -0.080 | -0.082 | 0.002 |
| external | K4 | cum_rejection_R | 0.022 | 0.036 | -0.014 |
| reference_validation | K1 | latest_close_H_R | -0.034 | -0.059 | 0.026 |
| reference_validation | K1 | cum_max_high_H_R | -0.007 | -0.039 | 0.032 |
| reference_validation | K1 | cum_min_low_H_R | -0.079 | -0.101 | 0.022 |
| reference_validation | K1 | cum_rejection_R | 0.026 | 0.023 | 0.003 |
| reference_validation | K2 | latest_close_H_R | -0.013 | -0.038 | 0.025 |
| reference_validation | K2 | cum_max_high_H_R | 0.021 | -0.013 | 0.034 |
| reference_validation | K2 | cum_min_low_H_R | -0.089 | -0.114 | 0.025 |
| reference_validation | K2 | cum_rejection_R | 0.035 | 0.034 | 0.000 |
| reference_validation | K3 | latest_close_H_R | 0.010 | -0.030 | 0.040 |
| reference_validation | K3 | cum_max_high_H_R | 0.051 | 0.011 | 0.040 |
| reference_validation | K3 | cum_min_low_H_R | -0.091 | -0.114 | 0.023 |
| reference_validation | K3 | cum_rejection_R | 0.040 | 0.051 | -0.012 |
| reference_validation | K4 | latest_close_H_R | 0.020 | 0.013 | 0.007 |
| reference_validation | K4 | cum_max_high_H_R | 0.077 | 0.044 | 0.033 |
| reference_validation | K4 | cum_min_low_H_R | -0.092 | -0.118 | 0.026 |
| reference_validation | K4 | cum_rejection_R | 0.039 | 0.046 | -0.008 |

## Decision

**Status: SOL_LONG_15UTC_W10_INTRABAR_1M_A58_INCONCLUSIVE**

Research only. Live Baba Bot remains unchanged.
