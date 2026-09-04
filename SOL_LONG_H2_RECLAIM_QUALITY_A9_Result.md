# SOL LONG H2 Reclaim Quality — A9 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A9 is forensic only. A8 remains rejected; no trading rule is changed.

## Reclaim persistence anatomy

| Role | Partition | Class | N | Reclaimed | Median consecutive >H | Q75 consecutive >H | Median failure time | Median max close | E40 before first failure | E40 eventual | Median cycles |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | RESIDUAL_LATENT_RECOVERABLE | 95 | 93 | 9.0 | 64.0 | 20m | 0.205R | 44.1% | 96.8% | 3.0 |
| CENTRAL | development | RESIDUAL_TRUE_FAILURE_PROXY | 67 | 42 | 2.0 | 4.0 | 10m | 0.056R | 0.0% | 0.0% | 3.0 |
| CENTRAL | external | RESIDUAL_TRUE_FAILURE_PROXY | 44 | 25 | 2.0 | 8.0 | 10m | 0.053R | 0.0% | 0.0% | 3.0 |
| CENTRAL | external | RESIDUAL_LATENT_RECOVERABLE | 51 | 51 | 3.0 | 20.5 | 15m | 0.099R | 39.2% | 96.1% | 3.0 |
| CENTRAL | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 51 | 51 | 3.0 | 13.0 | 10m | 0.107R | 33.3% | 100.0% | 3.0 |
| CENTRAL | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 53 | 35 | 3.0 | 10.0 | 15m | 0.086R | 0.0% | 0.0% | 3.0 |
| CLOCK_SUPPORT | external | RESIDUAL_TRUE_FAILURE_PROXY | 48 | 27 | 2.0 | 7.0 | 10m | 0.039R | 0.0% | 0.0% | 3.0 |
| CLOCK_SUPPORT | external | RESIDUAL_LATENT_RECOVERABLE | 51 | 51 | 6.0 | 47.0 | 22m | 0.237R | 43.1% | 98.0% | 3.0 |
| CLOCK_SUPPORT | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 51 | 51 | 4.0 | 34.0 | 15m | 0.104R | 37.3% | 98.0% | 4.0 |
| CLOCK_SUPPORT | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 51 | 37 | 2.0 | 7.0 | 10m | 0.049R | 0.0% | 0.0% | 3.0 |
| REF_SUPPORT | external | RESIDUAL_TRUE_FAILURE_PROXY | 43 | 24 | 2.0 | 7.2 | 10m | 0.065R | 0.0% | 0.0% | 3.0 |
| REF_SUPPORT | external | RESIDUAL_LATENT_RECOVERABLE | 53 | 52 | 5.0 | 20.2 | 12m | 0.125R | 44.2% | 92.3% | 3.0 |
| REF_SUPPORT | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 57 | 57 | 5.0 | 46.0 | 20m | 0.154R | 38.6% | 100.0% | 3.0 |
| REF_SUPPORT | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 48 | 27 | 2.0 | 4.0 | 10m | 0.051R | 0.0% | 0.0% | 3.0 |

## Central Development fixed post-reclaim separations

| Snapshot | Feature | Latent N | True N | Latent | True | Gap |
|---:|---|---:|---:|---:|---:|---:|
| +60m | closes_above_H | 92 | 41 | 12.000 | 4.000 | 8.000 |
| +30m | closes_above_H | 93 | 41 | 7.000 | 3.000 | 4.000 |
| +15m | closes_above_H | 93 | 41 | 4.000 | 2.000 | 2.000 |
| +10m | closes_above_H | 93 | 41 | 3.000 | 2.000 | 1.000 |
| +60m | fraction_closes_above_H | 92 | 41 | 0.923 | 0.308 | 0.615 |
| +30m | fraction_closes_above_H | 93 | 41 | 1.000 | 0.429 | 0.571 |
| +15m | fraction_closes_above_H | 93 | 41 | 1.000 | 0.500 | 0.500 |
| +15m | E10_by_snapshot | 93 | 41 | 0.839 | 0.439 | 0.400 |
| +10m | E10_by_snapshot | 93 | 41 | 0.806 | 0.415 | 0.392 |
| +30m | E20_by_snapshot | 93 | 41 | 0.613 | 0.244 | 0.369 |
| +60m | E20_by_snapshot | 92 | 41 | 0.707 | 0.341 | 0.365 |
| +15m | E20_by_snapshot | 93 | 41 | 0.484 | 0.146 | 0.338 |
| +10m | fraction_closes_above_H | 93 | 41 | 1.000 | 0.667 | 0.333 |
| +5m | E10_by_snapshot | 93 | 41 | 0.688 | 0.366 | 0.322 |
| +30m | E10_by_snapshot | 93 | 41 | 0.860 | 0.561 | 0.299 |
| +60m | E10_by_snapshot | 92 | 41 | 0.902 | 0.610 | 0.292 |
| +10m | E20_by_snapshot | 93 | 41 | 0.387 | 0.122 | 0.265 |
| +60m | close_R | 92 | 41 | 0.155 | -0.033 | 0.188 |
| +5m | E20_by_snapshot | 93 | 41 | 0.258 | 0.073 | 0.185 |
| +60m | running_mfe_R | 92 | 41 | 0.309 | 0.140 | 0.169 |

## Replicated candidate dimensions

| Snapshot | Feature | Dev gap | External gap | RefVal gap |
|---:|---|---:|---:|---:|
| +5m | close_R | 0.054 | 0.036 | 0.020 |
| +5m | running_mfe_R | 0.062 | 0.055 | 0.035 |
| +5m | E10_by_snapshot | 0.322 | 0.230 | 0.196 |
| +5m | E20_by_snapshot | 0.185 | 0.235 | 0.189 |
| +10m | close_R | 0.080 | 0.034 | 0.011 |
| +10m | running_mfe_R | 0.102 | 0.050 | 0.028 |
| +10m | E10_by_snapshot | 0.392 | 0.208 | 0.256 |
| +10m | E20_by_snapshot | 0.265 | 0.293 | 0.239 |
| +15m | close_R | 0.117 | 0.037 | 0.018 |
| +15m | running_mfe_R | 0.102 | 0.045 | 0.086 |
| +15m | E10_by_snapshot | 0.400 | 0.227 | 0.201 |
| +15m | E20_by_snapshot | 0.338 | 0.333 | 0.317 |
| +30m | close_R | 0.138 | 0.082 | 0.040 |
| +30m | running_mfe_R | 0.142 | 0.084 | 0.093 |
| +30m | closes_above_H | 4.000 | 2.000 | 1.500 |
| +30m | fraction_closes_above_H | 0.571 | 0.286 | 0.214 |
| +30m | E10_by_snapshot | 0.299 | 0.264 | 0.157 |
| +30m | E20_by_snapshot | 0.369 | 0.410 | 0.304 |
| +60m | close_R | 0.188 | 0.158 | 0.137 |
| +60m | running_mfe_R | 0.169 | 0.259 | 0.164 |
| +60m | closes_above_H | 8.000 | 5.000 | 3.000 |
| +60m | fraction_closes_above_H | 0.615 | 0.385 | 0.231 |
| +60m | E10_by_snapshot | 0.292 | 0.223 | 0.157 |
| +60m | E20_by_snapshot | 0.365 | 0.328 | 0.392 |

## Decision

- 24 fixed snapshot persistence comparisons replicate latent>true across both central OOS cells.

**Status: SOL_LONG_H2_RECLAIM_QUALITY_A9_SUPPORTED_FOR_A10**

If supported, A10 may preregister only a small persistence-confirmed re-entry family derived from rounded Central Development state counts/quantiles. A8 RC30 itself stays rejected.

Research only. Live Baba Bot remains unchanged.
