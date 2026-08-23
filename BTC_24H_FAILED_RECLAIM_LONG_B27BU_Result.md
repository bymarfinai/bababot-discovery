# B27BU — BTC 24H BEAR-Origin Failed-Reclaim LONG Economics — Result

**Audit status: PASS.** Entry is the next raw 5m open after B27BT causal re-break confirmation; no eventual regime outcome or containing 4H final close is used for entry or risk geometry.

Frozen B27BT BEAR FAILED_RECLAIM identity reproduced exactly: **34 signals = external 6 + development 20 + reference_validation 8; pooled OOS 14.**

Economics: **$500 notional, $0.40 round-trip fee**. One frozen structural stop (`LOCAL_LOW`) and targets 1R / 1.5R / 2R.

## Major-partition economics

| Target | Partition | N | WR | PF | Exp/trade | Total net | TP | SL | Regime exit | 24h exit |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| R1_0 | external | 6 | 66.7% | 3.29 | $+0.69 | $+4.17 | 4 | 2 | 0 | 0 |
| R1_0 | development | 20 | 45.0% | 0.51 | $-0.56 | $-11.30 | 10 | 9 | 1 | 0 |
| R1_0 | reference_validation | 8 | 62.5% | 0.78 | $-0.24 | $-1.95 | 4 | 3 | 1 | 0 |
| R1_5 | external | 6 | 50.0% | 2.01 | $+0.65 | $+3.88 | 3 | 3 | 0 | 0 |
| R1_5 | development | 20 | 40.0% | 0.49 | $-0.72 | $-14.36 | 8 | 11 | 1 | 0 |
| R1_5 | reference_validation | 8 | 50.0% | 0.51 | $-0.74 | $-5.88 | 3 | 4 | 1 | 0 |
| R2_0 | external | 6 | 50.0% | 2.78 | $+1.14 | $+6.86 | 3 | 3 | 0 | 0 |
| R2_0 | development | 20 | 40.0% | 0.69 | $-0.43 | $-8.67 | 8 | 11 | 1 | 0 |
| R2_0 | reference_validation | 8 | 50.0% | 0.61 | $-0.58 | $-4.61 | 3 | 4 | 1 | 0 |

## Pooled readout

| Target | Pool | N | WR | PF | Exp/trade | Total net | Median risk | Median hold |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| R1_0 | POOLED_OOS | 14 | 64.3% | 1.21 | $+0.16 | $+2.22 | 0.3% | 20m |
| R1_0 | POOLED_MAJOR | 34 | 52.9% | 0.73 | $-0.27 | $-9.08 | 0.3% | 18m |
| R1_5 | POOLED_OOS | 14 | 50.0% | 0.87 | $-0.14 | $-2.00 | 0.3% | 35m |
| R1_5 | POOLED_MAJOR | 34 | 44.1% | 0.63 | $-0.48 | $-16.36 | 0.3% | 20m |
| R2_0 | POOLED_OOS | 14 | 50.0% | 1.14 | $+0.16 | $+2.25 | 0.3% | 40m |
| R2_0 | POOLED_MAJOR | 34 | 44.1% | 0.85 | $-0.19 | $-6.42 | 0.3% | 32m |

## Outcome diagnostic — pooled major

| Target | Outcome | N | WR | PF | Exp/trade | Total net |
|---|---|---:|---:|---:|---:|---:|
| R1_0 | TRANSITION | 22 | 50.0% | 0.75 | $-0.25 | $-5.50 |
| R1_0 | RESUME | 12 | 58.3% | 0.69 | $-0.30 | $-3.57 |
| R1_5 | TRANSITION | 22 | 45.5% | 0.77 | $-0.29 | $-6.28 |
| R1_5 | RESUME | 12 | 41.7% | 0.41 | $-0.84 | $-10.08 |
| R2_0 | TRANSITION | 22 | 45.5% | 1.02 | $+0.03 | $+0.63 |
| R2_0 | RESUME | 12 | 41.7% | 0.59 | $-0.59 | $-7.06 |

## Frozen selection gate

| Target | N>=5 each | Exp>0 each | PF>=1.20 each | WR>=50% each | ROBUST_PASS | HIGH_QUALITY_70 | Min PF | Selected |
|---|---|---|---|---|---|---|---:|---|
| R1_0 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.51 | NO |
| R1_5 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.49 | NO |
| R2_0 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.61 | NO |

**Frozen verdict: `B27BU_BEAR_FAILED_RECLAIM_LONG_NOT_SUPPORTED`.**

Interpretation: this is an economic screen of the already-inspected B27BT lineage. A pass would still require a separate frequency/portfolio/live-readiness step before any BBC production change.

Research only. Live BBC unchanged.
