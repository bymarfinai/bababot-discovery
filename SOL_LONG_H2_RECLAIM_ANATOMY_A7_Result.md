# SOL LONG H2 Reclaim Anatomy — A7 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A7 is forensic only. It studies what happens after the frozen H2 recovery exits.

## Reclaim anatomy

| Role | Partition | Episode class | N | Post-exit reclaim | Median reclaim | E40 after exit | E40 after causal reclaim | Reclaim→E40 median | Median adverse before reclaim |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | RESIDUAL_LATENT_RECOVERABLE | 95 | 97.9% | 10m | 94.7% | 94.7% | 72m | 0.110R |
| CENTRAL | development | RESIDUAL_TRUE_FAILURE_PROXY | 67 | 62.7% | 12m | 0.0% | 0.0% | -m | 0.137R |
| CENTRAL | external | RESIDUAL_TRUE_FAILURE_PROXY | 44 | 56.8% | 5m | 0.0% | 0.0% | -m | 0.106R |
| CENTRAL | external | RESIDUAL_LATENT_RECOVERABLE | 51 | 100.0% | 10m | 96.1% | 94.1% | 95m | 0.141R |
| CENTRAL | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 51 | 100.0% | 5m | 100.0% | 100.0% | 110m | 0.125R |
| CENTRAL | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 53 | 66.0% | 5m | 0.0% | 0.0% | -m | 0.077R |
| CLOCK_SUPPORT | external | RESIDUAL_TRUE_FAILURE_PROXY | 48 | 56.2% | 5m | 0.0% | 0.0% | -m | 0.117R |
| CLOCK_SUPPORT | external | RESIDUAL_LATENT_RECOVERABLE | 51 | 100.0% | 10m | 98.0% | 96.1% | 70m | 0.142R |
| CLOCK_SUPPORT | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 51 | 100.0% | 5m | 98.0% | 98.0% | 90m | 0.095R |
| CLOCK_SUPPORT | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 51 | 72.5% | 5m | 0.0% | 0.0% | -m | 0.087R |
| REF_SUPPORT | external | RESIDUAL_TRUE_FAILURE_PROXY | 43 | 55.8% | 5m | 0.0% | 0.0% | -m | 0.096R |
| REF_SUPPORT | external | RESIDUAL_LATENT_RECOVERABLE | 53 | 98.1% | 15m | 90.6% | 90.6% | 45m | 0.175R |
| REF_SUPPORT | reference_validation | RESIDUAL_LATENT_RECOVERABLE | 57 | 100.0% | 5m | 100.0% | 100.0% | 80m | 0.125R |
| REF_SUPPORT | reference_validation | RESIDUAL_TRUE_FAILURE_PROXY | 48 | 56.2% | 5m | 0.0% | 0.0% | -m | 0.080R |

## Central Development post-H2-exit snapshots

| Class | Snapshot | N | Reclaimed | Median close | Median MFE | Median MAE |
|---|---:|---:|---:|---:|---:|---:|
| RESIDUAL_LATENT_RECOVERABLE | +5m | 95 | 40.0% | -0.016R | 0.017R | 0.100R |
| RESIDUAL_TRUE_FAILURE_PROXY | +5m | 67 | 19.4% | -0.069R | 0.000R | 0.098R |
| RESIDUAL_LATENT_RECOVERABLE | +10m | 94 | 48.9% | -0.029R | 0.027R | 0.101R |
| RESIDUAL_TRUE_FAILURE_PROXY | +10m | 63 | 28.6% | -0.074R | 0.000R | 0.134R |
| RESIDUAL_LATENT_RECOVERABLE | +15m | 94 | 58.5% | -0.011R | 0.046R | 0.107R |
| RESIDUAL_TRUE_FAILURE_PROXY | +15m | 63 | 31.7% | -0.084R | 0.006R | 0.141R |
| RESIDUAL_LATENT_RECOVERABLE | +30m | 94 | 70.2% | 0.020R | 0.145R | 0.135R |
| RESIDUAL_TRUE_FAILURE_PROXY | +30m | 62 | 43.5% | -0.105R | 0.022R | 0.192R |
| RESIDUAL_LATENT_RECOVERABLE | +60m | 94 | 85.1% | 0.072R | 0.219R | 0.166R |
| RESIDUAL_TRUE_FAILURE_PROXY | +60m | 61 | 52.5% | -0.132R | 0.038R | 0.235R |

## Decision

- Development reclaim gap=35.2%; External gap=43.2%; RefVal gap=34.0%.

**Status: SOL_LONG_H2_RECLAIM_ANATOMY_A7_SUPPORTED_FOR_REENTRY**

If supported, the next stage may test a reclaim-confirmed next-open re-entry. It may not substitute a resting H3/H4 retry.

Research only. Live Baba Bot remains unchanged.
