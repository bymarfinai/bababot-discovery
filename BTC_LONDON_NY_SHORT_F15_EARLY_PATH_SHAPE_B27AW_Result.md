# B27AW — BTC London->NY SHORT F15 Early Path-Shape Atlas — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27AV identities reproduced: pooled-major N=163, H2-before-exit=115, PRE_H2_FAILURE=48, E20 activated=92, realized E20-hybrid total $-15.05841591698896.

The fill bar high/low was excluded. Every horizon uses only completed 5m bars after the fill bar and only trades still unresolved at that horizon.

## At-risk sample by horizon

| Horizon | Partition | At risk | Later H2 | PRE_H2 failure | Eventual E20 |
|---:|---|---:|---:|---:|---:|
| 5m | external | 36 | 23 | 13 | 17 |
| 5m | development | 61 | 39 | 22 | 33 |
| 5m | reference_validation | 28 | 17 | 11 | 13 |
| 5m | POOLED_MAJOR | 125 | 79 | 46 | 63 |
| 10m | external | 33 | 20 | 13 | 14 |
| 10m | development | 49 | 30 | 19 | 25 |
| 10m | reference_validation | 25 | 15 | 10 | 11 |
| 10m | POOLED_MAJOR | 107 | 65 | 42 | 50 |
| 15m | external | 28 | 15 | 13 | 10 |
| 15m | development | 42 | 24 | 18 | 19 |
| 15m | reference_validation | 19 | 11 | 8 | 8 |
| 15m | POOLED_MAJOR | 89 | 50 | 39 | 37 |
| 20m | external | 26 | 14 | 12 | 10 |
| 20m | development | 35 | 18 | 17 | 15 |
| 20m | reference_validation | 17 | 9 | 8 | 7 |
| 20m | POOLED_MAJOR | 78 | 41 | 37 | 32 |
| 30m | external | 24 | 14 | 10 | 10 |
| 30m | development | 31 | 16 | 15 | 13 |
| 30m | reference_validation | 13 | 7 | 6 | 5 |
| 30m | POOLED_MAJOR | 68 | 37 | 31 | 28 |
| 40m | external | 22 | 12 | 10 | 9 |
| 40m | development | 26 | 12 | 14 | 9 |
| 40m | reference_validation | 10 | 5 | 5 | 3 |
| 40m | POOLED_MAJOR | 58 | 29 | 29 | 21 |
| 60m | external | 16 | 9 | 7 | 7 |
| 60m | development | 20 | 9 | 11 | 8 |
| 60m | reference_validation | 8 | 3 | 5 | 2 |
| 60m | POOLED_MAJOR | 44 | 21 | 23 | 17 |

## Pooled-major median path shape

| Horizon | Feature | Later-H2 median | Failure median | Failure-H2 gap | Expected direction across major partitions |
|---:|---|---:|---:|---:|---:|
| 5m | adverse_wick_r | 0.089 | 0.138 | 0.050 | 3/3 |
| 5m | favorable_wick_r | 0.047 | 0.016 | -0.031 | 2/3 |
| 5m | adverse_close_r | 0.022 | 0.077 | 0.055 | 3/3 |
| 5m | favorable_close_r | 0.000 | 0.000 | 0.000 | 0/3 |
| 5m | net_close_progress_r | -0.022 | -0.077 | -0.055 | 3/3 |
| 5m | wrong_side_close_fraction | 1.000 | 1.000 | 0.000 | 0/3 |
| 5m | lower_low_step_fraction | - | - | - | 0/3 |
| 5m | higher_high_step_fraction | - | - | - | 0/3 |
| 5m | close_path_efficiency | 0.000 | 0.000 | 0.000 | 0/3 |
| 5m | adverse_favorable_ratio | 1.571 | 7.402 | 5.831 | 3/3 |
| 10m | adverse_wick_r | 0.112 | 0.187 | 0.075 | 3/3 |
| 10m | favorable_wick_r | 0.060 | 0.028 | -0.032 | 2/3 |
| 10m | adverse_close_r | 0.062 | 0.158 | 0.096 | 3/3 |
| 10m | favorable_close_r | 0.000 | 0.000 | 0.000 | 2/3 |
| 10m | net_close_progress_r | -0.035 | -0.143 | -0.108 | 3/3 |
| 10m | wrong_side_close_fraction | 1.000 | 1.000 | 0.000 | 2/3 |
| 10m | lower_low_step_fraction | 0.000 | 0.000 | 0.000 | 0/3 |
| 10m | higher_high_step_fraction | 1.000 | 1.000 | 0.000 | 1/3 |
| 10m | close_path_efficiency | -1.000 | -1.000 | 0.000 | 1/3 |
| 10m | adverse_favorable_ratio | 1.734 | 4.921 | 3.187 | 3/3 |
| 15m | adverse_wick_r | 0.132 | 0.237 | 0.105 | 3/3 |
| 15m | favorable_wick_r | 0.063 | 0.037 | -0.025 | 2/3 |
| 15m | adverse_close_r | 0.090 | 0.169 | 0.078 | 3/3 |
| 15m | favorable_close_r | 0.000 | 0.000 | 0.000 | 1/3 |
| 15m | net_close_progress_r | -0.042 | -0.122 | -0.080 | 3/3 |
| 15m | wrong_side_close_fraction | 1.000 | 1.000 | 0.000 | 1/3 |
| 15m | lower_low_step_fraction | 0.500 | 0.500 | 0.000 | 1/3 |
| 15m | higher_high_step_fraction | 0.500 | 0.500 | 0.000 | 0/3 |
| 15m | close_path_efficiency | 0.172 | -0.535 | -0.707 | 3/3 |
| 15m | adverse_favorable_ratio | 3.005 | 4.388 | 1.383 | 2/3 |
| 20m | adverse_wick_r | 0.161 | 0.246 | 0.085 | 3/3 |
| 20m | favorable_wick_r | 0.071 | 0.044 | -0.028 | 2/3 |
| 20m | adverse_close_r | 0.136 | 0.175 | 0.038 | 3/3 |
| 20m | favorable_close_r | 0.004 | 0.000 | -0.004 | 2/3 |
| 20m | net_close_progress_r | -0.044 | -0.141 | -0.097 | 3/3 |
| 20m | wrong_side_close_fraction | 0.750 | 1.000 | 0.250 | 2/3 |
| 20m | lower_low_step_fraction | 0.333 | 0.333 | 0.000 | 0/3 |
| 20m | higher_high_step_fraction | 0.333 | 0.667 | 0.333 | 1/3 |
| 20m | close_path_efficiency | -0.062 | -0.316 | -0.254 | 2/3 |
| 20m | adverse_favorable_ratio | 2.722 | 4.107 | 1.386 | 3/3 |
| 30m | adverse_wick_r | 0.167 | 0.237 | 0.070 | 3/3 |
| 30m | favorable_wick_r | 0.078 | 0.037 | -0.041 | 3/3 |
| 30m | adverse_close_r | 0.136 | 0.175 | 0.038 | 3/3 |
| 30m | favorable_close_r | 0.023 | 0.000 | -0.023 | 3/3 |
| 30m | net_close_progress_r | -0.055 | -0.144 | -0.089 | 3/3 |
| 30m | wrong_side_close_fraction | 0.833 | 1.000 | 0.167 | 3/3 |
| 30m | lower_low_step_fraction | 0.400 | 0.400 | 0.000 | 1/3 |
| 30m | higher_high_step_fraction | 0.400 | 0.600 | 0.200 | 2/3 |
| 30m | close_path_efficiency | -0.026 | -0.255 | -0.229 | 3/3 |
| 30m | adverse_favorable_ratio | 2.712 | 4.486 | 1.774 | 3/3 |
| 40m | adverse_wick_r | 0.223 | 0.290 | 0.067 | 3/3 |
| 40m | favorable_wick_r | 0.073 | 0.044 | -0.029 | 3/3 |
| 40m | adverse_close_r | 0.159 | 0.220 | 0.061 | 3/3 |
| 40m | favorable_close_r | 0.020 | 0.000 | -0.020 | 3/3 |
| 40m | net_close_progress_r | -0.066 | -0.158 | -0.092 | 3/3 |
| 40m | wrong_side_close_fraction | 0.875 | 1.000 | 0.125 | 3/3 |
| 40m | lower_low_step_fraction | 0.429 | 0.429 | 0.000 | 1/3 |
| 40m | higher_high_step_fraction | 0.429 | 0.571 | 0.143 | 2/3 |
| 40m | close_path_efficiency | -0.022 | -0.297 | -0.275 | 3/3 |
| 40m | adverse_favorable_ratio | 3.143 | 5.092 | 1.949 | 3/3 |
| 60m | adverse_wick_r | 0.312 | 0.361 | 0.049 | 2/3 |
| 60m | favorable_wick_r | 0.089 | 0.035 | -0.055 | 3/3 |
| 60m | adverse_close_r | 0.236 | 0.334 | 0.098 | 3/3 |
| 60m | favorable_close_r | 0.036 | 0.000 | -0.036 | 3/3 |
| 60m | net_close_progress_r | -0.098 | -0.237 | -0.139 | 3/3 |
| 60m | wrong_side_close_fraction | 0.833 | 1.000 | 0.167 | 3/3 |
| 60m | lower_low_step_fraction | 0.364 | 0.364 | 0.000 | 1/3 |
| 60m | higher_high_step_fraction | 0.455 | 0.545 | 0.091 | 2/3 |
| 60m | close_path_efficiency | -0.055 | -0.190 | -0.135 | 2/3 |
| 60m | adverse_favorable_ratio | 3.250 | 5.955 | 2.706 | 3/3 |

## 3-of-3 partition-consistent expected-direction horizons

- **adverse_wick_r:** 5m, 10m, 15m, 20m, 30m, 40m
- **favorable_wick_r:** 30m, 40m, 60m
- **adverse_close_r:** 5m, 10m, 15m, 20m, 30m, 40m, 60m
- **favorable_close_r:** 30m, 40m, 60m
- **net_close_progress_r:** 5m, 10m, 15m, 20m, 30m, 40m, 60m
- **wrong_side_close_fraction:** 30m, 40m, 60m
- **lower_low_step_fraction:** NONE
- **higher_high_step_fraction:** NONE
- **close_path_efficiency:** 15m, 30m, 40m
- **adverse_favorable_ratio:** 5m, 10m, 20m, 30m, 40m, 60m

## Guardrail readout

No feature threshold, feature combination, classifier, stop, target, entry change, regime slice, or runner change was selected in B27AW. This atlas only localizes early causal path-shape separation.

Research only; live BBC unchanged.
