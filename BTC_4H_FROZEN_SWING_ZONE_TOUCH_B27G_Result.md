# B27G — BTC 4H Frozen Swing-Level Zone Retest Breakout

Source coverage: **100.0000%**. Same frozen swing-level breakout and 2R trade rule as B27F; only the pre-breakout retest definition is expanded to 0.10% and 0.20% zones.

Retest HIGH: high reaches at least level*(1-tolerance) while close remains <= original level. Retest LOW: low reaches at most level*(1+tolerance) while close remains >= original level. Consecutive qualifying candles = one visit. Breakout remains strict close-through of the original level.

| Tolerance | Partition | Prior retests | Resolved | LONG N | SHORT N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop | Median hold min |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| TOL_0.10 | external | ALL | 33 | 31 | 2 | 14 | 19 | 42.42% | 1.21 | $2.77 | $91.25 | 3.65% | 2175.0 |
| TOL_0.10 | external | 0 | 15 | 15 | 0 | 5 | 10 | 33.33% | 1.34 | $4.44 | $66.64 | 4.17% | 2605.0 |
| TOL_0.10 | external | 1 | 13 | 11 | 2 | 7 | 6 | 53.85% | 0.87 | $-1.79 | $-23.22 | 2.07% | 925.0 |
| TOL_0.10 | external | 2 | 4 | 4 | 0 | 1 | 3 | 25.00% | 1.04 | $0.43 | $1.73 | 3.22% | 1645.0 |
| TOL_0.10 | external | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.10 | external | 4+ | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $46.09 | $46.09 | 4.65% | 7165.0 |
| TOL_0.10 | development | ALL | 23 | 14 | 9 | 11 | 12 | 47.83% | 1.90 | $7.95 | $182.94 | 3.39% | 1120.0 |
| TOL_0.10 | development | 0 | 5 | 2 | 3 | 2 | 3 | 40.00% | 1.56 | $5.78 | $28.89 | 3.22% | 325.0 |
| TOL_0.10 | development | 1 | 12 | 8 | 4 | 6 | 6 | 50.00% | 3.06 | $13.00 | $156.01 | 2.64% | 895.0 |
| TOL_0.10 | development | 2 | 4 | 2 | 2 | 1 | 3 | 25.00% | 0.25 | $-14.23 | $-56.92 | 4.70% | 2425.0 |
| TOL_0.10 | development | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.10 | development | 4+ | 2 | 2 | 0 | 2 | 0 | 100.00% | inf | $27.48 | $54.96 | 2.79% | 2610.0 |
| TOL_0.10 | reference_validation | ALL | 16 | 9 | 7 | 5 | 11 | 31.25% | 0.60 | $-3.83 | $-61.21 | 2.22% | 730.0 |
| TOL_0.10 | reference_validation | 0 | 6 | 5 | 1 | 1 | 5 | 16.67% | 0.13 | $-10.21 | $-61.24 | 1.07% | 652.5 |
| TOL_0.10 | reference_validation | 1 | 5 | 2 | 3 | 3 | 2 | 60.00% | 2.35 | $7.51 | $37.54 | 2.63% | 1215.0 |
| TOL_0.10 | reference_validation | 2 | 2 | 1 | 1 | 0 | 2 | 0.00% | 0.00 | $-12.34 | $-24.67 | 2.39% | 1992.5 |
| TOL_0.10 | reference_validation | 3 | 3 | 1 | 2 | 1 | 2 | 33.33% | 0.57 | $-4.28 | $-12.83 | 2.11% | 610.0 |
| TOL_0.10 | reference_validation | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.10 | august | ALL | 2 | 2 | 1 | 1 | 1 | 50.00% | 4.37 | $7.47 | $14.95 | 1.39% | 11650.0 |
| TOL_0.10 | august | 0 | 1 | 1 | 1 | 0 | 1 | 0.00% | 0.00 | $-4.44 | $-4.44 | 0.81% | 315.0 |
| TOL_0.10 | august | 1 | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $19.38 | $19.38 | 1.98% | 22985.0 |
| TOL_0.10 | august | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.10 | august | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.10 | august | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.20 | external | ALL | 33 | 31 | 2 | 14 | 19 | 42.42% | 1.21 | $2.77 | $91.25 | 3.65% | 2175.0 |
| TOL_0.20 | external | 0 | 15 | 15 | 0 | 5 | 10 | 33.33% | 1.34 | $4.44 | $66.64 | 4.17% | 2605.0 |
| TOL_0.20 | external | 1 | 13 | 11 | 2 | 7 | 6 | 53.85% | 0.87 | $-1.79 | $-23.22 | 2.07% | 925.0 |
| TOL_0.20 | external | 2 | 3 | 3 | 0 | 1 | 2 | 33.33% | 1.79 | $6.89 | $20.67 | 2.72% | 960.0 |
| TOL_0.20 | external | 3 | 1 | 1 | 0 | 0 | 1 | 0.00% | 0.00 | $-18.94 | $-18.94 | 3.71% | 2330.0 |
| TOL_0.20 | external | 4+ | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $46.09 | $46.09 | 4.65% | 7165.0 |
| TOL_0.20 | development | ALL | 23 | 14 | 9 | 11 | 12 | 47.83% | 1.90 | $7.95 | $182.94 | 3.39% | 1120.0 |
| TOL_0.20 | development | 0 | 4 | 1 | 3 | 1 | 3 | 25.00% | 1.11 | $1.46 | $5.83 | 4.46% | 3195.0 |
| TOL_0.20 | development | 1 | 12 | 8 | 4 | 6 | 6 | 50.00% | 1.80 | $5.09 | $61.05 | 1.89% | 682.5 |
| TOL_0.20 | development | 2 | 5 | 3 | 2 | 2 | 3 | 40.00% | 1.81 | $12.22 | $61.09 | 5.46% | 4740.0 |
| TOL_0.20 | development | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.20 | development | 4+ | 2 | 2 | 0 | 2 | 0 | 100.00% | inf | $27.48 | $54.96 | 2.79% | 2610.0 |
| TOL_0.20 | reference_validation | ALL | 16 | 9 | 7 | 5 | 11 | 31.25% | 0.60 | $-3.83 | $-61.21 | 2.22% | 730.0 |
| TOL_0.20 | reference_validation | 0 | 4 | 3 | 1 | 1 | 3 | 25.00% | 0.15 | $-12.58 | $-50.33 | 3.11% | 652.5 |
| TOL_0.20 | reference_validation | 1 | 5 | 3 | 2 | 1 | 4 | 20.00% | 0.67 | $-2.57 | $-12.87 | 2.33% | 1695.0 |
| TOL_0.20 | reference_validation | 2 | 4 | 3 | 1 | 2 | 2 | 50.00% | 1.14 | $0.86 | $3.44 | 1.74% | 687.5 |
| TOL_0.20 | reference_validation | 3 | 3 | 0 | 3 | 1 | 2 | 33.33% | 0.95 | $-0.48 | $-1.45 | 2.89% | 1215.0 |
| TOL_0.20 | reference_validation | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.20 | august | ALL | 2 | 2 | 1 | 1 | 1 | 50.00% | 4.37 | $7.47 | $14.95 | 1.39% | 11650.0 |
| TOL_0.20 | august | 0 | 1 | 1 | 1 | 0 | 1 | 0.00% | 0.00 | $-4.44 | $-4.44 | 0.81% | 315.0 |
| TOL_0.20 | august | 1 | 1 | 1 | 0 | 1 | 0 | 100.00% | inf | $19.38 | $19.38 | 1.98% | 22985.0 |
| TOL_0.20 | august | 2 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.20 | august | 3 | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |
| TOL_0.20 | august | 4+ | 0 | 0 | 0 | 0 | 0 | - | - | $- | $- | - | - |

## Pre-registered repeatability verdict

- TOL_0.10, 0 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.10, 1 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.10, 2 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.10, 3 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.10, 4+ prior retests: **FAIL / INSUFFICIENT**
- TOL_0.20, 0 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.20, 1 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.20, 2 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.20, 3 prior retests: **FAIL / INSUFFICIENT**
- TOL_0.20, 4+ prior retests: **FAIL / INSUFFICIENT**

Gate: same tolerance + retest bucket must have >=30 resolved trades, positive fee-sensitive expectancy, and net PF >=1.20 in external, development, and reference_validation.

**B27G overall: FAIL / INSUFFICIENT.**

Research only; live BBC unchanged.
