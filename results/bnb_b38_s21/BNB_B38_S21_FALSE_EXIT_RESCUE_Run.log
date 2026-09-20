# BNB B38-S21 — False-Exit Winner Rescue

Population is frozen S20 Q4-wide clean failure triggers only.

## Recovery separator audit

| Period | Recovery state | Winner recovered | Loss leaked | Precision(win) | Med recovery time WIN | Med recovery time LOSS | Adverse R WIN | Adverse R LOSS |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| DEV | NEXT5_RECLAIM | 5/10 (50.0%) | 9/21 (42.9%) | 35.7% | 5.0m | 5.0m | -0.380R | -0.399R |
| DEV | NEXT15_RECLAIM | 5/10 (50.0%) | 9/21 (42.9%) | 35.7% | 10.0m | 15.0m | -0.581R | -0.563R |
| DEV | RECLAIM_HOLD | 6/10 (60.0%) | 9/21 (42.9%) | 40.0% | 12.5m | 15.0m | -0.621R | -0.686R |
| DEV | RECLAIM_FAILURE_HIGH_BREAK | 9/10 (90.0%) | 11/21 (52.4%) | 45.0% | 40.0m | 30.0m | -0.581R | -0.511R |
| DEV | RECLAIM_BREAK_LEVEL | 9/10 (90.0%) | 9/21 (42.9%) | 50.0% | 115.0m | 45.0m | -0.581R | -0.483R |
| REF | NEXT5_RECLAIM | 1/2 (50.0%) | 1/6 (16.7%) | 50.0% | 5.0m | 5.0m | -0.213R | -0.432R |
| REF | NEXT15_RECLAIM | 1/2 (50.0%) | 0/6 (0.0%) | 100.0% | 5.0m | —m | -0.213R | —R |
| REF | RECLAIM_HOLD | 2/2 (100.0%) | 1/6 (16.7%) | 66.7% | 27.5m | 15.0m | -0.393R | -0.643R |
| REF | RECLAIM_FAILURE_HIGH_BREAK | 2/2 (100.0%) | 2/6 (33.3%) | 50.0% | 60.0m | 35.0m | -0.499R | -0.561R |
| REF | RECLAIM_BREAK_LEVEL | 2/2 (100.0%) | 0/6 (0.0%) | 100.0% | 27.5m | —m | -0.393R | —R |

## Fixed-horizon executable rescue policies

| Period | Policy | Trigger N | Positive/Negative | Trigger Exp | Trigger Total R |
|---|---|---:|---:|---:|---:|
| DEV | NEXT5_RECLAIM | 31 | 5/26 | -0.550R | -17.047R |
| REF | NEXT5_RECLAIM | 8 | 1/7 | -0.456R | -3.649R |
| DEV | NEXT15_RECLAIM | 31 | 5/26 | -0.531R | -16.472R |
| REF | NEXT15_RECLAIM | 8 | 1/7 | -0.402R | -3.217R |

## Full E2 portfolio comparison

| Period | Config | Positive/Negative | Exp | Total R | Max DD |
|---|---|---:|---:|---:|---:|
| DEV | BASELINE | 325/115 | 0.035R | 15.312R | 15.370R |
| DEV | S20_IMMEDIATE_EXIT | 315/125 | 0.047R | 20.478R | 12.418R |
| DEV | NEXT5_RESCUE | 320/120 | 0.039R | 17.019R | 14.123R |
| DEV | NEXT15_RESCUE | 320/120 | 0.040R | 17.593R | 12.904R |
| REF | BASELINE | 201/71 | -0.002R | -0.519R | 11.135R |
| REF | S20_IMMEDIATE_EXIT | 199/73 | 0.005R | 1.405R | 11.222R |
| REF | NEXT5_RESCUE | 200/72 | 0.004R | 1.186R | 11.355R |
| REF | NEXT15_RESCUE | 200/72 | 0.006R | 1.618R | 10.835R |

## Annual recovery stability

| Year | State | Winner recovered | Loss leaked | Precision(win) |
|---:|---|---:|---:|---:|
| 2022 | NEXT5_RECLAIM | 2/5 (40.0%) | 6/10 (60.0%) | 25.0% |
| 2022 | NEXT15_RECLAIM | 3/5 (60.0%) | 6/10 (60.0%) | 33.3% |
| 2022 | RECLAIM_HOLD | 5/5 (100.0%) | 4/10 (40.0%) | 55.6% |
| 2022 | RECLAIM_FAILURE_HIGH_BREAK | 5/5 (100.0%) | 6/10 (60.0%) | 45.5% |
| 2022 | RECLAIM_BREAK_LEVEL | 5/5 (100.0%) | 6/10 (60.0%) | 45.5% |
| 2023 | NEXT5_RECLAIM | 0/1 (0.0%) | 1/2 (50.0%) | 0.0% |
| 2023 | NEXT15_RECLAIM | 1/1 (100.0%) | 2/2 (100.0%) | 33.3% |
| 2023 | RECLAIM_HOLD | 0/1 (0.0%) | 2/2 (100.0%) | 0.0% |
| 2023 | RECLAIM_FAILURE_HIGH_BREAK | 1/1 (100.0%) | 2/2 (100.0%) | 33.3% |
| 2023 | RECLAIM_BREAK_LEVEL | 1/1 (100.0%) | 1/2 (50.0%) | 50.0% |
| 2024 | NEXT5_RECLAIM | 3/4 (75.0%) | 2/9 (22.2%) | 60.0% |
| 2024 | NEXT15_RECLAIM | 1/4 (25.0%) | 1/9 (11.1%) | 50.0% |
| 2024 | RECLAIM_HOLD | 1/4 (25.0%) | 3/9 (33.3%) | 25.0% |
| 2024 | RECLAIM_FAILURE_HIGH_BREAK | 3/4 (75.0%) | 3/9 (33.3%) | 50.0% |
| 2024 | RECLAIM_BREAK_LEVEL | 3/4 (75.0%) | 2/9 (22.2%) | 60.0% |
| 2025 | NEXT5_RECLAIM | 1/1 (100.0%) | 0/4 (0.0%) | 100.0% |
| 2025 | NEXT15_RECLAIM | 1/1 (100.0%) | 0/4 (0.0%) | 100.0% |
| 2025 | RECLAIM_HOLD | 1/1 (100.0%) | 0/4 (0.0%) | 100.0% |
| 2025 | RECLAIM_FAILURE_HIGH_BREAK | 1/1 (100.0%) | 0/4 (0.0%) | 100.0% |
| 2025 | RECLAIM_BREAK_LEVEL | 1/1 (100.0%) | 0/4 (0.0%) | 100.0% |
| 2026 | NEXT5_RECLAIM | 0/1 (0.0%) | 1/2 (50.0%) | 0.0% |
| 2026 | NEXT15_RECLAIM | 0/1 (0.0%) | 0/2 (0.0%) | — |
| 2026 | RECLAIM_HOLD | 1/1 (100.0%) | 1/2 (50.0%) | 50.0% |
| 2026 | RECLAIM_FAILURE_HIGH_BREAK | 1/1 (100.0%) | 2/2 (100.0%) | 33.3% |
| 2026 | RECLAIM_BREAK_LEVEL | 1/1 (100.0%) | 0/2 (0.0%) | 100.0% |

## Stop rule
This is the only false-exit rescue discovery round.
If recovery separation is not consistent in DEV and REF, no further rescue tuning is allowed before expansion-character discovery.
