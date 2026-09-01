# ETH B27DX — S1B Native-Template Full Clock Rotation — Result

ETH raw 5m coverage: **100.0000%**.

Three preregistered templates were rotated over all 48 UTC half-hour execution clocks using the exact frozen B27DX scorer.

## Template summary

| Template | Ref | Horizon | Supported clocks | Longest contiguous run | Median Dev PF | Raw density sum/wk* |
|---|---:|---:|---:|---:|---:|---:|
| NATIVE_SHORT | 240m | 300m | 2 | 1 | 1.15 | 0.824 |
| NATIVE_CENTER | 300m | 360m | 4 | 1 | 1.16 | 2.165 |
| LEGACY_BENCHMARK | 330m | 390m | 2 | 1 | 1.40 | 1.003 |

*Raw density sum is an upper-bound structural diagnostic, not a portfolio trade rate; supported clocks can overlap.*

## NATIVE_SHORT — R240/X300

| Ref start | Exec start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |
|---:|---:|---:|---:|---:|---:|---:|
| 22:30 | 02:30 | 2/3 | 1.15 | 3/3 | 3/3 | 0.447 |
| 12:00 | 16:00 | 2/3 | 1.15 | 3/3 | 3/3 | 0.377 |

Contiguous supported runs:
- **02:30** (1 points; width 0m).
- **16:00** (1 points; width 0m).

## NATIVE_CENTER — R300/X360

| Ref start | Exec start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |
|---:|---:|---:|---:|---:|---:|---:|
| 00:00 | 05:00 | 2/3 | 1.13 | 2/3 | 3/3 | 0.441 |
| 04:00 | 09:00 | 2/3 | 1.34 | 3/3 | 3/3 | 0.645 |
| 05:00 | 10:00 | 2/3 | 1.16 | 3/3 | 2/3 | 0.690 |
| 11:00 | 16:00 | 2/3 | 1.17 | 3/3 | 3/3 | 0.390 |

Contiguous supported runs:
- **05:00** (1 points; width 0m).
- **09:00** (1 points; width 0m).
- **10:00** (1 points; width 0m).
- **16:00** (1 points; width 0m).

## LEGACY_BENCHMARK — R330/X390

| Ref start | Exec start | Dev + | Dev PF | Ext + | Val + | Raw opp/week |
|---:|---:|---:|---:|---:|---:|---:|
| 04:00 | 09:30 | 3/3 | 1.50 | 3/3 | 3/3 | 0.620 |
| 10:30 | 16:00 | 2/3 | 1.30 | 2/3 | 3/3 | 0.383 |

Contiguous supported runs:
- **09:30** (1 points; width 0m).
- **16:00** (1 points; width 0m).

## Decision

**Status: ETH_S1B_NATIVE_CLOCK_EXPANSION_SUPPORTED**

- Native clock expansion vs legacy: **SUPPORTED**.
- No entry/TP/stop/runner/leverage optimization was performed.
- No live BBC changes were made.
