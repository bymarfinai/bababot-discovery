# B27R — London -> New York LONG Entry Optimization — Result

5m source rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27Q signal identities were reused unchanged; B27R changed entry mechanics only.

Primary cohort: London->New York LONG, K1 High visit, OPP0. Secondary: same cohort at K2. TP/SL remain frozen previous-session High/Low.

## Primary K1 entry grid

| Partition | Method | Setups | Fills | Fill rate | W | L | WR | TP rate | PF | Net exp | Total net | Median RR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | NEXT_OPEN | 101 | 101 | 100.0% | 52 | 49 | 51.5% | 91.1% | 0.68 | $-0.17 | $-17.25 | 0.06 |
| external | F50 | 101 | 17 | 16.8% | 11 | 6 | 64.7% | 47.1% | 1.96 | $1.09 | $18.51 | 1.00 |
| external | F55 | 101 | 19 | 18.8% | 14 | 5 | 73.7% | 52.6% | 2.41 | $1.39 | $26.46 | 0.82 |
| external | F60 | 101 | 21 | 20.8% | 16 | 5 | 76.2% | 57.1% | 1.94 | $0.95 | $19.91 | 0.67 |
| external | F65 | 101 | 24 | 23.8% | 17 | 7 | 70.8% | 62.5% | 2.01 | $1.06 | $25.38 | 0.54 |
| external | F70 | 101 | 31 | 30.7% | 24 | 7 | 77.4% | 71.0% | 2.31 | $1.25 | $38.76 | 0.43 |
| external | F75 | 101 | 40 | 39.6% | 32 | 8 | 80.0% | 75.0% | 2.06 | $0.91 | $36.26 | 0.33 |
| external | F80 | 101 | 45 | 44.6% | 38 | 7 | 84.4% | 82.2% | 2.10 | $0.75 | $33.63 | 0.25 |
| external | SIG_MID | 101 | 59 | 58.4% | 39 | 20 | 66.1% | 91.5% | 0.72 | $-0.18 | $-10.41 | 0.06 |
| external | SIG_LOW | 101 | 58 | 57.4% | 48 | 10 | 82.8% | 82.8% | 1.48 | $0.35 | $20.01 | 0.16 |
| development | NEXT_OPEN | 164 | 164 | 100.0% | 91 | 73 | 55.5% | 83.5% | 0.38 | $-0.72 | $-118.72 | 0.09 |
| development | F50 | 164 | 62 | 37.8% | 21 | 41 | 33.9% | 32.3% | 0.64 | $-0.87 | $-53.98 | 1.00 |
| development | F55 | 164 | 68 | 41.5% | 27 | 41 | 39.7% | 38.2% | 0.64 | $-0.89 | $-60.81 | 0.82 |
| development | F60 | 164 | 75 | 45.7% | 35 | 40 | 46.7% | 45.3% | 0.64 | $-0.88 | $-66.37 | 0.67 |
| development | F65 | 164 | 82 | 50.0% | 44 | 38 | 53.7% | 51.2% | 0.66 | $-0.81 | $-66.66 | 0.54 |
| development | F70 | 164 | 86 | 52.4% | 49 | 37 | 57.0% | 55.8% | 0.55 | $-1.10 | $-94.55 | 0.43 |
| development | F75 | 164 | 99 | 60.4% | 62 | 37 | 62.6% | 61.6% | 0.50 | $-1.15 | $-113.66 | 0.33 |
| development | F80 | 164 | 110 | 67.1% | 75 | 35 | 68.2% | 68.2% | 0.48 | $-1.07 | $-117.42 | 0.25 |
| development | SIG_MID | 164 | 107 | 65.2% | 66 | 41 | 61.7% | 79.4% | 0.29 | $-0.99 | $-105.40 | 0.09 |
| development | SIG_LOW | 164 | 106 | 64.6% | 66 | 40 | 62.3% | 62.3% | 0.46 | $-1.22 | $-129.31 | 0.26 |
| reference_validation | NEXT_OPEN | 82 | 82 | 100.0% | 40 | 42 | 48.8% | 85.4% | 0.50 | $-0.32 | $-26.00 | 0.09 |
| reference_validation | F50 | 82 | 28 | 34.1% | 17 | 11 | 60.7% | 60.7% | 1.74 | $0.68 | $18.98 | 1.00 |
| reference_validation | F55 | 82 | 32 | 39.0% | 22 | 10 | 68.8% | 65.6% | 1.86 | $0.72 | $22.91 | 0.82 |
| reference_validation | F60 | 82 | 35 | 42.7% | 24 | 11 | 68.6% | 68.6% | 1.65 | $0.54 | $19.04 | 0.67 |
| reference_validation | F65 | 82 | 37 | 45.1% | 27 | 10 | 73.0% | 73.0% | 1.58 | $0.45 | $16.60 | 0.54 |
| reference_validation | F70 | 82 | 37 | 45.1% | 28 | 9 | 75.7% | 75.7% | 1.29 | $0.23 | $8.50 | 0.43 |
| reference_validation | F75 | 82 | 39 | 47.6% | 31 | 8 | 79.5% | 79.5% | 1.30 | $0.22 | $8.60 | 0.33 |
| reference_validation | F80 | 82 | 41 | 50.0% | 34 | 7 | 82.9% | 82.9% | 1.06 | $0.04 | $1.70 | 0.25 |
| reference_validation | SIG_MID | 82 | 37 | 45.1% | 27 | 10 | 73.0% | 97.3% | 2.23 | $0.17 | $6.34 | 0.10 |
| reference_validation | SIG_LOW | 82 | 49 | 59.8% | 35 | 14 | 71.4% | 75.5% | 1.20 | $0.15 | $7.42 | 0.30 |
| august | NEXT_OPEN | 4 | 4 | 100.0% | 2 | 2 | 50.0% | 100.0% | 4.10 | $0.29 | $1.15 | 0.06 |
| august | F50 | 4 | 1 | 25.0% | 1 | 0 | 100.0% | 100.0% | inf | $1.98 | $1.98 | 1.00 |
| august | F55 | 4 | 1 | 25.0% | 1 | 0 | 100.0% | 100.0% | inf | $1.74 | $1.74 | 0.82 |
| august | F60 | 4 | 1 | 25.0% | 1 | 0 | 100.0% | 100.0% | inf | $1.50 | $1.50 | 0.67 |
| august | F65 | 4 | 2 | 50.0% | 2 | 0 | 100.0% | 100.0% | inf | $1.12 | $2.23 | 0.54 |
| august | F70 | 4 | 2 | 50.0% | 2 | 0 | 100.0% | 100.0% | inf | $0.90 | $1.80 | 0.43 |
| august | F75 | 4 | 2 | 50.0% | 2 | 0 | 100.0% | 100.0% | inf | $0.68 | $1.36 | 0.33 |
| august | F80 | 4 | 3 | 75.0% | 3 | 0 | 100.0% | 100.0% | inf | $1.43 | $4.30 | 0.25 |
| august | SIG_MID | 4 | 3 | 75.0% | 3 | 0 | 100.0% | 100.0% | inf | $0.59 | $1.78 | 0.12 |
| august | SIG_LOW | 4 | 2 | 50.0% | 2 | 0 | 100.0% | 100.0% | inf | $0.60 | $1.20 | 0.31 |

## Development-only selection

**No primary method satisfied the predeclared external + development eligibility gate.**

## Secondary K2 diagnostic

| Partition | Method | Setups | Fills | WR | PF | Net exp | Total net |
|---|---|---:|---:|---:|---:|---:|---:|
| external | NEXT_OPEN | 27 | 26 | 61.5% | 2.02 | $0.21 | $5.42 |
| external | F50 | 27 | 1 | 100.0% | inf | $1.63 | $1.63 |
| external | F55 | 27 | 1 | 100.0% | inf | $1.43 | $1.43 |
| external | F60 | 27 | 1 | 100.0% | inf | $1.22 | $1.22 |
| external | F65 | 27 | 3 | 100.0% | inf | $2.37 | $7.12 |
| external | F70 | 27 | 4 | 100.0% | inf | $2.25 | $9.01 |
| external | F75 | 27 | 6 | 83.3% | 47.05 | $1.24 | $7.44 |
| external | F80 | 27 | 8 | 87.5% | 7.34 | $1.01 | $8.07 |
| external | SIG_MID | 27 | 17 | 70.6% | 0.68 | $-0.10 | $-1.66 |
| external | SIG_LOW | 27 | 17 | 88.2% | 5.62 | $0.80 | $13.56 |
| development | NEXT_OPEN | 44 | 43 | 41.9% | 0.62 | $-0.15 | $-6.51 |
| development | F50 | 44 | 9 | 44.4% | 1.79 | $1.24 | $11.13 |
| development | F55 | 44 | 13 | 61.5% | 1.99 | $1.21 | $15.78 |
| development | F60 | 44 | 13 | 61.5% | 1.55 | $0.74 | $9.67 |
| development | F65 | 44 | 17 | 70.6% | 1.87 | $0.99 | $16.87 |
| development | F70 | 44 | 19 | 73.7% | 1.66 | $0.74 | $14.09 |
| development | F75 | 44 | 21 | 76.2% | 1.60 | $0.57 | $11.96 |
| development | F80 | 44 | 23 | 82.6% | 2.62 | $0.81 | $18.67 |
| development | SIG_MID | 44 | 27 | 59.3% | 0.64 | $-0.17 | $-4.68 |
| development | SIG_LOW | 44 | 26 | 69.2% | 1.03 | $0.03 | $0.71 |
| reference_validation | NEXT_OPEN | 17 | 17 | 47.1% | 2.74 | $0.17 | $2.83 |
| reference_validation | F50 | 17 | 3 | 100.0% | inf | $2.66 | $7.99 |
| reference_validation | F55 | 17 | 5 | 100.0% | inf | $2.49 | $12.44 |
| reference_validation | F60 | 17 | 5 | 100.0% | inf | $2.17 | $10.83 |
| reference_validation | F65 | 17 | 5 | 100.0% | inf | $1.84 | $9.22 |
| reference_validation | F70 | 17 | 5 | 100.0% | inf | $1.52 | $7.61 |
| reference_validation | F75 | 17 | 5 | 100.0% | inf | $1.20 | $6.00 |
| reference_validation | F80 | 17 | 6 | 100.0% | inf | $0.78 | $4.67 |
| reference_validation | SIG_MID | 17 | 8 | 50.0% | 0.99 | $-0.00 | $-0.01 |
| reference_validation | SIG_LOW | 17 | 9 | 100.0% | inf | $0.67 | $6.04 |
| august | NEXT_OPEN | 2 | 2 | 0.0% | 0.00 | $-0.32 | $-0.65 |
| august | F50 | 2 | 0 | - | - | $- | $- |
| august | F55 | 2 | 0 | - | - | $- | $- |
| august | F60 | 2 | 0 | - | - | $- | $- |
| august | F65 | 2 | 0 | - | - | $- | $- |
| august | F70 | 2 | 0 | - | - | $- | $- |
| august | F75 | 2 | 0 | - | - | $- | $- |
| august | F80 | 2 | 0 | - | - | $- | $- |
| august | SIG_MID | 2 | 0 | - | - | $- | $- |
| august | SIG_LOW | 2 | 1 | 100.0% | inf | $0.64 | $0.64 |

Selection is research-only. Reference validation is historical and not pristine independent OOS. Live BBC unchanged.
