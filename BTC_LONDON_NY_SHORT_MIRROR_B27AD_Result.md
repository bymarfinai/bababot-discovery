# B27AD — BTC London -> New York SHORT Exact Mirror — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27Q SHORT K1 OPP0 identities, low-touch chronology, pre-H2 F15 fills, mirrored rejection entries, fixed E20_DOWN economics, and E20 profit-ceiling runner were evaluated without parameter tuning.

## Structural pre-H2 F15 mirror

| Partition | K1 opps | Clean windows | F15 fills | H2 hits | H2 hit rate | Median min fill->H2 |
|---|---:|---:|---:|---:|---:|---:|
| external | 94 | 68 | 50 | 37 | 74.0% | 15.00 |
| development | 192 | 135 | 79 | 59 | 74.7% | 15.00 |
| reference_validation | 92 | 59 | 34 | 24 | 70.6% | 17.50 |
| august | 2 | 2 | 1 | 1 | 100.0% | 5.00 |

**Structural screen: PASS.** Exact frozen requirement: >=30 F15 fills and >=70% H2 hit among fills in each major partition.

## Fixed E20_DOWN vs E20-lock short runner

| Rule | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed total | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid total | Delta total | E20 reach | Winner preserved |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F15 | external | 50 | 58.0% | 1.54 | $+0.82 | $+40.89 | 54.0% | 1.59 | $+0.91 | $+45.39 | $+4.50 | 56.0% | 93.1% |
| BLIND_F15 | development | 79 | 59.5% | 0.83 | $-0.29 | $-22.55 | 54.4% | 0.84 | $-0.27 | $-21.48 | $+1.06 | 59.5% | 91.5% |
| BLIND_F15 | reference_validation | 34 | 52.9% | 0.55 | $-0.88 | $-30.00 | 50.0% | 0.43 | $-1.15 | $-38.96 | $-8.96 | 50.0% | 94.4% |
| BLIND_F15 | august | 1 | 0.0% | 0.00 | $-2.42 | $-2.42 | 0.0% | 0.00 | $-2.42 | $-2.42 | $+0.00 | 0.0% | - |
| BLIND_F15 | POOLED_MAJOR | 163 | 57.7% | 0.96 | $-0.07 | $-11.67 | 53.4% | 0.95 | $-0.09 | $-15.06 | $-3.39 | 56.4% | 92.6% |
| EARLY_REJECT | external | 42 | 64.3% | 1.41 | $+0.59 | $+24.65 | 59.5% | 1.50 | $+0.74 | $+31.12 | $+6.47 | 61.9% | 92.6% |
| EARLY_REJECT | development | 56 | 58.9% | 0.87 | $-0.20 | $-11.22 | 50.0% | 0.95 | $-0.08 | $-4.39 | $+6.82 | 58.9% | 84.8% |
| EARLY_REJECT | reference_validation | 22 | 50.0% | 0.52 | $-0.96 | $-21.12 | 45.5% | 0.36 | $-1.34 | $-29.54 | $-8.42 | 50.0% | 90.9% |
| EARLY_REJECT | august | 1 | 0.0% | 0.00 | $-2.73 | $-2.73 | 0.0% | 0.00 | $-2.73 | $-2.73 | $+0.00 | 0.0% | - |
| EARLY_REJECT | POOLED_MAJOR | 120 | 59.2% | 0.96 | $-0.06 | $-7.68 | 52.5% | 0.99 | $-0.02 | $-2.81 | $+4.88 | 58.3% | 88.7% |
| SAME_BAR_REJECTION | external | 25 | 64.0% | 1.11 | $+0.16 | $+3.93 | 60.0% | 1.26 | $+0.38 | $+9.55 | $+5.62 | 60.0% | 93.8% |
| SAME_BAR_REJECTION | development | 25 | 60.0% | 0.77 | $-0.33 | $-8.26 | 52.0% | 0.59 | $-0.60 | $-14.96 | $-6.70 | 60.0% | 86.7% |
| SAME_BAR_REJECTION | reference_validation | 12 | 41.7% | 0.21 | $-1.93 | $-23.15 | 41.7% | 0.17 | $-2.02 | $-24.28 | $-1.13 | 41.7% | 100.0% |
| SAME_BAR_REJECTION | august | 1 | 0.0% | 0.00 | $-2.73 | $-2.73 | 0.0% | 0.00 | $-2.73 | $-2.73 | $+0.00 | 0.0% | - |
| SAME_BAR_REJECTION | POOLED_MAJOR | 62 | 58.1% | 0.73 | $-0.44 | $-27.49 | 53.2% | 0.71 | $-0.48 | $-29.70 | $-2.21 | 56.5% | 91.7% |

## Runner downside-extension capture

| Rule | Partition | Median trough ext below L | Median realized exit ext | Median capture | Median giveback |
|---|---|---:|---:|---:|---:|
| BLIND_F15 | external | 0.58R | 0.17R | 28.3% | 0.41R |
| BLIND_F15 | development | 0.64R | 0.13R | 16.8% | 0.59R |
| BLIND_F15 | reference_validation | 0.83R | 0.18R | 21.8% | 0.66R |
| BLIND_F15 | august | -R | -R | - | -R |
| BLIND_F15 | POOLED_MAJOR | 0.64R | 0.16R | 21.3% | 0.53R |
| EARLY_REJECT | external | 0.58R | 0.17R | 28.3% | 0.41R |
| EARLY_REJECT | development | 0.64R | 0.15R | 15.0% | 0.54R |
| EARLY_REJECT | reference_validation | 0.74R | 0.17R | 13.1% | 0.96R |
| EARLY_REJECT | august | -R | -R | - | -R |
| EARLY_REJECT | POOLED_MAJOR | 0.63R | 0.16R | 16.3% | 0.49R |
| SAME_BAR_REJECTION | external | 0.97R | 0.15R | 13.6% | 0.52R |
| SAME_BAR_REJECTION | development | 0.95R | 0.19R | 13.2% | 0.74R |
| SAME_BAR_REJECTION | reference_validation | 1.34R | 0.18R | 15.0% | 1.14R |
| SAME_BAR_REJECTION | august | -R | -R | - | -R |
| SAME_BAR_REJECTION | POOLED_MAJOR | 0.97R | 0.18R | 13.6% | 0.68R |

**Primary EARLY_REJECT economics: NOT SUPPORTED under the frozen confirmatory gate.**

No threshold, entry fraction, stop fraction, target extension, pivot width, or timeframe was tuned after seeing SHORT results.

Research only; live BBC unchanged.
