# BTC Fresh 4H Strong Bull → First Pullback B22D — Result

5m source rows: **698,112**; coverage: **100.0000%**

Fresh 4h STRONG activation → first lower-TF healthy pullback/reclaim only → reversal-state exit. Fakeout forensic uses only pre-entry features.

## Strategy — development leaderboard

| Entry TF | Regime | Exit | N | WR | PF | Median ret | Median MFE | Median MAE | Hold h | Eligible |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| 5m | R4_FRESH | X_4H_WEAK | 136 | 35.29% | 1.70 | -0.85% | 2.44% | -1.59% | 45.7 | NO |
| 15m | R4_FRESH | X_4H_WEAK | 104 | 32.69% | 1.49 | -1.00% | 2.01% | -2.13% | 50.5 | NO |
| 15m | R1H4_FRESH | X_1H_WEAK | 70 | 34.29% | 1.42 | -0.49% | 0.93% | -0.95% | 8.5 | NO |
| 5m | R1H4_FRESH | X_4H_WEAK | 122 | 32.79% | 1.40 | -0.92% | 2.47% | -1.71% | 52.0 | NO |
| 15m | R1H4_FRESH | X_4H_WEAK | 70 | 34.29% | 1.33 | -0.89% | 1.61% | -2.00% | 47.6 | NO |
| 5m | R4_FRESH | X_1H_WEAK | 136 | 32.35% | 1.32 | -0.34% | 1.19% | -0.72% | 11.3 | NO |
| 5m | R1H4_FRESH | X_1H_WEAK | 122 | 33.61% | 1.29 | -0.47% | 1.30% | -0.85% | 13.7 | NO |
| 15m | R4_FRESH | X_1H_WEAK | 104 | 26.92% | 1.11 | -0.53% | 0.99% | -0.92% | 7.9 | NO |

## Strategy replication

No development candidate passed the frozen eligibility gates.

## Fakeout label rates

| Partition | Entry TF | Regime | N | Follow | Fakeout | Ambig | Follow rate (non-amb) |
|---|---|---|---:|---:|---:|---:|---:|
| august | 15m | R1H4_FRESH | 1 | 1 | 0 | 0 | 100.00% |
| august | 15m | R4_FRESH | 3 | 1 | 1 | 1 | 50.00% |
| august | 5m | R1H4_FRESH | 4 | 1 | 2 | 1 | 33.33% |
| august | 5m | R4_FRESH | 4 | 1 | 2 | 1 | 33.33% |
| development | 15m | R1H4_FRESH | 70 | 40 | 29 | 1 | 57.97% |
| development | 15m | R4_FRESH | 104 | 66 | 37 | 1 | 64.08% |
| development | 5m | R1H4_FRESH | 122 | 86 | 36 | 0 | 70.49% |
| development | 5m | R4_FRESH | 136 | 89 | 47 | 0 | 65.44% |
| external | 15m | R1H4_FRESH | 57 | 36 | 21 | 0 | 63.16% |
| external | 15m | R4_FRESH | 95 | 55 | 40 | 0 | 57.89% |
| external | 5m | R1H4_FRESH | 102 | 67 | 35 | 0 | 65.69% |
| external | 5m | R4_FRESH | 122 | 69 | 53 | 0 | 56.56% |
| reference_validation | 15m | R1H4_FRESH | 38 | 24 | 14 | 0 | 63.16% |
| reference_validation | 15m | R4_FRESH | 50 | 29 | 21 | 0 | 58.00% |
| reference_validation | 5m | R1H4_FRESH | 56 | 32 | 24 | 0 | 57.14% |
| reference_validation | 5m | R4_FRESH | 63 | 32 | 31 | 0 | 50.79% |

## Stable pre-entry fakeout discriminators

No feature met the frozen cross-partition SMD replication rule.

## Shallow fakeout tree (development-only)

```text
|--- h1_ext20 <= 0.00
|   |--- volume_expansion_60m <= 0.93
|   |   |--- class: 0
|   |--- volume_expansion_60m >  0.93
|   |   |--- class: 0
|--- h1_ext20 >  0.00
|   |--- ret_60m <= 0.00
|   |   |--- class: 1
|   |--- ret_60m >  0.00
|   |   |--- class: 1
```

| Partition | Selected N | Follow rate | Baseline | Lift |
|---|---:|---:|---:|---:|
| development | 27 | 96.30% | 65.44% | 30.86% |
| external | 24 | 50.00% | 56.56% | -6.56% |
| reference_validation | 11 | 54.55% | 50.79% | 3.75% |

Tree is forensic only; it is not a promoted trading filter in B22D.

## Causality / interpretation

- All 1h/4h states are shifted to candle-close availability before use.
- Aggregate taker flow is kline-level flow, not L2/order-book evidence.
- August 2026 is diagnostic only.
- Live BBC remains untouched.
