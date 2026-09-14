# SOL Adaptive Structure Detector v2 — Sequence/Path Analog Walk-Forward

- Data coverage: **99.7698%**
- Structural events: **3266**
- Online predictions: **3146**
- No event may use an analog whose 60m outcome was not already known at prediction time.
- Analog memory: trailing **730 days**, K=60, minimum pool=120.
- Sequence: 18 time-normalized points from ORB anchor through BOS, using OHLC position vs ORB plus anchored-VWAP gap.
- Frozen trade gate: P(win) >= 60%, predicted net 60m edge >= 0.15%, effective analog N >= 20.
- 2025+ remains closed.

## Ranking diagnostics

- ROC AUC P(win): **0.5262**
- Brier score: **0.2433**
- Spearman(predicted edge, actual return): **0.0029**
- Pearson(predicted edge, actual return): **0.0128**

## Economics

| Selection | N | WR | Expectancy | Net PnL | PF | Max DD | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| All eligible | 3146 | 40.94% | -0.1011% | $-1589.97 | 0.800 | $1685.56 | 20 |
| Predicted TRADE | 10 | 30.00% | 0.0172% | $0.86 | 1.026 | $17.02 | 3 |

## Edge quartiles

| Q | N | Mean predicted edge | WR | Actual expectancy | PF |
|---:|---:|---:|---:|---:|---:|
| 1 | 787 | -0.2777% | 38.63% | -0.0952% | 0.810 |
| 2 | 786 | -0.1517% | 42.75% | -0.1130% | 0.757 |
| 3 | 786 | -0.0592% | 39.19% | -0.1556% | 0.694 |
| 4 | 787 | 0.0860% | 43.20% | -0.0406% | 0.925 |

## Calendar-year predicted TRADE

| Year | N | WR | Expectancy | Net PnL | PF |
|---|---:|---:|---:|---:|---:|
| 2020 | 0 | — | — | $0.00 | — |
| 2021 | 2 | 50.00% | 1.2760% | $12.76 | 2.425 |
| 2022 | 3 | 33.33% | -0.5161% | -$7.74 | 0.398 |
| 2023 | 5 | 20.00% | -0.1662% | -$4.16 | 0.634 |
| 2024 | 0 | — | — | $0.00 | — |

## Verdict

**REJECT_V2_SEQUENCE_ANALOG**

- Ranking gate: PASS only in the literal preregistered sense; the actual Spearman signal is near zero.
- Trade economics gate: **FAIL**.
- Multi-year stability gate: **FAIL** (0 positive trade years with N>=5).

No threshold, K/window value, sequence length, or gate was changed after reading the result. 2025+ remains unopened.