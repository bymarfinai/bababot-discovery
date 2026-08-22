# B27W — London -> New York Pre-Second-Touch Entry — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27Q K1 OPP0 signals were reused unchanged. Entry is only allowed after a causal leave from Touch #1 and strictly before the first later return/arrival to High.

## Window diagnostic

| Partition | K1 setups | Clean windows | H2 probability | H2 | Opp break first | No H2 |
|---|---:|---:|---:|---:|---:|---:|
| external | 101 | 63 | 85.7% | 54 | 2 | 7 |
| development | 164 | 119 | 69.7% | 83 | 27 | 9 |
| reference_validation | 82 | 53 | 77.4% | 41 | 9 | 3 |
| august | 4 | 3 | 100.0% | 3 | 0 | 0 |

## Pre-H2 limit-entry grid

| Partition | Entry | Fills | Fill rate | H2 hit rate after fill | Median min to H2 | Reward to H | Median min price f | P10 min price f | Median adverse excursion |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | F95 | 34 | 33.7% | 94.1% | 10.00 | 5.0% | 0.82 | 0.63 | 12.6% |
| external | F90 | 48 | 47.5% | 91.7% | 20.00 | 10.0% | 0.77 | 0.51 | 12.8% |
| external | F85 | 46 | 45.5% | 89.1% | 25.00 | 15.0% | 0.72 | 0.48 | 12.7% |
| external | F80 | 38 | 37.6% | 84.2% | 32.50 | 20.0% | 0.68 | 0.45 | 12.2% |
| external | F75 | 33 | 32.7% | 75.8% | 40.00 | 25.0% | 0.55 | 0.19 | 19.8% |
| development | F95 | 37 | 22.6% | 86.5% | 7.50 | 5.0% | 0.79 | 0.20 | 16.2% |
| development | F90 | 56 | 34.1% | 78.6% | 10.00 | 10.0% | 0.72 | 0.13 | 17.9% |
| development | F85 | 72 | 43.9% | 73.6% | 15.00 | 15.0% | 0.63 | 0.06 | 21.7% |
| development | F80 | 73 | 44.5% | 68.5% | 25.00 | 20.0% | 0.55 | 0.04 | 25.3% |
| development | F75 | 70 | 42.7% | 64.3% | 25.00 | 25.0% | 0.39 | 0.01 | 35.7% |
| reference_validation | F95 | 18 | 22.0% | 100.0% | 5.00 | 5.0% | 0.77 | 0.46 | 18.5% |
| reference_validation | F90 | 28 | 34.1% | 89.3% | 5.00 | 10.0% | 0.65 | 0.24 | 24.9% |
| reference_validation | F85 | 31 | 37.8% | 87.1% | 15.00 | 15.0% | 0.54 | 0.14 | 31.2% |
| reference_validation | F80 | 32 | 39.0% | 84.4% | 25.00 | 20.0% | 0.49 | 0.09 | 30.7% |
| reference_validation | F75 | 31 | 37.8% | 80.6% | 35.00 | 25.0% | 0.46 | 0.08 | 28.7% |
| august | F95 | 2 | 50.0% | 100.0% | 5.00 | 5.0% | 0.79 | 0.75 | 16.2% |
| august | F90 | 3 | 75.0% | 100.0% | 20.00 | 10.0% | 0.66 | 0.62 | 23.9% |
| august | F85 | 3 | 75.0% | 100.0% | 15.00 | 15.0% | 0.66 | 0.62 | 18.9% |
| august | F80 | 3 | 75.0% | 100.0% | 10.00 | 20.0% | 0.66 | 0.62 | 13.9% |
| august | F75 | 2 | 50.0% | 100.0% | 55.00 | 25.0% | 0.43 | 0.29 | 31.6% |

## Screen

**PASS:** F85

This experiment isolates entry availability/quality before the second High arrival. It does not optimize stops and is not a live-promotion test.

Research only; live BBC unchanged.
