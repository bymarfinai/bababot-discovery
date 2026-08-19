# BTC H1 Previous-Day Volume Profile VP1 — Result

Signal timeframe **1H**; no 1m. Previous-day POC/VAH/VAL constructed from completed 5m BTCUSDT USD-M candles using 100 equal-width bins and a contiguous 70% value area.

Coverage: **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:55:00+00:00**, 5m rows **697,536**, complete 1H rows **58,128**, complete daily profiles **2,422**, qualifying events **1,133**.

## Side aggregates

POC rate = target POC before event extreme, among POC-eligible next1H entries. VA rate = opposite value-area boundary before event extreme. Execution uses net RR1:1 after 0.15% fee, max6H.

| Partition | Side | N | +3H | POC elig/hit | POC rate | VA elig/hit | VA rate | Net1:1 N/WR | PnL |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | LONG | 286 | 53.15% | 271/104 | 38.38% | 286/52 | 18.18% | 286/27.27% | $-481.88 |
| development | SHORT | 292 | 46.58% | 266/108 | 40.60% | 292/52 | 17.81% | 292/28.08% | $-403.00 |
| reference_validation | LONG | 93 | 44.09% | 85/36 | 42.35% | 93/11 | 11.83% | 93/21.51% | $-160.47 |
| reference_validation | SHORT | 110 | 50.91% | 99/36 | 36.36% | 110/19 | 17.27% | 110/25.45% | $-160.95 |
| external | LONG | 169 | 54.44% | 148/59 | 39.86% | 169/35 | 20.71% | 169/30.77% | $-329.77 |
| external | SHORT | 170 | 48.24% | 157/63 | 40.13% | 170/27 | 15.88% | 170/32.35% | $-210.10 |
| august | LONG | 4 | 100.00% | 4/3 | 75.00% | 4/1 | 25.00% | 4/50.00% | $-0.45 |
| august | SHORT | 9 | 44.44% | 8/3 | 37.50% | 9/3 | 33.33% | 9/22.22% | $-8.60 |

## Fixed clock x side cells — reference validation

| WIB | Side | N | +3H | POC elig/hit/rate | VA elig/hit/rate | Net1:1 N/WR/PnL |
|---:|---|---:|---:|---:|---:|---:|
| 11:00 | LONG | 34 | 38.24% | 32/13/40.62% | 34/5/14.71% | 34/14.71%/$-72.82 |
| 11:00 | SHORT | 31 | 45.16% | 27/9/33.33% | 31/5/16.13% | 31/25.81%/$-32.85 |
| 15:00 | LONG | 23 | 60.87% | 21/9/42.86% | 23/1/4.35% | 23/26.09%/$-29.80 |
| 15:00 | SHORT | 31 | 70.97% | 31/14/45.16% | 31/7/22.58% | 31/38.71%/$-9.74 |
| 01:00 | LONG | 20 | 40.00% | 17/9/52.94% | 20/3/15.00% | 20/25.00%/$-31.23 |
| 01:00 | SHORT | 23 | 47.83% | 19/4/21.05% | 23/3/13.04% | 23/17.39%/$-56.69 |
| 02:00 | LONG | 16 | 37.50% | 15/5/33.33% | 16/2/12.50% | 16/25.00%/$-26.61 |
| 02:00 | SHORT | 25 | 36.00% | 22/9/40.91% | 25/4/16.00% | 25/16.00%/$-61.67 |

## Fixed clock x side cells — external 2020-2021

| WIB | Side | N | +3H | POC elig/hit/rate | VA elig/hit/rate | Net1:1 N/WR/PnL |
|---:|---|---:|---:|---:|---:|---:|
| 11:00 | LONG | 45 | 62.22% | 41/14/34.15% | 45/8/17.78% | 45/20.00%/$-93.09 |
| 11:00 | SHORT | 45 | 46.67% | 42/16/38.10% | 45/9/20.00% | 45/31.11%/$-62.33 |
| 15:00 | LONG | 59 | 44.07% | 51/16/31.37% | 59/9/15.25% | 59/23.73%/$-139.26 |
| 15:00 | SHORT | 50 | 52.00% | 47/20/42.55% | 50/8/16.00% | 50/30.00%/$-64.43 |
| 01:00 | LONG | 29 | 65.52% | 25/16/64.00% | 29/8/27.59% | 29/51.72%/$-46.90 |
| 01:00 | SHORT | 37 | 64.86% | 35/20/57.14% | 37/5/13.51% | 37/51.35%/$+13.50 |
| 02:00 | LONG | 36 | 52.78% | 31/13/41.94% | 36/10/27.78% | 36/38.89%/$-50.52 |
| 02:00 | SHORT | 38 | 28.95% | 33/7/21.21% | 38/5/13.16% | 38/18.42%/$-96.83 |

## External chronological POC blocks

### LONG

| Block | Events | POC eligible | Target | Adverse | Time | POC rate |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 42 | 38 | 18 | 20 | 0 | 47.37% |
| B2 | 42 | 38 | 11 | 27 | 0 | 28.95% |
| B3 | 42 | 38 | 17 | 21 | 0 | 44.74% |
| B4 | 43 | 34 | 13 | 21 | 0 | 38.24% |

### SHORT

| Block | Events | POC eligible | Target | Adverse | Time | POC rate |
|---|---:|---:|---:|---:|---:|---:|
| B1 | 42 | 38 | 18 | 20 | 0 | 47.37% |
| B2 | 43 | 40 | 13 | 27 | 0 | 32.50% |
| B3 | 42 | 38 | 19 | 19 | 0 | 50.00% |
| B4 | 43 | 41 | 13 | 28 | 0 | 31.71% |

## Verdicts

**VP1_POC_ROTATION_SUPPORTED: FAIL**
**VP1_80_CANDIDATE: FAIL**
**VP1_EXECUTION_SUPPORTED: FAIL**

No bin-count, value-area percentage, clock, side, distance, weekday, or execution parameter is reselected after result.
