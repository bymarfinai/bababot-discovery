# BTC AOH2 — Asia Open Context Optimization Result

Core setup unchanged: previous-day HIGH sweep -> immediate 15m reclaim -> SHORT next 15m open; structural SL; TP sized for **net 1:1 after 0.15% fee**.

Core events: external **45**, reference **68** (development 47, validation 21), August **0**.

## Frozen selected thresholds

- PRE_UP 60m minimum: **0.20%**
- Asia-open location in previous-day range: **>= 70%**
- Development selected N **28**, WR **50.00%**, Wilson lower **32.63%**, expectancy **$-0.168/trade**.

## Exact selected rule vs unfiltered control

| Partition | Rule | N | TP | SL | WR | Wilson 95% low | PnL | Exp/trade | Median risk | Avg raw TP |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | selected | 28 | 14 | 14 | 50.00% | 32.63% | $-4.71 | $-0.168 | 0.39% | 0.72% |
| development | control | 47 | 20 | 27 | 42.55% | 29.51% | $-20.85 | $-0.444 | 0.36% | 0.67% |
| reference_validation | selected | 8 | 4 | 4 | 50.00% | 21.52% | $1.15 | $0.143 | 0.29% | 0.64% |
| reference_validation | control | 21 | 7 | 14 | 33.33% | 17.19% | $-11.87 | $-0.565 | 0.29% | 0.58% |
| external | selected | 27 | 9 | 18 | 33.33% | 18.64% | $-21.47 | $-0.795 | 0.42% | 0.86% |
| external | control | 45 | 17 | 28 | 37.78% | 25.11% | $-34.46 | $-0.766 | 0.42% | 0.81% |
| august | selected | 0 | 0 | 0 | - | - | $0.00 | - | - | - |
| august | control | 0 | 0 | 0 | - | - | $0.00 | - | - | - |

## External selected-rule blocks

| Block | N | TP | SL | WR | PnL | Exp/trade |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 6 | 2 | 4 | 33.33% | $-6.36 | $-1.061 |
| B2 | 7 | 4 | 3 | 57.14% | $13.37 | $1.910 |
| B3 | 7 | 1 | 6 | 14.29% | $-20.71 | $-2.958 |
| B4 | 7 | 2 | 5 | 28.57% | $-7.77 | $-1.110 |

## Top development grid cells

| Rank | PRE60 min | Location min | N | WR | Wilson low | PnL | Exp/trade |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0.20% | 70% | 28 | 50.00% | 32.63% | $-4.71 | $-0.168 |
| 2 | 0.30% | 70% | 21 | 52.38% | 32.37% | $-0.82 | $-0.039 |
| 3 | 0.10% | 70% | 31 | 48.39% | 31.97% | $-5.15 | $-0.166 |
| 4 | 0.15% | 70% | 29 | 48.28% | 31.39% | $-5.77 | $-0.199 |
| 5 | 0.05% | 70% | 32 | 46.88% | 30.87% | $-7.27 | $-0.227 |
| 6 | 0.20% | 75% | 25 | 48.00% | 30.03% | $-6.28 | $-0.251 |
| 7 | 0.00% | 70% | 33 | 45.45% | 29.84% | $-10.07 | $-0.305 |
| 8 | 0.10% | 75% | 28 | 46.43% | 29.53% | $-6.72 | $-0.240 |
| 9 | 0.20% | 80% | 23 | 47.83% | 29.24% | $-5.46 | $-0.238 |
| 10 | 0.30% | 75% | 18 | 50.00% | 29.03% | $-2.39 | $-0.133 |

**AOH2_CONTEXT_SUPPORTED: FAIL**
**AOH2_80_CANDIDATE: FAIL**

Thresholds were selected only from development data; validation, external, and August were not used to choose them. No post-result rescue.
