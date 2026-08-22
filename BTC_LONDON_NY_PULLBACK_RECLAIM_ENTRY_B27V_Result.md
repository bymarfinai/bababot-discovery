# B27V — London -> New York Pullback Reclaim Entry — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27Q K1/K2 OPP0 signal identities are unchanged; entry waits for causal 5m pullback-reclaim confirmation and uses the frozen pre-entry pullback low as stop.

## Primary K1 OPP0

| Partition | Zone | Setups | Activated | Confirmed | Trades | WR | TP rate | PF | Net exp | Total net | Median RR | Median PB-low f |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | Z75 | 101 | 40 (39.6%) | 32 (31.7%) | 32 | 71.9% | 81.2% | 2.46 | $0.56 | $17.89 | 0.61 | 0.66 |
| external | Z80 | 101 | 47 (46.5%) | 35 (34.7%) | 35 | 71.4% | 82.9% | 1.80 | $0.32 | $11.33 | 0.57 | 0.69 |
| external | Z85 | 101 | 57 (56.4%) | 44 (43.6%) | 44 | 65.9% | 84.1% | 2.05 | $0.30 | $13.12 | 0.42 | 0.73 |
| development | Z75 | 164 | 99 (60.4%) | 61 (37.2%) | 61 | 52.5% | 67.2% | 0.49 | $-0.56 | $-33.87 | 0.43 | 0.58 |
| development | Z80 | 164 | 111 (67.7%) | 61 (37.2%) | 61 | 45.9% | 67.2% | 0.34 | $-0.70 | $-42.45 | 0.32 | 0.59 |
| development | Z85 | 164 | 121 (73.8%) | 56 (34.1%) | 56 | 46.4% | 73.2% | 0.38 | $-0.49 | $-27.38 | 0.24 | 0.62 |
| reference_validation | Z75 | 82 | 44 (53.7%) | 25 (30.5%) | 25 | 64.0% | 76.0% | 0.87 | $-0.08 | $-1.95 | 0.34 | 0.53 |
| reference_validation | Z80 | 82 | 47 (57.3%) | 24 (29.3%) | 24 | 58.3% | 75.0% | 0.56 | $-0.29 | $-7.02 | 0.32 | 0.56 |
| reference_validation | Z85 | 82 | 50 (61.0%) | 24 (29.3%) | 24 | 45.8% | 75.0% | 0.32 | $-0.47 | $-11.18 | 0.29 | 0.59 |
| august | Z75 | 4 | 2 (50.0%) | 2 (50.0%) | 2 | 50.0% | 50.0% | 0.41 | $-0.37 | $-0.73 | 0.56 | 0.43 |
| august | Z80 | 4 | 3 (75.0%) | 3 (75.0%) | 3 | 66.7% | 66.7% | 0.67 | $-0.14 | $-0.41 | 0.35 | 0.62 |
| august | Z85 | 4 | 3 (75.0%) | 2 (50.0%) | 2 | 50.0% | 100.0% | 1.65 | $0.06 | $0.13 | 0.20 | 0.71 |

## Screen

**No K1 zone passed the frozen three-partition screen.**

## Secondary K2 diagnostic

| Partition | Zone | Trades | WR | TP rate | PF | Net exp | Total net | Median RR |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| external | Z75 | 4 | 75.0% | 100.0% | 18.67 | $0.77 | $3.06 | 0.62 |
| external | Z80 | 6 | 66.7% | 83.3% | 1.79 | $0.22 | $1.31 | 0.33 |
| external | Z85 | 10 | 80.0% | 90.0% | 2.56 | $0.26 | $2.60 | 0.35 |
| development | Z75 | 15 | 60.0% | 66.7% | 0.62 | $-0.37 | $-5.55 | 0.69 |
| development | Z80 | 16 | 50.0% | 62.5% | 0.34 | $-0.80 | $-12.73 | 0.41 |
| development | Z85 | 13 | 53.8% | 69.2% | 0.42 | $-0.31 | $-3.97 | 0.17 |
| reference_validation | Z75 | 3 | 100.0% | 100.0% | inf | $0.72 | $2.17 | 0.29 |
| reference_validation | Z80 | 3 | 100.0% | 100.0% | inf | $0.39 | $1.17 | 0.28 |
| reference_validation | Z85 | 3 | 100.0% | 100.0% | inf | $0.26 | $0.77 | 0.21 |
| august | Z75 | 0 | - | - | - | $- | $- | - |
| august | Z80 | 0 | - | - | - | $- | $- | - |
| august | Z85 | 0 | - | - | - | $- | $- | - |

Research only; live BBC unchanged.
