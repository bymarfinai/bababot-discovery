# SOL LONG H1 Loss Anatomy — A3 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A3 is forensic only: frozen A2 `E0_RESTING_H -> E40` trades are not filtered, rescored, or altered.

## Parent parity / overall economics

| Role | Partition | N | Wins | Losses | PF | Gross profit | Gross loss | Net |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | 617 | 276 | 341 | 1.26 | $1545.33 | $1231.27 | $314.06 |
| CENTRAL | external | 273 | 99 | 174 | 1.46 | $1100.89 | $753.35 | $347.53 |
| CENTRAL | reference_validation | 317 | 119 | 198 | 1.16 | $580.56 | $498.60 | $81.96 |
| CLOCK_SUPPORT | external | 284 | 103 | 181 | 1.52 | $1122.85 | $737.80 | $385.05 |
| CLOCK_SUPPORT | reference_validation | 316 | 131 | 185 | 1.58 | $632.02 | $399.49 | $232.52 |
| REF_SUPPORT | external | 300 | 120 | 180 | 1.42 | $1152.94 | $814.65 | $338.29 |
| REF_SUPPORT | reference_validation | 349 | 148 | 201 | 1.23 | $589.74 | $480.89 | $108.84 |

## Central Development loss taxonomy

| Loss class | N | Share losers | Gross-loss $ | Share gross loss | Median loss | Median MFE | Median MAE | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | 37 | 10.9% | $571.53 | 46.4% | $14.00 | 0.073R | 1.214R | 195m |
| L1_NEVER_BREAK_TIME | 59 | 17.3% | $422.23 | 34.3% | $6.17 | 0.069R | 0.519R | 435m |
| L2_BREAK_FAST_FAIL_5M | 116 | 34.0% | $123.00 | 10.0% | $0.84 | 0.114R | 0.170R | 10m |
| L4_BREAK_FAIL_30M | 56 | 16.4% | $47.59 | 3.9% | $0.63 | 0.209R | 0.151R | 25m |
| L3_BREAK_FAST_FAIL_10M | 41 | 12.0% | $41.61 | 3.4% | $0.62 | 0.143R | 0.162R | 15m |
| L5_BREAK_FAIL_LATE | 32 | 9.4% | $25.32 | 2.1% | $0.47 | 0.305R | 0.130R | 62m |

## Central Development fixed causal snapshots

| Snapshot | Outcome | N observable | Median close vs H | Median running MFE | Median running MAE | Break confirmed | Median closes >H |
|---|---|---:|---:|---:|---:|---:|---:|
| +5m | LOSS | 341 | 0.004R | 0.055R | 0.129R | 53.1% | 1.0 |
| +5m | WIN | 276 | -0.013R | 0.066R | 0.161R | 41.3% | 0.0 |
| +10m | LOSS | 340 | -0.030R | 0.088R | 0.149R | 66.5% | 1.0 |
| +10m | WIN | 275 | 0.053R | 0.164R | 0.184R | 56.4% | 1.0 |
| +15m | LOSS | 340 | -0.037R | 0.107R | 0.164R | 70.9% | 1.0 |
| +15m | WIN | 212 | -0.023R | 0.112R | 0.187R | 46.7% | 0.0 |
| +30m | LOSS | 168 | -0.081R | 0.109R | 0.187R | 54.2% | 1.0 |
| +30m | WIN | 154 | -0.074R | 0.081R | 0.237R | 42.9% | 0.0 |

## OOS replication of loss classes

| Role | Partition | Dominant gross-loss class | Share gross loss | Never-break gross-loss share | <=30m failed-break gross-loss share |
|---|---|---|---:|---:|---:|
| CENTRAL | development | L0_NEVER_BREAK_REFERENCE_INVALIDATION | 46.4% | 80.7% | 17.2% |
| CENTRAL | external | L0_NEVER_BREAK_REFERENCE_INVALIDATION | 47.3% | 67.7% | 28.2% |
| CENTRAL | reference_validation | L1_NEVER_BREAK_TIME | 46.0% | 79.6% | 17.6% |
| CLOCK_SUPPORT | external | L0_NEVER_BREAK_REFERENCE_INVALIDATION | 50.2% | 68.4% | 28.1% |
| CLOCK_SUPPORT | reference_validation | L1_NEVER_BREAK_TIME | 40.2% | 73.6% | 24.6% |
| REF_SUPPORT | external | L0_NEVER_BREAK_REFERENCE_INVALIDATION | 55.3% | 72.6% | 23.5% |
| REF_SUPPORT | reference_validation | L0_NEVER_BREAK_REFERENCE_INVALIDATION | 47.1% | 78.6% | 19.8% |

## Tail damage

- Central Development maximum single loss: **$46.52**.
- Central Development top-10 worst-loss class composition: **{'L0_NEVER_BREAK_REFERENCE_INVALIDATION': 9, 'L1_NEVER_BREAK_TIME': 1}**.

## Decision

**Status: SOL_LONG_H1_LOSS_ANATOMY_A3_COMPLETED**

Central Development never-break classes contribute **80.7%** of gross loss; confirmed-break failures within 30m contribute **17.2%**.
Largest Central Development gross-loss class: **L0_NEVER_BREAK_REFERENCE_INVALIDATION (46.4%)**.

A3 does not authorize a filter or stop change. Any intervention must be separately preregistered and judged on preserved winners plus actual PF/expectancy under OOS and stress.

Research only. Live Baba Bot remains unchanged.
