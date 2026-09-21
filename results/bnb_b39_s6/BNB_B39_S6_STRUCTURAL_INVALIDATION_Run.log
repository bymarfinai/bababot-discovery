# BNB B39-S6 — Frozen D1 Structural Invalidation / SL Discovery

Frozen detector signature: `8ae240e94d64707d2077a40f83f50f896e36a9ecf738ef74c1ec9c2f3c21d6b2`
D1 unchanged: `p5_close_r > 0.20335748322474653`
Entry = D1 signal close; target = anchor +1 event-R; only SL changes.

## Static structural invalidation audit

| Period | Candidate | Avail | SL dist | Compression | W-L | WR | Med WIN R | Exp/signal | Total R | PF | GE1 retained | False stop | Stop→later target | FP→WIN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | DEMAND_LOW_BASELINE | 151/151 | 1.360 event-R | 0.0% | 108-43 | 71.5% | 0.439R | 0.014R | 2.069R | 1.048 | 108/108 | 0 (0.0%) | —m | 0 |
| DEV | TOUCH_BAR_LOW | 151/151 | 0.856 event-R | 39.5% | 95-56 | 62.9% | 0.575R | 0.066R | 9.925R | 1.177 | 94/108 | 14 (13.0%) | 55.0m | 1 |
| DEV | D1_BAR_LOW | 151/151 | 0.536 event-R | 62.1% | 77-74 | 51.0% | 0.812R | 0.049R | 7.457R | 1.101 | 77/108 | 31 (28.7%) | 55.0m | 0 |
| DEV | ANCHOR_LEVEL | 151/151 | 0.360 event-R | 73.5% | 66-83 | 44.3% | 1.290R | 0.109R | 16.482R | 1.199 | 66/108 | 40 (37.0%) | 50.0m | 0 |
| DEV | DEMAND_HIGH_LEVEL | 140/151 | 0.543 event-R | 60.5% | 72-66 | 52.2% | 0.874R | 0.126R | 19.063R | 1.289 | 72/100 | 26 (26.0%) | 45.0m | 0 |
| REF | DEMAND_LOW_BASELINE | 101/101 | 1.410 event-R | 0.0% | 83-17 | 83.0% | 0.412R | 0.163R | 16.480R | 1.969 | 83/83 | 0 (0.0%) | —m | 0 |
| REF | TOUCH_BAR_LOW | 101/101 | 0.903 event-R | 39.8% | 64-37 | 63.4% | 0.513R | 0.111R | 11.203R | 1.303 | 64/83 | 19 (22.9%) | 125.0m | 0 |
| REF | D1_BAR_LOW | 101/101 | 0.527 event-R | 63.6% | 57-44 | 56.4% | 0.905R | 0.234R | 23.623R | 1.537 | 57/83 | 26 (31.3%) | 117.5m | 0 |
| REF | ANCHOR_LEVEL | 101/101 | 0.410 event-R | 70.9% | 50-50 | 50.0% | 1.179R | 0.234R | 23.636R | 1.473 | 50/83 | 32 (38.6%) | 97.5m | 0 |
| REF | DEMAND_HIGH_LEVEL | 88/101 | 0.505 event-R | 64.4% | 47-41 | 53.4% | 0.846R | 0.207R | 20.924R | 1.510 | 47/73 | 26 (35.6%) | 85.0m | 0 |

## Annual stability

| Year | Candidate | W-L | WR | Exp/signal | Total R | GE1 false-stop |
|---:|---|---:|---:|---:|---:|---:|
| 2022 | DEMAND_LOW_BASELINE | 38-19 | 66.7% | -0.061R | -3.483R | 0/38 (0.0%) |
| 2022 | TOUCH_BAR_LOW | 35-22 | 61.4% | 0.080R | 4.544R | 3/38 (7.9%) |
| 2022 | D1_BAR_LOW | 29-28 | 50.9% | 0.003R | 0.143R | 9/38 (23.7%) |
| 2022 | ANCHOR_LEVEL | 25-31 | 44.6% | 0.058R | 3.297R | 12/38 (31.6%) |
| 2022 | DEMAND_HIGH_LEVEL | 23-28 | 45.1% | 0.050R | 2.854R | 10/35 (28.6%) |
| 2023 | DEMAND_LOW_BASELINE | 30-12 | 71.4% | 0.007R | 0.281R | 0/30 (0.0%) |
| 2023 | TOUCH_BAR_LOW | 27-15 | 64.3% | -0.001R | -0.058R | 4/30 (13.3%) |
| 2023 | D1_BAR_LOW | 21-21 | 50.0% | 0.011R | 0.446R | 9/30 (30.0%) |
| 2023 | ANCHOR_LEVEL | 16-25 | 39.0% | 0.006R | 0.263R | 13/30 (43.3%) |
| 2023 | DEMAND_HIGH_LEVEL | 22-18 | 55.0% | 0.092R | 3.843R | 7/29 (24.1%) |
| 2024 | DEMAND_LOW_BASELINE | 40-12 | 76.9% | 0.101R | 5.271R | 0/40 (0.0%) |
| 2024 | TOUCH_BAR_LOW | 33-19 | 63.5% | 0.105R | 5.439R | 7/40 (17.5%) |
| 2024 | D1_BAR_LOW | 27-25 | 51.9% | 0.132R | 6.868R | 13/40 (32.5%) |
| 2024 | ANCHOR_LEVEL | 25-27 | 48.1% | 0.249R | 12.922R | 15/40 (37.5%) |
| 2024 | DEMAND_HIGH_LEVEL | 27-20 | 57.4% | 0.238R | 12.366R | 9/36 (25.0%) |
| 2025 | DEMAND_LOW_BASELINE | 52-9 | 85.2% | 0.167R | 10.332R | 0/52 (0.0%) |
| 2025 | TOUCH_BAR_LOW | 41-21 | 66.1% | 0.127R | 7.869R | 11/52 (21.2%) |
| 2025 | D1_BAR_LOW | 36-26 | 58.1% | 0.197R | 12.198R | 16/52 (30.8%) |
| 2025 | ANCHOR_LEVEL | 31-30 | 50.8% | 0.133R | 8.274R | 20/52 (38.5%) |
| 2025 | DEMAND_HIGH_LEVEL | 29-24 | 54.7% | 0.162R | 10.034R | 15/44 (34.1%) |
| 2026 | DEMAND_LOW_BASELINE | 31-8 | 79.5% | 0.158R | 6.148R | 0/31 (0.0%) |
| 2026 | TOUCH_BAR_LOW | 23-16 | 59.0% | 0.085R | 3.334R | 8/31 (25.8%) |
| 2026 | D1_BAR_LOW | 21-18 | 53.8% | 0.293R | 11.425R | 10/31 (32.3%) |
| 2026 | ANCHOR_LEVEL | 19-20 | 48.7% | 0.394R | 15.361R | 12/31 (38.7%) |
| 2026 | DEMAND_HIGH_LEVEL | 18-17 | 51.4% | 0.279R | 10.890R | 11/29 (37.9%) |

## False-stop anatomy

| Period | Candidate | False stops | Med stop→later target | Med overshoot below stop |
|---|---|---:|---:|---:|
| DEV | TOUCH_BAR_LOW | 14 | 55.0m | 0.361 candidate-R |
| DEV | D1_BAR_LOW | 31 | 55.0m | 0.579 candidate-R |
| DEV | ANCHOR_LEVEL | 40 | 50.0m | 1.054 candidate-R |
| DEV | DEMAND_HIGH_LEVEL | 26 | 45.0m | 0.830 candidate-R |
| REF | TOUCH_BAR_LOW | 19 | 125.0m | 0.831 candidate-R |
| REF | D1_BAR_LOW | 26 | 117.5m | 0.911 candidate-R |
| REF | ANCHOR_LEVEL | 32 | 97.5m | 1.162 candidate-R |
| REF | DEMAND_HIGH_LEVEL | 26 | 85.0m | 1.130 candidate-R |

## Interpretation boundary
S6 changes only the hard structural invalidation level.
A tighter static stop is rejected if its higher R multiple is bought by excessive false stops or DEV/REF instability.
If no static level is robust, the next stage should search post-entry failure-state exits while retaining the wider structural floor.
