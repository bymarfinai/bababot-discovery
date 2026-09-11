# SOL Economic-First — Four-Winner Reference Validation Result

Raw SOLUSDT 5m coverage: **99.7698%**.

Primary forward OOS: **2025-01-01 UTC through 2026-07-30 UTC (exclusive end)**.
August 2026 remained unopened.
No rule, lookback, hold, clock, fee, feature definition, or gate threshold was changed.

## Development parity audit

All four frozen winners reproduced their Development candidate gate plus frozen N/WR/DD checkpoints before OOS interpretation.

| Hour | Character | LB | Hold | N | WR | Exp | PF | DD | Anchors | Gate |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| H04 | EFF_LOW__RANGE_HIGH | 360m | 240m | 201 | 62.19% | $+2.89 | 1.861 | $+118.37 | 4/4 | PASS |
| H15 | EFF_HIGH__RANGE_LOW | 240m | 960m | 171 | 60.82% | $+5.87 | 2.403 | $+119.05 | 3/3 | PASS |
| H22 | EFF_LOW__EXT_MID | 240m | 360m | 285 | 59.30% | $+2.52 | 1.940 | $+93.85 | 4/4 | PASS |
| H23 | DRIVE_DOWN__STR_B80_100 | 15m | 120m | 306 | 60.13% | $+2.09 | 1.911 | $+90.21 | 4/4 | PASS |

## Reference Validation

| Hour (WIB) | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Loss streak | Anchors | Anchor | Pooled | Era | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| H04 (11:00-12:00) | EFF_LOW__RANGE_HIGH | 360m | 240m | 84 | 51.19% | $-86.72 | $-1.03 | 0.763 | $+206.17 | 9 | 0/0 | FAIL | FAIL | FAIL | **REFERENCE_NOT_VALIDATED** |
| H15 (22:00-23:00) | EFF_HIGH__RANGE_LOW | 240m | 960m | 68 | 48.53% | $-48.10 | $-0.71 | 0.888 | $+224.53 | 8 | 0/0 | FAIL | FAIL | FAIL | **REFERENCE_NOT_VALIDATED** |
| H22 (05:00-06:00) | EFF_LOW__EXT_MID | 240m | 360m | 125 | 51.20% | $-175.32 | $-1.40 | 0.605 | $+223.38 | 6 | 0/0 | FAIL | FAIL | FAIL | **REFERENCE_NOT_VALIDATED** |
| H23 (06:00-07:00) | DRIVE_DOWN__STR_B80_100 | 15m | 120m | 162 | 50.62% | $-67.87 | $-0.42 | 0.809 | $+83.19 | 7 | 0/3 | FAIL | FAIL | FAIL | **REFERENCE_NOT_VALIDATED** |

## Forward-year detail

### H04

| Year | N | WR | Net | Exp | PF | DD | Basic year gate | WR>=55% |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2025 | 43 | 55.81% | $+28.83 | $+0.67 | 1.184 | $+77.27 | PASS | YES |
| 2026 | 41 | 46.34% | $-115.56 | $-2.82 | 0.448 | $+157.43 | FAIL | NO |

### H15

| Year | N | WR | Net | Exp | PF | DD | Basic year gate | WR>=55% |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2025 | 49 | 51.02% | $-82.75 | $-1.69 | 0.791 | $+207.03 | FAIL | NO |
| 2026 | 19 | 42.11% | $+34.65 | $+1.82 | 2.090 | $+17.50 | FAIL | NO |

### H22

| Year | N | WR | Net | Exp | PF | DD | Basic year gate | WR>=55% |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2025 | 73 | 47.95% | $-129.74 | $-1.78 | 0.566 | $+141.62 | FAIL | NO |
| 2026 | 52 | 55.77% | $-45.58 | $-0.88 | 0.686 | $+106.91 | FAIL | YES |

### H23

| Year | N | WR | Net | Exp | PF | DD | Basic year gate | WR>=55% |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 2025 | 98 | 52.04% | $-8.27 | $-0.08 | 0.959 | $+42.93 | FAIL | NO |
| 2026 | 64 | 48.44% | $-59.60 | $-0.93 | 0.613 | $+69.23 | FAIL | NO |

## Frozen decision

**SOL_4WINNER_REFERENCE_VALIDATION_NONE_PASS**

Validated winners: **0/4**.

A failed winner is not retuned or replaced after seeing Reference Validation. August 2026 remains unopened as the next final holdout.

Research/shadow only. No live promotion or profit guarantee.
