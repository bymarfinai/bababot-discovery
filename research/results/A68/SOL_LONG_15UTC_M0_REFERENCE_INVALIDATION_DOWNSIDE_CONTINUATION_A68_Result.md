# SOL LONG 15:00 UTC M0 Reference-Invalidation Downside-Continuation Anatomy — A68 Result

**Gate status: SOL_LONG_15UTC_M0_REFERENCE_INVALIDATION_DOWNSIDE_CONTINUATION_A68_INCONCLUSIVE**

Raw SOLUSDT 5m coverage: **99.7671%**.

A68 measures only after the M0 invalidating candle is complete. Directional origin is the next 5m bar open; same-bar reversal is prohibited. No TP/SL economics are simulated.

## Reconciliation

| Partition | Parent | Losses | L0/M0 | Winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |

## Causal-origin parity

| Partition | L0/M0 | Parent exit = next-bar origin | Rate |
|---|---:|---:|---:|
| Development | 37 | 37 | 100.0% |
| External Validation | 13 | 13 | 100.0% |
| Reference Validation | 26 | 26 | 100.0% |

## Forward-data coverage

| Partition | Horizon | Eligible | L0/M0 | Coverage |
|---|---:|---:|---:|---:|
| Development | 30m | 37 | 37 | 100.0% |
| Development | 60m | 37 | 37 | 100.0% |
| Development | 120m | 37 | 37 | 100.0% |
| External Validation | 30m | 13 | 13 | 100.0% |
| External Validation | 60m | 13 | 13 | 100.0% |
| External Validation | 120m | 13 | 13 | 100.0% |
| Reference Validation | 30m | 26 | 26 | 100.0% |
| Reference Validation | 60m | 26 | 26 | 100.0% |
| Reference Validation | 120m | 26 | 26 | 100.0% |

## Directional anatomy

| Partition | H | Feature | N | Median | Neutral | Centered | Effect | Dev blocks | Dev pass | OOS pass | Full |
|---|---:|---|---:|---:|---:|---:|---:|---|---|---|---|
| Development | 30m | `short_close_return_R` | 37 | -0.078 | 0.000 | -0.078 | 0.174 | 1/5 | NO | NO | NO |
| Development | 30m | `short_excursion_dominance_R` | 37 | 0.012 | 0.000 | 0.012 | 0.020 | 2/5 | NO | NO | NO |
| Development | 30m | `short_capture_fraction` | 37 | 0.520 | 0.500 | 0.020 | 0.029 | 2/5 | NO | NO | NO |
| Development | 60m | `short_close_return_R` | 37 | -0.087 | 0.000 | -0.087 | 0.192 | 2/5 | NO | NO | NO |
| Development | 60m | `short_excursion_dominance_R` | 37 | -0.074 | 0.000 | -0.074 | 0.108 | 2/5 | NO | NO | NO |
| Development | 60m | `short_capture_fraction` | 37 | 0.386 | 0.500 | -0.114 | 0.164 | 2/5 | NO | NO | NO |
| Development | 120m | `short_close_return_R` | 37 | -0.051 | 0.000 | -0.051 | 0.104 | 2/5 | NO | NO | NO |
| Development | 120m | `short_excursion_dominance_R` | 37 | 0.066 | 0.000 | 0.066 | 0.078 | 2/5 | NO | NO | NO |
| Development | 120m | `short_capture_fraction` | 37 | 0.570 | 0.500 | 0.070 | 0.105 | 2/5 | NO | NO | NO |
| External Validation | 30m | `short_close_return_R` | 13 | -0.057 | 0.000 | -0.057 | 0.387 | - | NO | NO | NO |
| External Validation | 30m | `short_excursion_dominance_R` | 13 | -0.057 | 0.000 | -0.057 | 0.258 | - | NO | NO | NO |
| External Validation | 30m | `short_capture_fraction` | 13 | 0.421 | 0.500 | -0.079 | 0.187 | - | NO | NO | NO |
| External Validation | 60m | `short_close_return_R` | 13 | -0.051 | 0.000 | -0.051 | 0.423 | - | NO | NO | NO |
| External Validation | 60m | `short_excursion_dominance_R` | 13 | -0.154 | 0.000 | -0.154 | 0.558 | - | NO | NO | NO |
| External Validation | 60m | `short_capture_fraction` | 13 | 0.313 | 0.500 | -0.187 | 0.453 | - | NO | NO | NO |
| External Validation | 120m | `short_close_return_R` | 13 | -0.195 | 0.000 | -0.195 | 0.383 | - | NO | NO | NO |
| External Validation | 120m | `short_excursion_dominance_R` | 13 | -0.252 | 0.000 | -0.252 | 0.512 | - | NO | NO | NO |
| External Validation | 120m | `short_capture_fraction` | 13 | 0.348 | 0.500 | -0.152 | 0.342 | - | NO | NO | NO |
| Reference Validation | 30m | `short_close_return_R` | 26 | -0.032 | 0.000 | -0.032 | 0.095 | - | NO | NO | NO |
| Reference Validation | 30m | `short_excursion_dominance_R` | 26 | -0.036 | 0.000 | -0.036 | 0.095 | - | NO | NO | NO |
| Reference Validation | 30m | `short_capture_fraction` | 26 | 0.445 | 0.500 | -0.055 | 0.121 | - | NO | NO | NO |
| Reference Validation | 60m | `short_close_return_R` | 26 | 0.041 | 0.000 | 0.041 | 0.119 | - | NO | NO | NO |
| Reference Validation | 60m | `short_excursion_dominance_R` | 26 | -0.041 | 0.000 | -0.041 | 0.092 | - | NO | NO | NO |
| Reference Validation | 60m | `short_capture_fraction` | 26 | 0.461 | 0.500 | -0.039 | 0.090 | - | NO | NO | NO |
| Reference Validation | 120m | `short_close_return_R` | 26 | 0.222 | 0.000 | 0.222 | 0.500 | - | NO | NO | NO |
| Reference Validation | 120m | `short_excursion_dominance_R` | 26 | 0.031 | 0.000 | 0.031 | 0.054 | - | NO | NO | NO |
| Reference Validation | 120m | `short_capture_fraction` | 26 | 0.507 | 0.500 | 0.007 | 0.018 | - | NO | NO | NO |

## Primary family gate

- `short_close_return_R` primary replicated horizons: []; strict 2-of-2 = NO.
- `short_excursion_dominance_R` primary replicated horizons: []; strict 2-of-2 = NO.
- `short_capture_fraction` corroborative replicated horizons: [].

## Interpretation boundary

Supported means post-invalidation downside continuation replicated from a causal next-bar origin. It does not establish tradable reverse-short economics; stop, target, cost, sizing, leverage, and combined long-plus-short economics require a separate preregistered experiment.

Research only. Live Baba Bot remains unchanged.
