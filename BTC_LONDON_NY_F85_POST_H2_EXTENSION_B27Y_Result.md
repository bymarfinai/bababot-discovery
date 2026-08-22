# B27Y — London -> New York F85 Post-H2 Breakout Extension Atlas — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27W F85 fill identity and H2 timestamps were frozen; H2 is treated as a milestone, not TP.

## Breakout acceptance and extension distribution

| Partition | F85 fills | H2 | H2 rate | 5m close > H given H2 | Close > H all fills | High ext P25 | P50 | P75 | P90 | Close ext P50 | P75 | P90 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 46 | 41 | 89.1% | 95.1% | 84.8% | 0.221 | 0.371 | 0.529 | 0.968 | 0.272 | 0.416 | 0.844 |
| development | 72 | 53 | 73.6% | 90.6% | 66.7% | 0.394 | 0.665 | 1.351 | 1.921 | 0.602 | 1.197 | 1.844 |
| reference_validation | 31 | 27 | 87.1% | 100.0% | 87.1% | 0.388 | 0.718 | 1.086 | 1.687 | 0.621 | 0.966 | 1.614 |
| august | 3 | 3 | 100.0% | 100.0% | 100.0% | 0.376 | 0.584 | 1.143 | 1.479 | 0.523 | 1.025 | 1.326 |

## Frozen extension atlas

| Partition | Extension | High reach / H2 | High reach / all fills | Close reach / H2 | Close reach / all fills | Median min H2→reach |
|---|---|---:|---:|---:|---:|---:|
| external | E05 | 97.6% | 87.0% | 87.8% | 78.3% | 0.000 |
| external | E10 | 92.7% | 82.6% | 73.2% | 65.2% | 5.000 |
| external | E15 | 82.9% | 73.9% | 68.3% | 60.9% | 10.000 |
| external | E20 | 78.0% | 69.6% | 65.9% | 58.7% | 15.000 |
| external | E25 | 70.7% | 63.0% | 53.7% | 47.8% | 25.000 |
| external | E30 | 58.5% | 52.2% | 48.8% | 43.5% | 35.000 |
| external | E40 | 48.8% | 43.5% | 31.7% | 28.3% | 60.000 |
| external | E50 | 34.1% | 30.4% | 17.1% | 15.2% | 45.000 |
| development | E05 | 94.3% | 69.4% | 84.9% | 62.5% | 0.000 |
| development | E10 | 90.6% | 66.7% | 84.9% | 62.5% | 5.000 |
| development | E15 | 88.7% | 65.3% | 81.1% | 59.7% | 10.000 |
| development | E20 | 84.9% | 62.5% | 79.2% | 58.3% | 10.000 |
| development | E25 | 84.9% | 62.5% | 75.5% | 55.6% | 10.000 |
| development | E30 | 83.0% | 61.1% | 67.9% | 50.0% | 25.000 |
| development | E40 | 73.6% | 54.2% | 60.4% | 44.4% | 50.000 |
| development | E50 | 58.5% | 43.1% | 52.8% | 38.9% | 80.000 |
| reference_validation | E05 | 100.0% | 87.1% | 100.0% | 87.1% | 0.000 |
| reference_validation | E10 | 100.0% | 87.1% | 100.0% | 87.1% | 0.000 |
| reference_validation | E15 | 100.0% | 87.1% | 100.0% | 87.1% | 5.000 |
| reference_validation | E20 | 100.0% | 87.1% | 100.0% | 87.1% | 10.000 |
| reference_validation | E25 | 100.0% | 87.1% | 85.2% | 74.2% | 10.000 |
| reference_validation | E30 | 92.6% | 80.6% | 70.4% | 61.3% | 25.000 |
| reference_validation | E40 | 74.1% | 64.5% | 66.7% | 58.1% | 32.500 |
| reference_validation | E50 | 66.7% | 58.1% | 51.9% | 45.2% | 32.500 |
| august | E05 | 100.0% | 100.0% | 100.0% | 100.0% | 0.000 |
| august | E10 | 100.0% | 100.0% | 100.0% | 100.0% | 0.000 |
| august | E15 | 100.0% | 100.0% | 66.7% | 66.7% | 5.000 |
| august | E20 | 66.7% | 66.7% | 66.7% | 66.7% | 2.500 |
| august | E25 | 66.7% | 66.7% | 66.7% | 66.7% | 12.500 |
| august | E30 | 66.7% | 66.7% | 66.7% | 66.7% | 115.000 |
| august | E40 | 66.7% | 66.7% | 66.7% | 66.7% | 115.000 |
| august | E50 | 66.7% | 66.7% | 66.7% | 66.7% | 127.500 |

No TP is selected in B27Y. This atlas exists to choose a breakout target later without pretending H2 itself is the exit.

Research only; live BBC unchanged.
