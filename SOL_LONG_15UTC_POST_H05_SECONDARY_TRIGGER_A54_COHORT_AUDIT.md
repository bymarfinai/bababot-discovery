# A54 Frozen POST_H05 Cohort Technical Audit

Raw coverage: **99.7671%**.

This is a technical audit of the already-frozen A53 `G2_POST_H05` guard-exit cohort. It does not change A54 thresholds, candidates, or gates.

Total G2 guard exits: **505**.

| Partition | Parent won | Parent exit reason | Parent loss class | N |
|---|---:|---|---|---:|
| development | False | FAILED_BREAK | L2_BREAK_FAST_FAIL_5M | 71 |
| development | False | FAILED_BREAK | L3_BREAK_FAST_FAIL_10M | 37 |
| development | False | FAILED_BREAK | L4_BREAK_FAIL_30M | 50 |
| development | False | FAILED_BREAK | L5_BREAK_FAIL_LATE | 24 |
| development | True | FAILED_BREAK | WIN | 2 |
| development | True | TARGET | WIN | 31 |
| development | True | TIME | WIN | 4 |
| external | False | FAILED_BREAK | L2_BREAK_FAST_FAIL_5M | 38 |
| external | False | FAILED_BREAK | L3_BREAK_FAST_FAIL_10M | 17 |
| external | False | FAILED_BREAK | L4_BREAK_FAIL_30M | 30 |
| external | False | FAILED_BREAK | L5_BREAK_FAIL_LATE | 25 |
| external | True | FAILED_BREAK | WIN | 3 |
| external | True | TARGET | WIN | 32 |
| external | True | TIME | WIN | 3 |
| reference_validation | False | FAILED_BREAK | L2_BREAK_FAST_FAIL_5M | 50 |
| reference_validation | False | FAILED_BREAK | L3_BREAK_FAST_FAIL_10M | 21 |
| reference_validation | False | FAILED_BREAK | L4_BREAK_FAIL_30M | 24 |
| reference_validation | False | FAILED_BREAK | L5_BREAK_FAIL_LATE | 11 |
| reference_validation | True | FAILED_BREAK | WIN | 1 |
| reference_validation | True | TARGET | WIN | 29 |
| reference_validation | True | TIME | WIN | 2 |

## Partition totals

| Partition | G2 exits | PnL>0 parent | TARGET parent | non-TARGET positive | M2 failed-break parent | other nonpositive |
|---|---:|---:|---:|---:|---:|---:|
| development | 219 | 37 | 31 | 6 | 182 | 0 |
| external | 148 | 38 | 32 | 6 | 110 | 0 |
| reference_validation | 138 | 32 | 29 | 3 | 106 | 0 |
