# B27BW — BTC 24H BEAR-Origin Failed-Reclaim Widened-Risk Economics — Result

**Audit status: PASS.** Same B27BT causal signal and next-5m-open entry; only the two preregistered B27BV-derived widened risk envelopes are tested.

Signal identity reproduced exactly: **34 = external 6 + development 20 + reference_validation 8; pooled OOS 14.**

Economics: **$500 notional, $0.40 round-trip fee**. Stops: S2/S3 local-R; targets: 1R/1.5R/2R of actual widened risk.

## Major-partition economics

| Variant | Partition | N | WR | PF | Exp/trade | Total net | TP | SL | Regime exit | 24h exit | Median risk |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| S2_T1_0 | external | 6 | 50.0% | 1.65 | $+0.70 | $+4.21 | 3 | 3 | 0 | 0 | 0.6% |
| S2_T1_0 | development | 20 | 45.0% | 0.55 | $-0.97 | $-19.44 | 9 | 9 | 2 | 0 | 0.6% |
| S2_T1_0 | reference_validation | 8 | 75.0% | 1.32 | $+0.39 | $+3.12 | 5 | 1 | 2 | 0 | 0.6% |
| S2_T1_5 | external | 6 | 33.3% | 1.30 | $+0.49 | $+2.92 | 2 | 4 | 0 | 0 | 0.6% |
| S2_T1_5 | development | 20 | 40.0% | 0.77 | $-0.52 | $-10.46 | 8 | 10 | 2 | 0 | 0.6% |
| S2_T1_5 | reference_validation | 8 | 50.0% | 0.62 | $-0.69 | $-5.52 | 2 | 3 | 3 | 0 | 0.6% |
| S2_T2_0 | external | 6 | 33.3% | 1.76 | $+1.24 | $+7.42 | 2 | 4 | 0 | 0 | 0.6% |
| S2_T2_0 | development | 20 | 35.0% | 0.56 | $-1.06 | $-21.18 | 5 | 10 | 5 | 0 | 0.6% |
| S2_T2_0 | reference_validation | 8 | 50.0% | 0.70 | $-0.55 | $-4.39 | 2 | 3 | 3 | 0 | 0.6% |
| S3_T1_0 | external | 6 | 66.7% | 2.78 | $+1.97 | $+11.79 | 4 | 2 | 0 | 0 | 0.9% |
| S3_T1_0 | development | 20 | 50.0% | 1.16 | $+0.28 | $+5.64 | 9 | 4 | 7 | 0 | 0.9% |
| S3_T1_0 | reference_validation | 8 | 50.0% | 0.49 | $-1.21 | $-9.65 | 2 | 3 | 3 | 0 | 1.0% |
| S3_T1_5 | external | 6 | 66.7% | 2.58 | $+1.74 | $+10.47 | 2 | 2 | 2 | 0 | 0.9% |
| S3_T1_5 | development | 20 | 35.0% | 0.67 | $-0.73 | $-14.53 | 4 | 6 | 10 | 0 | 0.9% |
| S3_T1_5 | reference_validation | 8 | 50.0% | 0.58 | $-0.99 | $-7.95 | 2 | 3 | 3 | 0 | 1.0% |
| S3_T2_0 | external | 6 | 66.7% | 3.13 | $+2.34 | $+14.06 | 2 | 2 | 2 | 0 | 0.9% |
| S3_T2_0 | development | 20 | 35.0% | 0.72 | $-0.61 | $-12.24 | 3 | 6 | 11 | 0 | 0.9% |
| S3_T2_0 | reference_validation | 8 | 50.0% | 0.67 | $-0.78 | $-6.25 | 2 | 3 | 3 | 0 | 1.0% |

## Pooled readout

| Variant | Pool | N | WR | PF | Exp/trade | Total net | Median risk | Median hold |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| S2_T1_0 | POOLED_OOS | 14 | 64.3% | 1.45 | $+0.52 | $+7.33 | 0.6% | 58m |
| S2_T1_0 | POOLED_MAJOR | 34 | 52.9% | 0.80 | $-0.36 | $-12.10 | 0.6% | 70m |
| S2_T1_5 | POOLED_OOS | 14 | 42.9% | 0.89 | $-0.19 | $-2.60 | 0.6% | 98m |
| S2_T1_5 | POOLED_MAJOR | 34 | 41.2% | 0.81 | $-0.38 | $-13.06 | 0.6% | 118m |
| S2_T2_0 | POOLED_OOS | 14 | 42.9% | 1.12 | $+0.22 | $+3.04 | 0.6% | 112m |
| S2_T2_0 | POOLED_MAJOR | 34 | 38.2% | 0.75 | $-0.53 | $-18.14 | 0.6% | 132m |
| S3_T1_0 | POOLED_OOS | 14 | 57.1% | 1.08 | $+0.15 | $+2.14 | 0.9% | 192m |
| S3_T1_0 | POOLED_MAJOR | 34 | 52.9% | 1.13 | $+0.23 | $+7.78 | 0.9% | 232m |
| S3_T1_5 | POOLED_OOS | 14 | 57.1% | 1.10 | $+0.18 | $+2.52 | 0.9% | 258m |
| S3_T1_5 | POOLED_MAJOR | 34 | 44.1% | 0.83 | $-0.35 | $-12.01 | 0.9% | 318m |
| S3_T2_0 | POOLED_OOS | 14 | 57.1% | 1.31 | $+0.56 | $+7.81 | 0.9% | 258m |
| S3_T2_0 | POOLED_MAJOR | 34 | 44.1% | 0.94 | $-0.13 | $-4.43 | 0.9% | 318m |

## Outcome diagnostic — pooled major

| Variant | Outcome | N | WR | PF | Exp/trade | Total net |
|---|---|---:|---:|---:|---:|---:|
| S2_T1_0 | TRANSITION | 22 | 54.5% | 1.09 | $+0.14 | $+3.01 |
| S2_T1_0 | RESUME | 12 | 50.0% | 0.42 | $-1.26 | $-15.11 |
| S2_T1_5 | TRANSITION | 22 | 45.5% | 1.15 | $+0.26 | $+5.67 |
| S2_T1_5 | RESUME | 12 | 33.3% | 0.39 | $-1.56 | $-18.73 |
| S2_T2_0 | TRANSITION | 22 | 45.5% | 1.13 | $+0.22 | $+4.95 |
| S2_T2_0 | RESUME | 12 | 25.0% | 0.32 | $-1.92 | $-23.08 |
| S3_T1_0 | TRANSITION | 22 | 63.6% | 2.08 | $+1.32 | $+29.11 |
| S3_T1_0 | RESUME | 12 | 33.3% | 0.36 | $-1.78 | $-21.33 |
| S3_T1_5 | TRANSITION | 22 | 59.1% | 1.77 | $+1.01 | $+22.23 |
| S3_T1_5 | RESUME | 12 | 16.7% | 0.16 | $-2.85 | $-34.24 |
| S3_T2_0 | TRANSITION | 22 | 59.1% | 1.95 | $+1.24 | $+27.37 |
| S3_T2_0 | RESUME | 12 | 16.7% | 0.22 | $-2.65 | $-31.80 |

## Frozen selection gate

| Variant | N>=5 each | Exp>0 each | PF>=1.20 each | WR>=50% each | ROBUST_PASS | HIGH_QUALITY_70 | Min PF | Selected |
|---|---|---|---|---|---|---|---:|---|
| S2_T1_0 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.55 | NO |
| S2_T1_5 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.62 | NO |
| S2_T2_0 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.56 | NO |
| S3_T1_0 | PASS | FAIL | FAIL | PASS | NO | NO | 0.49 | NO |
| S3_T1_5 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.58 | NO |
| S3_T2_0 | PASS | FAIL | FAIL | FAIL | NO | NO | 0.67 | NO |

**Frozen verdict: `B27BW_FAILED_RECLAIM_WIDE_RISK_NOT_SUPPORTED`.**

A pass is still historical discovery evidence and would require a separate frequency/portfolio/live-readiness step before any BBC production change.

Research only. Live BBC unchanged.
