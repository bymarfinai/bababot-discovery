# B27AB — London -> New York Post-Breakout Dynamic Runner — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27Z/B27AA entry identities and fixed-E20 baseline economics reproduce before dynamic-runner results are interpreted.

## Fixed E20 vs dynamic structural runner

| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Runner WR | Runner PF | Runner exp | Runner total | Delta total | Acceptance | E20 reach |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F85 | august | 3 | 100.0% | inf | $+1.93 | $+5.78 | 66.7% | 9.86 | $+1.64 | $+4.92 | $-0.86 | 100.0% | 66.7% |
| BLIND_F85 | development | 72 | 63.9% | 0.98 | $-0.04 | $-2.66 | 45.8% | 1.32 | $+0.68 | $+49.03 | $+51.69 | 65.3% | 55.6% |
| BLIND_F85 | external | 46 | 76.1% | 3.40 | $+1.94 | $+89.12 | 63.0% | 2.24 | $+1.02 | $+46.94 | $-42.19 | 84.8% | 63.0% |
| BLIND_F85 | reference_validation | 31 | 67.7% | 1.08 | $+0.10 | $+3.21 | 41.9% | 0.77 | $-0.39 | $-12.22 | $-15.43 | 67.7% | 58.1% |
| EARLY_RECLAIM | august | 3 | 100.0% | inf | $+1.44 | $+4.31 | 66.7% | 5.68 | $+1.15 | $+3.46 | $-0.86 | 100.0% | 66.7% |
| EARLY_RECLAIM | development | 54 | 66.7% | 1.08 | $+0.14 | $+7.44 | 40.7% | 1.29 | $+0.61 | $+33.17 | $+25.72 | 72.2% | 59.3% |
| EARLY_RECLAIM | external | 43 | 76.7% | 2.89 | $+1.62 | $+69.65 | 60.5% | 2.13 | $+0.86 | $+36.84 | $-32.81 | 86.0% | 62.8% |
| EARLY_RECLAIM | reference_validation | 21 | 71.4% | 0.98 | $-0.03 | $-0.59 | 38.1% | 0.53 | $-0.92 | $-19.40 | $-18.82 | 71.4% | 57.1% |
| SAME_BAR_REJECTION | august | 1 | 100.0% | inf | $+2.65 | $+2.65 | 100.0% | inf | $+2.14 | $+2.14 | $-0.52 | 100.0% | 0.0% |
| SAME_BAR_REJECTION | development | 30 | 66.7% | 1.17 | $+0.31 | $+9.16 | 43.3% | 1.58 | $+1.17 | $+35.14 | $+25.97 | 70.0% | 56.7% |
| SAME_BAR_REJECTION | external | 27 | 74.1% | 2.18 | $+1.34 | $+36.23 | 59.3% | 1.70 | $+0.62 | $+16.76 | $-19.47 | 81.5% | 63.0% |
| SAME_BAR_REJECTION | reference_validation | 11 | 90.9% | 6.23 | $+1.49 | $+16.41 | 45.5% | 0.19 | $-1.10 | $-12.12 | $-28.53 | 90.9% | 63.6% |
| BLIND_F85 | POOLED_MAJOR | 149 | 68.5% | 1.40 | $+0.60 | $+89.68 | 50.3% | 1.34 | $+0.56 | $+83.75 | $-5.93 | 71.8% | 58.4% |
| EARLY_RECLAIM | POOLED_MAJOR | 118 | 71.2% | 1.47 | $+0.65 | $+76.51 | 47.5% | 1.27 | $+0.43 | $+50.61 | $-25.90 | 77.1% | 60.2% |
| SAME_BAR_REJECTION | POOLED_MAJOR | 68 | 73.5% | 1.70 | $+0.91 | $+61.80 | 50.0% | 1.40 | $+0.58 | $+39.77 | $-22.03 | 77.9% | 60.3% |

## Runner peak-capture diagnostics

| Rule | Partition | Structure exits | Time exits | Pre-break stops | Exit >= E20 / accepted | Median peak ext | Median exit ext | Median capture | Median giveback | Median hold min |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F85 | august | 3 | 0 | 0 | 33.3% | 0.58R | 0.03R | 19.2% | 0.77R | 170.00 |
| BLIND_F85 | development | 44 | 6 | 22 | 42.6% | 0.80R | 0.05R | 7.7% | 0.75R | 107.50 |
| BLIND_F85 | external | 37 | 8 | 1 | 12.8% | 0.42R | -0.01R | 0.0% | 0.36R | 120.00 |
| BLIND_F85 | reference_validation | 20 | 2 | 9 | 28.6% | 0.73R | -0.05R | 0.0% | 0.82R | 70.00 |
| EARLY_RECLAIM | august | 3 | 0 | 0 | 33.3% | 0.58R | 0.03R | 19.2% | 0.77R | 140.00 |
| EARLY_RECLAIM | development | 37 | 5 | 12 | 35.9% | 0.66R | 0.02R | 1.5% | 0.67R | 110.00 |
| EARLY_RECLAIM | external | 35 | 7 | 1 | 13.5% | 0.37R | -0.00R | 0.0% | 0.36R | 110.00 |
| EARLY_RECLAIM | reference_validation | 14 | 2 | 5 | 13.3% | 0.55R | -0.08R | 0.0% | 0.50R | 65.00 |
| SAME_BAR_REJECTION | august | 1 | 0 | 0 | 0.0% | 0.17R | 0.03R | 19.2% | 0.14R | 165.00 |
| SAME_BAR_REJECTION | development | 19 | 4 | 7 | 47.6% | 0.80R | 0.20R | 16.5% | 0.53R | 110.00 |
| SAME_BAR_REJECTION | external | 22 | 4 | 1 | 9.1% | 0.42R | -0.00R | 0.0% | 0.37R | 115.00 |
| SAME_BAR_REJECTION | reference_validation | 10 | 0 | 1 | 0.0% | 0.53R | -0.15R | 0.0% | 0.66R | 60.00 |
| BLIND_F85 | POOLED_MAJOR | 101 | 16 | 32 | 29.0% | 0.53R | 0.02R | 1.7% | 0.46R | 110.00 |
| EARLY_RECLAIM | POOLED_MAJOR | 86 | 14 | 18 | 23.1% | 0.50R | -0.00R | 0.0% | 0.45R | 105.00 |
| SAME_BAR_REJECTION | POOLED_MAJOR | 51 | 8 | 9 | 22.6% | 0.50R | -0.00R | 0.0% | 0.46R | 110.00 |

## Frozen primary gate

- development: fixed exp $+0.14 -> runner exp $+0.61; runner PF 1.29 -> PASS
- external: fixed exp $+1.62 -> runner exp $+0.86; runner PF 2.13 -> FAIL
- reference_validation: fixed exp $-0.03 -> runner exp $-0.92; runner PF 0.53 -> FAIL

**Overall: B27AB_PRIMARY_RUNNER_NOT_SUPPORTED.**

E20 is diagnostic only in the runner. No pivot-width, ATR, percentage-trail, or target sweep is performed.

Research only; live BBC unchanged.
