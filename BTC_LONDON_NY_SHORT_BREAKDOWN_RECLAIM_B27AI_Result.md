# B27AI — BTC London -> New York SHORT Breakdown-Reclaim Exit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Frozen B27AD trade identities and fixed/hybrid economics reproduce before B27AI is interpreted. No 4H regime blocks a trade.

## All-regime SHORT-specific exit

| Rule | Partition | N | WR | PF | Exp | Total | Breakdown accepted | E20 diag | F65 invalid | L-reclaim exits | Time exits | B27AD fixed | B27AD hybrid |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F15 | external | 50 | 56.0% | 2.16 | $+1.46 | $+73.09 | 64.0% | 40.0% | 6 | 23 | 21 | $+40.89 | $+45.39 |
| BLIND_F15 | development | 79 | 41.8% | 0.52 | $-0.86 | $-67.61 | 60.8% | 48.1% | 23 | 40 | 16 | $-22.55 | $-21.48 |
| BLIND_F15 | reference_validation | 34 | 47.1% | 0.52 | $-0.98 | $-33.45 | 58.8% | 44.1% | 11 | 16 | 7 | $-30.00 | $-38.96 |
| BLIND_F15 | august | 1 | 0.0% | 0.00 | $-2.42 | $-2.42 | 0.0% | 0.0% | 1 | 0 | 0 | $-2.42 | $-2.42 |
| BLIND_F15 | POOLED_MAJOR | 163 | 47.2% | 0.90 | $-0.17 | $-27.97 | 61.3% | 44.8% | 40 | 79 | 44 | $-11.67 | $-15.06 |
| EARLY_REJECT | external | 42 | 50.0% | 2.35 | $+1.60 | $+67.21 | 71.4% | 42.9% | 4 | 21 | 17 | $+24.65 | $+31.12 |
| EARLY_REJECT | development | 56 | 41.1% | 0.64 | $-0.58 | $-32.49 | 62.5% | 46.4% | 13 | 28 | 15 | $-11.22 | $-4.39 |
| EARLY_REJECT | reference_validation | 22 | 45.5% | 0.68 | $-0.68 | $-14.91 | 59.1% | 45.5% | 6 | 9 | 7 | $-21.12 | $-29.54 |
| EARLY_REJECT | august | 1 | 0.0% | 0.00 | $-2.73 | $-2.73 | 0.0% | 0.0% | 1 | 0 | 0 | $-2.73 | $-2.73 |
| EARLY_REJECT | POOLED_MAJOR | 120 | 45.0% | 1.11 | $+0.17 | $+19.81 | 65.0% | 45.0% | 23 | 58 | 39 | $-7.68 | $-2.81 |
| SAME_BAR_REJECTION | external | 25 | 48.0% | 2.66 | $+2.09 | $+52.35 | 72.0% | 40.0% | 3 | 13 | 9 | $+3.93 | $+9.55 |
| SAME_BAR_REJECTION | development | 25 | 40.0% | 0.72 | $-0.38 | $-9.62 | 68.0% | 48.0% | 6 | 13 | 6 | $-8.26 | $-14.96 |
| SAME_BAR_REJECTION | reference_validation | 12 | 41.7% | 0.43 | $-1.26 | $-15.15 | 58.3% | 33.3% | 4 | 6 | 2 | $-23.15 | $-24.28 |
| SAME_BAR_REJECTION | august | 1 | 0.0% | 0.00 | $-2.73 | $-2.73 | 0.0% | 0.0% | 1 | 0 | 0 | $-2.73 | $-2.73 |
| SAME_BAR_REJECTION | POOLED_MAJOR | 62 | 43.5% | 1.30 | $+0.44 | $+27.58 | 67.7% | 41.9% | 13 | 32 | 17 | $-27.49 | $-29.70 |

## Accepted-breakdown path capture

| Rule | Partition | Median trough below L | Median realized exit vs L | Median capture | Median giveback |
|---|---|---:|---:|---:|---:|
| BLIND_F15 | external | 0.32R | -0.02R | 0.0% | 0.28R |
| BLIND_F15 | development | 0.36R | -0.03R | 0.0% | 0.37R |
| BLIND_F15 | reference_validation | 0.27R | -0.03R | 0.0% | 0.26R |
| BLIND_F15 | august | -R | -R | - | -R |
| BLIND_F15 | POOLED_MAJOR | 0.33R | -0.03R | 0.0% | 0.32R |
| EARLY_REJECT | external | 0.32R | -0.02R | 0.0% | 0.28R |
| EARLY_REJECT | development | 0.30R | -0.03R | 0.0% | 0.28R |
| EARLY_REJECT | reference_validation | 0.26R | -0.03R | 0.0% | 0.22R |
| EARLY_REJECT | august | -R | -R | - | -R |
| EARLY_REJECT | POOLED_MAJOR | 0.30R | -0.03R | 0.0% | 0.27R |
| SAME_BAR_REJECTION | external | 0.30R | -0.03R | 0.0% | 0.33R |
| SAME_BAR_REJECTION | development | 0.30R | -0.04R | 0.0% | 0.28R |
| SAME_BAR_REJECTION | reference_validation | 0.20R | -0.03R | 0.0% | 0.22R |
| SAME_BAR_REJECTION | august | -R | -R | - | -R |
| SAME_BAR_REJECTION | POOLED_MAJOR | 0.28R | -0.03R | 0.0% | 0.30R |

**Overall: B27AI_NOT_SUPPORTED.**

B27AI does not tune F15/F65, add a regime gate, or use E20 as an exit. Reference-validation primary N remains only 22 trades and is a limitation.

Research only; live BBC unchanged.
