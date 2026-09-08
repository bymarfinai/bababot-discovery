# SOL LONG 15:00 UTC L0 Early Progress Specificity — A63 Result

**Gate status: SOL_LONG_15UTC_L0_EARLY_PROGRESS_SPECIFICITY_A63_SUPPORTED**

Raw SOLUSDT 5m coverage: **99.7671%**.

A63 compares frozen L0/M0 reference-invalidation losses against frozen M1 time/no-structural-fail losses at the same early ages. It is descriptive/mechanistic only; live Baba Bot is unchanged.

## Reconciliation

| Partition | Parent | Losses | L0/M0 | M1 |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 58 |
| External Validation | 281 | 166 | 13 | 16 |
| Reference Validation | 337 | 187 | 26 | 21 |

## Snapshot matching

| Partition | Age | Eligible L0 | Matched M1 | Unique controls | Max reuse |
|---|---:|---:|---:|---:|---:|
| Development | 60m | 33 | 33 | 24 | 3x |
| Development | 120m | 29 | 29 | 22 | 3x |
| External Validation | 60m | 12 | 12 | 8 | 3x |
| External Validation | 120m | 11 | 11 | 8 | 3x |
| Reference Validation | 60m | 22 | 22 | 11 | 4x |
| Reference Validation | 120m | 19 | 19 | 9 | 4x |

## Specificity replication

| Age | Feature | Dev gap/effect | Dev blocks | External gap/effect | Reference gap/effect | Full OOS |
|---:|---|---:|---:|---:|---:|---|
| 60m | running_mae_R | 0.188/0.651 | 4/4 | 0.203/1.475 | 0.236/0.802 | YES |
| 60m | close_H_R | -0.217/0.812 | 4/4 | -0.337/1.810 | -0.135/0.584 | YES |
| 60m | drawdown_from_best_R | 0.221/0.950 | 4/4 | 0.208/2.409 | -0.032/0.091 | NO |
| 120m | running_mae_R | 0.261/1.098 | 3/3 | 0.271/1.186 | 0.321/1.189 | YES |
| 120m | close_H_R | -0.221/1.046 | 2/3 | -0.257/1.038 | -0.230/0.980 | NO |
| 120m | drawdown_from_best_R | 0.064/0.311 | 2/3 | 0.243/1.057 | 0.114/0.580 | NO |

## 2-of-2 specificity rule

- `running_mae_R`: [60, 120] -> **L0-SPECIFIC**
- `close_H_R`: [60] -> **NO**
- `drawdown_from_best_R`: none -> **NO**

L0-specific feature families: **running_mae_R**.

A63 does not authorize any threshold, composite, gate, derisk, position-size change, or exit. A specificity result is still not an economic intervention result.

Research only. Live Baba Bot remains unchanged.
