# B27DC — BTC 24H F05 SHORT Causal Abort Economics — Result

5m rows: **698,112**; coverage **100.0000%**. Audit **PASS**.

**Critical inference correction:** frozen B27CV models are trained exactly as before, but inference now scores every trade still alive at +10/+15, including eventual OTHER outcomes. Future labels do not gate abort eligibility.

Parent reproduction: +10 AUC **0.8452298452**, +15 AUC **0.8860088365**; BASE_H no-abort total net **$-278.39**.

BASE_H is diagnostic/non-promotable because nominal RR>=1:1 is not guaranteed. R100 is the RR-compliant 1:1 lane. External/reference_validation are reused; B27DA fresh holdout remains insufficient.

## Six clocks independently

| WIB | Candidate | Rule | N | WR | PF | Exp/trade | Total net | MaxDD | Loss streak | Aborts |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 07-11 | BASE_H | NO_ABORT | 101 | 68.3% | 0.48 | $-0.80 | $-80.84 | $+93.19 | 3 | 0 |
| 07-11 | BASE_H | GLOBAL_PLUS15_SAFE | 101 | 60.4% | 0.47 | $-0.74 | $-74.98 | $+87.33 | 4 | 20 |
| 07-11 | BASE_H | PERSIST_10_15 | 101 | 62.4% | 0.45 | $-0.81 | $-82.19 | $+94.55 | 4 | 13 |
| 07-11 | BASE_H | REFINED_BULL_IMPULSE | 101 | 62.4% | 0.47 | $-0.76 | $-76.73 | $+89.09 | 4 | 15 |
| 07-11 | R100 | NO_ABORT | 101 | 43.6% | 0.38 | $-0.63 | $-63.44 | $+67.19 | 7 | 0 |
| 07-11 | R100 | GLOBAL_PLUS15_SAFE | 101 | 42.6% | 0.38 | $-0.62 | $-62.63 | $+66.37 | 7 | 4 |
| 07-11 | R100 | PERSIST_10_15 | 101 | 42.6% | 0.38 | $-0.62 | $-62.63 | $+66.37 | 7 | 4 |
| 07-11 | R100 | REFINED_BULL_IMPULSE | 101 | 42.6% | 0.38 | $-0.62 | $-62.63 | $+66.37 | 7 | 4 |
| 11-15 | BASE_H | NO_ABORT | 96 | 71.9% | 1.23 | $+0.22 | $+20.71 | $+30.44 | 6 | 0 |
| 11-15 | BASE_H | GLOBAL_PLUS15_SAFE | 96 | 68.8% | 1.09 | $+0.09 | $+8.53 | $+30.44 | 6 | 5 |
| 11-15 | BASE_H | PERSIST_10_15 | 96 | 71.9% | 1.25 | $+0.23 | $+22.02 | $+30.44 | 6 | 1 |
| 11-15 | BASE_H | REFINED_BULL_IMPULSE | 96 | 71.9% | 1.25 | $+0.23 | $+22.02 | $+30.44 | 6 | 1 |
| 11-15 | R100 | NO_ABORT | 96 | 58.3% | 1.14 | $+0.12 | $+11.77 | $+28.08 | 7 | 0 |
| 11-15 | R100 | GLOBAL_PLUS15_SAFE | 96 | 59.4% | 1.26 | $+0.20 | $+19.24 | $+21.96 | 7 | 4 |
| 11-15 | R100 | PERSIST_10_15 | 96 | 58.3% | 1.15 | $+0.13 | $+12.44 | $+27.40 | 7 | 1 |
| 11-15 | R100 | REFINED_BULL_IMPULSE | 96 | 58.3% | 1.15 | $+0.13 | $+12.44 | $+27.40 | 7 | 1 |
| 15-19 | BASE_H | NO_ABORT | 114 | 64.0% | 0.53 | $-0.57 | $-65.20 | $+73.79 | 4 | 0 |
| 15-19 | BASE_H | GLOBAL_PLUS15_SAFE | 114 | 49.1% | 0.60 | $-0.34 | $-39.27 | $+39.48 | 7 | 34 |
| 15-19 | BASE_H | PERSIST_10_15 | 114 | 55.3% | 0.57 | $-0.41 | $-47.27 | $+49.08 | 7 | 20 |
| 15-19 | BASE_H | REFINED_BULL_IMPULSE | 114 | 55.3% | 0.60 | $-0.37 | $-42.71 | $+44.53 | 7 | 21 |
| 15-19 | R100 | NO_ABORT | 114 | 45.6% | 0.42 | $-0.59 | $-67.63 | $+67.84 | 7 | 0 |
| 15-19 | R100 | GLOBAL_PLUS15_SAFE | 114 | 37.7% | 0.44 | $-0.50 | $-57.39 | $+57.60 | 9 | 26 |
| 15-19 | R100 | PERSIST_10_15 | 114 | 41.2% | 0.43 | $-0.54 | $-61.81 | $+62.03 | 9 | 17 |
| 15-19 | R100 | REFINED_BULL_IMPULSE | 114 | 41.2% | 0.43 | $-0.54 | $-61.81 | $+62.03 | 9 | 17 |
| 19-23 | BASE_H | NO_ABORT | 147 | 68.0% | 0.64 | $-0.46 | $-67.81 | $+88.31 | 4 | 0 |
| 19-23 | BASE_H | GLOBAL_PLUS15_SAFE | 147 | 60.5% | 0.59 | $-0.45 | $-66.43 | $+70.83 | 4 | 33 |
| 19-23 | BASE_H | PERSIST_10_15 | 147 | 62.6% | 0.56 | $-0.53 | $-77.96 | $+86.74 | 4 | 25 |
| 19-23 | BASE_H | REFINED_BULL_IMPULSE | 147 | 62.6% | 0.58 | $-0.50 | $-73.67 | $+82.45 | 4 | 26 |
| 19-23 | R100 | NO_ABORT | 147 | 46.3% | 0.51 | $-0.58 | $-84.73 | $+95.97 | 5 | 0 |
| 19-23 | R100 | GLOBAL_PLUS15_SAFE | 147 | 44.9% | 0.43 | $-0.66 | $-96.80 | $+100.37 | 5 | 12 |
| 19-23 | R100 | PERSIST_10_15 | 147 | 44.9% | 0.44 | $-0.66 | $-96.76 | $+102.37 | 5 | 8 |
| 19-23 | R100 | REFINED_BULL_IMPULSE | 147 | 44.9% | 0.44 | $-0.65 | $-95.85 | $+101.46 | 5 | 9 |
| 23-03 | BASE_H | NO_ABORT | 106 | 66.0% | 0.59 | $-0.65 | $-68.60 | $+81.93 | 4 | 0 |
| 23-03 | BASE_H | GLOBAL_PLUS15_SAFE | 106 | 65.1% | 0.59 | $-0.64 | $-67.71 | $+81.04 | 4 | 2 |
| 23-03 | BASE_H | PERSIST_10_15 | 106 | 66.0% | 0.59 | $-0.63 | $-66.63 | $+79.97 | 4 | 1 |
| 23-03 | BASE_H | REFINED_BULL_IMPULSE | 106 | 66.0% | 0.59 | $-0.63 | $-66.63 | $+79.97 | 4 | 1 |
| 23-03 | R100 | NO_ABORT | 106 | 47.2% | 0.40 | $-0.83 | $-87.80 | $+89.42 | 4 | 0 |
| 23-03 | R100 | GLOBAL_PLUS15_SAFE | 106 | 46.2% | 0.40 | $-0.84 | $-88.88 | $+90.50 | 4 | 1 |
| 23-03 | R100 | PERSIST_10_15 | 106 | 47.2% | 0.40 | $-0.83 | $-87.80 | $+89.42 | 4 | 0 |
| 23-03 | R100 | REFINED_BULL_IMPULSE | 106 | 47.2% | 0.40 | $-0.83 | $-87.80 | $+89.42 | 4 | 0 |
| 03-07 | BASE_H | NO_ABORT | 88 | 60.2% | 0.82 | $-0.19 | $-16.64 | $+29.31 | 5 | 0 |
| 03-07 | BASE_H | GLOBAL_PLUS15_SAFE | 88 | 54.5% | 0.86 | $-0.12 | $-10.95 | $+20.63 | 5 | 14 |
| 03-07 | BASE_H | PERSIST_10_15 | 88 | 58.0% | 0.93 | $-0.06 | $-5.06 | $+20.53 | 5 | 8 |
| 03-07 | BASE_H | REFINED_BULL_IMPULSE | 88 | 58.0% | 0.93 | $-0.06 | $-5.06 | $+20.53 | 5 | 8 |
| 03-07 | R100 | NO_ABORT | 88 | 43.2% | 0.42 | $-0.73 | $-63.83 | $+63.83 | 11 | 0 |
| 03-07 | R100 | GLOBAL_PLUS15_SAFE | 88 | 40.9% | 0.46 | $-0.62 | $-54.61 | $+61.59 | 11 | 8 |
| 03-07 | R100 | PERSIST_10_15 | 88 | 42.0% | 0.44 | $-0.68 | $-59.80 | $+61.44 | 11 | 5 |
| 03-07 | R100 | REFINED_BULL_IMPULSE | 88 | 42.0% | 0.44 | $-0.68 | $-59.80 | $+61.44 | 11 | 5 |

## Pooled and partition economics

| Scope | Candidate | Rule | N | WR | PF | Exp/trade | Total net | Avg win | Avg loss | MaxDD | Loss streak | Abort rate | Trades/wk |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASE_H | NO_ABORT | 297 | 65.3% | 0.57 | $-0.47 | $-140.52 | $+0.97 | $-3.19 | $+152.30 | 6 | 0.0% | 1.90 |
| development | BASE_H | GLOBAL_PLUS15_SAFE | 297 | 61.3% | 0.72 | $-0.23 | $-67.12 | $+0.97 | $-2.12 | $+82.67 | 6 | 15.2% | 1.90 |
| development | BASE_H | PERSIST_10_15 | 297 | 63.6% | 0.67 | $-0.30 | $-88.48 | $+0.97 | $-2.52 | $+102.67 | 6 | 10.1% | 1.90 |
| development | BASE_H | REFINED_BULL_IMPULSE | 297 | 63.6% | 0.69 | $-0.28 | $-84.19 | $+0.97 | $-2.48 | $+98.38 | 6 | 10.4% | 1.90 |
| development | R100 | NO_ABORT | 297 | 45.1% | 0.39 | $-0.65 | $-192.63 | $+0.90 | $-1.92 | $+194.68 | 8 | 0.0% | 1.90 |
| development | R100 | GLOBAL_PLUS15_SAFE | 297 | 44.1% | 0.40 | $-0.61 | $-181.41 | $+0.91 | $-1.81 | $+183.46 | 9 | 6.7% | 1.90 |
| development | R100 | PERSIST_10_15 | 297 | 44.8% | 0.39 | $-0.62 | $-184.81 | $+0.90 | $-1.86 | $+186.86 | 8 | 4.4% | 1.90 |
| development | R100 | REFINED_BULL_IMPULSE | 297 | 44.8% | 0.40 | $-0.62 | $-183.90 | $+0.90 | $-1.85 | $+185.95 | 8 | 4.7% | 1.90 |
| external | BASE_H | NO_ABORT | 183 | 71.0% | 0.78 | $-0.41 | $-75.15 | $+2.03 | $-6.40 | $+114.11 | 4 | 0.0% | 1.77 |
| external | BASE_H | GLOBAL_PLUS15_SAFE | 183 | 62.3% | 0.71 | $-0.50 | $-91.08 | $+1.96 | $-4.55 | $+118.59 | 8 | 18.0% | 1.77 |
| external | BASE_H | PERSIST_10_15 | 183 | 65.0% | 0.74 | $-0.45 | $-82.62 | $+2.01 | $-5.03 | $+120.33 | 8 | 11.5% | 1.77 |
| external | BASE_H | REFINED_BULL_IMPULSE | 183 | 65.0% | 0.75 | $-0.43 | $-78.07 | $+2.01 | $-4.96 | $+115.78 | 8 | 12.0% | 1.77 |
| external | R100 | NO_ABORT | 183 | 50.8% | 0.72 | $-0.40 | $-73.56 | $+2.02 | $-2.91 | $+91.57 | 7 | 0.0% | 1.77 |
| external | R100 | GLOBAL_PLUS15_SAFE | 183 | 48.6% | 0.74 | $-0.34 | $-61.34 | $+1.99 | $-2.53 | $+85.83 | 8 | 11.5% | 1.77 |
| external | R100 | PERSIST_10_15 | 183 | 49.2% | 0.71 | $-0.40 | $-72.36 | $+2.00 | $-2.72 | $+92.38 | 8 | 7.1% | 1.77 |
| external | R100 | REFINED_BULL_IMPULSE | 183 | 49.2% | 0.71 | $-0.40 | $-72.36 | $+2.00 | $-2.72 | $+92.38 | 8 | 7.1% | 1.77 |
| reference_validation | BASE_H | NO_ABORT | 172 | 64.0% | 0.62 | $-0.36 | $-62.72 | $+0.93 | $-2.66 | $+82.31 | 4 | 0.0% | 2.11 |
| reference_validation | BASE_H | GLOBAL_PLUS15_SAFE | 172 | 54.1% | 0.47 | $-0.54 | $-92.60 | $+0.88 | $-2.21 | $+100.50 | 6 | 17.4% | 2.11 |
| reference_validation | BASE_H | PERSIST_10_15 | 172 | 58.1% | 0.50 | $-0.50 | $-85.99 | $+0.88 | $-2.41 | $+96.96 | 6 | 9.9% | 2.11 |
| reference_validation | BASE_H | REFINED_BULL_IMPULSE | 172 | 58.1% | 0.52 | $-0.47 | $-80.53 | $+0.88 | $-2.34 | $+91.50 | 6 | 11.0% | 2.11 |
| reference_validation | R100 | NO_ABORT | 172 | 47.1% | 0.43 | $-0.52 | $-89.48 | $+0.84 | $-1.73 | $+96.63 | 6 | 0.0% | 2.11 |
| reference_validation | R100 | GLOBAL_PLUS15_SAFE | 172 | 43.0% | 0.38 | $-0.57 | $-98.31 | $+0.81 | $-1.62 | $+104.44 | 7 | 8.1% | 2.11 |
| reference_validation | R100 | PERSIST_10_15 | 172 | 44.2% | 0.38 | $-0.58 | $-99.19 | $+0.80 | $-1.67 | $+106.34 | 7 | 5.2% | 2.11 |
| reference_validation | R100 | REFINED_BULL_IMPULSE | 172 | 44.2% | 0.38 | $-0.58 | $-99.19 | $+0.80 | $-1.67 | $+106.34 | 7 | 5.2% | 2.11 |
| POOLED_REUSED_EXTVAL | BASE_H | NO_ABORT | 355 | 67.6% | 0.73 | $-0.39 | $-137.87 | $+1.52 | $-4.38 | $+154.02 | 4 | 0.0% | 1.04 |
| POOLED_REUSED_EXTVAL | BASE_H | GLOBAL_PLUS15_SAFE | 355 | 58.3% | 0.62 | $-0.52 | $-183.69 | $+1.47 | $-3.30 | $+185.95 | 8 | 17.7% | 1.04 |
| POOLED_REUSED_EXTVAL | BASE_H | PERSIST_10_15 | 355 | 61.7% | 0.66 | $-0.47 | $-168.61 | $+1.49 | $-3.64 | $+174.89 | 8 | 10.7% | 1.04 |
| POOLED_REUSED_EXTVAL | BASE_H | REFINED_BULL_IMPULSE | 355 | 61.7% | 0.67 | $-0.45 | $-158.60 | $+1.49 | $-3.57 | $+164.88 | 8 | 11.5% | 1.04 |
| POOLED_REUSED_EXTVAL | R100 | NO_ABORT | 355 | 49.0% | 0.61 | $-0.46 | $-163.05 | $+1.47 | $-2.32 | $+165.07 | 7 | 0.0% | 1.04 |
| POOLED_REUSED_EXTVAL | R100 | GLOBAL_PLUS15_SAFE | 355 | 45.9% | 0.60 | $-0.45 | $-159.66 | $+1.45 | $-2.07 | $+163.70 | 8 | 9.9% | 1.04 |
| POOLED_REUSED_EXTVAL | R100 | PERSIST_10_15 | 355 | 46.8% | 0.58 | $-0.48 | $-171.55 | $+1.45 | $-2.18 | $+175.59 | 8 | 6.2% | 1.04 |
| POOLED_REUSED_EXTVAL | R100 | REFINED_BULL_IMPULSE | 355 | 46.8% | 0.58 | $-0.48 | $-171.55 | $+1.45 | $-2.18 | $+175.59 | 8 | 6.2% | 1.04 |
| POOLED_MAJOR | BASE_H | NO_ABORT | 652 | 66.6% | 0.67 | $-0.43 | $-278.39 | $+1.28 | $-3.82 | $+294.54 | 6 | 0.0% | 1.91 |
| POOLED_MAJOR | BASE_H | GLOBAL_PLUS15_SAFE | 652 | 59.7% | 0.66 | $-0.38 | $-250.80 | $+1.24 | $-2.79 | $+253.06 | 8 | 16.6% | 1.91 |
| POOLED_MAJOR | BASE_H | PERSIST_10_15 | 652 | 62.6% | 0.66 | $-0.39 | $-257.09 | $+1.25 | $-3.14 | $+263.37 | 8 | 10.4% | 1.91 |
| POOLED_MAJOR | BASE_H | REFINED_BULL_IMPULSE | 652 | 62.6% | 0.68 | $-0.37 | $-242.79 | $+1.25 | $-3.09 | $+249.07 | 8 | 11.0% | 1.91 |
| POOLED_MAJOR | R100 | NO_ABORT | 652 | 47.2% | 0.51 | $-0.55 | $-355.67 | $+1.22 | $-2.13 | $+357.70 | 8 | 0.0% | 1.91 |
| POOLED_MAJOR | R100 | GLOBAL_PLUS15_SAFE | 652 | 45.1% | 0.51 | $-0.52 | $-341.07 | $+1.21 | $-1.95 | $+345.11 | 9 | 8.4% | 1.91 |
| POOLED_MAJOR | R100 | PERSIST_10_15 | 652 | 45.9% | 0.50 | $-0.55 | $-356.36 | $+1.21 | $-2.03 | $+360.40 | 8 | 5.4% | 1.91 |
| POOLED_MAJOR | R100 | REFINED_BULL_IMPULSE | 652 | 45.9% | 0.50 | $-0.55 | $-355.45 | $+1.21 | $-2.03 | $+359.49 | 8 | 5.5% | 1.91 |

## Abort attribution (post-simulation only)

| Candidate | Rule | BAD aborts | GOOD aborts | OTHER aborts |
|---|---|---:|---:|---:|
| BASE_H | GLOBAL_PLUS15_SAFE | 45 | 38 | 25 |
| BASE_H | PERSIST_10_15 | 33 | 23 | 12 |
| BASE_H | REFINED_BULL_IMPULSE | 37 | 23 | 12 |
| R100 | GLOBAL_PLUS15_SAFE | 17 | 21 | 17 |
| R100 | PERSIST_10_15 | 14 | 15 | 6 |
| R100 | REFINED_BULL_IMPULSE | 15 | 15 | 6 |

**Frozen status: `B27DC_CAUSAL_ABORT_ECON_RESEARCH_ONLY_NO_LIVE_PROMOTION`.**

B27DC reports executable historical economics only. It does not upgrade reused anatomy evidence into untouched OOS evidence and does not change live BBC.
