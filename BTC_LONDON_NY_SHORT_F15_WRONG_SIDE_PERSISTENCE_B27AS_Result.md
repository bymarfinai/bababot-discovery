# B27AS — BTC London->NY SHORT F15 Wrong-Side Persistence Exit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27AK/B27AN F15 cohort and frozen E20/D50 baseline reproduced before persistence results were interpreted.

Frozen pooled-major B27AN E20/D50 baseline: **$-11.666**.

| Rule | Partition | N | Persist exits | Exit rate | Persist H2-fail | Persist baseline-loser | H2 before exit | TP rate | WR | PF | Exp/trade $ | Total $ | Delta vs base $ | Med persist PnL $ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| P1 | external | 50 | 35 | 70.0% | 37.1% | 51.4% | 26.0% | 22.0% | 24.0% | 0.746 | -0.247 | -12.370 | -53.255 | -0.789 |
| P1 | development | 79 | 63 | 79.7% | 31.7% | 44.4% | 16.5% | 15.2% | 15.2% | 0.343 | -0.623 | -49.181 | -26.632 | -0.846 |
| P1 | reference_validation | 34 | 31 | 91.2% | 32.3% | 48.4% | 5.9% | 5.9% | 5.9% | 0.052 | -0.986 | -33.518 | -3.515 | -0.744 |
| P1 | august | 1 | 0 | 0.0% | - | - | 100.0% | 0.0% | 0.0% | 0.000 | -2.420 | -2.420 | 0.000 | - |
| P1 | POOLED_MAJOR | 163 | 129 | 79.1% | 33.3% | 47.3% | 17.2% | 15.3% | 16.0% | 0.402 | -0.583 | -95.068 | -83.403 | -0.807 |
| P2 | external | 50 | 28 | 56.0% | 46.4% | 60.7% | 40.0% | 34.0% | 36.0% | 1.108 | 0.130 | 6.515 | -34.370 | -1.260 |
| P2 | development | 79 | 50 | 63.3% | 40.0% | 56.0% | 27.8% | 31.6% | 31.6% | 0.500 | -0.557 | -44.018 | -21.469 | -1.364 |
| P2 | reference_validation | 34 | 24 | 70.6% | 41.7% | 54.2% | 26.5% | 17.6% | 20.6% | 0.231 | -0.969 | -32.951 | -2.948 | -1.159 |
| P2 | august | 1 | 0 | 0.0% | - | - | 100.0% | 0.0% | 0.0% | 0.000 | -2.420 | -2.420 | 0.000 | - |
| P2 | POOLED_MAJOR | 163 | 102 | 62.6% | 42.2% | 56.9% | 31.3% | 29.4% | 30.7% | 0.631 | -0.432 | -70.453 | -58.788 | -1.283 |
| P3 | external | 50 | 26 | 52.0% | 50.0% | 65.4% | 44.0% | 38.0% | 40.0% | 1.224 | 0.301 | 15.029 | -25.856 | -1.432 |
| P3 | development | 79 | 42 | 53.2% | 45.2% | 61.9% | 32.9% | 39.2% | 39.2% | 0.690 | -0.370 | -29.243 | -6.694 | -1.472 |
| P3 | reference_validation | 34 | 19 | 55.9% | 52.6% | 68.4% | 35.3% | 32.4% | 35.3% | 0.483 | -0.692 | -23.542 | 6.460 | -1.425 |
| P3 | august | 1 | 0 | 0.0% | - | - | 100.0% | 0.0% | 0.0% | 0.000 | -2.420 | -2.420 | 0.000 | - |
| P3 | POOLED_MAJOR | 163 | 87 | 53.4% | 48.3% | 64.4% | 36.8% | 37.4% | 38.7% | 0.817 | -0.232 | -37.756 | -26.090 | -1.431 |

## Frozen readout

**Mechanism-supported rules: NONE.**
**Promotion-pass rules: NONE.**

No P4/P5, price buffer, regime filter, alternate entry, alternate stop, alternate TP, candle threshold, or runner was introduced.

Research only; live BBC unchanged.
