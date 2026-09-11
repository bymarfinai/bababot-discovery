# SOL Economic-First — Frozen-Winner OOS Validation Result

Raw SOLUSDT 5m coverage: **99.7698%**.

The four Development winners were evaluated without rescanning or changing rule, lookback, hold, clocks, fee, or validation thresholds.
External = 2020–2021; Reference Validation = 2025-01-01 through 2026-07-29. August 2026 remains excluded.

## Formal replication summary

| Hour | WIB | Frozen character | LB | Hold | OOS N | WR | Net | Exp | PF | DD | Loss streak | External | RefVal | Pooled | Verdict |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| H04 | 11:00-12:00 | EFF_LOW__RANGE_HIGH | 360m | 240m | 186 | 61.29% | $+343.56 | $+1.85 | 1.293 | $+307.78 | 9 | FAIL | FAIL | FAIL | OOS_NOT_REPLICATED |
| H15 | 22:00-23:00 | EFF_HIGH__RANGE_LOW | 240m | 960m | 152 | 44.08% | $-325.45 | $-2.14 | 0.776 | $+440.91 | 10 | FAIL | FAIL | FAIL | OOS_NOT_REPLICATED |
| H22 | 05:00-06:00 | EFF_LOW__EXT_MID | 240m | 360m | 226 | 46.90% | $-163.33 | $-0.72 | 0.861 | $+330.56 | 11 | FAIL | FAIL | FAIL | OOS_NOT_REPLICATED |
| H23 | 06:00-07:00 | DRIVE_DOWN__STR_B80_100 | 15m | 120m | 287 | 49.83% | $+255.56 | $+0.89 | 1.245 | $+347.13 | 7 | FAIL | FAIL | FAIL | OOS_NOT_REPLICATED |

## Partition detail

| Hour | Partition | N | WR | Net | Exp | PF | DD | Loss streak | Support gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| H04 | external | 102 | 69.61% | $+430.28 | $+4.22 | 1.534 | $+307.78 | 7 | FAIL |
| H04 | reference_validation | 84 | 51.19% | $-86.72 | $-1.03 | 0.763 | $+206.17 | 9 | FAIL |
| H15 | external | 84 | 40.48% | $-277.35 | $-3.30 | 0.729 | $+440.91 | 9 | FAIL |
| H15 | reference_validation | 68 | 48.53% | $-48.10 | $-0.71 | 0.888 | $+224.53 | 8 | FAIL |
| H22 | external | 101 | 41.58% | $+11.99 | $+0.12 | 1.016 | $+218.29 | 11 | FAIL |
| H22 | reference_validation | 125 | 51.20% | $-175.32 | $-1.40 | 0.605 | $+223.38 | 6 | FAIL |
| H23 | external | 125 | 48.80% | $+323.43 | $+2.59 | 1.471 | $+347.13 | 7 | FAIL |
| H23 | reference_validation | 162 | 50.62% | $-67.87 | $-0.42 | 0.809 | $+83.19 | 7 | FAIL |

## Formal verdict

**0 / 4 frozen hourly winners replicated out-of-sample.**

**Status: SOL_ECONOMIC_FIRST_OOS_0_OF_4_REPLICATED**

No failed winner is replaced by its Development runner-up in this experiment. No threshold relaxation or post-hoc subset is permitted.

Research/shadow only. This validation is not a live-trading authorization or profit guarantee.
