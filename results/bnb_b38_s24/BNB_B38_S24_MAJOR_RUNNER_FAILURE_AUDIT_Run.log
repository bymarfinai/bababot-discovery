# BNB B38-S24 — Major Runner Failure Character Audit

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

## Runner baseline

| Period | Runner N | HIT | BE | Amb | Hit rate ex-amb |
|---|---:|---:|---:|---:|---:|
| DEV | 90 | 44 | 43 | 3 | 50.6% |
| REF | 56 | 21 | 34 | 1 | 38.2% |

## Year anatomy

| Year | Runner N | HIT | BE | Amb | Hit rate | Runner total R |
|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 31 | 14 | 16 | 1 | 46.7% | 10.868R |
| 2023 | 30 | 12 | 16 | 2 | 42.9% | 6.391R |
| 2024 | 29 | 18 | 11 | 0 | 62.1% | 9.082R |
| 2025 | 39 | 16 | 23 | 0 | 41.0% | 8.149R |
| 2026 | 17 | 5 | 11 | 1 | 31.2% | 3.073R |

## Strongest directionally consistent pre-runner features

| Feature | DEV effect | REF effect | DEV HIT/BE med | REF HIT/BE med |
|---|---:|---:|---:|---:|
| tp1_r | 0.660 | 0.787 | 0.249/0.046 | 0.165/0.029 |
| tp1_bar_body_r | 0.572 | 1.003 | 0.151/0.051 | 0.139/-0.008 |
| last3_green_rate | -0.500 | -1.000 | 0.667/0.833 | 0.667/1.000 |
| tp1_bar_range_r | 0.438 | 0.504 | 0.248/0.170 | 0.246/0.128 |
| tp1_close_location | 0.402 | 0.919 | 0.718/0.538 | 0.790/0.444 |
| pre_tp1_green_rate | -0.367 | -0.299 | 0.525/0.593 | 0.538/0.595 |
| tp1_accept | 0.242 | 0.406 | 0.614/0.372 | 0.524/0.118 |
| tp1_close_above_r | 0.421 | 0.231 | 0.018/-0.027 | 0.001/-0.015 |
| pre_tp1_max_pullback_r | 0.170 | 0.216 | 0.330/0.279 | 0.251/0.209 |
| tp2_r | 0.157 | 0.256 | 0.334/0.246 | 0.226/0.114 |
| pre_tp1_mae_r | 0.125 | 0.585 | -0.154/-0.191 | -0.131/-0.194 |
| last3_progress_r | 0.099 | 1.453 | 0.169/0.150 | 0.154/0.057 |

## Interpretation boundary
S24 is diagnostic only and does not modify S23.
2026 is evaluated only after DEV cuts are frozen.
A skip filter requires a separate preregistered S25 validation.
