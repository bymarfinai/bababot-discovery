# B27AL — BTC London->NY SHORT F15 Winner MAE / Stop-Distance Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27AK F15 fill identity and H2 classifications reproduced exactly from raw 5m chronology.

B27AL is diagnostic only: no stop distance is selected or promoted.

## F15 H2-winner adverse excursion

| Partition | Winners | Pre-H2 D P50 | P75 | P90 | P95 | Max | Conservative-through-H2 D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 37 | 0.117 | 0.199 | 0.333 | 0.366 | 0.430 | 0.117 | 0.199 | 0.333 | 0.366 | 0.430 |
| development | 59 | 0.195 | 0.294 | 0.439 | 0.629 | 1.139 | 0.195 | 0.299 | 0.439 | 0.629 | 1.139 |
| reference_validation | 24 | 0.195 | 0.325 | 0.522 | 0.619 | 0.866 | 0.195 | 0.325 | 0.522 | 0.619 | 0.866 |
| august | 1 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 | 0.163 |

## Selected descriptive survival points

| Partition | D | Stop fraction | H2 winners | Pre-H2 survive | Conservative survive |
|---|---:|---:|---:|---:|---:|
| external | 0.10 | 0.25 | 37 | 37.8% | 37.8% |
| external | 0.20 | 0.35 | 37 | 75.7% | 75.7% |
| external | 0.30 | 0.45 | 37 | 86.5% | 86.5% |
| external | 0.40 | 0.55 | 37 | 97.3% | 97.3% |
| external | 0.50 | 0.65 | 37 | 100.0% | 100.0% |
| external | 0.60 | 0.75 | 37 | 100.0% | 100.0% |
| external | 0.70 | 0.85 | 37 | 100.0% | 100.0% |
| external | 0.85 | 1.00 | 37 | 100.0% | 100.0% |
| development | 0.10 | 0.25 | 59 | 8.5% | 8.5% |
| development | 0.20 | 0.35 | 59 | 52.5% | 52.5% |
| development | 0.30 | 0.45 | 59 | 78.0% | 76.3% |
| development | 0.40 | 0.55 | 59 | 84.7% | 84.7% |
| development | 0.50 | 0.65 | 59 | 91.5% | 91.5% |
| development | 0.60 | 0.75 | 59 | 93.2% | 93.2% |
| development | 0.70 | 0.85 | 59 | 94.9% | 94.9% |
| development | 0.85 | 1.00 | 59 | 96.6% | 96.6% |
| reference_validation | 0.10 | 0.25 | 24 | 16.7% | 16.7% |
| reference_validation | 0.20 | 0.35 | 24 | 50.0% | 50.0% |
| reference_validation | 0.30 | 0.45 | 24 | 66.7% | 66.7% |
| reference_validation | 0.40 | 0.55 | 24 | 83.3% | 83.3% |
| reference_validation | 0.50 | 0.65 | 24 | 83.3% | 83.3% |
| reference_validation | 0.60 | 0.75 | 24 | 91.7% | 91.7% |
| reference_validation | 0.70 | 0.85 | 24 | 95.8% | 95.8% |
| reference_validation | 0.85 | 1.00 | 24 | 95.8% | 95.8% |
| august | 0.10 | 0.25 | 1 | 0.0% | 0.0% |
| august | 0.20 | 0.35 | 1 | 100.0% | 100.0% |
| august | 0.30 | 0.45 | 1 | 100.0% | 100.0% |
| august | 0.40 | 0.55 | 1 | 100.0% | 100.0% |
| august | 0.50 | 0.65 | 1 | 100.0% | 100.0% |
| august | 0.60 | 0.75 | 1 | 100.0% | 100.0% |
| august | 0.70 | 0.85 | 1 | 100.0% | 100.0% |
| august | 0.85 | 1.00 | 1 | 100.0% | 100.0% |

## Non-H2 filled-path comparison

| Partition | Non-H2 fills | Adverse D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| external | 13 | 0.443 | 0.881 | 0.948 | 0.963 | 0.983 |
| development | 20 | 0.947 | 1.109 | 1.518 | 1.761 | 1.770 |
| reference_validation | 10 | 0.975 | 1.036 | 1.115 | 1.144 | 1.172 |
| august | 0 | - | - | - | - | - |

Distance D is measured upward from F15 in previous-London-range units; equality with a stop counts as stopped.

Research only; live BBC unchanged.
