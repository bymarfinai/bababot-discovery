# B27X — London -> New York F85 Winner MAE / Stop-Distance Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27W F85 fill identity, entry timestamps, and H2 classifications were reproduced exactly from raw 5m chronology.

B27X is diagnostic only: no stop distance is selected or promoted.

## F85 H2-winner adverse excursion

| Partition | Winners | Pre-H2 D P50 | P75 | P90 | P95 | Max | Conservative-through-H2 D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 41 | 0.114 | 0.184 | 0.298 | 0.376 | 0.666 | 0.114 | 0.184 | 0.298 | 0.376 | 0.666 |
| development | 53 | 0.153 | 0.288 | 0.505 | 0.574 | 0.814 | 0.153 | 0.288 | 0.505 | 0.574 | 1.702 |
| reference_validation | 27 | 0.267 | 0.396 | 0.669 | 0.736 | 0.767 | 0.273 | 0.396 | 0.669 | 0.736 | 0.767 |
| august | 3 | 0.189 | 0.212 | 0.226 | 0.230 | 0.235 | 0.189 | 0.212 | 0.226 | 0.230 | 0.235 |

## Conservative winner-survival curve

Distance D is measured downward from F85 in previous-London-range units. Equality with the stop counts as stopped.

| Partition | D | Stop fraction | H2 winners | Pre-H2 survive | Conservative through-H2 survive |
|---|---:|---:|---:|---:|---:|
| external | 0.10 | 0.75 | 41 | 43.9% | 43.9% |
| external | 0.15 | 0.70 | 41 | 61.0% | 61.0% |
| external | 0.20 | 0.65 | 41 | 78.0% | 78.0% |
| external | 0.25 | 0.60 | 41 | 85.4% | 85.4% |
| external | 0.30 | 0.55 | 41 | 90.2% | 90.2% |
| external | 0.40 | 0.45 | 41 | 97.6% | 97.6% |
| external | 0.50 | 0.35 | 41 | 97.6% | 97.6% |
| external | 0.60 | 0.25 | 41 | 97.6% | 97.6% |
| external | 0.70 | 0.15 | 41 | 100.0% | 100.0% |
| external | 0.85 | 0.00 | 41 | 100.0% | 100.0% |
| development | 0.10 | 0.75 | 53 | 24.5% | 24.5% |
| development | 0.15 | 0.70 | 53 | 47.2% | 47.2% |
| development | 0.20 | 0.65 | 53 | 66.0% | 66.0% |
| development | 0.25 | 0.60 | 53 | 69.8% | 69.8% |
| development | 0.30 | 0.55 | 53 | 79.2% | 79.2% |
| development | 0.40 | 0.45 | 53 | 88.7% | 88.7% |
| development | 0.50 | 0.35 | 53 | 88.7% | 88.7% |
| development | 0.60 | 0.25 | 53 | 96.2% | 96.2% |
| development | 0.70 | 0.15 | 53 | 96.2% | 96.2% |
| development | 0.85 | 0.00 | 53 | 100.0% | 98.1% |
| reference_validation | 0.10 | 0.75 | 27 | 18.5% | 18.5% |
| reference_validation | 0.15 | 0.70 | 27 | 25.9% | 25.9% |
| reference_validation | 0.20 | 0.65 | 27 | 29.6% | 29.6% |
| reference_validation | 0.25 | 0.60 | 27 | 40.7% | 40.7% |
| reference_validation | 0.30 | 0.55 | 27 | 55.6% | 55.6% |
| reference_validation | 0.40 | 0.45 | 27 | 74.1% | 74.1% |
| reference_validation | 0.50 | 0.35 | 27 | 81.5% | 81.5% |
| reference_validation | 0.60 | 0.25 | 27 | 81.5% | 81.5% |
| reference_validation | 0.70 | 0.15 | 27 | 88.9% | 88.9% |
| reference_validation | 0.85 | 0.00 | 27 | 100.0% | 100.0% |
| august | 0.10 | 0.75 | 3 | 33.3% | 33.3% |
| august | 0.15 | 0.70 | 3 | 33.3% | 33.3% |
| august | 0.20 | 0.65 | 3 | 66.7% | 66.7% |
| august | 0.25 | 0.60 | 3 | 100.0% | 100.0% |
| august | 0.30 | 0.55 | 3 | 100.0% | 100.0% |
| august | 0.40 | 0.45 | 3 | 100.0% | 100.0% |
| august | 0.50 | 0.35 | 3 | 100.0% | 100.0% |
| august | 0.60 | 0.25 | 3 | 100.0% | 100.0% |
| august | 0.70 | 0.15 | 3 | 100.0% | 100.0% |
| august | 0.85 | 0.00 | 3 | 100.0% | 100.0% |

## Non-H2 filled-path comparison

| Partition | Non-H2 fills | Adverse D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| external | 5 | 0.370 | 0.380 | 0.574 | 0.639 | 0.704 |
| development | 19 | 0.984 | 1.109 | 1.254 | 1.439 | 1.554 |
| reference_validation | 4 | 0.821 | 1.097 | 1.331 | 1.409 | 1.487 |
| august | 0 | - | - | - | - | - |

Full D05-D85 survival curve and one-row-per-F85-path audit are persisted in CSV outputs.

Research only; live BBC unchanged.
