# SOL LONG 15:00 UTC M2 Loss-Confirmation Sequence Anatomy — A57 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A57 inspects only the first frozen H10/H05 warning candle and the 1–2 completed candles immediately before it. No post-warning candle enters a motif.

## Reconciliation

Rows: **1181**. Errors: **0**.

| Partition | Warning | Total | Failed-break | E40 target | Unresolved time |
|---|---|---:|---:|---:|---:|
| development | W10 | 300 | 233 | 63 | 4 |
| development | W05 | 219 | 184 | 31 | 4 |
| external | W10 | 192 | 133 | 54 | 5 |
| external | W05 | 148 | 113 | 32 | 3 |
| reference_validation | W10 | 184 | 134 | 48 | 2 |
| reference_validation | W05 | 138 | 107 | 29 | 2 |

## Replicated live-causal sequence motifs

| Warning | Motif | Dev fail/target | Dev gap | Dev ratio | Ext fail/target | Ext gap | RefVal fail/target | RefVal gap |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| - | No motif passed Development + both OOS gates | - | - | - | - | - | - | - |

## Strongest Development motifs

| Warning | Motif | Fail hit | Target hit | Gap | Ratio | Blocks | Dev supported | Replicated |
|---|---|---:|---:|---:|---:|---:|---|---|
| W10 | TWO_BODY_CONTRACTIONS | 3.9% | 3.2% | 0.7pp | 1.22x | 5/6 | False | False |
| W10 | TWO_NEAR_H10 | 0.0% | 0.0% | 0.0pp | -x | 0/6 | False | False |
| W10 | TWO_NEAR_H05 | 0.0% | 0.0% | 0.0pp | -x | 0/6 | False | False |
| W10 | H05_DEEPEN_FROM_H10 | 0.0% | 0.0% | 0.0pp | -x | 0/6 | False | False |
| W10 | TWO_LOWER_HIGHS | 4.7% | 4.8% | -0.0pp | 0.99x | 3/6 | False | False |
| W10 | BODY_CONTRACT_1 | 30.9% | 31.7% | -0.8pp | 0.97x | 4/6 | False | False |
| W10 | LOWER_HIGH_AND_CLOSE_1 | 11.2% | 12.7% | -1.5pp | 0.88x | 3/6 | False | False |
| W10 | LOWER_CLOSE_1 | 16.7% | 19.0% | -2.3pp | 0.88x | 3/6 | False | False |
| W05 | BODY_CONTRACT_1 | 39.1% | 25.8% | 13.3pp | 1.52x | 4/6 | False | False |
| W05 | RANGE_CONTRACT_1 | 41.8% | 32.3% | 9.6pp | 1.30x | 4/6 | False | False |
| W05 | TWO_NEAR_H10 | 12.5% | 3.2% | 9.3pp | 3.88x | 5/6 | False | False |
| W05 | H05_DEEPEN_FROM_H10 | 12.5% | 3.2% | 9.3pp | 3.88x | 5/6 | False | False |
| W05 | LOWER_HIGH_1 | 27.7% | 19.4% | 8.4pp | 1.43x | 4/6 | False | False |
| W05 | LOWER_HIGH_AND_CLOSE_1 | 21.2% | 12.9% | 8.3pp | 1.64x | 4/6 | False | False |
| W05 | TWO_LOWER_HIGHS | 9.2% | 3.2% | 6.0pp | 2.86x | 5/6 | False | False |
| W05 | LOWER_CLOSE_1 | 28.3% | 22.6% | 5.7pp | 1.25x | 4/6 | False | False |

## Report-only continuous warning-candle anatomy

These are diagnostics only; A57 does not derive a threshold from them.

| Partition | Warning | Feature | Fail median | E40 median | Gap |
|---|---|---|---:|---:|---:|
| development | W10 | close_H_R | 0.038 | 0.064 | -0.025 |
| development | W10 | high_H_R | 0.098 | 0.139 | -0.041 |
| development | W10 | body_R | 0.102 | 0.118 | -0.016 |
| development | W10 | range_R | 0.196 | 0.223 | -0.027 |
| development | W05 | close_H_R | 0.025 | 0.023 | 0.001 |
| development | W05 | high_H_R | 0.083 | 0.089 | -0.007 |
| development | W05 | body_R | 0.073 | 0.083 | -0.010 |
| development | W05 | range_R | 0.171 | 0.192 | -0.021 |
| external | W10 | close_H_R | 0.032 | 0.052 | -0.020 |
| external | W10 | high_H_R | 0.071 | 0.092 | -0.022 |
| external | W10 | body_R | 0.089 | 0.089 | -0.000 |
| external | W10 | range_R | 0.164 | 0.169 | -0.005 |
| external | W05 | close_H_R | 0.023 | 0.034 | -0.011 |
| external | W05 | high_H_R | 0.058 | 0.073 | -0.014 |
| external | W05 | body_R | 0.062 | 0.059 | 0.004 |
| external | W05 | range_R | 0.149 | 0.159 | -0.010 |
| reference_validation | W10 | close_H_R | 0.030 | 0.053 | -0.023 |
| reference_validation | W10 | high_H_R | 0.097 | 0.098 | -0.001 |
| reference_validation | W10 | body_R | 0.096 | 0.143 | -0.047 |
| reference_validation | W10 | range_R | 0.188 | 0.231 | -0.043 |
| reference_validation | W05 | close_H_R | 0.021 | 0.021 | -0.000 |
| reference_validation | W05 | high_H_R | 0.084 | 0.061 | 0.023 |
| reference_validation | W05 | body_R | 0.084 | 0.144 | -0.061 |
| reference_validation | W05 | range_R | 0.174 | 0.223 | -0.049 |

## Decision

**Status: SOL_LONG_15UTC_M2_LOSS_CONFIRMATION_SEQUENCE_A57_INCONCLUSIVE**

No A58 sequence guard is authorized from this frozen motif family.

Research only. Live Baba Bot remains unchanged.
