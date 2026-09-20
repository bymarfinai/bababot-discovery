# BNB B38-S14 — Post-TP1 Continuation Character

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

## Eligible post-TP1 population

Only baseline E2 WINs with a causal TP2 above TP1 are eligible.

| Period | Eligible | TP2 before structural SL | TP2 before BE | Med TP1 | Med TP2 | Med extension gap |
|---|---:|---:|---:|---:|---:|---:|
| DEV | 288 | 241 (83.7%) | 178 (61.8%) | 0.200R | 0.447R | 0.122R |
| REF | 178 | 162 (91.0%) | 115 (64.6%) | 0.155R | 0.350R | 0.105R |

## Structural state results

A TP2 touch that happens before a state can complete is recorded separately rather than credited as a predictive signal.

| Period | State | Signals | Coverage | TP2 before signal | TP2 success after signal | Strict TP2 before BE | False signals | Continuation capture* | Median delay |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | ACCEPT | 80 | 27.8% | 107 | 60/80 (75.0%) | 35/80 (43.8%) | 20 | 167/241 (69.3%) | 0.0m |
| DEV | ACCEPT_HOLD | 41 | 14.2% | 135 | 25/41 (61.0%) | 16/41 (39.0%) | 16 | 160/241 (66.4%) | 5.0m |
| DEV | ACCEPT_HOLD_BREAK | 8 | 2.8% | 80 | 5/8 (62.5%) | 4/8 (50.0%) | 3 | 85/241 (35.3%) | 10.0m |
| DEV | RECLAIM_HOLD_BREAK | 36 | 12.5% | 217 | 25/36 (69.4%) | 18/36 (50.0%) | 11 | 241/241 (100.0%) | 45.0m |
| REF | ACCEPT | 39 | 21.9% | 65 | 34/39 (87.2%) | 22/39 (56.4%) | 5 | 99/162 (61.1%) | 0.0m |
| REF | ACCEPT_HOLD | 19 | 10.7% | 84 | 15/19 (78.9%) | 9/19 (47.4%) | 4 | 99/162 (61.1%) | 5.0m |
| REF | ACCEPT_HOLD_BREAK | 5 | 2.8% | 62 | 5/5 (100.0%) | 3/5 (60.0%) | 0 | 67/162 (41.4%) | 10.0m |
| REF | RECLAIM_HOLD_BREAK | 20 | 11.2% | 143 | 19/20 (95.0%) | 15/20 (75.0%) | 1 | 162/162 (100.0%) | 35.0m |

\*Continuation capture includes TP2 moves that completed before a slower confirmation signal; those are not counted as signal wins.

## Year stability

| Year | State | Eligible | Signals | Coverage | Success after signal | Strict success | TP2 before signal |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2022 | ACCEPT | 103 | 23 | 22.3% | 78.3% | 39.1% | 37 |
| 2022 | ACCEPT_HOLD | 103 | 11 | 10.7% | 63.6% | 36.4% | 47 |
| 2022 | ACCEPT_HOLD_BREAK | 103 | 2 | 1.9% | 50.0% | 50.0% | 25 |
| 2022 | RECLAIM_HOLD_BREAK | 103 | 12 | 11.7% | 83.3% | 58.3% | 77 |
| 2023 | ACCEPT | 91 | 38 | 41.8% | 71.1% | 42.1% | 33 |
| 2023 | ACCEPT_HOLD | 91 | 23 | 25.3% | 60.9% | 43.5% | 42 |
| 2023 | ACCEPT_HOLD_BREAK | 91 | 5 | 5.5% | 80.0% | 60.0% | 31 |
| 2023 | RECLAIM_HOLD_BREAK | 91 | 15 | 16.5% | 66.7% | 60.0% | 67 |
| 2024 | ACCEPT | 94 | 19 | 20.2% | 78.9% | 52.6% | 37 |
| 2024 | ACCEPT_HOLD | 94 | 7 | 7.4% | 57.1% | 28.6% | 46 |
| 2024 | ACCEPT_HOLD_BREAK | 94 | 1 | 1.1% | 0.0% | 0.0% | 24 |
| 2024 | RECLAIM_HOLD_BREAK | 94 | 9 | 9.6% | 55.6% | 22.2% | 73 |
| 2025 | ACCEPT | 120 | 23 | 19.2% | 91.3% | 73.9% | 47 |
| 2025 | ACCEPT_HOLD | 120 | 10 | 8.3% | 80.0% | 60.0% | 62 |
| 2025 | ACCEPT_HOLD_BREAK | 120 | 2 | 1.7% | 100.0% | 100.0% | 48 |
| 2025 | RECLAIM_HOLD_BREAK | 120 | 13 | 10.8% | 100.0% | 84.6% | 99 |
| 2026 | ACCEPT | 58 | 16 | 27.6% | 81.2% | 31.2% | 18 |
| 2026 | ACCEPT_HOLD | 58 | 9 | 15.5% | 77.8% | 33.3% | 22 |
| 2026 | ACCEPT_HOLD_BREAK | 58 | 3 | 5.2% | 100.0% | 33.3% | 14 |
| 2026 | RECLAIM_HOLD_BREAK | 58 | 7 | 12.1% | 85.7% | 57.1% | 44 |

## Interpretation boundary
S14 is a character-discovery stage only.
No partial sizing, runner allocation, TP promotion, or stop modification is selected here.
A useful continuation character should improve post-signal TP2 reliability without collapsing coverage or degrading sharply from DEV to REF.
