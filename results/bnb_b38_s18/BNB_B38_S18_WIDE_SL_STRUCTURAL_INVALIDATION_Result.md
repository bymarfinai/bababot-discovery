# BNB B38-S18 — Wide-SL Structural Invalidation Audit

Frozen wide-SL cut: `baseline_sl_pct > 0.017122`

## Wide-SL candidate audit

| Period | Candidate | Avail | Med SL % | Compression | W-L | WR | Med WIN R | Exp | Total R | Baseline WIN retained | False-stop | LOSS→WIN |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | TOUCH_LOW_BASELINE | 110/110 | 2.2% | 0.0% | 87-23 | 79.1% | 0.088R | -0.069R | -7.572R | 87/87 | 0 (0.0%) | 0 |
| DEV | RECLAIM_LOW | 110/110 | 2.1% | 0.0% | 86-24 | 78.2% | 0.089R | -0.054R | -5.995R | 86/87 | 1 (1.1%) | 0 |
| DEV | HOLD_LOW | 110/110 | 1.3% | 41.7% | 78-32 | 70.9% | 0.082R | -0.051R | -5.651R | 78/87 | 9 (10.3%) | 0 |
| DEV | PROTECTED_PIVOT_LOW | 90/110 | 1.9% | 0.7% | 68-22 | 75.6% | 0.058R | -0.115R | -10.354R | 68/72 | 4 (5.6%) | 0 |
| DEV | DEMAND_LOW_TOUCH | 49/110 | 2.0% | 13.8% | 37-12 | 75.5% | 0.042R | -0.172R | -8.424R | 37/38 | 1 (2.6%) | 0 |
| DEV | DEMAND_LOW_CLOSE15 | 49/110 | 2.0% | 13.8% | 39-10 | 79.6% | 0.045R | -0.139R | -6.792R | 37/38 | 1 (2.6%) | 2 |
| REF | TOUCH_LOW_BASELINE | 50/50 | 2.4% | 0.0% | 44-6 | 88.0% | 0.038R | -0.032R | -1.577R | 44/44 | 0 (0.0%) | 0 |
| REF | RECLAIM_LOW | 50/50 | 2.2% | 0.0% | 44-6 | 88.0% | 0.039R | -0.027R | -1.375R | 44/44 | 0 (0.0%) | 0 |
| REF | HOLD_LOW | 50/50 | 1.6% | 50.1% | 42-8 | 84.0% | 0.058R | -0.033R | -1.639R | 42/44 | 2 (4.5%) | 0 |
| REF | PROTECTED_PIVOT_LOW | 43/50 | 2.0% | 0.0% | 38-5 | 88.4% | 0.049R | -0.004R | -0.152R | 38/38 | 0 (0.0%) | 0 |
| REF | DEMAND_LOW_TOUCH | 35/50 | 2.3% | 18.7% | 31-4 | 88.6% | 0.043R | -0.035R | -1.209R | 31/31 | 0 (0.0%) | 0 |
| REF | DEMAND_LOW_CLOSE15 | 35/50 | 2.3% | 18.7% | 31-4 | 88.6% | 0.043R | -0.062R | -2.181R | 31/31 | 0 (0.0%) | 0 |

## False-stop anatomy

| Period | Candidate | False stops | Med stop→later TP1 | Med overshoot below stop | Med overshoot in candidate R |
|---|---|---:|---:|---:|---:|
| DEV | RECLAIM_LOW | 1 | 1855.0m | 0.5% | 0.208R |
| DEV | HOLD_LOW | 9 | 165.0m | 0.3% | 0.269R |
| DEV | PROTECTED_PIVOT_LOW | 4 | 1180.0m | 1.2% | 0.825R |
| DEV | DEMAND_LOW_TOUCH | 1 | 1855.0m | 0.5% | 0.202R |
| DEV | DEMAND_LOW_CLOSE15 | 1 | 1790.0m | 0.5% | 0.202R |
| REF | HOLD_LOW | 2 | 110.0m | 0.4% | 0.517R |

## Full E2 portfolio if only wide-SL Q4 is replaced

| Period | Candidate | W-L | WR | Exp | Total R |
|---|---|---:|---:|---:|---:|
| DEV | TOUCH_LOW_BASELINE | 325-115 | 73.9% | 0.035R | 15.312R |
| DEV | RECLAIM_LOW | 324-116 | 73.6% | 0.038R | 16.889R |
| DEV | HOLD_LOW | 316-124 | 71.8% | 0.039R | 17.233R |
| DEV | PROTECTED_PIVOT_LOW | 321-119 | 73.0% | 0.030R | 13.049R |
| DEV | DEMAND_LOW_TOUCH | 324-116 | 73.6% | 0.033R | 14.425R |
| DEV | DEMAND_LOW_CLOSE15 | 326-114 | 74.1% | 0.036R | 16.057R |
| REF | TOUCH_LOW_BASELINE | 201-71 | 73.9% | -0.002R | -0.519R |
| REF | RECLAIM_LOW | 201-71 | 73.9% | -0.001R | -0.318R |
| REF | HOLD_LOW | 199-73 | 73.2% | -0.002R | -0.582R |
| REF | PROTECTED_PIVOT_LOW | 201-71 | 73.9% | 0.001R | 0.287R |
| REF | DEMAND_LOW_TOUCH | 201-71 | 73.9% | -0.000R | -0.131R |
| REF | DEMAND_LOW_CLOSE15 | 201-71 | 73.9% | -0.004R | -1.103R |

## Annual stability

| Year | Candidate | Avail | W-L | WR | Exp | Total R | False-stop |
|---:|---|---:|---:|---:|---:|---:|---:|
| 2022 | TOUCH_LOW_BASELINE | 45/45 | 34-11 | 75.6% | -0.022R | -0.995R | 0 |
| 2022 | RECLAIM_LOW | 45/45 | 33-12 | 73.3% | 0.004R | 0.167R | 1 |
| 2022 | HOLD_LOW | 45/45 | 29-16 | 64.4% | 0.008R | 0.353R | 5 |
| 2022 | PROTECTED_PIVOT_LOW | 34/45 | 26-8 | 76.5% | -0.043R | -1.475R | 1 |
| 2022 | DEMAND_LOW_TOUCH | 12/45 | 6-6 | 50.0% | -0.401R | -4.813R | 1 |
| 2022 | DEMAND_LOW_CLOSE15 | 12/45 | 8-4 | 66.7% | -0.172R | -2.061R | 1 |
| 2023 | TOUCH_LOW_BASELINE | 31/31 | 28-3 | 90.3% | -0.037R | -1.156R | 0 |
| 2023 | RECLAIM_LOW | 31/31 | 28-3 | 90.3% | -0.030R | -0.928R | 0 |
| 2023 | HOLD_LOW | 31/31 | 28-3 | 90.3% | 0.018R | 0.570R | 0 |
| 2023 | PROTECTED_PIVOT_LOW | 26/31 | 22-4 | 84.6% | -0.078R | -2.024R | 1 |
| 2023 | DEMAND_LOW_TOUCH | 17/31 | 15-2 | 88.2% | -0.045R | -0.763R | 0 |
| 2023 | DEMAND_LOW_CLOSE15 | 17/31 | 15-2 | 88.2% | -0.050R | -0.850R | 0 |
| 2024 | TOUCH_LOW_BASELINE | 34/34 | 25-9 | 73.5% | -0.159R | -5.421R | 0 |
| 2024 | RECLAIM_LOW | 34/34 | 25-9 | 73.5% | -0.154R | -5.233R | 0 |
| 2024 | HOLD_LOW | 34/34 | 21-13 | 61.8% | -0.193R | -6.574R | 4 |
| 2024 | PROTECTED_PIVOT_LOW | 30/34 | 20-10 | 66.7% | -0.228R | -6.854R | 2 |
| 2024 | DEMAND_LOW_TOUCH | 20/34 | 16-4 | 80.0% | -0.142R | -2.848R | 0 |
| 2024 | DEMAND_LOW_CLOSE15 | 20/34 | 16-4 | 80.0% | -0.194R | -3.880R | 0 |
| 2025 | TOUCH_LOW_BASELINE | 39/39 | 35-4 | 89.7% | -0.022R | -0.869R | 0 |
| 2025 | RECLAIM_LOW | 39/39 | 35-4 | 89.7% | -0.017R | -0.673R | 0 |
| 2025 | HOLD_LOW | 39/39 | 34-5 | 87.2% | 0.004R | 0.155R | 1 |
| 2025 | PROTECTED_PIVOT_LOW | 32/39 | 29-3 | 90.6% | 0.011R | 0.348R | 0 |
| 2025 | DEMAND_LOW_TOUCH | 28/39 | 25-3 | 89.3% | -0.035R | -0.979R | 0 |
| 2025 | DEMAND_LOW_CLOSE15 | 28/39 | 25-3 | 89.3% | -0.060R | -1.677R | 0 |
| 2026 | TOUCH_LOW_BASELINE | 11/11 | 9-2 | 81.8% | -0.064R | -0.708R | 0 |
| 2026 | RECLAIM_LOW | 11/11 | 9-2 | 81.8% | -0.064R | -0.701R | 0 |
| 2026 | HOLD_LOW | 11/11 | 8-3 | 72.7% | -0.163R | -1.794R | 1 |
| 2026 | PROTECTED_PIVOT_LOW | 11/11 | 9-2 | 81.8% | -0.045R | -0.500R | 0 |
| 2026 | DEMAND_LOW_TOUCH | 7/11 | 6-1 | 85.7% | -0.033R | -0.230R | 0 |
| 2026 | DEMAND_LOW_CLOSE15 | 7/11 | 6-1 | 85.7% | -0.072R | -0.504R | 0 |

## Interpretation boundary
S18 audits whether wide baseline stops contain a closer causal invalidation point.
A tighter level that creates many false stops is not considered structurally valid merely because its R multiple looks better.
No candidate is promoted automatically.
