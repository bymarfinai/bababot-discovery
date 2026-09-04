# SOL LONG Three-Zone Complete Metrics Audit — A25 Result

Trade definition: every actual entry is one component trade; the 18UTC REC_H2 recovery is therefore a separate trade from its parent. Daily/weekly PnL aggregates components by exit timestamp. Positive-day/week rate is the share of active days/weeks with net PnL > 0.

## Portfolio — raw

| Partition | N | Trades/wk | WR | PF | Exp | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Avg win | Avg loss | Payoff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 2043 | 13.05 | 40.0% | 1.27 | $0.52 | $1069.20 | $162.79 | 20 | $-46.52 | $0.02 | $6.22 | $-3.28 | 1.90 |
| external | 931 | 8.92 | 37.6% | 1.61 | $1.51 | $1407.88 | $167.06 | 13 | $-89.98 | $0.09 | $10.60 | $-3.96 | 2.67 |
| reference_validation | 1113 | 13.55 | 40.3% | 1.35 | $0.51 | $562.75 | $77.28 | 17 | $-22.31 | $0.02 | $4.86 | $-2.43 | 2.00 |

## Portfolio — 5bps stress

| Partition | N | Trades/wk | WR | PF | Exp | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Avg win | Avg loss | Payoff |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 2043 | 13.05 | 39.3% | 1.13 | $0.27 | $558.45 | $201.11 | 20 | $-46.77 | $0.11 | $6.09 | $-3.48 | 1.75 |
| external | 931 | 8.92 | 37.3% | 1.48 | $1.26 | $1175.13 | $183.81 | 13 | $-90.23 | $0.01 | $10.44 | $-4.19 | 2.49 |
| reference_validation | 1113 | 13.55 | 39.3% | 1.16 | $0.26 | $284.50 | $105.63 | 17 | $-22.56 | $0.05 | $4.73 | $-2.64 | 1.79 |

## Daily — raw

| Partition | Active days | Positive-day rate | Avg PnL/day | Median | Best day | Worst day | Losing-day streak | Avg trades/day | Avg wins/day | Median wins/day | Max wins/day |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 923 | 51.0% | $1.16 | $0.57 | $51.79 | $-46.52 | 9 | 2.21 | 0.89 | 1.00 | 4 |
| external | 400 | 52.2% | $3.52 | $2.04 | $103.01 | $-80.02 | 6 | 2.33 | 0.88 | 1.00 | 4 |
| reference_validation | 487 | 51.1% | $1.16 | $1.00 | $31.36 | $-25.27 | 9 | 2.29 | 0.92 | 1.00 | 4 |

## Weekly — raw

| Partition | Active weeks | Positive-week rate | Avg PnL/week | Median | Best week | Worst week | Losing-week streak | Avg trades/active week | Avg wins/active week |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 158 | 55.7% | $6.77 | $3.19 | $106.27 | $-51.34 | 5 | 12.93 | 5.18 |
| external | 68 | 72.1% | $20.70 | $12.95 | $173.95 | $-74.36 | 3 | 13.69 | 5.15 |
| reference_validation | 83 | 65.1% | $6.78 | $4.54 | $72.17 | $-54.41 | 4 | 13.41 | 5.40 |

## Weekly — 5bps stress

| Partition | Positive-week rate | Avg PnL/week | Median | Best week | Worst week | Losing-week streak |
|---|---:|---:|---:|---:|---:|---:|
| development | 50.0% | $3.53 | $0.18 | $101.77 | $-55.59 | 5 |
| external | 63.2% | $17.28 | $9.89 | $170.95 | $-77.61 | 5 |
| reference_validation | 54.2% | $3.43 | $1.94 | $68.92 | $-57.66 | 5 |

## Habitat breakdown — raw

| Partition | Habitat | N | Trades/wk | WR | PF | Net | Max DD | Max loss streak | Max loss/trade | Min win/trade | Positive-week rate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 18UTC/R240 parent + H2 entries | 833 | 5.32 | 40.1% | 1.31 | $448.82 | $99.52 | 11 | $-46.52 | $0.04 | 63.9% |
| external | 18UTC/R240 parent + H2 entries | 398 | 3.81 | 33.4% | 1.46 | $460.40 | $137.47 | 15 | $-89.98 | $0.10 | 61.8% |
| reference_validation | 18UTC/R240 parent + H2 entries | 456 | 5.55 | 35.3% | 1.20 | $127.92 | $69.26 | 10 | $-22.31 | $0.02 | 57.3% |
