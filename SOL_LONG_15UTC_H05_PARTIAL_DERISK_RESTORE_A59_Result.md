# SOL LONG 15:00 UTC H05 Partial De-risk + H10 Restore — A59 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A59 tests exactly one preregistered executable hybrid: first POST_H05 completed warning -> cut 50% at next 5m open -> if the still-live trade later closes above H+0.10R, restore the removed 50% at the next 5m open. No ratio or threshold sweep is used.

## Reconciliation

Frozen parent counts and winner counts reconcile at 601/281/337 and 244/115/150. BASELINE replay is exact trade-by-trade within tolerance, and A59 management does not alter the parent structural terminal/target timestamp or reason.

## Economics

| Partition | Variant | WR | PF | Exp | Net | DD | Loss streak | Week+ | 5bps WR | 5bps PF | 5bps Exp | 5bps Net | 5bps DD | 5bps streak | 5bps Week+ | Cuts | Restores | Restore/cut | Winner cut/restored | Loss cut/restored | Winner Δ | Loss Δ | Total Δ | 5bps Δ |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASELINE | 40.6% | 1.28 | $0.56 | $338.91 | $148.06 | 10 | 59.5% | 40.3% | 1.14 | $0.31 | $188.66 | $168.56 | 10 | 55.1% | 0 | 0 | - | 0/0 | 0/0 | $0.00 | $0.00 | $0.00 | $0.00 |
| development | A59_H05_HALF_RESTORE_H10 | 46.9% | 1.33 | $0.62 | $374.10 | $138.45 | 9 | 60.1% | 41.4% | 1.18 | $0.36 | $215.47 | $160.20 | 10 | 57.0% | 219 | 67 | 30.6% | 37/29 | 182/38 | $-56.03 | $91.22 | $35.19 | $26.81 |
| external | BASELINE | 40.9% | 1.55 | $1.49 | $419.82 | $130.72 | 10 | 66.2% | 40.6% | 1.43 | $1.24 | $349.57 | $145.22 | 10 | 66.2% | 0 | 0 | - | 0/0 | 0/0 | $0.00 | $0.00 | $0.00 | $0.00 |
| external | A59_H05_HALF_RESTORE_H10 | 48.0% | 1.49 | $1.29 | $361.25 | $132.09 | 8 | 63.2% | 43.8% | 1.36 | $1.01 | $282.75 | $147.22 | 10 | 63.2% | 148 | 66 | 44.6% | 38/33 | 110/33 | $-92.14 | $33.56 | $-58.57 | $-66.82 |
| reference_validation | BASELINE | 44.5% | 1.57 | $0.78 | $263.33 | $64.85 | 14 | 66.3% | 43.9% | 1.35 | $0.53 | $179.08 | $77.85 | 14 | 61.4% | 0 | 0 | - | 0/0 | 0/0 | $0.00 | $0.00 | $0.00 | $0.00 |
| reference_validation | A59_H05_HALF_RESTORE_H10 | 51.0% | 1.61 | $0.78 | $262.30 | $59.21 | 11 | 67.5% | 44.8% | 1.36 | $0.51 | $172.68 | $71.15 | 14 | 65.1% | 138 | 43 | 31.2% | 32/26 | 106/17 | $-37.28 | $36.26 | $-1.03 | $-6.40 |

## Development six-block deltas

| Block | N | Raw ΔNet | 5bps ΔNet | Cuts | Restores |
|---:|---:|---:|---:|---:|---:|
| 1 | 85 | $-0.43 | $-2.05 | 36 | 13 |
| 2 | 105 | $5.52 | $4.14 | 39 | 11 |
| 3 | 111 | $17.71 | $16.71 | 38 | 8 |
| 4 | 94 | $4.27 | $3.27 | 30 | 8 |
| 5 | 103 | $12.93 | $11.56 | 41 | 11 |
| 6 | 103 | $-4.81 | $-6.81 | 35 | 16 |

Positive Development blocks: **4/6 raw**, **4/6 stress**.

## Frozen gate decision

| Partition | Gate | Details |
|---|---:|---|
| Development | PASS | raw_net=PASS, stress_net=PASS, raw_pf=PASS, stress_pf=PASS, stress_wr=PASS, raw_dd=PASS, raw_blocks=PASS, stress_blocks=PASS |
| External | fail | raw_net=fail, stress_net=fail, raw_pf=fail, stress_pf=fail, stress_wr=PASS, raw_dd=fail |
| Reference Validation | fail | raw_net=fail, stress_net=fail, raw_pf=PASS, stress_pf=PASS, stress_wr=PASS, raw_dd=PASS |

## Decision

**Status: SOL_LONG_15UTC_H05_PARTIAL_DERISK_RESTORE_A59_DEVELOPMENT_ONLY**

The hybrid passes Development but fails at least one OOS confirmation gate; it is not authorized for live promotion.

Research only. Live Baba Bot remains unchanged.
