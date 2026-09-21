# BNB B39-S7 — Frozen D1 Post-Entry Failure Character

Frozen detector signature: `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
D1 unchanged: `p5_close_r > 0.20335748322474653`
Entry = D1 signal close; target = anchor +1 event-R; structural floor remains demand_low.

## Failure-state audit

| Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | Med exit R loss | Lead to floor | Lead to later target | Reclaim <=5m | Reclaim <=15m | CF W-L-BE | CF Exp | CF Total R | PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | TOUCH_DEMAND_HIGH | 68/151 (45.0%) | 36/43 (83.7%) | 32/108 (29.6%) | 52.9% | -0.386R | 27.5m | 40.0m | 65.6% | 84.4% | 81-68-2 | 0.019R | 2.834R | 1.099 |
| DEV | CLOSE5_BELOW_DEMAND_HIGH | 52/151 (34.4%) | 30/43 (69.8%) | 22/108 (20.4%) | 57.7% | -0.462R | 22.5m | 40.0m | 59.1% | 77.3% | 86-65-0 | 0.003R | 0.384R | 1.011 |
| DEV | CLOSE5_BELOW_ANCHOR | 65/151 (43.0%) | 38/43 (88.4%) | 27/108 (25.0%) | 58.5% | -0.394R | 30.0m | 50.0m | 40.7% | 81.5% | 81-70-0 | 0.008R | 1.186R | 1.039 |
| DEV | CLOSE5_BELOW_D1_LOW | 54/151 (35.8%) | 34/43 (79.1%) | 20/108 (18.5%) | 63.0% | -0.466R | 27.5m | 52.5m | 50.0% | 85.0% | 88-63-0 | 0.013R | 1.905R | 1.057 |
| DEV | CLOSE15_BELOW_ANCHOR | 56/151 (37.1%) | 33/43 (76.7%) | 23/108 (21.3%) | 58.9% | -0.411R | 25.0m | 50.0m | 56.5% | 78.3% | 85-66-0 | 0.004R | 0.548R | 1.016 |
| DEV | CLOSE15_BELOW_DEMAND_HIGH | 42/151 (27.8%) | 26/43 (60.5%) | 16/108 (14.8%) | 61.9% | -0.481R | 17.5m | 32.5m | 50.0% | 81.2% | 94-57-0 | 0.012R | 1.837R | 1.050 |
| REF | TOUCH_DEMAND_HIGH | 48/101 (47.5%) | 14/17 (82.4%) | 33/83 (39.8%) | 29.2% | -0.341R | 12.5m | 90.0m | 57.6% | 78.8% | 60-41-0 | 0.061R | 6.161R | 1.418 |
| REF | CLOSE5_BELOW_DEMAND_HIGH | 37/101 (36.6%) | 12/17 (70.6%) | 24/83 (28.9%) | 32.4% | -0.505R | 12.5m | 112.5m | 37.5% | 66.7% | 61-40-0 | 0.032R | 3.245R | 1.168 |
| REF | CLOSE5_BELOW_ANCHOR | 39/101 (38.6%) | 15/17 (88.2%) | 23/83 (27.7%) | 38.5% | -0.384R | 15.0m | 125.0m | 43.5% | 56.5% | 60-41-0 | 0.044R | 4.477R | 1.245 |
| REF | CLOSE5_BELOW_D1_LOW | 33/101 (32.7%) | 14/17 (82.4%) | 19/83 (22.9%) | 42.4% | -0.469R | 15.0m | 125.0m | 42.1% | 52.6% | 64-36-1 | 0.063R | 6.371R | 1.353 |
| REF | CLOSE15_BELOW_ANCHOR | 32/101 (31.7%) | 13/17 (76.5%) | 19/83 (22.9%) | 40.6% | -0.454R | 10.0m | 125.0m | 26.3% | 52.6% | 64-36-1 | 0.062R | 6.214R | 1.341 |
| REF | CLOSE15_BELOW_DEMAND_HIGH | 31/101 (30.7%) | 11/17 (64.7%) | 20/83 (24.1%) | 35.5% | -0.485R | 10.0m | 115.0m | 40.0% | 55.0% | 65-35-1 | 0.061R | 6.136R | 1.339 |

## Annual counterfactual stability

| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | CF Total R |
|---:|---|---:|---:|---:|---:|---:|
| 2022 | TOUCH_DEMAND_HIGH | 14/19 (73.7%) | 12/38 (31.6%) | 53.8% | -0.042R | -2.378R |
| 2022 | CLOSE5_BELOW_DEMAND_HIGH | 12/19 (63.2%) | 5/38 (13.2%) | 70.6% | -0.030R | -1.684R |
| 2022 | CLOSE5_BELOW_ANCHOR | 16/19 (84.2%) | 6/38 (15.8%) | 72.7% | 0.004R | 0.213R |
| 2022 | CLOSE5_BELOW_D1_LOW | 14/19 (73.7%) | 3/38 (7.9%) | 82.4% | 0.015R | 0.848R |
| 2022 | CLOSE15_BELOW_ANCHOR | 14/19 (73.7%) | 5/38 (13.2%) | 73.7% | -0.001R | -0.080R |
| 2022 | CLOSE15_BELOW_DEMAND_HIGH | 9/19 (47.4%) | 3/38 (7.9%) | 75.0% | -0.029R | -1.671R |
| 2023 | TOUCH_DEMAND_HIGH | 11/12 (91.7%) | 7/30 (23.3%) | 61.1% | 0.026R | 1.109R |
| 2023 | CLOSE5_BELOW_DEMAND_HIGH | 8/12 (66.7%) | 6/30 (20.0%) | 57.1% | -0.001R | -0.058R |
| 2023 | CLOSE5_BELOW_ANCHOR | 11/12 (91.7%) | 9/30 (30.0%) | 55.0% | -0.007R | -0.304R |
| 2023 | CLOSE5_BELOW_D1_LOW | 9/12 (75.0%) | 7/30 (23.3%) | 56.2% | -0.029R | -1.230R |
| 2023 | CLOSE15_BELOW_ANCHOR | 9/12 (75.0%) | 7/30 (23.3%) | 56.2% | -0.016R | -0.682R |
| 2023 | CLOSE15_BELOW_DEMAND_HIGH | 7/12 (58.3%) | 4/30 (13.3%) | 63.6% | 0.007R | 0.286R |
| 2024 | TOUCH_DEMAND_HIGH | 11/12 (91.7%) | 13/40 (32.5%) | 45.8% | 0.079R | 4.103R |
| 2024 | CLOSE5_BELOW_DEMAND_HIGH | 10/12 (83.3%) | 11/40 (27.5%) | 47.6% | 0.041R | 2.125R |
| 2024 | CLOSE5_BELOW_ANCHOR | 11/12 (91.7%) | 12/40 (30.0%) | 47.8% | 0.025R | 1.277R |
| 2024 | CLOSE5_BELOW_D1_LOW | 11/12 (91.7%) | 10/40 (25.0%) | 52.4% | 0.044R | 2.287R |
| 2024 | CLOSE15_BELOW_ANCHOR | 10/12 (83.3%) | 11/40 (27.5%) | 47.6% | 0.025R | 1.310R |
| 2024 | CLOSE15_BELOW_DEMAND_HIGH | 10/12 (83.3%) | 9/40 (22.5%) | 52.6% | 0.062R | 3.222R |
| 2025 | TOUCH_DEMAND_HIGH | 8/9 (88.9%) | 21/52 (40.4%) | 26.7% | 0.061R | 3.785R |
| 2025 | CLOSE5_BELOW_DEMAND_HIGH | 7/9 (77.8%) | 16/52 (30.8%) | 29.2% | 0.036R | 2.254R |
| 2025 | CLOSE5_BELOW_ANCHOR | 8/9 (88.9%) | 13/52 (25.0%) | 36.4% | 0.053R | 3.317R |
| 2025 | CLOSE5_BELOW_D1_LOW | 7/9 (77.8%) | 11/52 (21.2%) | 38.9% | 0.064R | 3.988R |
| 2025 | CLOSE15_BELOW_ANCHOR | 7/9 (77.8%) | 11/52 (21.2%) | 38.9% | 0.065R | 4.039R |
| 2025 | CLOSE15_BELOW_DEMAND_HIGH | 7/9 (77.8%) | 14/52 (26.9%) | 33.3% | 0.053R | 3.294R |
| 2026 | TOUCH_DEMAND_HIGH | 6/8 (75.0%) | 12/31 (38.7%) | 33.3% | 0.061R | 2.376R |
| 2026 | CLOSE5_BELOW_DEMAND_HIGH | 5/8 (62.5%) | 8/31 (25.8%) | 38.5% | 0.025R | 0.991R |
| 2026 | CLOSE5_BELOW_ANCHOR | 7/8 (87.5%) | 10/31 (32.3%) | 41.2% | 0.030R | 1.161R |
| 2026 | CLOSE5_BELOW_D1_LOW | 7/8 (87.5%) | 8/31 (25.8%) | 46.7% | 0.061R | 2.382R |
| 2026 | CLOSE15_BELOW_ANCHOR | 6/8 (75.0%) | 8/31 (25.8%) | 42.9% | 0.056R | 2.176R |
| 2026 | CLOSE15_BELOW_DEMAND_HIGH | 4/8 (50.0%) | 6/31 (19.4%) | 40.0% | 0.073R | 2.842R |

## False-exit winner reclaim anatomy

| Period | Candidate | False exits | Reclaim next5 | Reclaim <=15m | Med signal→target | Med overshoot |
|---|---|---:|---:|---:|---:|---:|
| DEV | TOUCH_DEMAND_HIGH | 32 | 21 (65.6%) | 27 (84.4%) | 40.0m | 0.251 original-R |
| DEV | CLOSE5_BELOW_DEMAND_HIGH | 22 | 13 (59.1%) | 17 (77.3%) | 40.0m | 0.293 original-R |
| DEV | CLOSE5_BELOW_ANCHOR | 27 | 11 (40.7%) | 22 (81.5%) | 50.0m | 0.319 original-R |
| DEV | CLOSE5_BELOW_D1_LOW | 20 | 10 (50.0%) | 17 (85.0%) | 52.5m | 0.273 original-R |
| DEV | CLOSE15_BELOW_ANCHOR | 23 | 13 (56.5%) | 18 (78.3%) | 50.0m | 0.308 original-R |
| DEV | CLOSE15_BELOW_DEMAND_HIGH | 16 | 8 (50.0%) | 13 (81.2%) | 32.5m | 0.315 original-R |
| REF | TOUCH_DEMAND_HIGH | 33 | 19 (57.6%) | 26 (78.8%) | 90.0m | 0.283 original-R |
| REF | CLOSE5_BELOW_DEMAND_HIGH | 24 | 9 (37.5%) | 16 (66.7%) | 112.5m | 0.416 original-R |
| REF | CLOSE5_BELOW_ANCHOR | 23 | 10 (43.5%) | 13 (56.5%) | 125.0m | 0.397 original-R |
| REF | CLOSE5_BELOW_D1_LOW | 19 | 8 (42.1%) | 10 (52.6%) | 125.0m | 0.457 original-R |
| REF | CLOSE15_BELOW_ANCHOR | 19 | 5 (26.3%) | 10 (52.6%) | 125.0m | 0.472 original-R |
| REF | CLOSE15_BELOW_DEMAND_HIGH | 20 | 8 (40.0%) | 11 (55.0%) | 115.0m | 0.426 original-R |

## Interpretation boundary
S7 discovers failure states only; no early-exit rule is promoted automatically.
A candidate must improve DEV and REF economics while separating losses from eventual winners.
Fast reclaim among false exits indicates a liquidity dip rather than durable failure and is evidence against using that state alone.
