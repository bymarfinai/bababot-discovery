# B27CL — BTC 24H F05 State-Machine Trade Management — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** Exact eligible B27CE source identity/outcomes reproduced. One preregistered state machine only; no clock/regime exclusion.

Configuration: F05 entry; favorable L touch -> next-bar BE; genuine close>H -> full structural SL; confirmed rebreak -> T5/T7.5/T10 staircase; T10 -> F85-style strict 3-bar pivot-high runner. $500 notional, $0.40 fee.

## Six-clock untouched OOS economics — first

| UTC / WIB | N | WR | PF | Exp/trade | Net | Full SL | BE | Intermediate | T10+runner | Time |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-04 / 07-11 | 59 | 37.3% | 0.28 | $-1.20 | $-70.61 | 4 | 21 | 3 | 21 | 10 |
| 04-08 / 11-15 | 58 | 44.8% | 2.54 | $+0.99 | $+57.50 | 0 | 17 | 9 | 21 | 11 |
| 08-12 / 15-19 | 64 | 31.2% | 0.78 | $-0.21 | $-13.53 | 2 | 24 | 4 | 15 | 19 |
| 12-16 / 19-23 | 71 | 36.6% | 0.40 | $-0.61 | $-43.24 | 5 | 31 | 5 | 20 | 10 |
| 16-20 / 23-03 | 52 | 28.8% | 0.15 | $-1.60 | $-83.05 | 1 | 20 | 7 | 9 | 15 |
| 20-00 / 03-07 | 51 | 33.3% | 0.68 | $-0.31 | $-15.80 | 2 | 15 | 4 | 15 | 15 |

## Major partitions and pools

| Scope | Source | Trades | Fill | WR | PF | Exp | Net | Avg win | Avg loss | Max DD | Streak | Full SL | BE | L-lock | T5-lock | T10-lock | Runner | Time | Rebreak | T5 | T7.5 | T10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 202 | 183 | 90.6% | 39.9% | 0.69 | $-0.44 | $-80.74 | $+2.49 | $-2.39 | $+140.76 | 11 | 6 | 67 | 11 | 7 | 46 | 8 | 38 | 99 | 74 | 63 | 55 |
| development | 333 | 297 | 89.2% | 32.7% | 0.36 | $-0.59 | $-175.74 | $+1.03 | $-1.38 | $+177.70 | 11 | 19 | 107 | 15 | 10 | 76 | 10 | 60 | 159 | 116 | 101 | 91 |
| reference_validation | 194 | 172 | 88.7% | 30.8% | 0.42 | $-0.51 | $-87.99 | $+1.23 | $-1.29 | $+94.28 | 7 | 8 | 61 | 6 | 8 | 42 | 5 | 42 | 89 | 64 | 58 | 50 |
| POOLED_OOS | 396 | 355 | 89.6% | 35.5% | 0.59 | $-0.48 | $-168.74 | $+1.96 | $-1.82 | $+169.16 | 11 | 14 | 128 | 17 | 15 | 88 | 13 | 80 | 188 | 138 | 121 | 105 |
| POOLED_MAJOR | 729 | 652 | 89.4% | 34.2% | 0.50 | $-0.53 | $-344.48 | $+1.55 | $-1.61 | $+344.90 | 11 | 33 | 235 | 32 | 25 | 164 | 23 | 140 | 347 | 254 | 222 | 196 |

## Per 100 filled entries

| Scope | Full SL | Scratch/BE | Intermediate lock | T10-or-runner family | Other time exit | Non-full-SL |
|---|---:|---:|---:|---:|---:|---:|
| external | 3.3 | 36.6 | 9.8 | 30.1 | 20.2 | 96.7% |
| development | 6.4 | 36.0 | 8.4 | 30.6 | 18.5 | 93.6% |
| reference_validation | 4.7 | 35.5 | 8.1 | 29.1 | 22.7 | 95.3% |
| POOLED_OOS | 3.9 | 36.1 | 9.0 | 29.6 | 21.4 | 96.1% |
| POOLED_MAJOR | 5.1 | 36.0 | 8.7 | 30.1 | 20.1 | 94.9% |

## Frozen gate

- positive economics/PF gate across all major partitions + OOS: **FAIL**
- OOS full structural SL share <=10%: **PASS**
- HIGH_QUALITY_70 economic WR: **FAIL**

**Frozen verdict: `B27CL_STATE_MACHINE_ECON_NOT_SUPPORTED`.**

Research only; live BBC unchanged.
