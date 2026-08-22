# B27T — London -> New York Pressure Path / Stop-Semantics Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27Q K1 OPP0 signal identity and structural first-close-break outcomes were reproduced exactly.

## Why 88-90% directional probability can coexist with weak trades

| Partition | Signals | Target-break | Target breaks | Prior wick to/below Low before eventual High break | Median minimum low fraction | 10th pct minimum low fraction | Median minimum close fraction |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 101 | 89.1% | 90 | 1 (1.1%) | 0.83 | 0.55 | 0.89 |
| development | 164 | 72.6% | 119 | 2 (1.7%) | 0.75 | 0.29 | 0.86 |
| reference_validation | 82 | 85.4% | 70 | 0 (0.0%) | 0.73 | 0.14 | 0.89 |
| august | 4 | 100.0% | 4 | 0 (0.0%) | 0.71 | 0.36 | 0.73 |

Range fraction is Low=0, High=1. Negative minimum-low fraction means price wicked below the previous-session Low without necessarily closing below it.

## Stop semantics comparison

| Partition | Method | Semantics | Fills | WR | PF | Net exp | Total net |
|---|---|---|---:|---:|---:|---:|---:|
| external | NEXT_OPEN | WICK_STOP | 101 | 51.5% | 0.68 | $-0.17 | $-17.25 |
| external | NEXT_OPEN | CLOSE_INVALIDATION | 101 | 52.5% | 0.86 | $-0.06 | $-6.30 |
| external | F50 | WICK_STOP | 17 | 64.7% | 1.96 | $1.09 | $18.51 |
| external | F50 | CLOSE_INVALIDATION | 17 | 70.6% | 3.18 | $1.61 | $27.32 |
| external | F55 | WICK_STOP | 19 | 73.7% | 2.41 | $1.39 | $26.46 |
| external | F55 | CLOSE_INVALIDATION | 19 | 73.7% | 3.03 | $1.59 | $30.30 |
| external | F60 | WICK_STOP | 21 | 76.2% | 1.94 | $0.95 | $19.91 |
| external | F60 | CLOSE_INVALIDATION | 21 | 76.2% | 2.37 | $1.13 | $23.75 |
| external | F65 | WICK_STOP | 24 | 70.8% | 2.01 | $1.06 | $25.38 |
| external | F65 | CLOSE_INVALIDATION | 24 | 70.8% | 2.37 | $1.22 | $29.22 |
| external | F70 | WICK_STOP | 31 | 77.4% | 2.31 | $1.25 | $38.76 |
| external | F70 | CLOSE_INVALIDATION | 31 | 77.4% | 2.66 | $1.37 | $42.59 |
| external | F75 | WICK_STOP | 40 | 80.0% | 2.06 | $0.91 | $36.26 |
| external | F75 | CLOSE_INVALIDATION | 40 | 80.0% | 2.32 | $1.00 | $40.09 |
| external | F80 | WICK_STOP | 45 | 84.4% | 2.10 | $0.75 | $33.63 |
| external | F80 | CLOSE_INVALIDATION | 45 | 84.4% | 2.09 | $0.75 | $33.53 |
| development | NEXT_OPEN | WICK_STOP | 164 | 55.5% | 0.38 | $-0.72 | $-118.72 |
| development | NEXT_OPEN | CLOSE_INVALIDATION | 164 | 56.7% | 0.36 | $-0.80 | $-130.84 |
| development | F50 | WICK_STOP | 62 | 33.9% | 0.64 | $-0.87 | $-53.98 |
| development | F50 | CLOSE_INVALIDATION | 62 | 38.7% | 0.59 | $-1.12 | $-69.18 |
| development | F55 | WICK_STOP | 68 | 39.7% | 0.64 | $-0.89 | $-60.81 |
| development | F55 | CLOSE_INVALIDATION | 68 | 44.1% | 0.60 | $-1.12 | $-75.99 |
| development | F60 | WICK_STOP | 75 | 46.7% | 0.64 | $-0.88 | $-66.37 |
| development | F60 | CLOSE_INVALIDATION | 75 | 50.7% | 0.60 | $-1.07 | $-80.37 |
| development | F65 | WICK_STOP | 82 | 53.7% | 0.66 | $-0.81 | $-66.66 |
| development | F65 | CLOSE_INVALIDATION | 82 | 57.3% | 0.62 | $-0.97 | $-79.66 |
| development | F70 | WICK_STOP | 86 | 57.0% | 0.55 | $-1.10 | $-94.55 |
| development | F70 | CLOSE_INVALIDATION | 86 | 59.3% | 0.52 | $-1.28 | $-109.98 |
| development | F75 | WICK_STOP | 99 | 62.6% | 0.50 | $-1.15 | $-113.66 |
| development | F75 | CLOSE_INVALIDATION | 99 | 64.6% | 0.47 | $-1.30 | $-129.07 |
| development | F80 | WICK_STOP | 110 | 68.2% | 0.48 | $-1.07 | $-117.42 |
| development | F80 | CLOSE_INVALIDATION | 110 | 69.1% | 0.45 | $-1.23 | $-135.05 |
| reference_validation | NEXT_OPEN | WICK_STOP | 82 | 48.8% | 0.50 | $-0.32 | $-26.00 |
| reference_validation | NEXT_OPEN | CLOSE_INVALIDATION | 82 | 48.8% | 0.42 | $-0.44 | $-36.02 |
| reference_validation | F50 | WICK_STOP | 28 | 60.7% | 1.74 | $0.68 | $18.98 |
| reference_validation | F50 | CLOSE_INVALIDATION | 28 | 60.7% | 1.25 | $0.32 | $8.93 |
| reference_validation | F55 | WICK_STOP | 32 | 68.8% | 1.86 | $0.72 | $22.91 |
| reference_validation | F55 | CLOSE_INVALIDATION | 32 | 68.8% | 1.38 | $0.42 | $13.55 |
| reference_validation | F60 | WICK_STOP | 35 | 68.6% | 1.65 | $0.54 | $19.04 |
| reference_validation | F60 | CLOSE_INVALIDATION | 35 | 68.6% | 1.25 | $0.28 | $9.69 |
| reference_validation | F65 | WICK_STOP | 37 | 73.0% | 1.58 | $0.45 | $16.60 |
| reference_validation | F65 | CLOSE_INVALIDATION | 37 | 73.0% | 1.24 | $0.24 | $8.78 |
| reference_validation | F70 | WICK_STOP | 37 | 75.7% | 1.29 | $0.23 | $8.50 |
| reference_validation | F70 | CLOSE_INVALIDATION | 37 | 75.7% | 1.02 | $0.02 | $0.72 |
| reference_validation | F75 | WICK_STOP | 39 | 79.5% | 1.30 | $0.22 | $8.60 |
| reference_validation | F75 | CLOSE_INVALIDATION | 39 | 79.5% | 1.08 | $0.07 | $2.83 |
| reference_validation | F80 | WICK_STOP | 41 | 82.9% | 1.06 | $0.04 | $1.70 |
| reference_validation | F80 | CLOSE_INVALIDATION | 41 | 82.9% | 0.90 | $-0.08 | $-3.41 |
| august | NEXT_OPEN | WICK_STOP | 4 | 50.0% | 4.10 | $0.29 | $1.15 |
| august | NEXT_OPEN | CLOSE_INVALIDATION | 4 | 50.0% | 4.10 | $0.29 | $1.15 |
| august | F50 | WICK_STOP | 1 | 100.0% | inf | $1.98 | $1.98 |
| august | F50 | CLOSE_INVALIDATION | 1 | 100.0% | inf | $1.98 | $1.98 |
| august | F55 | WICK_STOP | 1 | 100.0% | inf | $1.74 | $1.74 |
| august | F55 | CLOSE_INVALIDATION | 1 | 100.0% | inf | $1.74 | $1.74 |
| august | F60 | WICK_STOP | 1 | 100.0% | inf | $1.50 | $1.50 |
| august | F60 | CLOSE_INVALIDATION | 1 | 100.0% | inf | $1.50 | $1.50 |
| august | F65 | WICK_STOP | 2 | 100.0% | inf | $1.12 | $2.23 |
| august | F65 | CLOSE_INVALIDATION | 2 | 100.0% | inf | $1.12 | $2.23 |
| august | F70 | WICK_STOP | 2 | 100.0% | inf | $0.90 | $1.80 |
| august | F70 | CLOSE_INVALIDATION | 2 | 100.0% | inf | $0.90 | $1.80 |
| august | F75 | WICK_STOP | 2 | 100.0% | inf | $0.68 | $1.36 |
| august | F75 | CLOSE_INVALIDATION | 2 | 100.0% | inf | $0.68 | $1.36 |
| august | F80 | WICK_STOP | 3 | 100.0% | inf | $1.43 | $4.30 |
| august | F80 | CLOSE_INVALIDATION | 3 | 100.0% | inf | $1.43 | $4.30 |

Diagnostic only. CLOSE_INVALIDATION is not promoted as a live stop rule. This audit exists to separate directional edge, path quality, reward:risk, and stop-definition mismatch.

Research only; live BBC unchanged.
