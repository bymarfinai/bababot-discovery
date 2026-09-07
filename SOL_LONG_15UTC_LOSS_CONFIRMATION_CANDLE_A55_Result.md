# SOL LONG 15:00 UTC Loss Confirmation Candle Anatomy — A55 Result

A55 compares fixed pre-terminal completed candles with deterministic same-age, same-state eventual-positive parent controls. No exit is changed and no continuous threshold is scanned.

Raw SOLUSDT 5m coverage: **99.7671%**.

## Matched snapshot coverage

| Part | Mechanism | Lead | Loss N | Eligible | Matched | Match/eligible | Unique controls | Max reuse |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| development | M2_FAILED_BREAK | 15m | 262 | 93 | 89 | 95.7% | 55 | 7 |
| development | M2_FAILED_BREAK | 10m | 262 | 147 | 143 | 97.3% | 69 | 7 |
| development | M2_FAILED_BREAK | 5m | 262 | 262 | 258 | 98.5% | 95 | 10 |
| development | M0_REFERENCE_INVALIDATION | 15m | 37 | 35 | 35 | 100.0% | 25 | 6 |
| development | M0_REFERENCE_INVALIDATION | 10m | 37 | 37 | 37 | 100.0% | 27 | 6 |
| development | M0_REFERENCE_INVALIDATION | 5m | 37 | 37 | 37 | 100.0% | 27 | 6 |
| external | M2_FAILED_BREAK | 15m | 137 | 61 | 60 | 98.4% | 34 | 6 |
| external | M2_FAILED_BREAK | 10m | 137 | 86 | 85 | 98.8% | 41 | 6 |
| external | M2_FAILED_BREAK | 5m | 137 | 137 | 136 | 99.3% | 59 | 8 |
| external | M0_REFERENCE_INVALIDATION | 15m | 13 | 13 | 13 | 100.0% | 8 | 3 |
| external | M0_REFERENCE_INVALIDATION | 10m | 13 | 13 | 13 | 100.0% | 8 | 3 |
| external | M0_REFERENCE_INVALIDATION | 5m | 13 | 13 | 13 | 100.0% | 8 | 3 |
| reference_validation | M2_FAILED_BREAK | 15m | 140 | 43 | 43 | 100.0% | 24 | 4 |
| reference_validation | M2_FAILED_BREAK | 10m | 140 | 72 | 72 | 100.0% | 37 | 7 |
| reference_validation | M2_FAILED_BREAK | 5m | 140 | 140 | 140 | 100.0% | 57 | 10 |
| reference_validation | M0_REFERENCE_INVALIDATION | 15m | 26 | 26 | 26 | 100.0% | 20 | 3 |
| reference_validation | M0_REFERENCE_INVALIDATION | 10m | 26 | 26 | 26 | 100.0% | 19 | 3 |
| reference_validation | M0_REFERENCE_INVALIDATION | 5m | 26 | 26 | 26 | 100.0% | 19 | 3 |

## Replicated binary candle states

| Mechanism | Lead | Feature | Dev loss/control | Gap | Ratio | External loss/control | RefVal loss/control |
|---|---:|---|---:|---:|---:|---:|---:|
| M0_REFERENCE_INVALIDATION | 15m | M0_CLOSE_L25 | 51.4% / 0.0% | 51.4pp | infx | 76.9% / 7.7% | 42.3% / 0.0% |
| M2_FAILED_BREAK | 15m | M2_CLOSE_H10 | 60.7% / 19.1% | 41.6pp | 3.18x | 70.0% / 41.7% | 44.2% / 30.2% |
| M0_REFERENCE_INVALIDATION | 10m | M0_CLOSE_L25 | 70.3% / 0.0% | 70.3pp | infx | 84.6% / 7.7% | 69.2% / 0.0% |
| M2_FAILED_BREAK | 10m | M2_CLOSE_H10 | 63.6% / 23.1% | 40.6pp | 2.76x | 71.8% / 40.0% | 58.3% / 34.7% |
| M0_REFERENCE_INVALIDATION | 10m | LOWER_LOW | 70.3% / 35.1% | 35.1pp | 2.00x | 69.2% / 46.2% | 80.8% / 30.8% |
| M0_REFERENCE_INVALIDATION | 5m | M0_CLOSE_L25 | 81.1% / 0.0% | 81.1pp | infx | 100.0% / 0.0% | 88.5% / 3.8% |
| M2_FAILED_BREAK | 5m | M2_CLOSE_H10 | 81.4% / 29.1% | 52.3pp | 2.80x | 86.8% / 44.1% | 90.7% / 40.0% |
| M2_FAILED_BREAK | 5m | M2_CLOSE_H05 | 55.0% / 12.8% | 42.2pp | 4.30x | 64.0% / 21.3% | 66.4% / 12.1% |

## Replicated continuous candle characteristics

| Mechanism | Lead | Feature | Dev loss/control med | Effect | External effect | RefVal effect |
|---|---:|---|---:|---:|---:|---:|
| M0_REFERENCE_INVALIDATION | 15m | low_H_R | -0.810 / -0.139 | 3.021 | 2.851 | 2.306 |
| M0_REFERENCE_INVALIDATION | 15m | high_H_R | -0.685 / -0.073 | 2.573 | 2.548 | 2.300 |
| M0_REFERENCE_INVALIDATION | 15m | close_H_R | -0.755 / -0.125 | 2.421 | 3.143 | 2.270 |
| M0_REFERENCE_INVALIDATION | 15m | close_L_R | 0.245 / 0.875 | 2.421 | 3.143 | 2.270 |
| M2_FAILED_BREAK | 15m | close_L_R | 1.087 / 1.189 | 0.848 | 0.487 | 0.402 |
| M2_FAILED_BREAK | 15m | close_H_R | 0.087 / 0.189 | 0.848 | 0.487 | 0.402 |
| M2_FAILED_BREAK | 15m | high_H_R | 0.161 / 0.279 | 0.837 | 0.433 | 0.543 |
| M0_REFERENCE_INVALIDATION | 15m | close_location | 0.413 / 0.625 | 0.450 | 0.542 | 0.730 |
| M2_FAILED_BREAK | 15m | low_H_R | -0.014 / 0.037 | 0.332 | 0.208 | 0.368 |
| M0_REFERENCE_INVALIDATION | 10m | close_L_R | 0.161 / 0.896 | 3.992 | 3.846 | 3.081 |
| M0_REFERENCE_INVALIDATION | 10m | close_H_R | -0.839 / -0.104 | 3.992 | 3.846 | 3.081 |
| M0_REFERENCE_INVALIDATION | 10m | low_H_R | -0.869 / -0.137 | 3.613 | 4.280 | 3.363 |
| M0_REFERENCE_INVALIDATION | 10m | high_H_R | -0.694 / -0.080 | 2.596 | 3.369 | 3.099 |
| M2_FAILED_BREAK | 10m | close_L_R | 1.074 / 1.187 | 0.959 | 0.626 | 0.528 |
| M2_FAILED_BREAK | 10m | close_H_R | 0.074 / 0.187 | 0.959 | 0.626 | 0.528 |
| M0_REFERENCE_INVALIDATION | 10m | body_R | -0.064 / 0.028 | 0.867 | 0.482 | 0.544 |
| M0_REFERENCE_INVALIDATION | 10m | close_change_R | -0.064 / 0.024 | 0.827 | 0.535 | 0.561 |
| M2_FAILED_BREAK | 10m | high_H_R | 0.146 / 0.243 | 0.713 | 0.594 | 0.174 |
| M0_REFERENCE_INVALIDATION | 10m | low_change_R | -0.039 / 0.014 | 0.497 | 0.612 | 1.140 |
| M2_FAILED_BREAK | 10m | body_R | 0.032 / 0.099 | 0.381 | 0.206 | 0.355 |
| M2_FAILED_BREAK | 10m | close_change_R | 0.033 / 0.099 | 0.380 | 0.216 | 0.366 |
| M0_REFERENCE_INVALIDATION | 5m | low_H_R | -0.908 / -0.166 | 4.427 | 4.704 | 3.571 |
| M0_REFERENCE_INVALIDATION | 5m | close_H_R | -0.848 / -0.136 | 4.110 | 4.647 | 3.602 |
| M0_REFERENCE_INVALIDATION | 5m | close_L_R | 0.152 / 0.864 | 4.110 | 4.647 | 3.602 |
| M0_REFERENCE_INVALIDATION | 5m | high_H_R | -0.749 / -0.076 | 3.898 | 3.596 | 3.579 |
| M2_FAILED_BREAK | 5m | close_L_R | 1.042 / 1.159 | 1.107 | 0.845 | 0.972 |
| M2_FAILED_BREAK | 5m | close_H_R | 0.042 / 0.159 | 1.107 | 0.845 | 0.972 |
| M2_FAILED_BREAK | 5m | high_H_R | 0.111 / 0.245 | 1.040 | 0.595 | 0.598 |
| M0_REFERENCE_INVALIDATION | 5m | high_change_R | -0.062 / 0.000 | 0.673 | 0.300 | 0.539 |
| M0_REFERENCE_INVALIDATION | 5m | range_R | 0.140 / 0.087 | 0.591 | 0.573 | 0.720 |
| M2_FAILED_BREAK | 5m | range_R | 0.162 / 0.222 | 0.441 | 0.231 | 0.309 |
| M2_FAILED_BREAK | 5m | low_change_R | 0.043 / 0.083 | 0.352 | 0.236 | 0.133 |
| M0_REFERENCE_INVALIDATION | 5m | body_R | -0.020 / 0.007 | 0.343 | 0.232 | 0.502 |
| M0_REFERENCE_INVALIDATION | 5m | close_change_R | -0.020 / 0.006 | 0.339 | 0.227 | 0.537 |
| M2_FAILED_BREAK | 5m | body_R | 0.041 / 0.095 | 0.311 | 0.309 | 0.489 |

## Strongest Development diagnostics (not automatically valid OOS)

### Binary

| Mechanism | Lead | Feature | Loss hit | Control hit | Gap | Blocks | Dev eligible | Replicated |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| M0_REFERENCE_INVALIDATION | 5m | M0_CLOSE_L25 | 81.1% | 0.0% | 81.1pp | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | M0_CLOSE_L25 | 70.3% | 0.0% | 70.3pp | 5/5 | yes | yes |
| M2_FAILED_BREAK | 5m | M2_CLOSE_H10 | 81.4% | 29.1% | 52.3pp | 6/6 | yes | yes |
| M0_REFERENCE_INVALIDATION | 15m | M0_CLOSE_L25 | 51.4% | 0.0% | 51.4pp | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | BEARISH | 83.8% | 32.4% | 51.4pp | 5/5 | yes | no |
| M0_REFERENCE_INVALIDATION | 10m | LOWER_CLOSE | 83.8% | 32.4% | 51.4pp | 5/5 | yes | no |
| M2_FAILED_BREAK | 5m | M2_CLOSE_H05 | 55.0% | 12.8% | 42.2pp | 6/6 | yes | yes |
| M2_FAILED_BREAK | 15m | M2_CLOSE_H10 | 60.7% | 19.1% | 41.6pp | 6/6 | yes | yes |
| M2_FAILED_BREAK | 10m | M2_CLOSE_H10 | 63.6% | 23.1% | 40.6pp | 6/6 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | LOWER_LOW | 70.3% | 35.1% | 35.1pp | 5/5 | yes | yes |

### Continuous

| Mechanism | Lead | Feature | Loss med | Control med | Effect | Blocks | Dev eligible | Replicated |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| M0_REFERENCE_INVALIDATION | 5m | low_H_R | -0.908 | -0.166 | 4.427 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 5m | close_H_R | -0.848 | -0.136 | 4.110 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 5m | close_L_R | 0.152 | 0.864 | 4.110 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | close_L_R | 0.161 | 0.896 | 3.992 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | close_H_R | -0.839 | -0.104 | 3.992 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 5m | high_H_R | -0.749 | -0.076 | 3.898 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | low_H_R | -0.869 | -0.137 | 3.613 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 15m | low_H_R | -0.810 | -0.139 | 3.021 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 10m | high_H_R | -0.694 | -0.080 | 2.596 | 5/5 | yes | yes |
| M0_REFERENCE_INVALIDATION | 15m | high_H_R | -0.685 | -0.073 | 2.573 | 5/5 | yes | yes |

## Decision

Primary replicated Loss Confirmation Candle characteristic: **BINARY / M0_REFERENCE_INVALIDATION / M0_CLOSE_L25 at 15m pre-terminal lead**.

This is an anatomy result only. A56 must test causal next-open economics; no live exit is authorized by A55.

**Status: SOL_LONG_15UTC_LOSS_CONFIRMATION_CANDLE_A55_SUPPORTED_FOR_A56**

Research only. Live Baba Bot remains unchanged.
