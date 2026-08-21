# BTC Weekly Liquidity Sweep + Order-Flow Resolution B18 — Result

**Verdict: B18_NO_HIGH_PRECISION_SWEEP_FLOW**

15m rows **232,608**, H1 rows **58,152**, 2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00.

Frozen development PRIMARY: **W1_VAH|CONT|MICRO_PERSIST**

Frozen TOP4: W1_VAH|CONT|MICRO_PERSIST, PDH|CONT|FLOW3, PWH|CONT|RAW, PDH|REV|RAW

| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|
| PRIMARY | development | 156/42/26.92% | 29/13/0 | 69.05% | 0.38% | 2.231 | 2 |
| PRIMARY | external | 103/39/37.86% | 21/18/0 | 53.85% | 0.08% | 1.167 | 4 |
| PRIMARY | reference_validation | 81/23/28.40% | 11/12/0 | 47.83% | -0.04% | 0.917 | 5 |
| PRIMARY | august | 2/1/50.00% | 0/1/0 | 0.00% | -1.00% | 0.000 | 1 |
| TOP4 | development | 156/155/99.36% | 74/81/0 | 47.74% | -0.05% | 0.914 | 7 |
| TOP4 | external | 103/99/96.12% | 45/53/1 | 45.45% | -0.09% | 0.839 | 5 |
| TOP4 | reference_validation | 81/78/96.30% | 37/41/0 | 47.44% | -0.05% | 0.902 | 6 |
| TOP4 | august | 2/2/100.00% | 0/2/0 | 0.00% | -1.00% | 0.000 | 2 |

## Development top rules

| Rank | Rule | N | Coverage | WR | Wilson LB | PF |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `W1_VAH|CONT|MICRO_PERSIST` | 42 | 26.92% | 69.05% | 53.97% | 2.231 |
| 2 | `W1_VAH|CONT|PERSIST` | 62 | 39.74% | 64.52% | 52.08% | 1.818 |
| 3 | `W1_VAH|CONT|FLOW3` | 69 | 44.23% | 63.77% | 51.98% | 1.760 |
| 4 | `W1_VAH|CONT|H1_FLOW` | 79 | 50.64% | 62.03% | 51.00% | 1.633 |
| 5 | `W1_VAH|CONT|RAW` | 82 | 52.56% | 59.76% | 48.94% | 1.485 |
| 6 | `W1_VAH|CONT|MICRO` | 49 | 31.41% | 61.22% | 47.25% | 1.579 |
| 7 | `PDH|CONT|FLOW3` | 147 | 94.23% | 51.02% | 43.02% | 1.042 |
| 8 | `PDH|CONT|RAW` | 147 | 94.23% | 50.34% | 42.35% | 1.014 |
| 9 | `PDH|CONT|PERSIST` | 142 | 91.03% | 50.00% | 41.89% | 1.000 |
| 10 | `PDH|CONT|H1_FLOW` | 145 | 92.95% | 48.97% | 40.96% | 0.959 |
| 11 | `PWH|CONT|RAW` | 75 | 48.08% | 48.00% | 37.07% | 0.923 |
| 12 | `PWH|CONT|H1_FLOW` | 73 | 46.79% | 47.95% | 36.88% | 0.921 |
| 13 | `PWH|CONT|PERSIST` | 70 | 44.87% | 47.14% | 35.90% | 0.892 |
| 14 | `PWH|CONT|FLOW3` | 73 | 46.79% | 46.58% | 35.59% | 0.872 |
| 15 | `PDH|CONT|MICRO` | 123 | 78.85% | 43.90% | 35.45% | 0.783 |
| 16 | `PDH|CONT|MICRO_PERSIST` | 123 | 78.85% | 43.90% | 35.45% | 0.783 |
| 17 | `PDH|REV|RAW` | 133 | 85.26% | 42.11% | 34.05% | 0.727 |
| 18 | `PDH|REV|H1_FLOW` | 52 | 33.33% | 46.15% | 33.34% | 0.894 |

## Gates

- B18_HIGH_PRECISION: **FAIL**
- B18_ROBUST_WEEKLY_100: **FAIL**

No OOS retuning. No equal-high/low rescue. No flow-threshold sweep. Live BBC untouched.
