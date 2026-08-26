# ETH LONG B27DE-Adapt — Generic F75 LONG Clock-Rotation Scan — Result

ETHUSDT 5m rows: **698,112**; coverage: **100.0000%**.

Clock-only scan: 48 half-hour reference starts, 5h30 reference + 6h30 execution. ETH-specific F75 EARLY_RECLAIM + E10/F15 is frozen; no 4H regime filter.

## London parity

| Partition | Expected N | Got N | Missing | Extra | WR | PF | Exp | Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 40 | 40 | 0 | 0 | 72.5% | 1.21 | $0.50 | $20.02 |
| development | 54 | 54 | 0 | 0 | 74.1% | 1.07 | $0.15 | $8.00 |
| reference_validation | 28 | 28 | 0 | 0 | 71.4% | 1.02 | $0.06 | $1.75 |
| august | 2 | 2 | 0 | 0 | 50.0% | 0.76 | $-0.74 | $-1.47 |

**London parity: PASS.**

## Development leaderboard — top 12

| Clock | N | WR | PF | Exp | Net | Eligible |
|---|---:|---:|---:|---:|---:|---|
| 04:00 | 79 | 83.5% | 2.22 | $0.99 | $77.91 | YES |
| 10:00 | 39 | 76.9% | 1.99 | $1.08 | $41.97 | YES |
| 05:30 | 72 | 76.4% | 1.95 | $0.93 | $66.82 | YES |
| 04:30 | 86 | 79.1% | 1.91 | $0.80 | $68.88 | YES |
| 05:00 | 82 | 75.6% | 1.83 | $0.89 | $72.70 | YES |
| 03:30 | 81 | 74.1% | 1.52 | $0.59 | $47.43 | YES |
| 03:00 | 82 | 73.2% | 1.32 | $0.37 | $30.55 | YES |
| 11:00 | 37 | 64.9% | 2.54 | $1.51 | $55.76 | NO |
| 22:30 | 52 | 69.2% | 1.62 | $0.58 | $30.05 | NO |
| 16:00 | 43 | 60.5% | 1.33 | $0.40 | $17.40 | NO |
| 12:00 | 31 | 64.5% | 1.32 | $0.46 | $14.28 | NO |
| 11:30 | 27 | 66.7% | 1.27 | $0.47 | $12.82 | NO |

## Selected development clock

**04:00 UTC reference start** — development N=79, WR=83.5%, PF=2.22, exp=$0.99, net=$77.91.
- external: N=33, WR=81.8%, PF=2.91, exp=$2.11, net=$69.68.
- reference_validation: N=32, WR=75.0%, PF=1.56, exp=$0.69, net=$22.14.

**Status: ETH_LONG_B27DE_ADAPT_HISTORICAL_REPLICATION_SUPPORTED**

Historical replication uses reused partitions and is not pristine OOS. Research only; no live changes.
