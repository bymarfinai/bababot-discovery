# SOL LONG E20 Continuation vs Staller Anatomy — A13 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A13 is forensic only. The supported strategy remains A2 parent + A4 REC_H2; rejected A6/A8/A10/A11/A12 remain absent.

## E20 cohort anatomy

| Role | Partition | Component | Outcome | N | Median entry→E20 | Median break→E20 | Median E20 close | Median close vs E20 | Median MAE to E20 | Median closes >H |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | POOLED | E20_TO_E40_CONTINUATION | 305 | 10m | 5m | 0.219R | 0.019R | 0.209R | 2.0 |
| CENTRAL | development | POOLED | E20_STALLER | 166 | 10m | 5m | 0.165R | -0.035R | 0.150R | 2.0 |
| CENTRAL | external | POOLED | E20_STALLER | 82 | 10m | 5m | 0.187R | -0.013R | 0.140R | 2.0 |
| CENTRAL | external | POOLED | E20_TO_E40_CONTINUATION | 128 | 12m | 5m | 0.211R | 0.011R | 0.146R | 2.0 |
| CENTRAL | reference_validation | POOLED | E20_TO_E40_CONTINUATION | 152 | 10m | 5m | 0.223R | 0.023R | 0.181R | 2.0 |
| CENTRAL | reference_validation | POOLED | E20_STALLER | 90 | 10m | 5m | 0.161R | -0.039R | 0.153R | 2.0 |
| CLOCK_SUPPORT | external | POOLED | E20_TO_E40_CONTINUATION | 133 | 15m | 5m | 0.216R | 0.016R | 0.164R | 3.0 |
| CLOCK_SUPPORT | external | POOLED | E20_STALLER | 86 | 10m | 5m | 0.173R | -0.027R | 0.136R | 2.0 |
| CLOCK_SUPPORT | reference_validation | POOLED | E20_STALLER | 102 | 5m | 5m | 0.150R | -0.050R | 0.160R | 2.0 |
| CLOCK_SUPPORT | reference_validation | POOLED | E20_TO_E40_CONTINUATION | 147 | 10m | 5m | 0.228R | 0.028R | 0.174R | 2.0 |
| REF_SUPPORT | external | POOLED | E20_TO_E40_CONTINUATION | 148 | 10m | 5m | 0.231R | 0.031R | 0.192R | 2.0 |
| REF_SUPPORT | external | POOLED | E20_STALLER | 89 | 10m | 5m | 0.182R | -0.018R | 0.141R | 2.0 |
| REF_SUPPORT | reference_validation | POOLED | E20_TO_E40_CONTINUATION | 189 | 10m | 5m | 0.226R | 0.026R | 0.191R | 2.0 |
| REF_SUPPORT | reference_validation | POOLED | E20_STALLER | 90 | 8m | 5m | 0.157R | -0.043R | 0.158R | 2.0 |

## Largest Central Development fixed separations

| Stage | Snapshot | Feature | Cont N | Stall N | Continuation | Staller | Gap | Meaningful |
|---|---:|---|---:|---:|---:|---:|---:|---|
| SNAPSHOT | +60m | closes_ge_E20 | 43 | 50 | 2.000 | 1.000 | 1.000 | YES |
| SNAPSHOT | +10m | closes_ge_E20 | 123 | 127 | 1.000 | 0.000 | 1.000 | YES |
| SNAPSHOT | +5m | closes_ge_E20 | 159 | 152 | 1.000 | 0.000 | 1.000 | YES |
| SNAPSHOT | +5m | fraction_closes_ge_E20 | 159 | 152 | 0.500 | 0.000 | 0.500 | YES |
| SNAPSHOT | +5m | closed_back_le_E10 | 305 | 166 | 0.148 | 0.482 | -0.334 | YES |
| SNAPSHOT | +10m | fraction_closes_ge_E20 | 123 | 127 | 0.333 | 0.000 | 0.333 | YES |
| SNAPSHOT | +10m | closed_back_le_E10 | 305 | 166 | 0.174 | 0.488 | -0.314 | YES |
| SNAPSHOT | +30m | closed_back_le_E10 | 305 | 166 | 0.154 | 0.398 | -0.243 | YES |
| SNAPSHOT | +15m | closed_back_le_E10 | 305 | 166 | 0.157 | 0.398 | -0.240 | YES |
| SNAPSHOT | +10m | E25_by_snapshot | 305 | 166 | 0.298 | 0.500 | -0.202 | YES |
| SNAPSHOT | +10m | closed_back_le_H | 305 | 166 | 0.052 | 0.241 | -0.189 | YES |
| SNAPSHOT | +30m | E25_by_snapshot | 305 | 166 | 0.174 | 0.361 | -0.188 | YES |
| SNAPSHOT | +15m | E25_by_snapshot | 305 | 166 | 0.249 | 0.434 | -0.185 | YES |
| SNAPSHOT | +5m | closed_back_le_H | 305 | 166 | 0.033 | 0.211 | -0.178 | YES |
| SNAPSHOT | +5m | E25_by_snapshot | 305 | 166 | 0.364 | 0.524 | -0.160 | YES |
| SNAPSHOT | +60m | closed_back_le_E10 | 305 | 166 | 0.125 | 0.265 | -0.140 | YES |
| SNAPSHOT | +10m | close_R | 123 | 127 | 0.185 | 0.066 | 0.119 | YES |
| SNAPSHOT | +10m | close_vs_E20_R | 123 | 127 | -0.015 | -0.134 | 0.119 | YES |
| SNAPSHOT | +15m | closed_back_le_H | 305 | 166 | 0.052 | 0.163 | -0.110 | YES |
| SNAPSHOT | +60m | E25_by_snapshot | 305 | 166 | 0.115 | 0.217 | -0.102 | YES |
| SNAPSHOT | +30m | closed_back_le_H | 305 | 166 | 0.066 | 0.157 | -0.091 | NO |
| SNAPSHOT | +60m | closed_back_le_H | 305 | 166 | 0.072 | 0.157 | -0.084 | NO |
| SNAPSHOT | +15m | close_R | 99 | 102 | 0.174 | 0.090 | 0.084 | YES |
| SNAPSHOT | +15m | close_vs_E20_R | 99 | 102 | -0.026 | -0.110 | 0.084 | YES |

## Replicated A14 candidate dimensions

| Stage | Snapshot | Feature | Dev gap | External gap | RefVal gap | Support same/reversed |
|---|---:|---|---:|---:|---:|---:|
| ANCHOR | +0m | e20_bar_close_R | 0.054 | 0.024 | 0.062 | 4/0 |
| ANCHOR | +0m | e20_bar_close_vs_E20_R | 0.054 | 0.024 | 0.062 | 4/0 |
| ANCHOR | +0m | running_mae_R_to_E20 | 0.059 | 0.006 | 0.028 | 4/0 |
| SNAPSHOT | +5m | E25_by_snapshot | -0.160 | -0.067 | -0.187 | 4/0 |
| SNAPSHOT | +5m | close_R | 0.068 | 0.099 | 0.060 | 4/0 |
| SNAPSHOT | +5m | close_vs_E20_R | 0.068 | 0.099 | 0.060 | 4/0 |
| SNAPSHOT | +5m | closed_back_le_E10 | -0.334 | -0.358 | -0.340 | 4/0 |
| SNAPSHOT | +5m | closed_back_le_H | -0.178 | -0.082 | -0.065 | 4/0 |
| SNAPSHOT | +5m | post_e20_giveback_from_peak_R | -0.056 | -0.080 | -0.054 | 4/0 |
| SNAPSHOT | +5m | post_e20_peak_R | 0.036 | 0.020 | 0.011 | 4/0 |
| SNAPSHOT | +10m | E25_by_snapshot | -0.202 | -0.078 | -0.211 | 4/0 |
| SNAPSHOT | +10m | close_R | 0.119 | 0.137 | 0.087 | 4/0 |
| SNAPSHOT | +10m | close_vs_E20_R | 0.119 | 0.137 | 0.087 | 4/0 |
| SNAPSHOT | +10m | closed_back_le_E10 | -0.314 | -0.365 | -0.404 | 4/0 |
| SNAPSHOT | +10m | closed_back_le_H | -0.189 | -0.172 | -0.070 | 4/0 |
| SNAPSHOT | +10m | post_e20_giveback_from_peak_R | -0.046 | -0.092 | -0.048 | 4/0 |
| SNAPSHOT | +15m | E25_by_snapshot | -0.185 | -0.065 | -0.219 | 4/0 |
| SNAPSHOT | +15m | close_R | 0.084 | 0.134 | 0.122 | 4/0 |
| SNAPSHOT | +15m | close_vs_E20_R | 0.084 | 0.134 | 0.122 | 4/0 |
| SNAPSHOT | +15m | closed_back_le_E10 | -0.240 | -0.272 | -0.365 | 4/0 |
| SNAPSHOT | +15m | closed_back_le_H | -0.110 | -0.074 | -0.185 | 4/0 |
| SNAPSHOT | +15m | post_e20_giveback_from_peak_R | -0.031 | -0.089 | -0.081 | 4/0 |
| SNAPSHOT | +30m | E25_by_snapshot | -0.188 | -0.065 | -0.109 | 4/0 |
| SNAPSHOT | +30m | close_R | 0.064 | 0.146 | 0.136 | 4/0 |
| SNAPSHOT | +30m | close_vs_E20_R | 0.064 | 0.146 | 0.136 | 4/0 |
| SNAPSHOT | +30m | closed_back_le_E10 | -0.243 | -0.173 | -0.131 | 4/0 |
| SNAPSHOT | +30m | post_e20_giveback_from_peak_R | -0.031 | -0.052 | -0.083 | 4/0 |
| SNAPSHOT | +60m | E25_by_snapshot | -0.102 | -0.034 | -0.031 | 4/0 |
| SNAPSHOT | +60m | close_R | 0.075 | 0.107 | 0.128 | 3/1 |
| SNAPSHOT | +60m | close_vs_E20_R | 0.075 | 0.107 | 0.128 | 3/1 |
| SNAPSHOT | +60m | closed_back_le_E10 | -0.140 | -0.066 | -0.026 | 4/0 |
| SNAPSHOT | +60m | closes_ge_E20 | 1.000 | 2.000 | 1.000 | 2/1 |
| SNAPSHOT | +60m | post_e20_giveback_from_peak_R | -0.043 | -0.007 | -0.053 | 2/2 |

## Decision

- 33 Development-meaningful fixed E20 dimensions replicate across both central OOS cells without broad support contradiction.

**Status: SOL_LONG_E20_CONTINUATION_A13_SUPPORTED_FOR_A14**

If supported, A14 may preregister only a small conditional protection family derived from rounded Central Development quantiles/discrete states. Clean continuation must remain eligible for E40.

Research only. Live Baba Bot remains unchanged.
