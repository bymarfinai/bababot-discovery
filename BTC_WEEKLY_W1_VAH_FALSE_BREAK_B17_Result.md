# BTC Weekly W1 VAH False-Break Filter B17 — Result

**Verdict: B17_NO_USEFUL_FALSE_BREAK_FILTER**

Baseline sanity reproduced exactly: **{'development': (82, 49), 'external': (64, 36), 'reference_validation': (47, 24), 'august': (2, 0)}**.
Stable differentiators: **1**.
Extended derivatives allowed: **False**.

Frozen selected model: **CORE_TREE**, leaf **1**
Rule: `break_close_pos <= 0.67316833`

## Baseline vs filtered

| Partition | Baseline N/WR/PF | Filtered N/WR/PF | Retention |
|---|---:|---:|---:|
| development | 82 / 59.76% / 1.485 | 17 / 88.24% / 7.500 | 20.73% |
| external | 64 / 56.25% / 1.286 | 11 / 36.36% / 0.571 | 17.19% |
| reference_validation | 47 / 51.06% / 1.043 | 8 / 62.50% / 1.667 | 17.02% |
| august | 2 / 0.00% / 0.000 | 2 / 0.00% / 0.000 | 100.00% |

## Top forensic differences

| Feature | Stable | Dev SMD | Ext SMD | Val SMD | Dev AUC | Ext AUC | Val AUC |
|---|---|---:|---:|---:|---:|---:|---:|
| `f_taker_imbalance_6h` | yes | 0.320 | 0.634 | 0.332 | 0.573 | 0.656 | 0.571 |
| `oi_chg4h` | no | 0.690 | -0.301 | 0.195 | 0.703 | 0.562 | 0.545 |
| `oi_chg60` | no | 0.438 | -0.285 | 0.338 | 0.652 | 0.542 | 0.621 |
| `oi_chg15` | no | 0.403 | -0.315 | 0.167 | 0.652 | 0.549 | 0.565 |
| `break_close_pos` | no | -0.377 | 0.128 | -0.172 | 0.576 | 0.505 | 0.553 |
| `f_taker_imbalance_3h` | no | 0.248 | 0.649 | 0.461 | 0.558 | 0.642 | 0.632 |
| `basis_now` | no | -0.224 | -0.450 | 0.165 | 0.527 | 0.625 | 0.551 |
| `break_range_atr` | no | 0.222 | -0.050 | 0.065 | 0.643 | 0.536 | 0.533 |
| `spot_ret_3h` | no | 0.207 | -0.478 | 0.082 | 0.547 | 0.617 | 0.533 |
| `prior3h_ret` | no | 0.203 | -0.487 | 0.085 | 0.549 | 0.615 | 0.536 |
| `break_close_above_vah_atr` | no | -0.198 | -0.310 | 0.308 | 0.502 | 0.567 | 0.525 |
| `premium_now` | no | -0.185 | -0.492 | -0.072 | 0.518 | 0.648 | 0.511 |
| `spot_taker_imbalance_3h` | no | 0.180 | -0.037 | 0.253 | 0.558 | 0.509 | 0.540 |
| `spot_minus_fut_ret_3h` | no | 0.164 | 0.421 | -0.266 | 0.510 | 0.575 | 0.587 |
| `f_taker_imbalance_1h` | no | 0.159 | 0.474 | 0.176 | 0.526 | 0.595 | 0.571 |

## Data coverage

Core complete coverage: `{'development': 1.0, 'external': 1.0, 'reference_validation': 1.0, 'august': 1.0}`
Extended complete coverage: `{'development': 0.7073170731707317, 'external': 0.65625, 'reference_validation': 1.0, 'august': 1.0}`

## Gates

- B17_USEFUL_FALSE_BREAK_FILTER: **FAIL**
- B17_HIGH_PRECISION_FILTER: **FAIL**

No OOS retuning. This filter applies only when a W1 VAH breakout candidate exists; it is not a universal weekly-entry rule. Live BBC untouched.
