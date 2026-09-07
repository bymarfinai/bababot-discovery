# SOL LONG 15:00 UTC Executable Failure Guard — A53 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A53 executes only the three A52-replicated standalone warnings at the next 5m open. No warning combination or threshold retuning is used.

## Reconciliation

Baseline replay parity: **1219/1219 trades exact within tolerance**; expected winner counts 244/115/150 reconciled.

## Economics by partition

| Partition | Guard | WR | PF | Net | DD | 5bps WR | 5bps PF | 5bps Net | Guard exits | Parent winners guarded | Winner flips | Winner ΔPnL | Loss ΔPnL | Total ΔNet |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | BASELINE | 40.6% | 1.28 | $338.91 | $148.06 | 40.3% | 1.14 | $188.66 | 0 | 0 (0.0%) | 0 | $0.00 | $0.00 | $0.00 |
| development | G1_PRE_L25 | 39.1% | 1.26 | $317.43 | $121.20 | 38.8% | 1.13 | $167.18 | 52 | 9 (3.7%) | 9 | $-116.38 | $94.90 | $-21.48 |
| development | G2_POST_H05 | 70.2% | 1.47 | $461.18 | $111.75 | 58.7% | 1.30 | $310.93 | 219 | 37 (15.2%) | 1 | $-198.43 | $320.69 | $122.26 |
| development | G3_POST_H10 | 78.4% | 1.46 | $432.90 | $122.02 | 68.7% | 1.29 | $282.65 | 300 | 69 (28.3%) | 1 | $-372.16 | $466.15 | $93.99 |
| external | BASELINE | 40.9% | 1.55 | $419.82 | $130.72 | 40.6% | 1.43 | $349.57 | 0 | 0 (0.0%) | 0 | $0.00 | $0.00 | $0.00 |
| external | G1_PRE_L25 | 39.5% | 1.46 | $360.91 | $134.91 | 39.1% | 1.35 | $290.66 | 19 | 4 (3.5%) | 4 | $-129.86 | $70.95 | $-58.91 |
| external | G2_POST_H05 | 78.3% | 1.57 | $326.37 | $100.25 | 70.1% | 1.43 | $256.12 | 148 | 38 (33.0%) | 2 | $-372.87 | $279.41 | $-93.46 |
| external | G3_POST_H10 | 85.8% | 1.44 | $237.21 | $115.80 | 78.6% | 1.30 | $166.96 | 192 | 62 (53.9%) | 2 | $-561.53 | $378.92 | $-182.61 |
| reference_validation | BASELINE | 44.5% | 1.57 | $263.33 | $64.85 | 43.9% | 1.35 | $179.08 | 0 | 0 (0.0%) | 0 | $0.00 | $0.00 | $0.00 |
| reference_validation | G1_PRE_L25 | 42.7% | 1.49 | $235.00 | $79.19 | 42.4% | 1.29 | $150.75 | 35 | 6 (4.0%) | 6 | $-66.32 | $37.99 | $-28.33 |
| reference_validation | G2_POST_H05 | 74.5% | 1.65 | $243.68 | $56.49 | 52.8% | 1.39 | $159.43 | 138 | 32 (21.3%) | 2 | $-142.93 | $123.28 | $-19.64 |
| reference_validation | G3_POST_H10 | 82.8% | 1.58 | $205.59 | $55.60 | 63.2% | 1.32 | $121.34 | 184 | 51 (34.0%) | 2 | $-235.43 | $177.69 | $-57.74 |

## Development six-block deltas

| Guard | +blocks raw | +blocks 5bps | B1 | B2 | B3 | B4 | B5 | B6 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| G1_PRE_L25 | 3/6 | 3/6 | $13.04 | $-16.88 | $-26.73 | $6.83 | $28.10 | $-25.83 |
| G2_POST_H05 | 5/6 | 5/6 | $30.16 | $11.78 | $31.35 | $3.48 | $46.83 | $-1.33 |
| G3_POST_H10 | 5/6 | 5/6 | $36.69 | $-17.59 | $19.42 | $0.27 | $40.08 | $15.13 |

## Frozen gate decision

| Guard | Dev | External | RefVal | Fully supported |
|---|---:|---:|---:|---:|
| G1_PRE_L25 | fail | fail | fail | no |
| G2_POST_H05 | PASS | fail | fail | no |
| G3_POST_H10 | PASS | fail | fail | no |

## Decision

Fully supported standalone guards: **none**.

**Status: SOL_LONG_15UTC_EXECUTABLE_GUARD_A53_REJECTED**

A53 is the executable economics test. A warning that was predictive in A52 is rejected here if winner sacrifice or realized execution destroys portfolio economics.

Research only. Live Baba Bot remains unchanged.
