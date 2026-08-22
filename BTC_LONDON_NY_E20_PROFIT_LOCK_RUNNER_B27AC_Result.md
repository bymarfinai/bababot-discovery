# B27AC — London -> New York E20 Profit-Lock Runner — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27Z/B27AA entry identities and fixed-E20 baseline economics reproduce before the hybrid result is interpreted.

## Fixed E20 vs E20-lock structural runner

| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total | Delta total | E20 reach | Winner preserved |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F85 | august | 3 | 100.0% | inf | $+1.93 | $+5.78 | 100.0% | inf | $+1.78 | $+5.33 | $-0.44 | 66.7% | 100.0% |
| BLIND_F85 | development | 72 | 63.9% | 0.98 | $-0.04 | $-2.66 | 55.6% | 1.18 | $+0.37 | $+26.53 | $+29.19 | 61.1% | 87.0% |
| BLIND_F85 | external | 46 | 76.1% | 3.40 | $+1.94 | $+89.12 | 71.7% | 2.82 | $+1.49 | $+68.55 | $-20.58 | 69.6% | 94.3% |
| BLIND_F85 | reference_validation | 31 | 67.7% | 1.08 | $+0.10 | $+3.21 | 67.7% | 1.34 | $+0.43 | $+13.34 | $+10.13 | 67.7% | 100.0% |
| EARLY_RECLAIM | august | 3 | 100.0% | inf | $+1.44 | $+4.31 | 100.0% | inf | $+1.29 | $+3.87 | $-0.44 | 66.7% | 100.0% |
| EARLY_RECLAIM | development | 54 | 66.7% | 1.08 | $+0.14 | $+7.44 | 59.3% | 1.42 | $+0.78 | $+42.05 | $+34.60 | 66.7% | 88.9% |
| EARLY_RECLAIM | external | 43 | 76.7% | 2.89 | $+1.62 | $+69.65 | 72.1% | 2.38 | $+1.20 | $+51.73 | $-17.92 | 69.8% | 93.9% |
| EARLY_RECLAIM | reference_validation | 21 | 71.4% | 0.98 | $-0.03 | $-0.59 | 71.4% | 1.35 | $+0.45 | $+9.51 | $+10.10 | 71.4% | 100.0% |
| SAME_BAR_REJECTION | august | 1 | 100.0% | inf | $+2.65 | $+2.65 | 100.0% | inf | $+2.65 | $+2.65 | $+0.00 | 0.0% | 100.0% |
| SAME_BAR_REJECTION | development | 30 | 66.7% | 1.17 | $+0.31 | $+9.16 | 63.3% | 2.01 | $+1.83 | $+54.92 | $+45.76 | 66.7% | 95.0% |
| SAME_BAR_REJECTION | external | 27 | 74.1% | 2.18 | $+1.34 | $+36.23 | 66.7% | 1.62 | $+0.72 | $+19.36 | $-16.87 | 66.7% | 90.0% |
| SAME_BAR_REJECTION | reference_validation | 11 | 90.9% | 6.23 | $+1.49 | $+16.41 | 90.9% | 6.42 | $+1.55 | $+17.02 | $+0.62 | 90.9% | 100.0% |
| BLIND_F85 | POOLED_MAJOR | 149 | 68.5% | 1.40 | $+0.60 | $+89.68 | 63.1% | 1.48 | $+0.73 | $+108.42 | $+18.74 | 65.1% | 92.2% |
| EARLY_RECLAIM | POOLED_MAJOR | 118 | 71.2% | 1.47 | $+0.65 | $+76.51 | 66.1% | 1.62 | $+0.88 | $+103.29 | $+26.78 | 68.6% | 92.9% |
| SAME_BAR_REJECTION | POOLED_MAJOR | 68 | 73.5% | 1.70 | $+0.91 | $+61.80 | 69.1% | 2.03 | $+1.34 | $+91.31 | $+29.51 | 70.6% | 94.0% |

## Profit-lock diagnostics

| Rule | Partition | Pre-E20 stops | E20-floor exits | Structural-floor exits | Open/gap exits | Time exits | Exit >= E20 / reached | Touch-bar close < E20 | Median peak ext | Median exit ext | Median capture | Median giveback | Median ratchets |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F85 | august | 0 | 2 | 0 | 1 | 1 | 50.0% | 50.0% | 1.14R | 0.15R | 14.9% | 0.99R | 0.00 |
| BLIND_F85 | development | 23 | 39 | 5 | 29 | 5 | 34.1% | 65.9% | 0.96R | 0.17R | 18.0% | 0.71R | 0.00 |
| BLIND_F85 | external | 2 | 29 | 2 | 21 | 13 | 31.2% | 68.8% | 0.47R | 0.15R | 34.8% | 0.30R | 0.00 |
| BLIND_F85 | reference_validation | 9 | 19 | 1 | 3 | 2 | 85.7% | 14.3% | 0.73R | 0.20R | 35.7% | 0.37R | 0.00 |
| EARLY_RECLAIM | august | 0 | 2 | 0 | 1 | 1 | 50.0% | 50.0% | 1.14R | 0.15R | 14.9% | 0.99R | 0.00 |
| EARLY_RECLAIM | development | 13 | 31 | 5 | 23 | 5 | 36.1% | 63.9% | 0.76R | 0.18R | 22.4% | 0.53R | 0.00 |
| EARLY_RECLAIM | external | 2 | 27 | 2 | 19 | 12 | 33.3% | 66.7% | 0.46R | 0.15R | 36.7% | 0.30R | 0.00 |
| EARLY_RECLAIM | reference_validation | 5 | 13 | 1 | 4 | 2 | 73.3% | 26.7% | 0.55R | 0.20R | 49.3% | 0.29R | 0.00 |
| SAME_BAR_REJECTION | august | 0 | 0 | 0 | 0 | 1 | - | - | -R | -R | - | -R | - |
| SAME_BAR_REJECTION | development | 7 | 15 | 5 | 11 | 3 | 45.0% | 55.0% | 0.92R | 0.19R | 27.6% | 0.49R | 0.00 |
| SAME_BAR_REJECTION | external | 2 | 18 | 0 | 13 | 7 | 27.8% | 72.2% | 0.47R | 0.15R | 31.7% | 0.31R | 0.00 |
| SAME_BAR_REJECTION | reference_validation | 1 | 9 | 1 | 2 | 0 | 80.0% | 20.0% | 0.53R | 0.20R | 45.2% | 0.33R | 0.00 |
| BLIND_F85 | POOLED_MAJOR | 34 | 87 | 8 | 53 | 20 | 44.3% | 55.7% | 0.61R | 0.18R | 29.4% | 0.42R | 0.00 |
| EARLY_RECLAIM | POOLED_MAJOR | 20 | 71 | 8 | 46 | 19 | 42.0% | 58.0% | 0.53R | 0.18R | 34.0% | 0.34R | 0.00 |
| SAME_BAR_REJECTION | POOLED_MAJOR | 10 | 42 | 6 | 26 | 10 | 45.8% | 54.2% | 0.52R | 0.18R | 31.9% | 0.37R | 0.00 |

## Frozen primary gate

- development: fixed exp $+0.14 -> hybrid exp $+0.78; hybrid PF 1.42 -> PASS
- external: fixed exp $+1.62 -> hybrid exp $+1.20; hybrid PF 2.38 -> FAIL
- reference_validation: fixed exp $-0.03 -> hybrid exp $+0.45; hybrid PF 1.35 -> PASS

**Overall: B27AC_PRIMARY_HYBRID_NOT_SUPPORTED.**

E20 is frozen. The E20 floor is effective only from the bar after first E20 reach; no retroactive intrabar stop is assumed.

Research only; live BBC unchanged.
