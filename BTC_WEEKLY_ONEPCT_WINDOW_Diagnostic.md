# BTC Weekly 1% Winning-Window Diagnostic

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00**, official H1 rows **58,152**. Complete ISO weeks: **345**.

Diagnostic only, not a live selector. For every completed H1/H4 bar, entry is the next bar open. LONG and SHORT are evaluated separately against a symmetric **+1% TP / -1% SL** until the end of the same ISO week. Same-bar TP+SL ambiguity is adverse-first. A `winning window` means at least one direction reaches +1% before -1% from that next-open entry.

| TF | Weeks with >=1 winning window | Min | P10 | Median | Mean | P90 | Max | Median candidates/week |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| H1 | 345/345 (100.00%) | 78 | 137.8 | 161.0 | 155.6 | 166.0 | 167 | 167.0 |
| H4 | 345/345 (100.00%) | 17 | 29.0 | 37.0 | 35.7 | 41.0 | 41 | 41.0 |

## Weeks with the fewest winning windows

### H1

| Week | Candidates | Winning windows | Long wins | Short wins | Both-dir wins |
|---|---:|---:|---:|---:|---:|
| 2023-W32 | 167 | 78 | 44 | 34 | 0 |
| 2022-W51 | 167 | 96 | 25 | 71 | 0 |
| 2022-W49 | 167 | 99 | 48 | 51 | 0 |
| 2026-W33 | 167 | 105 | 23 | 82 | 0 |
| 2025-W38 | 167 | 109 | 46 | 63 | 0 |
| 2023-W34 | 167 | 110 | 35 | 75 | 0 |
| 2022-W52 | 167 | 111 | 6 | 105 | 0 |
| 2025-W52 | 167 | 112 | 48 | 64 | 0 |
| 2023-W27 | 167 | 113 | 53 | 60 | 0 |
| 2025-W37 | 167 | 113 | 95 | 18 | 0 |

### H4

| Week | Candidates | Winning windows | Long wins | Short wins | Both-dir wins |
|---|---:|---:|---:|---:|---:|
| 2021-W20 | 41 | 17 | 8 | 9 | 0 |
| 2020-W12 | 41 | 18 | 7 | 11 | 0 |
| 2023-W32 | 41 | 19 | 12 | 7 | 0 |
| 2021-W01 | 41 | 21 | 10 | 11 | 0 |
| 2021-W02 | 41 | 22 | 11 | 11 | 0 |
| 2021-W21 | 41 | 22 | 9 | 13 | 0 |
| 2020-W11 | 41 | 23 | 7 | 16 | 0 |
| 2022-W19 | 41 | 23 | 10 | 13 | 0 |
| 2022-W51 | 41 | 23 | 6 | 17 | 0 |
| 2023-W40 | 41 | 23 | 16 | 7 | 0 |
