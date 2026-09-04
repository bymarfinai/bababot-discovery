# SOL LONG H1 Residual Failure — A5 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A5 is forensic only. Frozen A2 parent and frozen A4 `REC_H2` are unchanged.

## Residual damage after H2 overlay

| Role | Partition | Parent N | Parent losses | H2 eligible | H2 rescues | Residual N | Latent residual | True-failure proxy | Residual loss $ | True-failure share $ | Never-break share $ | Failed-break share $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | 617 | 341 | 216 | 54 | 287 | 130 | 157 | $1380.23 | 73.5% | 70.3% | 29.7% |
| CENTRAL | external | 273 | 174 | 125 | 30 | 144 | 66 | 78 | $920.85 | 74.1% | 52.4% | 47.6% |
| CENTRAL | reference_validation | 317 | 198 | 139 | 35 | 163 | 67 | 96 | $588.64 | 79.4% | 67.0% | 33.0% |
| CLOCK_SUPPORT | external | 284 | 181 | 134 | 35 | 146 | 68 | 78 | $945.36 | 72.6% | 50.8% | 49.2% |
| CLOCK_SUPPORT | reference_validation | 316 | 185 | 129 | 27 | 158 | 67 | 91 | $460.47 | 78.2% | 62.3% | 37.7% |
| REF_SUPPORT | external | 300 | 180 | 127 | 31 | 149 | 70 | 79 | $1014.66 | 73.9% | 56.7% | 43.3% |
| REF_SUPPORT | reference_validation | 349 | 201 | 150 | 45 | 156 | 73 | 83 | $569.15 | 74.2% | 64.9% | 35.1% |

## Central Development residual loss classes

| Original loss class | Residual label | N | Gross loss $ | Median loss | Q90 loss | H2 eligible |
|---|---|---:|---:|---:|---:|---:|
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | RESIDUAL_TRUE_FAILURE_PROXY | 30 | $455.65 | $13.97 | $21.69 | 3.3% |
| L1_NEVER_BREAK_TIME | RESIDUAL_TRUE_FAILURE_PROXY | 36 | $304.22 | $8.37 | $15.86 | 13.9% |
| L2_BREAK_FAST_FAIL_5M | RESIDUAL_TRUE_FAILURE_PROXY | 39 | $122.04 | $1.45 | $5.00 | 66.7% |
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | RESIDUAL_LATENT_RECOVERABLE | 7 | $106.92 | $10.84 | $26.67 | 71.4% |
| L1_NEVER_BREAK_TIME | RESIDUAL_LATENT_RECOVERABLE | 21 | $103.47 | $3.49 | $9.82 | 19.0% |
| L2_BREAK_FAST_FAIL_5M | RESIDUAL_LATENT_RECOVERABLE | 53 | $84.58 | $1.38 | $3.01 | 86.8% |
| L4_BREAK_FAIL_30M | RESIDUAL_TRUE_FAILURE_PROXY | 19 | $56.76 | $1.27 | $7.85 | 52.6% |
| L5_BREAK_FAIL_LATE | RESIDUAL_TRUE_FAILURE_PROXY | 14 | $38.45 | $1.58 | $3.09 | 78.6% |
| L3_BREAK_FAST_FAIL_10M | RESIDUAL_TRUE_FAILURE_PROXY | 19 | $36.97 | $1.45 | $3.29 | 73.7% |
| L4_BREAK_FAIL_30M | RESIDUAL_LATENT_RECOVERABLE | 25 | $36.37 | $1.39 | $2.59 | 84.0% |
| L3_BREAK_FAST_FAIL_10M | RESIDUAL_LATENT_RECOVERABLE | 14 | $23.47 | $1.08 | $3.12 | 78.6% |
| L5_BREAK_FAIL_LATE | RESIDUAL_LATENT_RECOVERABLE | 10 | $11.33 | $0.71 | $1.94 | 80.0% |

## Strongest Central Development causal separations (descriptive)

Positive `good - true` means the non-true-failure group has the larger value; negative means the true-failure proxy has the larger value.

| Attempt | Snapshot | Feature | Good N | True N | Good median | True median | Good-True | IQR-scaled gap |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| H2 | +60m | break_confirmed_by_snapshot | 38 | 33 | 1.000 | 0.000 | 1.000 | 1.00 |
| H2 | +30m | break_confirmed_by_snapshot | 77 | 46 | 1.000 | 0.000 | 1.000 | 1.00 |
| H2 | +10m | break_confirmed_by_snapshot | 147 | 66 | 1.000 | 0.000 | 1.000 | 1.00 |
| H2 | +30m | closes_le_H | 77 | 46 | 3.000 | 6.000 | -3.000 | 0.60 |
| H2 | +30m | closes_above_H | 77 | 46 | 3.000 | 0.000 | 3.000 | 0.60 |
| PARENT | +5m | closes_above_H | 460 | 157 | 0.500 | 0.000 | 0.500 | 0.50 |
| H2 | +15m | closes_le_H | 141 | 66 | 1.000 | 2.000 | -1.000 | 0.50 |
| H2 | +60m | closes_above_H | 38 | 33 | 5.000 | 0.000 | 5.000 | 0.50 |
| H2 | +60m | closes_le_H | 38 | 33 | 7.000 | 12.000 | -5.000 | 0.50 |
| PARENT | +5m | closes_le_H | 460 | 157 | 0.500 | 1.000 | -0.500 | 0.50 |
| PARENT | +5m | break_confirmed_by_snapshot | 460 | 157 | 0.500 | 0.000 | 0.500 | 0.50 |
| H2 | +10m | closes_above_H | 147 | 66 | 1.000 | 0.000 | 1.000 | 0.50 |
| H2 | +15m | closes_above_H | 141 | 66 | 2.000 | 1.000 | 1.000 | 0.50 |
| H2 | +10m | closes_le_H | 147 | 66 | 1.000 | 2.000 | -1.000 | 0.50 |
| H2 | +30m | running_mfe_R | 77 | 46 | 0.136 | 0.057 | 0.079 | 0.47 |
| H2 | +60m | running_mfe_R | 38 | 33 | 0.171 | 0.058 | 0.113 | 0.47 |
| H2 | +10m | running_mfe_R | 147 | 66 | 0.082 | 0.043 | 0.039 | 0.41 |
| H2 | +15m | running_mfe_R | 141 | 66 | 0.103 | 0.057 | 0.046 | 0.39 |

## A5 decision

- Central Development residual N: **287**.
- True-failure proxy N: **157**.
- True-failure proxy share of residual gross-loss dollars: **73.5%**.
- Decision reason: **Residual true-failure damage is material and causal separation is visible**.

**Status: SOL_LONG_H1_RESIDUAL_FAILURE_A5_SUPPORTED_FOR_A6**

A5 does not authorize a trading change. If supported, A6 must preregister a small early-invalidation family using Development quantiles only, then freeze it before OOS evaluation.

Research only. Live Baba Bot remains unchanged.
