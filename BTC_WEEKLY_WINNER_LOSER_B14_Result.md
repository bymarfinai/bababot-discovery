# BTC Weekly Winner-vs-Loser Fingerprint B14 — Result

**Stable differentiators: 0**
**Strong evidence gate: FAIL**
**Very-strong separability: FAIL**

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00**, H1 rows **58,152**.

## Candidate-side outcome base rates

| Partition | N | TP | SL | TIME | decisive WR |
|---|---:|---:|---:|---:|---:|
| development | 41494 | 16892 | 23944 | 658 | 41.37% |
| external | 27398 | 11062 | 16304 | 32 | 40.42% |
| reference_validation | 21546 | 8989 | 12197 | 360 | 42.43% |
| august | 532 | 174 | 261 | 97 | 40.00% |

## Frozen development top-20 feature differences

| Feature | Stable | Dev SMD | Ext SMD | Val SMD | Dev AUC* | Ext AUC* | Val AUC* |
|---|---|---:|---:|---:|---:|---:|---:|
| `ema21_dist_aligned` | no | 0.106 | 0.055 | 0.062 | 0.529 | 0.513 | 0.518 |
| `eff12` | no | 0.105 | 0.061 | 0.041 | 0.530 | 0.516 | 0.510 |
| `forward12_atr` | no | -0.097 | -0.045 | -0.035 | 0.523 | 0.508 | 0.509 |
| `ema8_dist_aligned` | no | 0.095 | 0.056 | 0.041 | 0.525 | 0.510 | 0.513 |
| `pos24_aligned` | no | 0.092 | 0.001 | 0.038 | 0.527 | 0.500 | 0.511 |
| `forward24_atr` | no | -0.088 | -0.023 | -0.035 | 0.526 | 0.503 | 0.509 |
| `ema55_dist_aligned` | no | 0.086 | 0.048 | 0.074 | 0.525 | 0.515 | 0.518 |
| `pos12_aligned` | no | 0.083 | 0.017 | 0.032 | 0.524 | 0.505 | 0.509 |
| `adverse12_atr` | no | 0.082 | 0.016 | 0.027 | 0.522 | 0.502 | 0.507 |
| `prevday_forward_atr` | no | -0.078 | -0.023 | -0.027 | 0.521 | 0.506 | 0.506 |
| `adverse24_atr` | no | 0.076 | -0.005 | 0.038 | 0.524 | 0.502 | 0.509 |
| `supportive_wick` | no | -0.075 | -0.035 | -0.033 | 0.521 | 0.510 | 0.510 |
| `dirfrac12` | no | 0.073 | 0.070 | 0.047 | 0.523 | 0.520 | 0.514 |
| `week_pos_aligned` | no | 0.073 | 0.040 | 0.024 | 0.522 | 0.511 | 0.507 |
| `pos48_aligned` | no | 0.073 | 0.009 | 0.023 | 0.521 | 0.503 | 0.507 |
| `ema8_slope3_aligned` | no | 0.072 | 0.036 | 0.034 | 0.524 | 0.509 | 0.514 |
| `aligned_ret12` | no | 0.072 | 0.053 | 0.037 | 0.525 | 0.516 | 0.510 |
| `ema21_slope3_aligned` | no | 0.071 | 0.040 | 0.039 | 0.523 | 0.511 | 0.513 |
| `forward48_atr` | no | -0.071 | -0.017 | -0.053 | 0.521 | 0.504 | 0.507 |
| `prevday_adverse_atr` | no | 0.069 | 0.014 | 0.032 | 0.518 | 0.502 | 0.507 |

*AUC is orientation-free max(AUC,1-AUC).

## Stable differentiators

## Frozen top-20 logistic separability

| Partition | N | ROC AUC | Accuracy | Base WR |
|---|---:|---:|---:|---:|
| development | 40836 | 0.545 | 52.79% | 41.37% |
| external | 27366 | 0.518 | 50.65% | 40.42% |
| reference_validation | 21186 | 0.520 | 50.46% | 42.43% |
| august | 435 | 0.444 | 48.05% | 40.00% |

This is a fingerprint diagnostic, not yet a one-trade-per-week strategy. No OOS retuning. Live BBC untouched.
