# B27C — 4H Swing High/Low “Tektok” Before Breakout

Source coverage: **100.0000%**. Source trades: frozen B27A 4H R2. No trading rule changed.

Definition: latest causally-confirmed 3-bar swing high and swing low before the B27A signal candle. A test candle wicks to/through a swing boundary but closes back inside. Consecutive tests of the same side are collapsed into one side visit; `side_switches` counts H→L or L→H changes. The breakout candle itself is excluded from the pre-breakout count.

## Does B27A actually break the latest swing range?

| Partition | B27A 4H R2 trades with swing context | True swing breakout | Share |
|---|---:|---:|---:|
| external | 228 | 150 | 65.79% |
| development | 483 | 289 | 59.83% |
| reference_validation | 343 | 199 | 58.02% |
| august | 4 | 3 | 75.00% |

## True swing breakouts: result by pre-breakout side switches

| Partition | Switches | N | W | L | WR | Net PF | Net exp/trade | Total net | Median test candles | Median side visits |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 0 | 150 | 62 | 88 | 41.33% | 1.33 | $3.84 | $576.10 | 0.0 | 0.0 |
| external | 1 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 2 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 3 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| external | 4+ | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | 0 | 288 | 120 | 168 | 41.67% | 1.26 | $2.24 | $645.37 | 0.0 | 0.0 |
| development | 1 | 1 | 1 | 0 | 100.00% | inf | $9.26 | $9.26 | 2.0 | 2.0 |
| development | 2 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | 3 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| development | 4+ | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 0 | 199 | 68 | 131 | 34.17% | 0.92 | $-0.58 | $-115.20 | 0.0 | 0.0 |
| reference_validation | 1 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 2 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 3 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| reference_validation | 4+ | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 0 | 3 | 0 | 3 | 0.00% | 0.00 | $-5.42 | $-16.25 | 0.0 | 0.0 |
| august | 1 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 2 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 3 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| august | 4+ | 0 | 0 | 0 | - | - | $- | $- | - | - |

## Validation true swing breakouts: raw tektok distribution

| Metric | Value |
|---|---:|
| N | 199 |
| Median upper-test candles | 0.0 |
| Median lower-test candles | 0.0 |
| Median total test candles | 0.0 |
| Median side visits | 0.0 |
| Median side switches | 0.0 |
| 75th percentile side switches | 0.0 |

Forensic only. Any apparently good switch-count subgroup is hindsight-discovered and is NOT a validated filter until tested in a new preregistered experiment.

Research only; live BBC unchanged.
