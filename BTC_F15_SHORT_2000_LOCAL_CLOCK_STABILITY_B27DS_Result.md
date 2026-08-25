# B27DS — F15 SHORT 20:00 UTC Local Clock Stability — Result

5m rows: **698,112**; coverage: **100.0000%**.

**20:00 B27DR parity: PASS.**

## Development local-clock scan

| Ref | Exec | End | N | WR | PF | Exp | Net | H2/F15 | Eligible | Neighbor-support |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 20:00 | 01:30+1d | 08:00+1d | 19 | 78.9% | 3.99 | $2.08 | $39.46 | 69.0% | YES | YES |
| 20:10 | 01:40+1d | 08:10+1d | 25 | 72.0% | 3.05 | $1.66 | $41.45 | 72.9% | YES | YES |
| 20:20 | 01:50+1d | 08:20+1d | 25 | 68.0% | 2.06 | $1.08 | $26.90 | 69.8% | NO | YES |
| 20:30 | 02:00+1d | 08:30+1d | 28 | 60.7% | 1.47 | $0.65 | $18.21 | 65.5% | NO | NO |
| 19:50 | 01:20+1d | 07:50+1d | 24 | 66.7% | 1.35 | $0.60 | $14.35 | 66.0% | NO | YES |
| 19:40 | 01:10+1d | 07:40+1d | 18 | 66.7% | 1.14 | $0.16 | $2.96 | 66.7% | NO | NO |
| 19:30 | 01:00+1d | 07:30+1d | 19 | 42.1% | 0.28 | $-1.43 | $-27.20 | 57.7% | NO | NO |

## Selection

Selected clock: **20:00 UTC reference -> 01:30+1d-08:00+1d UTC execution**.
Development: N=19, WR=78.9%, PF=3.99, exp=$2.08, net=$39.46.
Immediate-neighbor local basin: **SUPPORTED**.
Historical external + reference-validation replication: **SUPPORTED**.

| Partition | N | WR | PF | Exp | Net | H2/F15 | TP |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 27 | 74.1% | 2.22 | $1.16 | $31.35 | 66.0% | 63.0% |
| development | 19 | 78.9% | 3.99 | $2.08 | $39.46 | 69.0% | 78.9% |
| reference_validation | 10 | 80.0% | 2.70 | $0.69 | $6.91 | 90.0% | 80.0% |
| august | 1 | 100.0% | inf | $1.24 | $1.24 | 100.0% | 100.0% |

### Pooled major selected clock

N=56, wins=43, WR=76.8%, PF=2.81, expectancy=$1.39, net=$77.73.

**Status: B27DS_LOCAL_BASIN_HISTORICAL_REPLICATION_SUPPORTED**

Evidence remains exploratory historical discovery; not pristine unseen OOS. Research only; live BBC unchanged.
