# B27CI — BTC 24H Post-Rebreak TP Frontier — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** Exact B27CE confirmed-rebreak cohort reproduced: external 149 / development 237 / validation 133 / pooled OOS 282 / pooled major 519. Anatomy only; trading WR/PF/PnL/expectancy/SL are N/A.

Evaluation begins on the next raw 5m bar after the Low rebreak is confirmed. A target may be touched before a later same-bar close reclaims L.

## TP hit frontier — major partitions

| Target below L | External | Development | Validation | Pooled OOS |
|---|---:|---:|---:|---:|
| T2.5 = 2.5% R4 | 95.2% | 95.7% | 96.2% | 95.7% |
| T05 = 5% R4 | 82.3% | 89.3% | 86.5% | 84.3% |
| T7.5 = 7.5% R4 | 73.5% | 79.4% | 79.7% | 76.4% |
| T10 = 10% R4 | 65.3% | 73.8% | 73.7% | 69.3% |
| T15 = 15% R4 | 59.2% | 56.2% | 59.4% | 59.3% |
| T20 = 20% R4 | 49.7% | 48.1% | 48.9% | 49.3% |
| T25 = 25% R4 | 42.9% | 41.6% | 40.6% | 41.8% |
| T35 = 35% R4 | 32.7% | 31.3% | 27.1% | 30.0% |
| T50 = 50% R4 | 24.5% | 22.7% | 16.5% | 20.7% |

## Maximum downside extension after confirmed rebreak

| Scope | Source / eligible | P25 | P50 | P75 | P90 | Fresh reclaim rate |
|---|---:|---:|---:|---:|---:|---:|
| external | 149 / 147 | 7.1% | 20.0% | 48.6% | 103.6% | 79.6% |
| development | 237 / 233 | 9.5% | 19.0% | 47.5% | 109.3% | 80.3% |
| reference_validation | 133 / 133 | 9.6% | 19.5% | 35.8% | 106.4% | 79.7% |
| POOLED_OOS | 282 / 280 | 8.2% | 19.8% | 42.4% | 104.7% | 79.6% |
| POOLED_MAJOR | 519 / 513 | 8.8% | 19.5% | 44.1% | 107.4% | 79.9% |

## Six-clock frontier — pooled major

| UTC block | Eligible N | T05 | T10 | T15 | T20 | T25 | Median max extension |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | 80 | 91.2% | 77.5% | 65.0% | 57.5% | 50.0% | 24.9% |
| 04-08 | 86 | 81.4% | 66.3% | 48.8% | 40.7% | 29.1% | 14.0% |
| 08-12 | 84 | 86.9% | 76.2% | 65.5% | 58.3% | 50.0% | 25.2% |
| 12-16 | 114 | 89.5% | 79.8% | 70.2% | 59.6% | 51.8% | 26.1% |
| 16-20 | 84 | 84.5% | 61.9% | 42.9% | 35.7% | 32.1% | 13.0% |
| 20-00 | 65 | 84.6% | 61.5% | 49.2% | 33.8% | 32.3% | 14.7% |

## Development selection

| Target | Dev eligible N | Dev hit | >=70% | Selected |
|---|---:|---:|---|---|
| T2.5 | 233 | 95.7% | YES | NO |
| T05 | 233 | 89.3% | YES | NO |
| T7.5 | 233 | 79.4% | YES | NO |
| T10 | 233 | 73.8% | YES | YES |
| T15 | 233 | 56.2% | NO | NO |
| T20 | 233 | 48.1% | NO | NO |
| T25 | 233 | 41.6% | NO | NO |
| T35 | 233 | 31.3% | NO | NO |
| T50 | 233 | 22.7% | NO | NO |

Frozen structural TP candidate: **T10 = L - 10% R4**.
Untouched OOS support: **PASS** (external 65.3%, validation 73.7%, pooled OOS 69.3%).

**Frozen verdict: `B27CI_TP_FRONTIER_SUPPORTED`.**

This TP is a structural continuation target only, not a trading win rate or profit-optimal target. SL/economics require a separate preregistered test.
