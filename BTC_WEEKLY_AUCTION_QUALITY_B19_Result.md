# BTC Weekly Auction-Quality Breakout / Sweep B19 — Result

**Verdict: B19_NO_ROBUST_AUCTION_QUALITY**

Baseline sanity reproduced exactly: **{'development': (82, 49), 'external': (64, 36), 'reference_validation': (47, 24), 'august': (2, 0)}**.
15m rows **232,608**, H1 rows **58,152**, 2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00.

Frozen development PRIMARY: **W1_VAH|AQ10_NIR1|RAW**

| Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---:|---:|---:|---:|---:|---:|
| development | 156/68/43.59% | 41/27/0 | 60.29% | 0.21% | 1.519 | 3 |
| external | 103/53/51.46% | 28/25/0 | 52.83% | 0.06% | 1.120 | 7 |
| reference_validation | 81/33/40.74% | 21/12/0 | 63.64% | 0.27% | 1.750 | 2 |
| august | 2/2/100.00% | 0/2/0 | 0.00% | -1.00% | 0.000 | 2 |

## Development ranking

| Rank | Rule | N | Coverage | WR | Wilson LB | PF |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `W1_VAH|AQ10_NIR1|RAW` | 68 | 43.59% | 60.29% | 48.42% | 1.519 |
| 2 | `W1_VAH|AQ10_NIR2|RAW` | 63 | 40.38% | 55.56% | 43.32% | 1.250 |
| 3 | `W1_VAH|AQ25_NIR1|RAW` | 61 | 39.10% | 55.74% | 43.30% | 1.259 |
| 4 | `PDH|FAILED_AUCTION|FLOW` | 42 | 26.92% | 57.14% | 42.21% | 1.399 |
| 5 | `PDL|FAILED_AUCTION|RAW` | 70 | 44.87% | 52.86% | 41.32% | 1.172 |
| 6 | `PDL|FAILED_AUCTION|FLOW` | 35 | 22.44% | 57.14% | 40.86% | 1.370 |
| 7 | `W1_VAH|AQ25_NIR1|PERSIST` | 36 | 23.08% | 55.56% | 39.58% | 1.250 |
| 8 | `W1_VAH|AQ10_NIR2|PERSIST` | 51 | 32.69% | 52.94% | 39.52% | 1.125 |
| 9 | `W1_VAH|AQ10_NIR1|PERSIST` | 41 | 26.28% | 53.66% | 38.75% | 1.158 |
| 10 | `PDH|FAILED_AUCTION|RAW` | 70 | 44.87% | 41.43% | 30.63% | 0.734 |
| 11 | `PWL|FAILED_AUCTION|RAW` | 12 | 7.69% | 66.67% | 39.06% | 2.000 |
| 12 | `PWL|FAILED_AUCTION|FLOW` | 5 | 3.21% | 60.00% | 23.07% | 1.500 |
| 13 | `PWH|FAILED_AUCTION|RAW` | 16 | 10.26% | 37.50% | 18.48% | 0.600 |
| 14 | `PWH|FAILED_AUCTION|FLOW` | 13 | 8.33% | 38.46% | 17.71% | 0.625 |

## Atomic OOS passers (descriptive only; not promotable unless selected on development)

none

## Gates

- B19_HIGH_QUALITY_PRIMARY: **FAIL**
- B19_ROBUST_100_DIAGNOSTIC: **FAIL**

No OOS retuning. No equal-high/low rescue. No regime filter. No threshold sweep. Live BBC untouched.
