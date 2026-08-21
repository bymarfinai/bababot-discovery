# BTC Strong Uptrend Lifecycle B22B — Result

5m source rows: **698,112**; coverage: **100.0000%**

Setup family: EMA20/EMA50 rising/widening strong-uptrend state, crossover or healthy pullback/reclaim entry, and reversal-state exit. No fixed TP and no stop-loss.

## Development leaderboard (eligible rows first)

| TF | Entry | Exit | N | WR | PF | Median ret | Median MFE | Median MAE | Hold h |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 4h | PULLBACK_RECLAIM | E_BEAR_CROSS | 27 | 40.74% | 2.60 | -1.42% | 6.32% | -3.32% | 224.0 |
| 4h | PULLBACK_RECLAIM | E_FAST_20 | 48 | 37.50% | 2.18 | -0.76% | 2.29% | -1.33% | 48.0 |
| 4h | PULLBACK_RECLAIM | E_WEAKEN_20 | 48 | 37.50% | 2.18 | -0.76% | 2.29% | -1.33% | 48.0 |
| 1h | PULLBACK_RECLAIM | E_STRUCT_50 | 159 | 28.93% | 2.10 | -0.49% | 1.11% | -0.86% | 14.0 |
| 4h | PULLBACK_RECLAIM | E_STRUCT_50 | 43 | 30.23% | 1.86 | -1.23% | 2.66% | -1.60% | 72.0 |
| 4h | CROSSOVER_INIT | E_BEAR_CROSS | 58 | 24.14% | 1.69 | -1.68% | 4.42% | -2.96% | 138.0 |
| 1h | PULLBACK_RECLAIM | E_FAST_20 | 201 | 32.84% | 1.56 | -0.34% | 0.85% | -0.65% | 8.0 |
| 1h | PULLBACK_RECLAIM | E_WEAKEN_20 | 201 | 32.84% | 1.56 | -0.34% | 0.85% | -0.65% | 8.0 |
| 4h | CROSSOVER_INIT | E_STRUCT_50 | 58 | 29.31% | 1.41 | -0.90% | 3.21% | -2.07% | 66.0 |
| 1h | PULLBACK_RECLAIM | E_BEAR_CROSS | 121 | 32.23% | 1.39 | -0.91% | 2.03% | -1.67% | 37.0 |
| 4h | CROSSOVER_INIT | E_FAST_20 | 58 | 37.93% | 1.38 | -0.58% | 2.81% | -1.73% | 54.0 |
| 4h | CROSSOVER_INIT | E_WEAKEN_20 | 58 | 37.93% | 1.38 | -0.58% | 2.81% | -1.73% | 54.0 |
| 1h | CROSSOVER_INIT | E_BEAR_CROSS | 249 | 26.91% | 1.37 | -0.71% | 1.51% | -1.57% | 32.0 |
| 15m | CROSSOVER_INIT | E_BEAR_CROSS | 1016 | 27.26% | 1.16 | -0.36% | 0.68% | -0.67% | 8.2 |
| 15m | PULLBACK_RECLAIM | E_STRUCT_50 | 824 | 22.94% | 1.12 | -0.23% | 0.42% | -0.38% | 3.0 |
| 1h | CROSSOVER_INIT | E_STRUCT_50 | 249 | 21.69% | 1.10 | -0.63% | 1.03% | -1.08% | 14.0 |

## Frozen champion replication

No development candidate passed the preregistered eligibility gates.

## Scientific note

- Entries and exits are causal: completed-candle signal, execution at next candle open.
- External/reference-validation were not used to select the champion.
- No fees/slippage are included, so marginal gross edges are not promotable.
- No old discovery result and no live BBC logic was changed.
