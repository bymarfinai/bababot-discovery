# B27AF — BTC London -> New York F85/F15 Post-Fill Path Anatomy — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen F85/F15 cohorts and H2 identities reproduce. Fill-bar high/low are excluded; all OHLC excursion diagnostics start on the next complete 5m bar.

## All-fill post-entry behavior

| Partition | Side | N | H2 | Fill close wrong | Next-bar N | Next-bar wrong | Ever wrong | Median wrong-close rate | Median close MAE | Median wick MAE | Median stop distance consumed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | LONG | 46 | 89.1% | 41.3% | 41 | 56.1% | 73.9% | 46.4% | 0.057R | 0.106R | 21.2% |
| external | SHORT | 50 | 74.0% | 50.0% | 36 | 61.1% | 70.0% | 65.5% | 0.092R | 0.120R | 24.1% |
| development | LONG | 72 | 73.6% | 58.3% | 56 | 71.4% | 80.6% | 80.0% | 0.123R | 0.180R | 35.9% |
| development | SHORT | 79 | 74.7% | 68.4% | 63 | 73.0% | 79.7% | 87.2% | 0.118R | 0.177R | 35.3% |
| reference_validation | LONG | 31 | 87.1% | 64.5% | 21 | 71.4% | 80.6% | 85.7% | 0.164R | 0.245R | 49.1% |
| reference_validation | SHORT | 34 | 70.6% | 64.7% | 28 | 67.9% | 91.2% | 92.8% | 0.136R | 0.182R | 36.3% |
| POOLED_MAJOR | LONG | 149 | 81.2% | 54.4% | 118 | 66.1% | 78.5% | 69.4% | 0.094R | 0.135R | 26.9% |
| POOLED_MAJOR | SHORT | 163 | 73.6% | 62.0% | 127 | 68.5% | 79.1% | 80.0% | 0.116R | 0.160R | 32.0% |
| august | LONG | 3 | 100.0% | 66.7% | 3 | 66.7% | 100.0% | 50.0% | 0.044R | 0.109R | 21.9% |
| august | SHORT | 1 | 100.0% | 0.0% | 0 | - | 0.0% | 0.0% | 0.000R | 0.000R | 0.0% |

## Pooled-major winners vs failures

| Side | Outcome | N | Fill close wrong | Next-bar wrong | Ever wrong | Median wrong-close rate | Max wrong streak med | Close MAE med | Wick MAE med | Stop consumed med | Terminal min med |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | H2_SUCCESS | 121 | 52.1% | 63.3% | 73.6% | 54.5% | 2.000 | 0.062R | 0.104R | 20.8% | 20.000 |
| LONG | H2_FAIL | 28 | 64.3% | 75.0% | 100.0% | 97.1% | 25.000 | 0.636R | 0.704R | 140.7% | 170.000 |
| SHORT | H2_SUCCESS | 120 | 59.2% | 63.1% | 71.7% | 63.4% | 1.000 | 0.058R | 0.098R | 19.7% | 15.000 |
| SHORT | H2_FAIL | 43 | 69.8% | 79.1% | 100.0% | 97.6% | 21.000 | 0.661R | 0.756R | 151.3% | 125.000 |

## Diagnostic readout

- All fills: SHORT minus LONG fill-bar-wrong = +7.6pp; next-bar-wrong = +2.4pp; ever-wrong = +0.6pp.
- All fills median wick MAE: LONG 0.135R vs SHORT 0.160R; median mirrored stop-distance consumed: LONG 26.9% vs SHORT 32.0%.
- H2 winners median wrong-close rate: LONG 54.5% vs SHORT 63.4%; H2 failures: LONG 97.1% vs SHORT 97.6%.
- SHORT internal separation (FAIL minus SUCCESS): fill-bar-wrong +10.6pp; next-bar-wrong +16.0pp; median wick MAE +0.658R.

No filter is selected from these diagnostics. Research only; live BBC unchanged.
