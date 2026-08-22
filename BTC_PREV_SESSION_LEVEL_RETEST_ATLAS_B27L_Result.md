# B27L — Previous-Session High/Low Retest Atlas

5m source rows: **698,112**; coverage: **100.0000%**.

Faithful session-level detector: completed previous-session High/Low are frozen; active session is observed on 15m and 1H bars. Retest zones are ±0.10% and ±0.20%. BULL = first strict close above previous-session High; BEAR = first strict close below previous-session Low; NO_BREAK = neither by session end.

Two touch metrics are retained: **distinct retests** (consecutive zone-intersecting TF bars collapse to one visit) and **raw touch bars** (every TF bar intersecting the zone before breakout). This makes visual repeated taps auditable instead of forcing one interpretation.

1H bars are anchored to active-session start; the final 30-minute session-close partial bar is retained and flagged for London/New York windows rather than mixing the next session.

## Direction sample counts

| TF | Tol | Transition | Partition | Bull N | Bear N | No-break N |
|---|---|---|---|---:|---:|---:|
| 15m | TOL_0.10 | ASIA_TO_LONDON | august | 5 | 3 | 6 |
| 15m | TOL_0.10 | ASIA_TO_LONDON | development | 247 | 197 | 338 |
| 15m | TOL_0.10 | ASIA_TO_LONDON | external | 179 | 171 | 173 |
| 15m | TOL_0.10 | ASIA_TO_LONDON | reference_validation | 129 | 130 | 152 |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | august | 9 | 3 | 2 |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | development | 322 | 358 | 102 |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | external | 225 | 165 | 133 |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | 185 | 197 | 29 |
| 15m | TOL_0.20 | ASIA_TO_LONDON | august | 5 | 3 | 6 |
| 15m | TOL_0.20 | ASIA_TO_LONDON | development | 247 | 197 | 338 |
| 15m | TOL_0.20 | ASIA_TO_LONDON | external | 179 | 171 | 173 |
| 15m | TOL_0.20 | ASIA_TO_LONDON | reference_validation | 129 | 130 | 152 |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | august | 9 | 3 | 2 |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | development | 322 | 358 | 102 |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | external | 225 | 165 | 133 |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | 185 | 197 | 29 |
| 1h | TOL_0.10 | ASIA_TO_LONDON | august | 5 | 3 | 6 |
| 1h | TOL_0.10 | ASIA_TO_LONDON | development | 220 | 172 | 390 |
| 1h | TOL_0.10 | ASIA_TO_LONDON | external | 166 | 146 | 211 |
| 1h | TOL_0.10 | ASIA_TO_LONDON | reference_validation | 114 | 114 | 183 |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | august | 8 | 4 | 2 |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | development | 292 | 333 | 157 |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | external | 200 | 150 | 173 |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | 175 | 189 | 47 |
| 1h | TOL_0.20 | ASIA_TO_LONDON | august | 5 | 3 | 6 |
| 1h | TOL_0.20 | ASIA_TO_LONDON | development | 220 | 172 | 390 |
| 1h | TOL_0.20 | ASIA_TO_LONDON | external | 166 | 146 | 211 |
| 1h | TOL_0.20 | ASIA_TO_LONDON | reference_validation | 114 | 114 | 183 |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | august | 8 | 4 | 2 |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | development | 292 | 333 | 157 |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | external | 200 | 150 | 173 |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | 175 | 189 | 47 |

## Bull/Bear retest summary — distinct visits

| TF | Tol | Transition | Partition | Dir | N | High retests med / mean / P75 / max | Low retests med / mean / P75 / max | H>=2 | H>=3 | L>=2 | L>=3 |
|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|
| 15m | TOL_0.10 | ASIA_TO_LONDON | external | BULL | 179 | 0.0 / 0.65 / 1.0 / 5 | 0.0 / 0.06 / 0.0 / 2 | 14.5% | 2.2% | 0.6% | 0.0% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | external | BEAR | 171 | 0.0 / 0.06 / 0.0 / 1 | 1.0 / 0.72 / 1.0 / 3 | 0.0% | 0.0% | 16.4% | 3.5% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | development | BULL | 247 | 1.0 / 0.89 / 1.0 / 4 | 0.0 / 0.13 / 0.0 / 4 | 20.2% | 4.9% | 3.2% | 0.8% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | development | BEAR | 197 | 0.0 / 0.08 / 0.0 / 2 | 1.0 / 0.86 / 1.0 / 4 | 0.5% | 0.0% | 16.8% | 2.0% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BULL | 129 | 1.0 / 0.78 / 1.0 / 3 | 0.0 / 0.06 / 0.0 / 2 | 13.2% | 1.6% | 0.8% | 0.0% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BEAR | 130 | 0.0 / 0.11 / 0.0 / 3 | 1.0 / 0.96 / 1.0 / 3 | 0.8% | 0.8% | 21.5% | 3.1% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 0.80 / 2.0 / 2 | 0.0 / 0.00 / 0.0 / 0 | 40.0% | 0.0% | 0.0% | 0.0% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.33 / 0.5 / 1 | 1.0 / 1.00 / 1.5 / 2 | 0.0% | 0.0% | 33.3% | 0.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | external | BULL | 225 | 0.0 / 0.75 / 1.0 / 5 | 0.0 / 0.06 / 0.0 / 2 | 16.0% | 5.8% | 0.4% | 0.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | external | BEAR | 165 | 0.0 / 0.08 / 0.0 / 3 | 1.0 / 0.69 / 1.0 / 4 | 1.2% | 0.6% | 12.1% | 3.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | development | BULL | 322 | 1.0 / 0.73 / 1.0 / 6 | 0.0 / 0.27 / 0.0 / 3 | 12.4% | 3.7% | 5.3% | 1.2% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | development | BEAR | 358 | 0.0 / 0.21 / 0.0 / 3 | 1.0 / 0.70 / 1.0 / 4 | 2.5% | 0.3% | 12.0% | 2.2% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BULL | 185 | 1.0 / 0.82 / 1.0 / 3 | 0.0 / 0.26 / 0.0 / 2 | 19.5% | 3.2% | 4.3% | 0.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BEAR | 197 | 0.0 / 0.23 / 0.0 / 2 | 1.0 / 0.77 / 1.0 / 5 | 2.0% | 0.0% | 14.7% | 4.1% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | august | BULL | 9 | 1.0 / 1.00 / 1.0 / 2 | 0.0 / 0.44 / 1.0 / 2 | 11.1% | 0.0% | 11.1% | 0.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | august | BEAR | 3 | 0.0 / 0.00 / 0.0 / 0 | 1.0 / 0.67 / 1.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | external | BULL | 179 | 1.0 / 0.95 / 1.0 / 4 | 0.0 / 0.11 / 0.0 / 2 | 23.5% | 6.1% | 1.7% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | external | BEAR | 171 | 0.0 / 0.11 / 0.0 / 2 | 1.0 / 1.00 / 1.5 / 3 | 1.2% | 0.0% | 25.1% | 8.8% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | development | BULL | 247 | 1.0 / 1.13 / 2.0 / 4 | 0.0 / 0.19 / 0.0 / 3 | 27.1% | 6.9% | 3.2% | 1.2% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | development | BEAR | 197 | 0.0 / 0.16 / 0.0 / 3 | 1.0 / 1.05 / 1.0 / 5 | 4.1% | 0.5% | 21.8% | 5.1% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BULL | 129 | 1.0 / 0.98 / 1.0 / 4 | 0.0 / 0.13 / 0.0 / 2 | 19.4% | 0.8% | 3.9% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BEAR | 130 | 0.0 / 0.23 / 0.0 / 5 | 1.0 / 1.17 / 1.8 / 4 | 3.8% | 1.5% | 25.4% | 7.7% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | august | BULL | 5 | 1.0 / 0.60 / 1.0 / 1 | 0.0 / 0.20 / 0.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.33 / 0.5 / 1 | 1.0 / 1.00 / 1.5 / 2 | 0.0% | 0.0% | 33.3% | 0.0% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | external | BULL | 225 | 1.0 / 0.95 / 1.0 / 4 | 0.0 / 0.09 / 0.0 / 2 | 22.7% | 7.6% | 1.3% | 0.0% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | external | BEAR | 165 | 0.0 / 0.16 / 0.0 / 3 | 1.0 / 0.89 / 1.0 / 3 | 3.0% | 0.6% | 18.8% | 4.2% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | development | BULL | 322 | 1.0 / 0.91 / 1.0 / 5 | 0.0 / 0.35 / 1.0 / 4 | 18.0% | 5.6% | 6.2% | 1.6% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | development | BEAR | 358 | 0.0 / 0.32 / 1.0 / 3 | 1.0 / 0.84 / 1.0 / 4 | 5.3% | 0.8% | 14.8% | 3.6% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BULL | 185 | 1.0 / 0.97 / 1.0 / 4 | 0.0 / 0.40 / 1.0 / 3 | 20.5% | 7.0% | 9.7% | 1.1% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BEAR | 197 | 0.0 / 0.33 / 1.0 / 2 | 1.0 / 0.85 / 1.0 / 4 | 4.1% | 0.0% | 13.7% | 4.1% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | august | BULL | 9 | 1.0 / 1.11 / 1.0 / 2 | 0.0 / 0.33 / 1.0 / 1 | 11.1% | 0.0% | 0.0% | 0.0% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | august | BEAR | 3 | 0.0 / 0.00 / 0.0 / 0 | 1.0 / 0.67 / 1.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | external | BULL | 166 | 0.0 / 0.44 / 1.0 / 2 | 0.0 / 0.05 / 0.0 / 1 | 4.2% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | external | BEAR | 146 | 0.0 / 0.07 / 0.0 / 1 | 0.0 / 0.40 / 1.0 / 2 | 0.0% | 0.0% | 1.4% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | development | BULL | 220 | 0.0 / 0.49 / 1.0 / 2 | 0.0 / 0.10 / 0.0 / 2 | 4.1% | 0.0% | 0.5% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | development | BEAR | 172 | 0.0 / 0.12 / 0.0 / 2 | 0.0 / 0.43 / 1.0 / 2 | 0.6% | 0.0% | 2.3% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BULL | 114 | 0.0 / 0.48 / 1.0 / 2 | 0.0 / 0.06 / 0.0 / 1 | 0.9% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BEAR | 114 | 0.0 / 0.13 / 0.0 / 3 | 0.0 / 0.53 / 1.0 / 2 | 0.9% | 0.9% | 4.4% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 0.40 / 1.0 / 1 | 0.0 / 0.00 / 0.0 / 0 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.33 / 0.5 / 1 | 1.0 / 0.67 / 1.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | external | BULL | 200 | 0.0 / 0.41 / 1.0 / 2 | 0.0 / 0.07 / 0.0 / 1 | 3.5% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | external | BEAR | 150 | 0.0 / 0.11 / 0.0 / 1 | 0.0 / 0.38 / 1.0 / 2 | 0.0% | 0.0% | 2.7% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | development | BULL | 292 | 0.0 / 0.40 / 1.0 / 2 | 0.0 / 0.22 / 0.0 / 2 | 3.8% | 0.0% | 0.7% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | development | BEAR | 333 | 0.0 / 0.20 / 0.0 / 2 | 0.0 / 0.42 / 1.0 / 2 | 0.3% | 0.0% | 2.7% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BULL | 175 | 0.0 / 0.56 / 1.0 / 3 | 0.0 / 0.28 / 1.0 / 2 | 6.3% | 1.1% | 1.7% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BEAR | 189 | 0.0 / 0.23 / 0.0 / 2 | 0.0 / 0.42 / 1.0 / 2 | 0.5% | 0.0% | 3.2% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | august | BULL | 8 | 0.5 / 0.50 / 1.0 / 1 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | august | BEAR | 4 | 0.0 / 0.25 / 0.2 / 1 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | external | BULL | 166 | 1.0 / 0.55 / 1.0 / 2 | 0.0 / 0.10 / 0.0 / 1 | 3.6% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | external | BEAR | 146 | 0.0 / 0.11 / 0.0 / 1 | 0.5 / 0.53 / 1.0 / 2 | 0.0% | 0.0% | 2.7% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | development | BULL | 220 | 1.0 / 0.62 / 1.0 / 2 | 0.0 / 0.16 / 0.0 / 2 | 6.4% | 0.0% | 0.5% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | development | BEAR | 172 | 0.0 / 0.17 / 0.0 / 2 | 0.0 / 0.48 / 1.0 / 2 | 1.2% | 0.0% | 0.6% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BULL | 114 | 1.0 / 0.56 / 1.0 / 2 | 0.0 / 0.11 / 0.0 / 2 | 3.5% | 0.0% | 1.8% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BEAR | 114 | 0.0 / 0.18 / 0.0 / 2 | 1.0 / 0.61 / 1.0 / 2 | 0.9% | 0.0% | 1.8% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 0.40 / 1.0 / 1 | 0.0 / 0.20 / 0.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.33 / 0.5 / 1 | 1.0 / 0.67 / 1.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | external | BULL | 200 | 0.0 / 0.54 / 1.0 / 2 | 0.0 / 0.09 / 0.0 / 1 | 4.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | external | BEAR | 150 | 0.0 / 0.17 / 0.0 / 1 | 0.0 / 0.44 / 1.0 / 2 | 0.0% | 0.0% | 2.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | development | BULL | 292 | 0.0 / 0.49 / 1.0 / 2 | 0.0 / 0.28 / 1.0 / 2 | 4.8% | 0.0% | 0.3% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | development | BEAR | 333 | 0.0 / 0.26 / 1.0 / 2 | 0.0 / 0.46 / 1.0 / 2 | 0.6% | 0.0% | 2.4% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BULL | 175 | 1.0 / 0.60 / 1.0 / 3 | 0.0 / 0.34 / 1.0 / 2 | 6.3% | 0.6% | 3.4% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BEAR | 189 | 0.0 / 0.27 / 1.0 / 2 | 0.0 / 0.48 / 1.0 / 2 | 0.5% | 0.0% | 2.6% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | august | BULL | 8 | 0.5 / 0.50 / 1.0 / 1 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | august | BEAR | 4 | 0.0 / 0.25 / 0.2 / 1 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |

## Bull/Bear raw touch-candle summary

| TF | Tol | Transition | Partition | Dir | N | High raw med / mean / P75 / max | Low raw med / mean / P75 / max | Hraw>=3 | Hraw>=4 | Lraw>=3 | Lraw>=4 |
|---|---|---|---|---|---:|---|---|---:|---:|---:|---:|
| 15m | TOL_0.10 | ASIA_TO_LONDON | external | BULL | 179 | 0.0 / 1.04 / 1.0 / 9 | 0.0 / 0.08 / 0.0 / 4 | 14.5% | 8.4% | 1.1% | 0.6% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | external | BEAR | 171 | 0.0 / 0.11 / 0.0 / 3 | 1.0 / 1.06 / 2.0 / 5 | 1.2% | 0.0% | 16.4% | 8.8% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | development | BULL | 247 | 1.0 / 1.50 / 2.0 / 11 | 0.0 / 0.25 / 0.0 / 8 | 22.3% | 12.6% | 3.6% | 2.8% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | development | BEAR | 197 | 0.0 / 0.18 / 0.0 / 9 | 1.0 / 1.78 / 2.0 / 12 | 2.0% | 1.5% | 24.9% | 13.7% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BULL | 129 | 1.0 / 1.65 / 3.0 / 9 | 0.0 / 0.13 / 0.0 / 5 | 25.6% | 13.2% | 2.3% | 0.8% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BEAR | 130 | 0.0 / 0.21 / 0.0 / 5 | 1.0 / 1.64 / 2.0 / 9 | 3.1% | 2.3% | 20.0% | 11.5% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 1.20 / 2.0 / 4 | 0.0 / 0.00 / 0.0 / 0 | 20.0% | 20.0% | 0.0% | 0.0% |
| 15m | TOL_0.10 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.67 / 1.0 / 2 | 1.0 / 1.33 / 2.0 / 3 | 0.0% | 0.0% | 33.3% | 0.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | external | BULL | 225 | 0.0 / 1.34 / 2.0 / 12 | 0.0 / 0.13 / 0.0 / 8 | 19.1% | 14.7% | 2.2% | 0.9% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | external | BEAR | 165 | 0.0 / 0.11 / 0.0 / 4 | 1.0 / 1.18 / 2.0 / 12 | 1.8% | 0.6% | 15.2% | 11.5% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | development | BULL | 322 | 1.0 / 1.31 / 2.0 / 15 | 0.0 / 0.45 / 0.0 / 7 | 17.1% | 9.6% | 6.8% | 4.0% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | development | BEAR | 358 | 0.0 / 0.35 / 0.0 / 10 | 1.0 / 1.27 / 2.0 / 10 | 3.6% | 1.1% | 15.9% | 10.3% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BULL | 185 | 1.0 / 1.48 / 2.0 / 13 | 0.0 / 0.45 / 0.0 / 5 | 19.5% | 13.5% | 7.6% | 2.2% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BEAR | 197 | 0.0 / 0.31 / 0.0 / 4 | 1.0 / 1.28 / 2.0 / 13 | 2.5% | 1.0% | 15.7% | 9.1% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | august | BULL | 9 | 2.0 / 2.22 / 4.0 / 4 | 0.0 / 1.11 / 2.0 / 6 | 33.3% | 33.3% | 11.1% | 11.1% |
| 15m | TOL_0.10 | LONDON_TO_NEWYORK | august | BEAR | 3 | 0.0 / 0.00 / 0.0 / 0 | 2.0 / 1.33 / 2.0 / 2 | 0.0% | 0.0% | 0.0% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | external | BULL | 179 | 1.0 / 1.79 / 2.0 / 14 | 0.0 / 0.21 / 0.0 / 7 | 23.5% | 16.2% | 2.2% | 2.2% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | external | BEAR | 171 | 0.0 / 0.23 / 0.0 / 6 | 1.0 / 1.81 / 3.0 / 11 | 2.9% | 2.3% | 26.9% | 19.3% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | development | BULL | 247 | 2.0 / 2.56 / 4.0 / 16 | 0.0 / 0.58 / 0.0 / 16 | 40.1% | 27.5% | 6.9% | 4.5% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | development | BEAR | 197 | 0.0 / 0.40 / 0.0 / 11 | 2.0 / 2.71 / 3.0 / 15 | 6.1% | 5.1% | 37.6% | 24.9% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BULL | 129 | 2.0 / 2.74 / 4.0 / 16 | 0.0 / 0.28 / 0.0 / 8 | 36.4% | 27.9% | 4.7% | 1.6% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BEAR | 130 | 0.0 / 0.53 / 0.0 / 11 | 2.0 / 2.92 / 4.0 / 14 | 7.7% | 4.6% | 44.6% | 32.3% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | august | BULL | 5 | 1.0 / 2.20 / 5.0 / 5 | 0.0 / 0.40 / 0.0 / 2 | 40.0% | 40.0% | 0.0% | 0.0% |
| 15m | TOL_0.20 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 1.33 / 2.0 / 4 | 1.0 / 2.00 / 3.0 / 5 | 33.3% | 33.3% | 33.3% | 33.3% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | external | BULL | 225 | 1.0 / 2.20 / 3.0 / 18 | 0.0 / 0.20 / 0.0 / 8 | 29.3% | 21.3% | 3.6% | 1.3% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | external | BEAR | 165 | 0.0 / 0.28 / 0.0 / 9 | 1.0 / 1.75 / 2.0 / 15 | 3.6% | 1.8% | 21.8% | 16.4% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | development | BULL | 322 | 1.0 / 1.91 / 3.0 / 18 | 0.0 / 0.77 / 1.0 / 11 | 28.0% | 16.5% | 11.5% | 7.8% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | development | BEAR | 358 | 0.0 / 0.66 / 1.0 / 11 | 1.0 / 1.84 / 3.0 / 14 | 9.5% | 4.7% | 27.4% | 16.8% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BULL | 185 | 1.0 / 2.16 / 3.0 / 14 | 0.0 / 0.83 / 1.0 / 7 | 32.4% | 23.8% | 15.7% | 8.1% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BEAR | 197 | 0.0 / 0.55 / 1.0 / 6 | 1.0 / 1.91 / 3.0 / 17 | 6.1% | 3.0% | 29.4% | 17.3% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | august | BULL | 9 | 2.0 / 3.00 / 4.0 / 6 | 0.0 / 1.33 / 2.0 / 8 | 44.4% | 33.3% | 11.1% | 11.1% |
| 15m | TOL_0.20 | LONDON_TO_NEWYORK | august | BEAR | 3 | 0.0 / 0.00 / 0.0 / 0 | 3.0 / 2.00 / 3.0 / 3 | 0.0% | 0.0% | 66.7% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | external | BULL | 166 | 0.0 / 0.59 / 1.0 / 5 | 0.0 / 0.06 / 0.0 / 2 | 4.8% | 1.2% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | external | BEAR | 146 | 0.0 / 0.09 / 0.0 / 2 | 0.0 / 0.51 / 1.0 / 5 | 0.0% | 0.0% | 2.1% | 0.7% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | development | BULL | 220 | 0.0 / 0.68 / 1.0 / 5 | 0.0 / 0.14 / 0.0 / 3 | 4.5% | 2.3% | 0.9% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | development | BEAR | 172 | 0.0 / 0.17 / 0.0 / 3 | 0.0 / 0.67 / 1.0 / 4 | 1.7% | 0.0% | 7.0% | 2.9% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BULL | 114 | 0.0 / 0.64 / 1.0 / 3 | 0.0 / 0.08 / 0.0 / 2 | 2.6% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | reference_validation | BEAR | 114 | 0.0 / 0.16 / 0.0 / 3 | 0.0 / 0.76 / 1.0 / 5 | 0.9% | 0.0% | 5.3% | 2.6% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 0.40 / 1.0 / 1 | 0.0 / 0.00 / 0.0 / 0 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.67 / 1.0 / 2 | 1.0 / 0.67 / 1.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | external | BULL | 200 | 0.0 / 0.57 / 1.0 / 4 | 0.0 / 0.09 / 0.0 / 2 | 5.0% | 1.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | external | BEAR | 150 | 0.0 / 0.13 / 0.0 / 2 | 0.0 / 0.53 / 1.0 / 4 | 0.0% | 0.0% | 3.3% | 2.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | development | BULL | 292 | 0.0 / 0.61 / 1.0 / 5 | 0.0 / 0.31 / 0.0 / 3 | 6.2% | 2.1% | 1.7% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | development | BEAR | 333 | 0.0 / 0.28 / 0.0 / 4 | 0.0 / 0.63 / 1.0 / 5 | 1.5% | 0.6% | 4.8% | 1.5% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BULL | 175 | 0.0 / 0.73 / 1.0 / 4 | 0.0 / 0.34 / 1.0 / 4 | 4.6% | 0.6% | 1.1% | 0.6% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | reference_validation | BEAR | 189 | 0.0 / 0.28 / 0.0 / 3 | 0.0 / 0.61 / 1.0 / 4 | 0.5% | 0.0% | 6.3% | 2.1% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | august | BULL | 8 | 0.5 / 1.00 / 2.0 / 3 | 0.0 / 0.38 / 0.2 / 2 | 12.5% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.10 | LONDON_TO_NEWYORK | august | BEAR | 4 | 0.0 / 0.50 / 0.5 / 2 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | external | BULL | 166 | 1.0 / 0.80 / 1.0 / 5 | 0.0 / 0.13 / 0.0 / 3 | 5.4% | 3.0% | 0.6% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | external | BEAR | 146 | 0.0 / 0.14 / 0.0 / 2 | 0.5 / 0.71 / 1.0 / 5 | 0.0% | 0.0% | 3.4% | 0.7% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | development | BULL | 220 | 1.0 / 0.97 / 2.0 / 5 | 0.0 / 0.25 / 0.0 / 3 | 9.5% | 4.5% | 2.7% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | development | BEAR | 172 | 0.0 / 0.26 / 0.0 / 4 | 0.0 / 0.83 / 1.0 / 5 | 2.9% | 0.6% | 9.3% | 5.2% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BULL | 114 | 1.0 / 0.90 / 2.0 / 4 | 0.0 / 0.14 / 0.0 / 3 | 7.9% | 2.6% | 0.9% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | reference_validation | BEAR | 114 | 0.0 / 0.30 / 0.0 / 5 | 1.0 / 1.11 / 2.0 / 5 | 3.5% | 0.9% | 13.2% | 5.3% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | august | BULL | 5 | 0.0 / 0.40 / 1.0 / 1 | 0.0 / 0.20 / 0.0 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | ASIA_TO_LONDON | august | BEAR | 3 | 0.0 / 0.67 / 1.0 / 2 | 1.0 / 1.00 / 1.5 / 2 | 0.0% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | external | BULL | 200 | 0.0 / 0.79 / 1.0 / 5 | 0.0 / 0.13 / 0.0 / 3 | 5.5% | 3.5% | 0.5% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | external | BEAR | 150 | 0.0 / 0.21 / 0.0 / 3 | 0.0 / 0.67 / 1.0 / 4 | 1.3% | 0.0% | 6.0% | 2.7% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | development | BULL | 292 | 0.0 / 0.78 / 1.0 / 5 | 0.0 / 0.42 / 1.0 / 4 | 9.2% | 4.5% | 2.7% | 1.7% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | development | BEAR | 333 | 0.0 / 0.40 / 1.0 / 4 | 0.0 / 0.76 / 1.0 / 6 | 3.6% | 1.2% | 8.1% | 2.7% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BULL | 175 | 1.0 / 0.86 / 1.0 / 5 | 0.0 / 0.49 / 1.0 / 4 | 8.6% | 1.1% | 2.9% | 1.7% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | reference_validation | BEAR | 189 | 0.0 / 0.34 / 1.0 / 3 | 0.0 / 0.72 / 1.0 / 5 | 1.6% | 0.0% | 7.9% | 3.2% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | august | BULL | 8 | 0.5 / 1.00 / 2.0 / 3 | 0.0 / 0.38 / 0.2 / 2 | 12.5% | 0.0% | 0.0% | 0.0% |
| 1h | TOL_0.20 | LONDON_TO_NEWYORK | august | BEAR | 4 | 0.0 / 0.50 / 0.5 / 2 | 0.0 / 0.25 / 0.2 / 1 | 0.0% | 0.0% | 0.0% | 0.0% |

## Exact combinations

Every exact `(High distinct retests, Low distinct retests)` combination and frequency is persisted in `BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Combos.csv`. Raw day-level observations are in `BTC_PREV_SESSION_LEVEL_RETEST_ATLAS_B27L_Events.csv`.

Diagnostic only. No retest-count bucket is a validated trading rule.

Research only; live BBC unchanged.
