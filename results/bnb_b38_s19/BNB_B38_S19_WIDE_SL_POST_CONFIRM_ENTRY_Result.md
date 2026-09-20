# BNB B38-S19 — Wide-SL Post-Confirmation Entry Audit

Frozen wide-SL cut: `baseline_sl_pct > 0.017122`

Detector and original structural SL remain unchanged. Retest orders activate only after E2 break confirmation.

## Q4 entry audit

| Period | Candidate | Avail | Fill | Entry improvement | Risk compression | W-L | WR | Med WIN R | Exp filled | Total R filled | WIN filled/available | WIN missed | WIN→LOSS | LOSS avoided |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | MARKET_BREAK_CLOSE | 110/110 | 110/110 (100.0%) | 0.0% | 0.0% | 87-23 | 79.1% | 0.088R | -0.069R | -7.572R | 87/87 | 0 | 0 | 0 |
| DEV | LIMIT_BREAK_LEVEL_RETEST | 110/110 | 62/110 (56.4%) | 0.2% | 8.0% | 39-23 | 62.9% | 0.261R | -0.169R | -10.495R | 39/87 | 41 | 0 | 0 |
| DEV | LIMIT_HOLD_CLOSE_RETEST | 110/110 | 39/110 (35.5%) | 0.8% | 35.2% | 17-22 | 43.6% | 0.514R | -0.322R | -12.541R | 17/87 | 69 | 0 | 0 |
| DEV | LIMIT_RECLAIM_CLOSE_RETEST | 110/110 | 33/110 (30.0%) | 1.1% | 46.3% | 12-21 | 36.4% | 0.726R | -0.304R | -10.041R | 12/87 | 75 | 0 | 0 |
| DEV | LIMIT_DEMAND_HIGH_RETEST | 110/110 | 24/110 (21.8%) | 1.7% | 72.9% | 5-19 | 20.8% | 1.342R | -0.521R | -12.493R | 5/87 | 82 | 0 | 0 |
| REF | MARKET_BREAK_CLOSE | 50/50 | 50/50 (100.0%) | 0.0% | 0.0% | 44-6 | 88.0% | 0.038R | -0.032R | -1.577R | 44/44 | 0 | 0 | 0 |
| REF | LIMIT_BREAK_LEVEL_RETEST | 50/50 | 33/50 (66.0%) | 0.4% | 7.6% | 27-6 | 81.8% | 0.106R | 0.005R | 0.180R | 27/44 | 13 | 0 | 0 |
| REF | LIMIT_HOLD_CLOSE_RETEST | 50/50 | 24/50 (48.0%) | 0.8% | 28.0% | 18-6 | 75.0% | 0.167R | 0.028R | 0.669R | 18/44 | 26 | 0 | 0 |
| REF | LIMIT_RECLAIM_CLOSE_RETEST | 50/50 | 9/50 (18.0%) | 1.3% | 48.6% | 3-6 | 33.3% | 0.461R | -0.468R | -4.214R | 3/44 | 41 | 0 | 0 |
| REF | LIMIT_DEMAND_HIGH_RETEST | 50/50 | 6/50 (12.0%) | 1.6% | 67.4% | 2-4 | 33.3% | 1.328R | -0.224R | -1.343R | 2/44 | 42 | 0 | 0 |

## Full E2 portfolio if Q4 waits for retest

Nonfills/unavailable/ambiguous Q4 cases are treated as no-trade (0R).

| Period | Candidate | Traded | W-L | WR | Exp / all E2 | Exp / traded | Total R |
|---|---|---:|---:|---:|---:|---:|---:|
| DEV | MARKET_BREAK_CLOSE | 440/440 | 325-115 | 73.9% | 0.035R | 0.035R | 15.312R |
| DEV | LIMIT_BREAK_LEVEL_RETEST | 392/440 | 277-115 | 70.7% | 0.028R | 0.032R | 12.389R |
| DEV | LIMIT_HOLD_CLOSE_RETEST | 369/440 | 255-114 | 69.1% | 0.024R | 0.028R | 10.343R |
| DEV | LIMIT_RECLAIM_CLOSE_RETEST | 363/440 | 250-113 | 68.9% | 0.029R | 0.035R | 12.843R |
| DEV | LIMIT_DEMAND_HIGH_RETEST | 354/440 | 243-111 | 68.6% | 0.024R | 0.029R | 10.391R |
| REF | MARKET_BREAK_CLOSE | 272/272 | 201-71 | 73.9% | -0.002R | -0.002R | -0.519R |
| REF | LIMIT_BREAK_LEVEL_RETEST | 255/272 | 184-71 | 72.2% | 0.005R | 0.005R | 1.237R |
| REF | LIMIT_HOLD_CLOSE_RETEST | 246/272 | 175-71 | 71.1% | 0.006R | 0.007R | 1.726R |
| REF | LIMIT_RECLAIM_CLOSE_RETEST | 231/272 | 160-71 | 69.3% | -0.012R | -0.014R | -3.157R |
| REF | LIMIT_DEMAND_HIGH_RETEST | 228/272 | 159-69 | 69.7% | -0.001R | -0.001R | -0.286R |

## Annual stability

| Year | Candidate | Avail | Fill | W-L | WR | Exp filled | WIN missed | LOSS avoided |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | MARKET_BREAK_CLOSE | 45/45 | 45/45 | 34-11 | 75.6% | -0.022R | 0 | 0 |
| 2022 | LIMIT_BREAK_LEVEL_RETEST | 45/45 | 27/45 | 16-11 | 59.3% | -0.134R | 16 | 0 |
| 2022 | LIMIT_HOLD_CLOSE_RETEST | 45/45 | 20/45 | 9-11 | 45.0% | -0.346R | 25 | 0 |
| 2022 | LIMIT_RECLAIM_CLOSE_RETEST | 45/45 | 17/45 | 7-10 | 41.2% | -0.159R | 27 | 0 |
| 2022 | LIMIT_DEMAND_HIGH_RETEST | 45/45 | 11/45 | 2-9 | 18.2% | -0.558R | 32 | 0 |
| 2023 | MARKET_BREAK_CLOSE | 31/31 | 31/31 | 28-3 | 90.3% | -0.037R | 0 | 0 |
| 2023 | LIMIT_BREAK_LEVEL_RETEST | 31/31 | 14/31 | 11-3 | 78.6% | -0.086R | 13 | 0 |
| 2023 | LIMIT_HOLD_CLOSE_RETEST | 31/31 | 4/31 | 2-2 | 50.0% | -0.224R | 25 | 0 |
| 2023 | LIMIT_RECLAIM_CLOSE_RETEST | 31/31 | 3/31 | 1-2 | 33.3% | -0.499R | 27 | 0 |
| 2023 | LIMIT_DEMAND_HIGH_RETEST | 31/31 | 1/31 | 0-1 | 0.0% | -1.000R | 28 | 0 |
| 2024 | MARKET_BREAK_CLOSE | 34/34 | 34/34 | 25-9 | 73.5% | -0.159R | 0 | 0 |
| 2024 | LIMIT_BREAK_LEVEL_RETEST | 34/34 | 21/34 | 12-9 | 57.1% | -0.270R | 12 | 0 |
| 2024 | LIMIT_HOLD_CLOSE_RETEST | 34/34 | 15/34 | 6-9 | 40.0% | -0.315R | 19 | 0 |
| 2024 | LIMIT_RECLAIM_CLOSE_RETEST | 34/34 | 13/34 | 4-9 | 30.8% | -0.449R | 21 | 0 |
| 2024 | LIMIT_DEMAND_HIGH_RETEST | 34/34 | 12/34 | 3-9 | 25.0% | -0.447R | 22 | 0 |
| 2025 | MARKET_BREAK_CLOSE | 39/39 | 39/39 | 35-4 | 89.7% | -0.022R | 0 | 0 |
| 2025 | LIMIT_BREAK_LEVEL_RETEST | 39/39 | 26/39 | 22-4 | 84.6% | 0.003R | 11 | 0 |
| 2025 | LIMIT_HOLD_CLOSE_RETEST | 39/39 | 19/39 | 15-4 | 78.9% | 0.006R | 20 | 0 |
| 2025 | LIMIT_RECLAIM_CLOSE_RETEST | 39/39 | 5/39 | 1-4 | 20.0% | -0.708R | 34 | 0 |
| 2025 | LIMIT_DEMAND_HIGH_RETEST | 39/39 | 4/39 | 1-3 | 25.0% | -0.535R | 34 | 0 |
| 2026 | MARKET_BREAK_CLOSE | 11/11 | 11/11 | 9-2 | 81.8% | -0.064R | 0 | 0 |
| 2026 | LIMIT_BREAK_LEVEL_RETEST | 11/11 | 7/11 | 5-2 | 71.4% | 0.016R | 2 | 0 |
| 2026 | LIMIT_HOLD_CLOSE_RETEST | 11/11 | 5/11 | 3-2 | 60.0% | 0.112R | 6 | 0 |
| 2026 | LIMIT_RECLAIM_CLOSE_RETEST | 11/11 | 4/11 | 2-2 | 50.0% | -0.169R | 7 | 0 |
| 2026 | LIMIT_DEMAND_HIGH_RETEST | 11/11 | 2/11 | 1-1 | 50.0% | 0.399R | 8 | 0 |

## Interpretation boundary
S19 does not alter E2 confirmation or structural invalidation.
A retest candidate is useful only if better R is not purchased by missing too many baseline winners or becoming regime-dependent.
No candidate is promoted automatically.
