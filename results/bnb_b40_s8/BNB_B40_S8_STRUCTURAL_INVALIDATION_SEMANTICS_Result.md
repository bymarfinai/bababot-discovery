# BNB B40-S8 — Structural Invalidation Semantics Discovery

Frozen SD1 signature: `c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0`
S8 signature: `e48b302b244e58afd6ae6f00e80ea9483b1005f5d8d941991ffe377016d396a0`

Entry = MARKET_SD1_CLOSE. Target = anchor +1 event-R. Only structural invalidation level/semantics change.

## Invalidation audit

| Period | Candidate | Avail | Level dist | Compression | W-L | WR | Med WIN R | Med LOSS R | Loss q10 | Exp/signal | Total R | PF | GE1 retained | False stop | Survivor stopped | Consumed caught |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | PROTECTED_LOW_TOUCH | 286/286 | 1.121 event-R | 0.0% | 149-115 | 56.4% | 0.761R | -1.000R | -1.000R | -0.018R | -5.151R | 0.955 | 149/163 | 14 (8.6%) | 64/235 (27.2%) | 51/51 (100.0%) |
| DEV | PROTECTED_LOW_CLOSE5 | 286/286 | 1.121 event-R | 0.0% | 156-102 | 60.5% | 0.762R | -1.163R | -1.475R | -0.046R | -13.242R | 0.897 | 156/163 | 7 (4.3%) | 51/235 (21.7%) | 51/51 (100.0%) |
| DEV | PROTECTED_LOW_CLOSE15 | 286/286 | 1.121 event-R | 0.0% | 163-94 | 63.4% | 0.763R | -1.184R | -1.683R | -0.015R | -4.214R | 0.966 | 163/163 | 0 (0.0%) | 43/235 (18.3%) | 51/51 (100.0%) |
| DEV | REACTION_LOW_TOUCH | 286/286 | 0.236 event-R | 78.8% | 67-219 | 23.4% | 2.113R | -1.000R | -1.000R | -0.066R | -18.920R | 0.914 | 67/163 | 96 (58.9%) | 168/235 (71.5%) | 51/51 (100.0%) |
| DEV | REACTION_LOW_CLOSE5 | 286/286 | 0.236 event-R | 78.8% | 79-206 | 27.7% | 2.136R | -1.295R | -2.092R | -0.248R | -71.017R | 0.766 | 79/163 | 84 (51.5%) | 155/235 (66.0%) | 51/51 (100.0%) |
| DEV | REACTION_LOW_CLOSE15 | 286/286 | 0.236 event-R | 78.8% | 89-194 | 31.4% | 2.142R | -1.488R | -2.866R | -0.179R | -51.112R | 0.857 | 89/163 | 74 (45.4%) | 143/235 (60.9%) | 51/51 (100.0%) |
| REF | PROTECTED_LOW_TOUCH | 160/160 | 1.121 event-R | 0.0% | 87-59 | 59.6% | 0.784R | -1.000R | -1.000R | 0.046R | 7.333R | 1.124 | 87/99 | 12 (12.1%) | 36/137 (26.3%) | 23/23 (100.0%) |
| REF | PROTECTED_LOW_CLOSE5 | 160/160 | 1.121 event-R | 0.0% | 92-53 | 63.4% | 0.786R | -1.064R | -1.289R | 0.066R | 10.510R | 1.174 | 92/99 | 7 (7.1%) | 30/137 (21.9%) | 23/23 (100.0%) |
| REF | PROTECTED_LOW_CLOSE15 | 160/160 | 1.121 event-R | 0.0% | 99-44 | 69.2% | 0.787R | -1.154R | -1.429R | 0.135R | 21.552R | 1.394 | 99/99 | 0 (0.0%) | 21/137 (15.3%) | 23/23 (100.0%) |
| REF | REACTION_LOW_TOUCH | 160/160 | 0.220 event-R | 80.6% | 42-118 | 26.2% | 3.338R | -1.000R | -1.000R | 0.330R | 52.874R | 1.448 | 42/99 | 57 (57.6%) | 95/137 (69.3%) | 23/23 (100.0%) |
| REF | REACTION_LOW_CLOSE5 | 160/160 | 0.220 event-R | 80.6% | 46-112 | 29.1% | 3.439R | -1.261R | -1.833R | 0.213R | 34.107R | 1.218 | 46/99 | 53 (53.5%) | 89/137 (65.0%) | 23/23 (100.0%) |
| REF | REACTION_LOW_CLOSE15 | 160/160 | 0.220 event-R | 80.6% | 57-101 | 36.1% | 3.476R | -1.426R | -2.453R | 0.355R | 56.750R | 1.335 | 57/99 | 42 (42.4%) | 78/137 (56.9%) | 23/23 (100.0%) |

## Annual stability

| Year | Candidate | W-L | WR | Med LOSS R | Exp/signal | Total R | GE1 false-stop | Consumed caught |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | PROTECTED_LOW_TOUCH | 47-38 | 55.3% | -1.000R | -0.024R | -2.115R | 4/51 (7.8%) | 20/20 (100.0%) |
| 2022 | PROTECTED_LOW_CLOSE5 | 49-34 | 59.0% | -1.176R | -0.051R | -4.449R | 2/51 (3.9%) | 20/20 (100.0%) |
| 2022 | PROTECTED_LOW_CLOSE15 | 51-32 | 61.4% | -1.166R | -0.030R | -2.665R | 0/51 (0.0%) | 20/20 (100.0%) |
| 2022 | REACTION_LOW_TOUCH | 22-66 | 25.0% | -1.000R | -0.010R | -0.921R | 29/51 (56.9%) | 20/20 (100.0%) |
| 2022 | REACTION_LOW_CLOSE5 | 28-60 | 31.8% | -1.353R | -0.150R | -13.169R | 23/51 (45.1%) | 20/20 (100.0%) |
| 2022 | REACTION_LOW_CLOSE15 | 30-58 | 34.1% | -1.606R | -0.174R | -15.339R | 21/51 (41.2%) | 20/20 (100.0%) |
| 2023 | PROTECTED_LOW_TOUCH | 49-38 | 56.3% | -1.000R | -0.029R | -2.815R | 6/55 (10.9%) | 15/15 (100.0%) |
| 2023 | PROTECTED_LOW_CLOSE5 | 52-34 | 60.5% | -1.165R | -0.101R | -9.943R | 3/55 (5.5%) | 15/15 (100.0%) |
| 2023 | PROTECTED_LOW_CLOSE15 | 55-30 | 64.7% | -1.228R | -0.042R | -4.077R | 0/55 (0.0%) | 15/15 (100.0%) |
| 2023 | REACTION_LOW_TOUCH | 23-75 | 23.5% | -1.000R | -0.032R | -3.113R | 32/55 (58.2%) | 15/15 (100.0%) |
| 2023 | REACTION_LOW_CLOSE5 | 26-72 | 26.5% | -1.383R | -0.266R | -26.056R | 29/55 (52.7%) | 15/15 (100.0%) |
| 2023 | REACTION_LOW_CLOSE15 | 29-67 | 30.2% | -1.567R | -0.497R | -48.674R | 26/55 (47.3%) | 15/15 (100.0%) |
| 2024 | PROTECTED_LOW_TOUCH | 53-39 | 57.6% | -1.000R | -0.002R | -0.222R | 4/57 (7.0%) | 16/16 (100.0%) |
| 2024 | PROTECTED_LOW_CLOSE5 | 55-34 | 61.8% | -1.115R | 0.012R | 1.150R | 2/57 (3.5%) | 16/16 (100.0%) |
| 2024 | PROTECTED_LOW_CLOSE15 | 57-32 | 64.0% | -1.190R | 0.025R | 2.528R | 0/57 (0.0%) | 16/16 (100.0%) |
| 2024 | REACTION_LOW_TOUCH | 22-78 | 22.0% | -1.000R | -0.149R | -14.887R | 35/57 (61.4%) | 16/16 (100.0%) |
| 2024 | REACTION_LOW_CLOSE5 | 25-74 | 25.3% | -1.238R | -0.318R | -31.792R | 32/57 (56.1%) | 16/16 (100.0%) |
| 2024 | REACTION_LOW_CLOSE15 | 30-69 | 30.3% | -1.389R | 0.129R | 12.901R | 27/57 (47.4%) | 16/16 (100.0%) |
| 2025 | PROTECTED_LOW_TOUCH | 60-36 | 62.5% | -1.000R | 0.095R | 10.056R | 10/70 (14.3%) | 11/11 (100.0%) |
| 2025 | PROTECTED_LOW_CLOSE5 | 63-32 | 66.3% | -1.048R | 0.130R | 13.764R | 7/70 (10.0%) | 11/11 (100.0%) |
| 2025 | PROTECTED_LOW_CLOSE15 | 70-24 | 74.5% | -1.157R | 0.239R | 25.294R | 0/70 (0.0%) | 11/11 (100.0%) |
| 2025 | REACTION_LOW_TOUCH | 30-76 | 28.3% | -1.000R | 0.413R | 43.739R | 40/70 (57.1%) | 11/11 (100.0%) |
| 2025 | REACTION_LOW_CLOSE5 | 34-70 | 32.7% | -1.244R | 0.406R | 43.067R | 36/70 (51.4%) | 11/11 (100.0%) |
| 2025 | REACTION_LOW_CLOSE15 | 41-63 | 39.4% | -1.398R | 0.616R | 65.251R | 29/70 (41.4%) | 11/11 (100.0%) |
| 2026 | PROTECTED_LOW_TOUCH | 27-23 | 54.0% | -1.000R | -0.050R | -2.722R | 2/29 (6.9%) | 12/12 (100.0%) |
| 2026 | PROTECTED_LOW_CLOSE5 | 29-21 | 58.0% | -1.081R | -0.060R | -3.255R | 0/29 (0.0%) | 12/12 (100.0%) |
| 2026 | PROTECTED_LOW_CLOSE15 | 29-20 | 59.2% | -1.134R | -0.069R | -3.742R | 0/29 (0.0%) | 12/12 (100.0%) |
| 2026 | REACTION_LOW_TOUCH | 12-42 | 22.2% | -1.000R | 0.169R | 9.135R | 17/29 (58.6%) | 12/12 (100.0%) |
| 2026 | REACTION_LOW_CLOSE5 | 12-42 | 22.2% | -1.276R | -0.166R | -8.960R | 17/29 (58.6%) | 12/12 (100.0%) |
| 2026 | REACTION_LOW_CLOSE15 | 16-38 | 29.6% | -1.503R | -0.157R | -8.500R | 13/29 (44.8%) | 12/12 (100.0%) |

## False-stop anatomy

| Period | Candidate | False stops | Med stop→later target | Med overshoot below level |
|---|---|---:|---:|---:|
| DEV | PROTECTED_LOW_TOUCH | 14 | 690.0m | 0.163 initial-R |
| DEV | PROTECTED_LOW_CLOSE5 | 7 | 565.0m | 0.333 initial-R |
| DEV | REACTION_LOW_TOUCH | 96 | 337.5m | 1.752 initial-R |
| DEV | REACTION_LOW_CLOSE5 | 84 | 382.5m | 2.016 initial-R |
| DEV | REACTION_LOW_CLOSE15 | 74 | 415.0m | 2.268 initial-R |
| REF | PROTECTED_LOW_TOUCH | 12 | 275.0m | 0.240 initial-R |
| REF | PROTECTED_LOW_CLOSE5 | 7 | 290.0m | 0.219 initial-R |
| REF | REACTION_LOW_TOUCH | 57 | 370.0m | 1.949 initial-R |
| REF | REACTION_LOW_CLOSE5 | 53 | 360.0m | 2.000 initial-R |
| REF | REACTION_LOW_CLOSE15 | 42 | 365.0m | 2.947 initial-R |

## Interpretation boundary
S8 changes only structural invalidation semantics; demand construction, SD1, and market entry remain frozen.
CLOSE5/CLOSE15 losses use the actual completed close, so tail loss can exceed -1R.
A close-based rule is not preferred merely because it reduces false stops; DEV/REF expectancy and loss-tail behavior must also remain acceptable.
No final TP or XP1 runner policy is changed in S8.
