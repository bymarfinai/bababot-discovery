# BNB B38-S20 — Post-Entry Failure Character

Frozen E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`

## Structural failure-state audit

| Scope | Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | Med signal R (loss) | Lead to SL | Lead to later TP1 | CF W-L-BE | CF Exp | CF Total R |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| ALL | DEV | TOUCH_BREAK_LEVEL | 293/440 (66.6%) | 114/115 (99.1%) | 179/325 (55.1%) | 38.9% | -0.109R | 102.5m | 105.0m | 146-294-0 | -0.009R | -4.125R |
| ALL | DEV | CLOSE5_BELOW_BREAK_LEVEL | 254/440 (57.7%) | 113/115 (98.3%) | 141/325 (43.4%) | 44.5% | -0.222R | 95.0m | 115.0m | 184-256-0 | -0.003R | -1.334R |
| ALL | DEV | CLOSE5_BELOW_HOLD_CLOSE | 179/440 (40.7%) | 104/115 (90.4%) | 75/325 (23.1%) | 58.1% | -0.420R | 65.0m | 165.0m | 250-190-0 | 0.002R | 0.835R |
| ALL | DEV | CLOSE5_BELOW_RECLAIM_CLOSE | 146/440 (33.2%) | 97/115 (84.3%) | 49/325 (15.1%) | 66.4% | -0.485R | 45.0m | 220.0m | 276-164-0 | 0.026R | 11.268R |
| ALL | DEV | CLOSE5_BELOW_DEMAND_HIGH | 86/440 (19.5%) | 65/115 (56.5%) | 21/325 (6.5%) | 75.6% | -0.704R | 30.0m | 230.0m | 304-136-0 | 0.030R | 13.227R |
| ALL | DEV | CLOSE15_BELOW_DEMAND_HIGH | 59/440 (13.4%) | 46/115 (40.0%) | 13/325 (4.0%) | 78.0% | -0.618R | 27.5m | 360.0m | 312-128-0 | 0.041R | 18.092R |
| ALL | REF | TOUCH_BREAK_LEVEL | 180/272 (66.2%) | 70/71 (98.6%) | 110/201 (54.7%) | 38.9% | -0.121R | 112.5m | 80.0m | 91-181-0 | -0.019R | -5.227R |
| ALL | REF | CLOSE5_BELOW_BREAK_LEVEL | 152/272 (55.9%) | 70/71 (98.6%) | 82/201 (40.8%) | 46.1% | -0.210R | 105.0m | 107.5m | 119-153-0 | 0.011R | 3.082R |
| ALL | REF | CLOSE5_BELOW_HOLD_CLOSE | 115/272 (42.3%) | 69/71 (97.2%) | 46/201 (22.9%) | 60.0% | -0.410R | 65.0m | 155.0m | 155-117-0 | 0.006R | 1.549R |
| ALL | REF | CLOSE5_BELOW_RECLAIM_CLOSE | 93/272 (34.2%) | 67/71 (94.4%) | 26/201 (12.9%) | 72.0% | -0.517R | 45.0m | 175.0m | 175-97-0 | 0.001R | 0.338R |
| ALL | REF | CLOSE5_BELOW_DEMAND_HIGH | 62/272 (22.8%) | 48/71 (67.6%) | 14/201 (7.0%) | 77.4% | -0.640R | 30.0m | 207.5m | 187-85-0 | -0.003R | -0.684R |
| ALL | REF | CLOSE15_BELOW_DEMAND_HIGH | 50/272 (18.4%) | 37/71 (52.1%) | 13/201 (6.5%) | 74.0% | -0.592R | 50.0m | 195.0m | 188-84-0 | -0.013R | -3.622R |
| Q4_WIDE | DEV | TOUCH_BREAK_LEVEL | 62/110 (56.4%) | 23/23 (100.0%) | 39/87 (44.8%) | 37.1% | -0.074R | 185.0m | 125.0m | 48-62-0 | 0.013R | 1.478R |
| Q4_WIDE | DEV | CLOSE5_BELOW_BREAK_LEVEL | 55/110 (50.0%) | 23/23 (100.0%) | 32/87 (36.8%) | 41.8% | -0.162R | 185.0m | 135.0m | 55-55-0 | 0.004R | 0.412R |
| Q4_WIDE | DEV | CLOSE5_BELOW_HOLD_CLOSE | 38/110 (34.5%) | 22/23 (95.7%) | 16/87 (18.4%) | 57.9% | -0.373R | 165.0m | 157.5m | 71-39-0 | -0.019R | -2.058R |
| Q4_WIDE | DEV | CLOSE5_BELOW_RECLAIM_CLOSE | 31/110 (28.2%) | 21/23 (91.3%) | 10/87 (11.5%) | 67.7% | -0.458R | 185.0m | 360.0m | 77-33-0 | -0.022R | -2.406R |
| Q4_WIDE | DEV | CLOSE5_BELOW_DEMAND_HIGH | 21/110 (19.1%) | 17/23 (73.9%) | 4/87 (4.6%) | 81.0% | -0.583R | 70.0m | 320.0m | 83-27-0 | -0.028R | -3.072R |
| Q4_WIDE | DEV | CLOSE15_BELOW_DEMAND_HIGH | 17/110 (15.5%) | 14/23 (60.9%) | 3/87 (3.4%) | 82.4% | -0.500R | 67.5m | 475.0m | 84-26-0 | -0.030R | -3.277R |
| Q4_WIDE | REF | TOUCH_BREAK_LEVEL | 33/50 (66.0%) | 6/6 (100.0%) | 27/44 (61.4%) | 18.2% | -0.105R | 165.0m | 110.0m | 17-33-0 | -0.030R | -1.494R |
| Q4_WIDE | REF | CLOSE5_BELOW_BREAK_LEVEL | 29/50 (58.0%) | 6/6 (100.0%) | 23/44 (52.3%) | 20.7% | -0.176R | 157.5m | 180.0m | 21-29-0 | -0.015R | -0.757R |
| Q4_WIDE | REF | CLOSE5_BELOW_HOLD_CLOSE | 20/50 (40.0%) | 6/6 (100.0%) | 14/44 (31.8%) | 30.0% | -0.310R | 117.5m | 155.0m | 30-20-0 | -0.018R | -0.881R |
| Q4_WIDE | REF | CLOSE5_BELOW_RECLAIM_CLOSE | 8/50 (16.0%) | 6/6 (100.0%) | 2/44 (4.5%) | 75.0% | -0.475R | 102.5m | 127.5m | 42-8-0 | 0.007R | 0.348R |
| Q4_WIDE | REF | CLOSE5_BELOW_DEMAND_HIGH | 5/50 (10.0%) | 4/6 (66.7%) | 1/44 (2.3%) | 80.0% | -0.634R | 107.5m | 40.0m | 43-7-0 | -0.013R | -0.653R |
| Q4_WIDE | REF | CLOSE15_BELOW_DEMAND_HIGH | 5/50 (10.0%) | 4/6 (66.7%) | 1/44 (2.3%) | 80.0% | -0.634R | 107.5m | 35.0m | 43-7-0 | -0.017R | -0.851R |

## Annual stability — Q4 wide subset

| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | CF Total R |
|---:|---|---:|---:|---:|---:|---:|
| 2022 | TOUCH_BREAK_LEVEL | 11/11 (100.0%) | 16/34 (47.1%) | 40.7% | 0.045R | 2.038R |
| 2022 | CLOSE5_BELOW_BREAK_LEVEL | 11/11 (100.0%) | 14/34 (41.2%) | 44.0% | 0.042R | 1.900R |
| 2022 | CLOSE5_BELOW_HOLD_CLOSE | 11/11 (100.0%) | 9/34 (26.5%) | 55.0% | 0.038R | 1.724R |
| 2022 | CLOSE5_BELOW_RECLAIM_CLOSE | 10/11 (90.9%) | 5/34 (14.7%) | 66.7% | 0.022R | 0.999R |
| 2022 | CLOSE5_BELOW_DEMAND_HIGH | 8/11 (72.7%) | 1/34 (2.9%) | 88.9% | 0.040R | 1.789R |
| 2022 | CLOSE15_BELOW_DEMAND_HIGH | 8/11 (72.7%) | 1/34 (2.9%) | 88.9% | 0.044R | 1.981R |
| 2023 | TOUCH_BREAK_LEVEL | 3/3 (100.0%) | 11/28 (39.3%) | 21.4% | -0.011R | -0.349R |
| 2023 | CLOSE5_BELOW_BREAK_LEVEL | 3/3 (100.0%) | 10/28 (35.7%) | 23.1% | -0.024R | -0.747R |
| 2023 | CLOSE5_BELOW_HOLD_CLOSE | 2/3 (66.7%) | 1/28 (3.6%) | 66.7% | -0.015R | -0.470R |
| 2023 | CLOSE5_BELOW_RECLAIM_CLOSE | 2/3 (66.7%) | 1/28 (3.6%) | 66.7% | -0.008R | -0.247R |
| 2023 | CLOSE5_BELOW_DEMAND_HIGH | 1/3 (33.3%) | 0/28 (0.0%) | 100.0% | -0.037R | -1.132R |
| 2023 | CLOSE15_BELOW_DEMAND_HIGH | 0/3 (0.0%) | 0/28 (0.0%) | — | -0.037R | -1.156R |
| 2024 | TOUCH_BREAK_LEVEL | 9/9 (100.0%) | 12/25 (48.0%) | 42.9% | -0.006R | -0.211R |
| 2024 | CLOSE5_BELOW_BREAK_LEVEL | 9/9 (100.0%) | 8/25 (32.0%) | 52.9% | -0.022R | -0.741R |
| 2024 | CLOSE5_BELOW_HOLD_CLOSE | 9/9 (100.0%) | 6/25 (24.0%) | 60.0% | -0.097R | -3.312R |
| 2024 | CLOSE5_BELOW_RECLAIM_CLOSE | 9/9 (100.0%) | 4/25 (16.0%) | 69.2% | -0.093R | -3.159R |
| 2024 | CLOSE5_BELOW_DEMAND_HIGH | 8/9 (88.9%) | 3/25 (12.0%) | 72.7% | -0.110R | -3.729R |
| 2024 | CLOSE15_BELOW_DEMAND_HIGH | 6/9 (66.7%) | 2/25 (8.0%) | 75.0% | -0.121R | -4.102R |
| 2025 | TOUCH_BREAK_LEVEL | 4/4 (100.0%) | 22/35 (62.9%) | 15.4% | -0.022R | -0.845R |
| 2025 | CLOSE5_BELOW_BREAK_LEVEL | 4/4 (100.0%) | 19/35 (54.3%) | 17.4% | -0.021R | -0.817R |
| 2025 | CLOSE5_BELOW_HOLD_CLOSE | 4/4 (100.0%) | 13/35 (37.1%) | 23.5% | -0.020R | -0.798R |
| 2025 | CLOSE5_BELOW_RECLAIM_CLOSE | 4/4 (100.0%) | 1/35 (2.9%) | 80.0% | 0.019R | 0.753R |
| 2025 | CLOSE5_BELOW_DEMAND_HIGH | 3/4 (75.0%) | 1/35 (2.9%) | 75.0% | -0.009R | -0.354R |
| 2025 | CLOSE15_BELOW_DEMAND_HIGH | 3/4 (75.0%) | 1/35 (2.9%) | 75.0% | -0.014R | -0.552R |
| 2026 | TOUCH_BREAK_LEVEL | 2/2 (100.0%) | 5/9 (55.6%) | 28.6% | -0.059R | -0.649R |
| 2026 | CLOSE5_BELOW_BREAK_LEVEL | 2/2 (100.0%) | 4/9 (44.4%) | 33.3% | 0.005R | 0.060R |
| 2026 | CLOSE5_BELOW_HOLD_CLOSE | 2/2 (100.0%) | 1/9 (11.1%) | 66.7% | -0.008R | -0.083R |
| 2026 | CLOSE5_BELOW_RECLAIM_CLOSE | 2/2 (100.0%) | 1/9 (11.1%) | 66.7% | -0.037R | -0.406R |
| 2026 | CLOSE5_BELOW_DEMAND_HIGH | 1/2 (50.0%) | 0/9 (0.0%) | 100.0% | -0.027R | -0.300R |
| 2026 | CLOSE15_BELOW_DEMAND_HIGH | 1/2 (50.0%) | 0/9 (0.0%) | 100.0% | -0.027R | -0.300R |

## Interpretation boundary
S20 discovers failure states only; it does not promote a live exit rule.
A state that captures losses but exits too many eventual TP1 winners is not considered a valid failure character.
Any promoted early-exit policy must be preregistered separately.
