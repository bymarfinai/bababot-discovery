# SOL H23 Exact-Anchor All-Era Discovery Result

Raw SOLUSDT 5m coverage: **99.7669%**.
Discovery history ends: **2026-07-30T00:00:00+00:00** exclusive.
Direction: **LONG only**.
Four quarter-hour anchors were evaluated independently; no anchor pooling was used.
Search space: **12,960** candidates (4 anchors × 90 rules × 6 lookbacks × 6 holds).
Full-gate passers: **20**.

## Selected robust character per exact anchor

| UTC | WIB | Character | LB | Hold | N | WR | Net | Exp | PF | DD | Min-era WR | Min-era Exp | Ext WR/Exp | Dev WR/Exp | Ref WR/Exp |
|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 23:00 | 06:00 | DRIVE_DOWN__STR_B80_100 | 30m | 240m | 145 | 61.38% | $+395.22 | $+2.73 | 1.716 | $+85.70 | 57.78% | $+0.32 | 67.86%/$+6.92 | 61.11%/$+2.59 | 57.78%/$+0.32 |
| 23:15 | 06:15 | DRIVE_DOWN__STR_B80_100 | 60m | 360m | 168 | 60.71% | $+531.16 | $+3.16 | 1.667 | $+113.99 | 57.14% | $+0.86 | 60.00%/$+6.73 | 63.10%/$+3.02 | 57.14%/$+0.86 |
| 23:30 | 06:30 | EFF_MID__RANGE_HIGH | 240m | 360m | 125 | 60.00% | $+343.65 | $+2.75 | 1.576 | $+87.49 | 57.14% | $+2.34 | 57.14%/$+4.62 | 58.11%/$+2.34 | 66.67%/$+2.44 |
| 23:45 | 06:45 | DRIVE_DOWN__STR_B80_100 | 30m | 360m | 148 | 62.16% | $+474.92 | $+3.21 | 1.735 | $+122.38 | 59.21% | $+1.79 | 66.67%/$+6.06 | 59.21%/$+2.70 | 64.10%/$+1.79 |

## Prior 06:45 WIB lineage check

The previously isolated **DRIVE_DOWN__STR_B80_100 / LB15 / hold120** at 23:45 UTC has N **146**, WR **58.22%**, net **$+374.37**, expectancy **$+2.56**, PF **1.933**, DD **$+97.53** across the three discovery eras.
Its all-era gate = **PASS**, combined gate = **PASS**, full gate = **PASS**.

## Scientific status

**Status: SOL_ANCHOR_LOCAL_H23_4_OF_4_ROBUST_ANCHORS**

These are all-era robust discovery candidates, not clean OOS confirmations. No August 2026 or later data influenced this scan.

Workflow run: **34630772851**. Artifact: **10276396949**. Artifact digest: **sha256:b2833b672d0625836a11b349b0c1db8805ac72e70c3765fa47b4cdab18c6ded5**.

Research/shadow only. No live-trading authorization or profit guarantee.
