# BNB B40-S7 — Frozen SD1 Post-Confirmation Entry Geometry

Frozen SD1 signature: `c742621214a18aa46140bc10a37fcf9c482ea8e0c6d5bc11f8af634cec12f1d0`
Entry-study signature: `70a0a6811ffb6bd4bce2f5089fb6700690169f2a9828488e1bef0ba10981a24a`

Cohort = SD1 PASS only. XP1 is NOT used for entry selection.
Audit target = anchor +1 event-R; structural audit floor = protected_low; all limits activate strictly after SD1 closes.

## Entry geometry

| Period | Candidate | Fill | W-L | WR | Med WIN R | Exp/fill | Exp/signal | Total R | PF | Med target R:R | Improvement | Risk compression | GE1 fill/win | GE1 missed | GE1→LOSS | Consumed avoided | Local-only avoided |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | MARKET_SD1_CLOSE | 286/286 (100.0%) | 149-115 | 56.4% | 0.761R | -0.018R | -0.018R | -5.151R | 0.955 | 0.784 | 0.000 event-R | 0.0% | 163/149 of 163 | 0 | 14 | 0/51 (0.0%) | 0/72 (0.0%) |
| DEV | LIMIT_HALF_RETRACE | 264/279 (94.6%) | 130-113 | 53.5% | 0.874R | -0.005R | -0.005R | -1.451R | 0.987 | 0.882 | 0.063 event-R | 5.6% | 143/130 of 158 | 15 | 13 | 0/50 (0.0%) | 0/71 (0.0%) |
| DEV | LIMIT_TOUCH_ANCHOR | 242/279 (86.7%) | 108-113 | 48.9% | 1.000R | -0.021R | -0.017R | -5.000R | 0.956 | 1.000 | 0.125 event-R | 11.1% | 121/108 of 158 | 37 | 13 | 0/50 (0.0%) | 0/71 (0.0%) |
| DEV | LIMIT_ZONE_HIGH | 190/242 (78.5%) | 75-98 | 43.4% | 1.096R | -0.047R | -0.031R | -8.897R | 0.909 | 1.166 | 0.248 event-R | 20.8% | 85/75 of 136 | 51 | 10 | 0/41 (0.0%) | 1/65 (1.5%) |
| DEV | LIMIT_REACTION_LOW | 218/285 (76.5%) | 83-113 | 42.3% | 1.180R | 0.008R | 0.006R | 1.797R | 1.016 | 1.207 | 0.235 event-R | 21.2% | 96/83 of 162 | 66 | 13 | 0/51 (0.0%) | 0/72 (0.0%) |
| REF | MARKET_SD1_CLOSE | 160/160 (100.0%) | 87-59 | 59.6% | 0.784R | 0.046R | 0.046R | 7.333R | 1.124 | 0.784 | 0.000 event-R | 0.0% | 99/87 of 99 | 0 | 12 | 0/23 (0.0%) | 0/38 (0.0%) |
| REF | LIMIT_HALF_RETRACE | 138/158 (87.3%) | 66-58 | 53.2% | 0.896R | 0.002R | 0.001R | 0.223R | 1.004 | 0.884 | 0.061 event-R | 5.5% | 77/66 of 97 | 20 | 11 | 0/23 (0.0%) | 0/38 (0.0%) |
| REF | LIMIT_TOUCH_ANCHOR | 132/158 (83.5%) | 60-58 | 50.8% | 1.000R | 0.015R | 0.013R | 2.000R | 1.034 | 1.000 | 0.123 event-R | 10.9% | 71/60 of 97 | 26 | 11 | 0/23 (0.0%) | 0/38 (0.0%) |
| REF | LIMIT_ZONE_HIGH | 109/141 (77.3%) | 48-49 | 49.5% | 1.049R | 0.063R | 0.043R | 6.905R | 1.141 | 1.155 | 0.199 event-R | 18.2% | 55/48 of 86 | 31 | 7 | 0/19 (0.0%) | 1/36 (2.8%) |
| REF | LIMIT_REACTION_LOW | 117/160 (73.1%) | 45-58 | 43.7% | 1.141R | -0.037R | -0.027R | -4.313R | 0.926 | 1.168 | 0.220 event-R | 19.4% | 56/45 of 99 | 42 | 11 | 0/23 (0.0%) | 0/38 (0.0%) |

## Annual stability

| Year | Candidate | Fill | W-L | WR | Exp/signal | Total R | Med target R:R | GE1 missed | Consumed avoided |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | MARKET_SD1_CLOSE | 88/88 | 47-38 | 55.3% | -0.024R | -2.115R | 0.803 | 0 | 0 |
| 2022 | LIMIT_HALF_RETRACE | 78/84 | 39-37 | 51.3% | -0.031R | -2.733R | 0.889 | 6 | 0 |
| 2022 | LIMIT_TOUCH_ANCHOR | 74/84 | 35-37 | 48.6% | -0.023R | -2.000R | 1.000 | 10 | 0 |
| 2022 | LIMIT_ZONE_HIGH | 53/69 | 21-31 | 40.4% | -0.060R | -5.297R | 1.184 | 16 | 0 |
| 2022 | LIMIT_REACTION_LOW | 65/88 | 25-37 | 40.3% | -0.059R | -5.204R | 1.271 | 22 | 0 |
| 2023 | MARKET_SD1_CLOSE | 98/98 | 49-38 | 56.3% | -0.029R | -2.815R | 0.762 | 0 | 0 |
| 2023 | LIMIT_HALF_RETRACE | 93/97 | 45-37 | 54.9% | 0.012R | 1.165R | 0.873 | 4 | 0 |
| 2023 | LIMIT_TOUCH_ANCHOR | 81/97 | 33-37 | 47.1% | -0.041R | -4.000R | 1.000 | 16 | 0 |
| 2023 | LIMIT_ZONE_HIGH | 66/87 | 25-33 | 43.1% | -0.017R | -1.640R | 1.205 | 20 | 0 |
| 2023 | LIMIT_REACTION_LOW | 75/97 | 27-37 | 42.2% | 0.057R | 5.597R | 1.179 | 22 | 0 |
| 2024 | MARKET_SD1_CLOSE | 100/100 | 53-39 | 57.6% | -0.002R | -0.222R | 0.775 | 0 | 0 |
| 2024 | LIMIT_HALF_RETRACE | 93/98 | 46-39 | 54.1% | 0.001R | 0.117R | 0.877 | 5 | 0 |
| 2024 | LIMIT_TOUCH_ANCHOR | 87/98 | 40-39 | 50.6% | 0.010R | 1.000R | 1.000 | 11 | 0 |
| 2024 | LIMIT_ZONE_HIGH | 71/86 | 29-34 | 46.0% | -0.020R | -1.960R | 1.123 | 15 | 0 |
| 2024 | LIMIT_REACTION_LOW | 78/100 | 31-39 | 44.3% | 0.014R | 1.405R | 1.186 | 22 | 0 |
| 2025 | MARKET_SD1_CLOSE | 106/106 | 60-36 | 62.5% | 0.095R | 10.056R | 0.802 | 0 | 0 |
| 2025 | LIMIT_HALF_RETRACE | 93/105 | 47-36 | 56.6% | 0.052R | 5.535R | 0.895 | 12 | 0 |
| 2025 | LIMIT_TOUCH_ANCHOR | 90/105 | 44-36 | 55.0% | 0.075R | 8.000R | 1.000 | 15 | 0 |
| 2025 | LIMIT_ZONE_HIGH | 74/96 | 34-32 | 51.5% | 0.037R | 3.870R | 1.094 | 21 | 0 |
| 2025 | LIMIT_REACTION_LOW | 76/106 | 30-36 | 45.5% | -0.011R | -1.144R | 1.165 | 30 | 0 |
| 2026 | MARKET_SD1_CLOSE | 54/54 | 27-23 | 54.0% | -0.050R | -2.722R | 0.763 | 0 | 0 |
| 2026 | LIMIT_HALF_RETRACE | 45/53 | 19-22 | 46.3% | -0.098R | -5.313R | 0.874 | 8 | 0 |
| 2026 | LIMIT_TOUCH_ANCHOR | 42/53 | 16-22 | 42.1% | -0.111R | -6.000R | 1.000 | 11 | 0 |
| 2026 | LIMIT_ZONE_HIGH | 35/45 | 14-17 | 45.2% | 0.056R | 3.035R | 1.361 | 10 | 0 |
| 2026 | LIMIT_REACTION_LOW | 41/54 | 15-22 | 40.5% | -0.059R | -3.169R | 1.176 | 12 | 0 |

## Interpretation boundary
S7 changes entry geometry only; H1 demand and SD1 remain frozen.
No-fill, ambiguous, and unresolved cases contribute 0R to per-signal audit economics.
The protected-low floor and +1 event-R objective are audit geometry, not yet final SL/TP.
A deeper entry is not preferred automatically if it improves R:R by missing too many genuine expanders or selectively filling weak pullbacks.
