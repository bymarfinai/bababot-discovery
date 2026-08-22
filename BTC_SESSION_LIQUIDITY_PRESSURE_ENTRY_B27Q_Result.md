# B27Q — Causal Previous-Session Liquidity Pressure -> Retrace Entry Grid — Result

5m source rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Synthetic chronology tests and real-data mapping assertions completed before persistence.

Exact frozen previous-session High/Low only. Distinct visits are counted on raw 5m chronology; no B27C-P aggregated touch count is reused.

## Structural pressure probability

| Transition | Partition | Side | K | Purity | N | Target break | Opposite break | No break |
|---|---|---|---:|---|---:|---:|---:|---:|
| ASIA_TO_LONDON | external | LONG | 1 | ALL | 104 | 64.4% | 6.7% | 28.8% |
| ASIA_TO_LONDON | external | LONG | 1 | OPP0 | 100 | 66.0% | 5.0% | 29.0% |
| ASIA_TO_LONDON | external | LONG | 2 | ALL | 24 | 62.5% | 4.2% | 33.3% |
| ASIA_TO_LONDON | external | LONG | 2 | OPP0 | 24 | 62.5% | 4.2% | 33.3% |
| ASIA_TO_LONDON | external | LONG | 3 | ALL | 4 | 75.0% | 0.0% | 25.0% |
| ASIA_TO_LONDON | external | LONG | 3 | OPP0 | 4 | 75.0% | 0.0% | 25.0% |
| ASIA_TO_LONDON | external | SHORT | 1 | ALL | 111 | 74.8% | 4.5% | 20.7% |
| ASIA_TO_LONDON | external | SHORT | 1 | OPP0 | 107 | 74.8% | 4.7% | 20.6% |
| ASIA_TO_LONDON | external | SHORT | 2 | ALL | 35 | 68.6% | 0.0% | 31.4% |
| ASIA_TO_LONDON | external | SHORT | 2 | OPP0 | 31 | 67.7% | 0.0% | 32.3% |
| ASIA_TO_LONDON | external | SHORT | 3 | ALL | 6 | 100.0% | 0.0% | 0.0% |
| ASIA_TO_LONDON | external | SHORT | 3 | OPP0 | 6 | 100.0% | 0.0% | 0.0% |
| ASIA_TO_LONDON | development | LONG | 1 | ALL | 164 | 65.9% | 3.7% | 30.5% |
| ASIA_TO_LONDON | development | LONG | 1 | OPP0 | 161 | 65.8% | 3.1% | 31.1% |
| ASIA_TO_LONDON | development | LONG | 2 | ALL | 43 | 65.1% | 4.7% | 30.2% |
| ASIA_TO_LONDON | development | LONG | 2 | OPP0 | 43 | 65.1% | 4.7% | 30.2% |
| ASIA_TO_LONDON | development | LONG | 3 | ALL | 8 | 87.5% | 12.5% | 0.0% |
| ASIA_TO_LONDON | development | LONG | 3 | OPP0 | 8 | 87.5% | 12.5% | 0.0% |
| ASIA_TO_LONDON | development | SHORT | 1 | ALL | 155 | 67.7% | 5.2% | 27.1% |
| ASIA_TO_LONDON | development | SHORT | 1 | OPP0 | 150 | 68.7% | 5.3% | 26.0% |
| ASIA_TO_LONDON | development | SHORT | 2 | ALL | 44 | 65.9% | 6.8% | 27.3% |
| ASIA_TO_LONDON | development | SHORT | 2 | OPP0 | 44 | 65.9% | 6.8% | 27.3% |
| ASIA_TO_LONDON | development | SHORT | 3 | ALL | 12 | 58.3% | 16.7% | 25.0% |
| ASIA_TO_LONDON | development | SHORT | 3 | OPP0 | 12 | 58.3% | 16.7% | 25.0% |
| ASIA_TO_LONDON | reference_validation | LONG | 1 | ALL | 78 | 76.9% | 5.1% | 17.9% |
| ASIA_TO_LONDON | reference_validation | LONG | 1 | OPP0 | 77 | 76.6% | 5.2% | 18.2% |
| ASIA_TO_LONDON | reference_validation | LONG | 2 | ALL | 18 | 66.7% | 5.6% | 27.8% |
| ASIA_TO_LONDON | reference_validation | LONG | 2 | OPP0 | 18 | 66.7% | 5.6% | 27.8% |
| ASIA_TO_LONDON | reference_validation | LONG | 3 | ALL | 3 | 66.7% | 0.0% | 33.3% |
| ASIA_TO_LONDON | reference_validation | LONG | 3 | OPP0 | 3 | 66.7% | 0.0% | 33.3% |
| ASIA_TO_LONDON | reference_validation | SHORT | 1 | ALL | 65 | 84.6% | 1.5% | 13.8% |
| ASIA_TO_LONDON | reference_validation | SHORT | 1 | OPP0 | 65 | 84.6% | 1.5% | 13.8% |
| ASIA_TO_LONDON | reference_validation | SHORT | 2 | ALL | 15 | 93.3% | 0.0% | 6.7% |
| ASIA_TO_LONDON | reference_validation | SHORT | 2 | OPP0 | 15 | 93.3% | 0.0% | 6.7% |
| ASIA_TO_LONDON | reference_validation | SHORT | 3 | ALL | 5 | 100.0% | 0.0% | 0.0% |
| ASIA_TO_LONDON | reference_validation | SHORT | 3 | OPP0 | 5 | 100.0% | 0.0% | 0.0% |
| LONDON_TO_NEWYORK | external | LONG | 1 | ALL | 104 | 88.5% | 1.9% | 9.6% |
| LONDON_TO_NEWYORK | external | LONG | 1 | OPP0 | 101 | 89.1% | 2.0% | 8.9% |
| LONDON_TO_NEWYORK | external | LONG | 2 | ALL | 28 | 92.9% | 0.0% | 7.1% |
| LONDON_TO_NEWYORK | external | LONG | 2 | OPP0 | 27 | 92.6% | 0.0% | 7.4% |
| LONDON_TO_NEWYORK | external | LONG | 3 | ALL | 9 | 88.9% | 0.0% | 11.1% |
| LONDON_TO_NEWYORK | external | LONG | 3 | OPP0 | 9 | 88.9% | 0.0% | 11.1% |
| LONDON_TO_NEWYORK | external | SHORT | 1 | ALL | 97 | 71.1% | 8.2% | 20.6% |
| LONDON_TO_NEWYORK | external | SHORT | 1 | OPP0 | 94 | 73.4% | 7.4% | 19.1% |
| LONDON_TO_NEWYORK | external | SHORT | 2 | ALL | 28 | 71.4% | 3.6% | 25.0% |
| LONDON_TO_NEWYORK | external | SHORT | 2 | OPP0 | 28 | 71.4% | 3.6% | 25.0% |
| LONDON_TO_NEWYORK | external | SHORT | 3 | ALL | 5 | 40.0% | 0.0% | 60.0% |
| LONDON_TO_NEWYORK | external | SHORT | 3 | OPP0 | 5 | 40.0% | 0.0% | 60.0% |
| LONDON_TO_NEWYORK | development | LONG | 1 | ALL | 185 | 71.9% | 18.9% | 9.2% |
| LONDON_TO_NEWYORK | development | LONG | 1 | OPP0 | 164 | 72.6% | 18.3% | 9.1% |
| LONDON_TO_NEWYORK | development | LONG | 2 | ALL | 53 | 79.2% | 9.4% | 11.3% |
| LONDON_TO_NEWYORK | development | LONG | 2 | OPP0 | 44 | 81.8% | 6.8% | 11.4% |
| LONDON_TO_NEWYORK | development | LONG | 3 | ALL | 17 | 76.5% | 17.6% | 5.9% |
| LONDON_TO_NEWYORK | development | LONG | 3 | OPP0 | 13 | 84.6% | 7.7% | 7.7% |
| LONDON_TO_NEWYORK | development | SHORT | 1 | ALL | 205 | 77.6% | 15.6% | 6.8% |
| LONDON_TO_NEWYORK | development | SHORT | 1 | OPP0 | 192 | 77.1% | 15.6% | 7.3% |
| LONDON_TO_NEWYORK | development | SHORT | 2 | ALL | 63 | 82.5% | 9.5% | 7.9% |
| LONDON_TO_NEWYORK | development | SHORT | 2 | OPP0 | 55 | 83.6% | 7.3% | 9.1% |
| LONDON_TO_NEWYORK | development | SHORT | 3 | ALL | 21 | 85.7% | 9.5% | 4.8% |
| LONDON_TO_NEWYORK | development | SHORT | 3 | OPP0 | 16 | 87.5% | 6.2% | 6.2% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 1 | ALL | 91 | 84.6% | 12.1% | 3.3% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 1 | OPP0 | 82 | 85.4% | 11.0% | 3.7% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 2 | ALL | 18 | 100.0% | 0.0% | 0.0% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 2 | OPP0 | 17 | 100.0% | 0.0% | 0.0% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 3 | ALL | 2 | 100.0% | 0.0% | 0.0% |
| LONDON_TO_NEWYORK | reference_validation | LONG | 3 | OPP0 | 2 | 100.0% | 0.0% | 0.0% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 1 | ALL | 94 | 74.5% | 20.2% | 5.3% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 1 | OPP0 | 92 | 73.9% | 20.7% | 5.4% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 2 | ALL | 20 | 70.0% | 15.0% | 15.0% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 2 | OPP0 | 19 | 68.4% | 15.8% | 15.8% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 3 | ALL | 5 | 80.0% | 0.0% | 20.0% |
| LONDON_TO_NEWYORK | reference_validation | SHORT | 3 | OPP0 | 4 | 75.0% | 0.0% | 25.0% |

## Provisional entry screen

**No entry candidate passed the predeclared three-partition screen.**

Full entry grid is persisted in `BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_EntrySummary.csv`.
Every distinct visit is auditable in `BTC_SESSION_LIQUIDITY_PRESSURE_ENTRY_B27Q_Visits.csv`.

A `SCREEN_PASS` is discovery evidence only because multiple K/depth combinations are examined. It is not independent validation and does not modify live BBC.

Research only; live BBC unchanged.
