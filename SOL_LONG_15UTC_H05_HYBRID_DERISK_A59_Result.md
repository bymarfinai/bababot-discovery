# SOL LONG 15:00 UTC H05 Hybrid De-risk + H10 Re-arm — A59 Result

Frozen SOLUSDT 5m coverage: **99.7671%**.

A59 tests one preregistered nonlinear response only: first live H05 warning -> cut 50% next open -> restore that 50% only after a later completed close > H+0.10R, executed next open. One cut / one re-arm maximum. No fraction or threshold sweep.

## Parent reconciliation

Development parent replay: **601/601 exact PnL/timestamp parity**; winner count **244**.

External / Reference Validation opened only after Development passed: **281 / 337** rows reconciled.

## Economics

| Partition | Variant | WR | PF | Net | Exp | DD | Streak | 5bps WR | 5bps PF | 5bps Net | De-risk | Re-arm | Re-arm rate | Winner de-risk | Loser de-risk | Winner Δ | Loser Δ | ΔNet | 5bps ΔNet |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASELINE | 40.6% | 1.28 | $338.91 | $0.56 | $148.06 | 10 | 40.3% | 1.14 | $188.66 | 0 | 0 | - | 0 | 0 | $0.00 | $0.00 | $0.00 | $0.00 |
| development | HYB50_H05_H10_REARM | 46.9% | 1.33 | $374.10 | $0.62 | $138.45 | 9 | 41.4% | 1.18 | $215.47 | 219 | 67 | 30.6% | 37 | 182 | $-56.03 | $91.22 | $35.19 | $26.81 |
| external | BASELINE | 40.9% | 1.55 | $419.82 | $1.49 | $130.72 | 10 | 40.6% | 1.43 | $349.57 | 0 | 0 | - | 0 | 0 | $0.00 | $0.00 | $0.00 | $0.00 |
| external | HYB50_H05_H10_REARM | 48.0% | 1.49 | $361.25 | $1.29 | $132.09 | 8 | 43.8% | 1.36 | $282.75 | 148 | 66 | 44.6% | 38 | 110 | $-92.14 | $33.56 | $-58.57 | $-66.82 |
| reference_validation | BASELINE | 44.5% | 1.57 | $263.33 | $0.78 | $64.85 | 14 | 43.9% | 1.35 | $179.08 | 0 | 0 | - | 0 | 0 | $0.00 | $0.00 | $0.00 | $0.00 |
| reference_validation | HYB50_H05_H10_REARM | 51.0% | 1.61 | $262.30 | $0.78 | $59.21 | 11 | 44.8% | 1.36 | $172.68 | 138 | 43 | 31.2% | 32 | 106 | $-37.28 | $36.26 | $-1.03 | $-6.40 |

## Development six-block deltas

| Block | N | Raw ΔNet | 5bps ΔNet |
|---:|---:|---:|---:|
| 1 | 85 | $-0.43 | $-2.05 |
| 2 | 105 | $5.52 | $4.14 |
| 3 | 111 | $17.71 | $16.71 |
| 4 | 94 | $4.27 | $3.27 |
| 5 | 103 | $12.93 | $11.56 |
| 6 | 103 | $-4.81 | $-6.81 |

Positive Development blocks: **4/6 raw**, **4/6 stress**.

Development gate: **PASS**.

## OOS confirmation

| Partition | Gate |
|---|---:|
| External | FAIL |
| Reference Validation | FAIL |

## Decision

**Status: SOL_LONG_15UTC_H05_HYBRID_DERISK_A59_REJECTED_OOS**

A59 judges economics, not WR aesthetics. Rejection does not authorize a posthoc size-fraction sweep or H05/H10 retuning.

Research only. Live Baba Bot remains unchanged.
