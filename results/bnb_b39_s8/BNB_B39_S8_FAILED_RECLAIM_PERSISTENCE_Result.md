# BNB B39-S8 — Failed-Reclaim Persistence Character

Frozen detector signature: `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
D1, market entry, +1 event-R target, and demand-low structural floor remain unchanged.

## Persistence audit

| Period | Candidate | Signal | Loss captured | Winner false-exit | Precision(loss) | CF Exp | Δ vs wide | Δ vs S7 single | S7 loss cap→S8 | S7 false exit→S8 | Total R | PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | D1_TWO_CLOSES_BELOW | 36/151 (23.8%) | 26/43 (60.5%) | 10/108 (9.3%) | 72.2% | 0.027R | 0.013R | 0.014R | 79.1%→60.5% | 18.5%→9.3% | 4.093R | 1.113 |
| DEV | D1_NO_RECLAIM_15M | 11/151 (7.3%) | 8/43 (18.6%) | 3/108 (2.8%) | 72.7% | 0.015R | 0.001R | 0.002R | 79.1%→18.6% | 18.5%→2.8% | 2.233R | 1.054 |
| DEV | D1_RECLAIM_ATTEMPT_REJECT | 14/151 (9.3%) | 9/43 (20.9%) | 5/108 (4.6%) | 64.3% | 0.016R | 0.002R | 0.003R | 79.1%→20.9% | 18.5%→4.6% | 2.385R | 1.059 |
| DEV | ANCHOR_TWO_CLOSES_BELOW | 44/151 (29.1%) | 28/43 (65.1%) | 16/108 (14.8%) | 63.6% | 0.007R | -0.007R | -0.001R | 88.4%→65.1% | 25.0%→14.8% | 1.060R | 1.029 |
| DEV | ANCHOR_NO_RECLAIM_15M | 18/151 (11.9%) | 13/43 (30.2%) | 5/108 (4.6%) | 72.2% | 0.020R | 0.006R | 0.012R | 88.4%→30.2% | 25.0%→4.6% | 3.021R | 1.077 |
| DEV | ANCHOR_RECLAIM_ATTEMPT_REJECT | 23/151 (15.2%) | 14/43 (32.6%) | 9/108 (8.3%) | 60.9% | 0.019R | 0.006R | 0.011R | 88.4%→32.6% | 25.0%→8.3% | 2.917R | 1.077 |
| REF | D1_TWO_CLOSES_BELOW | 20/101 (19.8%) | 9/17 (52.9%) | 11/83 (13.3%) | 45.0% | 0.094R | -0.070R | 0.030R | 82.4%→52.9% | 22.9%→13.3% | 9.449R | 1.514 |
| REF | D1_NO_RECLAIM_15M | 13/101 (12.9%) | 4/17 (23.5%) | 9/83 (10.8%) | 30.8% | 0.087R | -0.076R | 0.024R | 82.4%→23.5% | 22.9%→10.8% | 8.836R | 1.436 |
| REF | D1_RECLAIM_ATTEMPT_REJECT | 6/101 (5.9%) | 2/17 (11.8%) | 4/83 (4.8%) | 33.3% | 0.134R | -0.029R | 0.071R | 82.4%→11.8% | 22.9%→4.8% | 13.527R | 1.752 |
| REF | ANCHOR_TWO_CLOSES_BELOW | 23/101 (22.8%) | 10/17 (58.8%) | 13/83 (15.7%) | 43.5% | 0.087R | -0.076R | 0.042R | 88.2%→58.8% | 27.7%→15.7% | 8.763R | 1.477 |
| REF | ANCHOR_NO_RECLAIM_15M | 13/101 (12.9%) | 3/17 (17.6%) | 10/83 (12.0%) | 23.1% | 0.082R | -0.082R | 0.037R | 88.2%→17.6% | 27.7%→12.0% | 8.241R | 1.403 |
| REF | ANCHOR_RECLAIM_ATTEMPT_REJECT | 9/101 (8.9%) | 2/17 (11.8%) | 7/83 (8.4%) | 22.2% | 0.120R | -0.044R | 0.075R | 88.2%→11.8% | 27.7%→8.4% | 12.085R | 1.660 |

## Annual stability

| Year | Candidate | Loss capture | Winner false-exit | Precision(loss) | CF Exp | Total R |
|---:|---|---:|---:|---:|---:|---:|
| 2022 | D1_TWO_CLOSES_BELOW | 9/19 (47.4%) | 1/38 (2.6%) | 90.0% | -0.001R | -0.034R |
| 2022 | D1_NO_RECLAIM_15M | 4/19 (21.1%) | 1/38 (2.6%) | 80.0% | -0.048R | -2.763R |
| 2022 | D1_RECLAIM_ATTEMPT_REJECT | 5/19 (26.3%) | 1/38 (2.6%) | 83.3% | -0.029R | -1.630R |
| 2022 | ANCHOR_TWO_CLOSES_BELOW | 11/19 (57.9%) | 2/38 (5.3%) | 84.6% | 0.004R | 0.206R |
| 2022 | ANCHOR_NO_RECLAIM_15M | 7/19 (36.8%) | 1/38 (2.6%) | 87.5% | -0.020R | -1.126R |
| 2022 | ANCHOR_RECLAIM_ATTEMPT_REJECT | 6/19 (31.6%) | 1/38 (2.6%) | 85.7% | -0.012R | -0.675R |
| 2023 | D1_TWO_CLOSES_BELOW | 7/12 (58.3%) | 4/30 (13.3%) | 63.6% | -0.014R | -0.576R |
| 2023 | D1_NO_RECLAIM_15M | 1/12 (8.3%) | 1/30 (3.3%) | 50.0% | -0.015R | -0.612R |
| 2023 | D1_RECLAIM_ATTEMPT_REJECT | 1/12 (8.3%) | 2/30 (6.7%) | 33.3% | -0.017R | -0.710R |
| 2023 | ANCHOR_TWO_CLOSES_BELOW | 8/12 (66.7%) | 6/30 (20.0%) | 57.1% | -0.020R | -0.820R |
| 2023 | ANCHOR_NO_RECLAIM_15M | 4/12 (33.3%) | 2/30 (6.7%) | 66.7% | -0.001R | -0.027R |
| 2023 | ANCHOR_RECLAIM_ATTEMPT_REJECT | 5/12 (41.7%) | 3/30 (10.0%) | 62.5% | 0.024R | 0.992R |
| 2024 | D1_TWO_CLOSES_BELOW | 10/12 (83.3%) | 5/40 (12.5%) | 66.7% | 0.090R | 4.703R |
| 2024 | D1_NO_RECLAIM_15M | 3/12 (25.0%) | 1/40 (2.5%) | 75.0% | 0.108R | 5.608R |
| 2024 | D1_RECLAIM_ATTEMPT_REJECT | 3/12 (25.0%) | 2/40 (5.0%) | 60.0% | 0.091R | 4.726R |
| 2024 | ANCHOR_TWO_CLOSES_BELOW | 9/12 (75.0%) | 8/40 (20.0%) | 52.9% | 0.032R | 1.673R |
| 2024 | ANCHOR_NO_RECLAIM_15M | 2/12 (16.7%) | 2/40 (5.0%) | 50.0% | 0.080R | 4.174R |
| 2024 | ANCHOR_RECLAIM_ATTEMPT_REJECT | 3/12 (25.0%) | 5/40 (12.5%) | 37.5% | 0.050R | 2.600R |
| 2025 | D1_TWO_CLOSES_BELOW | 5/9 (55.6%) | 6/52 (11.5%) | 45.5% | 0.104R | 6.469R |
| 2025 | D1_NO_RECLAIM_15M | 3/9 (33.3%) | 6/52 (11.5%) | 33.3% | 0.079R | 4.893R |
| 2025 | D1_RECLAIM_ATTEMPT_REJECT | 1/9 (11.1%) | 3/52 (5.8%) | 25.0% | 0.127R | 7.903R |
| 2025 | ANCHOR_TWO_CLOSES_BELOW | 5/9 (55.6%) | 6/52 (11.5%) | 45.5% | 0.105R | 6.495R |
| 2025 | ANCHOR_NO_RECLAIM_15M | 2/9 (22.2%) | 6/52 (11.5%) | 25.0% | 0.083R | 5.138R |
| 2025 | ANCHOR_RECLAIM_ATTEMPT_REJECT | 0/9 (0.0%) | 3/52 (5.8%) | 0.0% | 0.129R | 7.979R |
| 2026 | D1_TWO_CLOSES_BELOW | 4/8 (50.0%) | 5/31 (16.1%) | 44.4% | 0.076R | 2.981R |
| 2026 | D1_NO_RECLAIM_15M | 1/8 (12.5%) | 3/31 (9.7%) | 25.0% | 0.101R | 3.943R |
| 2026 | D1_RECLAIM_ATTEMPT_REJECT | 1/8 (12.5%) | 1/31 (3.2%) | 50.0% | 0.144R | 5.624R |
| 2026 | ANCHOR_TWO_CLOSES_BELOW | 5/8 (62.5%) | 7/31 (22.6%) | 41.7% | 0.058R | 2.267R |
| 2026 | ANCHOR_NO_RECLAIM_15M | 1/8 (12.5%) | 4/31 (12.9%) | 20.0% | 0.080R | 3.102R |
| 2026 | ANCHOR_RECLAIM_ATTEMPT_REJECT | 2/8 (25.0%) | 4/31 (12.9%) | 33.3% | 0.105R | 4.107R |

## False-exit reclaim after persistence signal

| Period | Candidate | False exits | Reclaim next5 | Reclaim <=15m | Med signal→target | Med overshoot |
|---|---|---:|---:|---:|---:|---:|
| DEV | D1_TWO_CLOSES_BELOW | 10 | 5 (50.0%) | 8 (80.0%) | 62.5m | 0.313 original-R |
| DEV | D1_NO_RECLAIM_15M | 3 | 1 (33.3%) | 2 (66.7%) | 115.0m | 0.301 original-R |
| DEV | D1_RECLAIM_ATTEMPT_REJECT | 5 | 3 (60.0%) | 5 (100.0%) | 65.0m | 0.245 original-R |
| DEV | ANCHOR_TWO_CLOSES_BELOW | 16 | 9 (56.2%) | 12 (75.0%) | 72.5m | 0.392 original-R |
| DEV | ANCHOR_NO_RECLAIM_15M | 5 | 1 (20.0%) | 2 (40.0%) | 105.0m | 0.387 original-R |
| DEV | ANCHOR_RECLAIM_ATTEMPT_REJECT | 9 | 6 (66.7%) | 8 (88.9%) | 45.0m | 0.457 original-R |
| REF | D1_TWO_CLOSES_BELOW | 11 | 1 (9.1%) | 3 (27.3%) | 155.0m | 0.475 original-R |
| REF | D1_NO_RECLAIM_15M | 9 | 1 (11.1%) | 4 (44.4%) | 145.0m | 0.461 original-R |
| REF | D1_RECLAIM_ATTEMPT_REJECT | 4 | 0 (0.0%) | 2 (50.0%) | 72.5m | 0.466 original-R |
| REF | ANCHOR_TWO_CLOSES_BELOW | 13 | 1 (7.7%) | 5 (38.5%) | 125.0m | 0.472 original-R |
| REF | ANCHOR_NO_RECLAIM_15M | 10 | 2 (20.0%) | 5 (50.0%) | 117.5m | 0.467 original-R |
| REF | ANCHOR_RECLAIM_ATTEMPT_REJECT | 7 | 2 (28.6%) | 4 (57.1%) | 120.0m | 0.463 original-R |

## Interpretation boundary
S8 tests persistence and failed reclaim only; levels are unchanged from S7.
No candidate is promoted unless it improves wide-floor expectancy in both DEV and REF and improves separation versus the corresponding S7 single-breach state.
If none passes, the wide structural floor remains the correct protection and failure-exit tuning stops.
