# ETH LONG Entry Optimization Audit E2 — Result

ETHUSDT 5m rows: **698,112**; coverage: **100.0000%**; frozen windows: **381**.

Frozen economics: E10 target + D60/F15 completed-close invalidation, $500 fixed notional, $0.40 fee. Selection uses development only; diagnostic close-fill modes cannot be selected.

## Development entry surface (selectable modes)

| Mode | Depth | N | WR | PF | Exp | Net | Exec | Median actual f | MAE/R | MFE/R | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_LIMIT | F65 | 52 | 59.6% | 1.14 | $0.36 | $18.72 | 30.1% | 0.65 | 0.40 | 0.46 | 3 |
| BLIND_LIMIT | F67.5 | 57 | 63.2% | 1.17 | $0.41 | $23.24 | 32.9% | 0.68 | 0.39 | 0.43 | 3 |
| BLIND_LIMIT | F70 | 62 | 64.5% | 1.08 | $0.20 | $12.12 | 35.8% | 0.70 | 0.30 | 0.42 | 3 |
| BLIND_LIMIT | F72.5 | 63 | 68.3% | 1.18 | $0.38 | $23.76 | 36.4% | 0.73 | 0.27 | 0.40 | 3 |
| BLIND_LIMIT | F75 | 65 | 69.2% | 1.08 | $0.17 | $11.31 | 37.6% | 0.75 | 0.27 | 0.38 | 3 |
| BLIND_LIMIT | F77.5 | 67 | 71.6% | 1.03 | $0.06 | $3.71 | 38.7% | 0.78 | 0.24 | 0.35 | 3 |
| BLIND_LIMIT | F80 | 69 | 75.4% | 1.05 | $0.09 | $6.31 | 39.9% | 0.80 | 0.23 | 0.34 | 3 |
| BLIND_NEXT_OPEN | F65 | 52 | 59.6% | 1.34 | $0.79 | $41.16 | 30.1% | 0.64 | 0.29 | 0.45 | 3 |
| BLIND_NEXT_OPEN | F67.5 | 57 | 63.2% | 1.43 | $0.92 | $52.72 | 32.9% | 0.66 | 0.28 | 0.42 | 3 |
| BLIND_NEXT_OPEN | F70 | 62 | 64.5% | 1.25 | $0.54 | $33.53 | 35.8% | 0.70 | 0.26 | 0.39 | 3 |
| BLIND_NEXT_OPEN | F72.5 | 63 | 68.3% | 1.26 | $0.54 | $34.21 | 36.4% | 0.73 | 0.23 | 0.37 | 3 |
| BLIND_NEXT_OPEN | F75 | 65 | 69.2% | 1.14 | $0.28 | $18.05 | 37.6% | 0.75 | 0.26 | 0.37 | 3 |
| BLIND_NEXT_OPEN | F77.5 | 67 | 71.6% | 1.07 | $0.13 | $8.83 | 38.7% | 0.77 | 0.25 | 0.35 | 3 |
| BLIND_NEXT_OPEN | F80 | 69 | 75.4% | 1.10 | $0.19 | $13.44 | 39.9% | 0.80 | 0.24 | 0.32 | 3 |
| SAME_BAR_REJECTION_NEXT_OPEN | F65 | 23 | 69.6% | 0.93 | $-0.18 | $-4.14 | 13.3% | 0.71 | 0.14 | 0.51 | 2 |
| SAME_BAR_REJECTION_NEXT_OPEN | F67.5 | 26 | 73.1% | 1.05 | $0.10 | $2.65 | 15.0% | 0.72 | 0.16 | 0.41 | 3 |
| SAME_BAR_REJECTION_NEXT_OPEN | F70 | 31 | 64.5% | 0.77 | $-0.62 | $-19.24 | 17.9% | 0.74 | 0.20 | 0.32 | 3 |
| SAME_BAR_REJECTION_NEXT_OPEN | F72.5 | 33 | 69.7% | 1.03 | $0.06 | $2.04 | 19.1% | 0.77 | 0.25 | 0.35 | 3 |
| SAME_BAR_REJECTION_NEXT_OPEN | F75 | 31 | 67.7% | 0.81 | $-0.46 | $-14.14 | 17.9% | 0.79 | 0.26 | 0.32 | 3 |
| SAME_BAR_REJECTION_NEXT_OPEN | F77.5 | 30 | 76.7% | 1.05 | $0.10 | $3.06 | 17.3% | 0.81 | 0.23 | 0.31 | 1 |
| SAME_BAR_REJECTION_NEXT_OPEN | F80 | 33 | 75.8% | 0.67 | $-0.84 | $-27.87 | 19.1% | 0.83 | 0.23 | 0.29 | 3 |
| EARLY_RECLAIM_NEXT_OPEN | F65 | 45 | 71.1% | 1.42 | $0.84 | $37.92 | 26.0% | 0.70 | 0.20 | 0.42 | 2 |
| EARLY_RECLAIM_NEXT_OPEN | F67.5 | 48 | 72.9% | 1.52 | $0.92 | $44.00 | 27.7% | 0.71 | 0.16 | 0.40 | 2 |
| EARLY_RECLAIM_NEXT_OPEN | F70 | 52 | 71.2% | 1.16 | $0.33 | $17.27 | 30.1% | 0.74 | 0.13 | 0.36 | 3 |
| EARLY_RECLAIM_NEXT_OPEN | F72.5 | 53 | 71.7% | 1.25 | $0.48 | $25.40 | 30.6% | 0.77 | 0.18 | 0.35 | 3 |
| EARLY_RECLAIM_NEXT_OPEN | F75 | 54 | 74.1% | 1.07 | $0.15 | $8.00 | 31.2% | 0.80 | 0.22 | 0.34 | 3 |
| EARLY_RECLAIM_NEXT_OPEN | F77.5 | 56 | 78.6% | 1.11 | $0.20 | $10.94 | 32.4% | 0.81 | 0.19 | 0.31 | 3 |
| EARLY_RECLAIM_NEXT_OPEN | F80 | 59 | 79.7% | 1.04 | $0.08 | $4.67 | 34.1% | 0.84 | 0.18 | 0.30 | 3 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F65 | 19 | 78.9% | 1.53 | $0.83 | $15.76 | 11.0% | 0.69 | 0.15 | 0.43 | 1 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F67.5 | 22 | 77.3% | 1.79 | $1.14 | $25.13 | 12.7% | 0.74 | 0.19 | 0.41 | 2 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F70 | 21 | 71.4% | 0.97 | $-0.06 | $-1.22 | 12.1% | 0.79 | 0.18 | 0.33 | 4 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F72.5 | 25 | 76.0% | 1.16 | $0.31 | $7.83 | 14.5% | 0.79 | 0.18 | 0.32 | 4 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F75 | 26 | 73.1% | 0.92 | $-0.17 | $-4.37 | 15.0% | 0.80 | 0.20 | 0.30 | 3 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F77.5 | 26 | 69.2% | 0.89 | $-0.26 | $-6.79 | 15.0% | 0.82 | 0.22 | 0.30 | 2 |
| NEXT_BAR_CONFIRM_NEXT_OPEN | F80 | 17 | 82.4% | 1.52 | $0.72 | $12.30 | 9.8% | 0.83 | 0.23 | 0.30 | 2 |

## Development plateau selection

Frozen development winner: **EARLY_RECLAIM_NEXT_OPEN / F67.5**, qualifying adjacent depth **F65**.
Robustness PF floor: **1.42**; robustness expectancy floor: **$0.84**.

### Frozen winner across partitions

| Partition | Depth | N | WR | PF | Exp | Net | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | F65 | 28 | 67.9% | 0.99 | $-0.04 | $-1.00 | 3 |
| external | F67.5 | 31 | 67.7% | 1.15 | $0.40 | $12.32 | 2 |
| development | F65 | 45 | 71.1% | 1.42 | $0.84 | $37.92 | 2 |
| development | F67.5 | 48 | 72.9% | 1.52 | $0.92 | $44.00 | 2 |
| reference_validation | F65 | 26 | 61.5% | 0.86 | $-0.43 | $-11.11 | 3 |
| reference_validation | F67.5 | 23 | 65.2% | 1.02 | $0.05 | $1.05 | 2 |
| august | F65 | 1 | 0.0% | 0.00 | $-5.69 | $-5.69 | 1 |
| august | F67.5 | 1 | 0.0% | 0.00 | $-6.37 | $-6.37 | 1 |

Validation center: **FAIL**; validation neighbor: **PASS** (F65:FAIL;F70:PASS).

## Diagnostic confirmation-close executions (not selectable)

| Partition | Mode | Depth | N | WR | PF | Exp | Net |
|---|---|---:|---:|---:|---:|---:|---:|

**Status: ETH_LONG_ENTRY_OPTIMIZATION_E2_VALIDATION_FAILED**

Research only; no live changes.
