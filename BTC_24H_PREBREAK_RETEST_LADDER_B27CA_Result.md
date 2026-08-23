# B27CA — BTC 24H Pre-Break Retest Ladder + Adaptive Pre-L2 SHORT — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Structural anatomy only; no trading WR, PF, PnL, stop, TP, RR, fee, or live change.

## Retest ladder by clock — pooled major

| UTC block | K1 | Low break | Break after 1 visit | after 2 | after 3 | after 4+ | Genuine L2 | Break after L2 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | 444 | 72.1% | 75.0% | 19.7% | 5.0% | 0.3% | 99 | 80.8% |
| 04-08 | 455 | 72.3% | 73.6% | 20.7% | 4.9% | 0.9% | 115 | 75.7% |
| 08-12 | 476 | 68.1% | 77.2% | 16.7% | 5.6% | 0.6% | 109 | 67.9% |
| 12-16 | 557 | 72.4% | 72.5% | 21.3% | 5.7% | 0.5% | 153 | 72.5% |
| 16-20 | 461 | 72.5% | 75.1% | 20.4% | 2.4% | 2.1% | 111 | 74.8% |
| 20-00 | 374 | 67.9% | 76.8% | 16.9% | 5.5% | 0.8% | 91 | 64.8% |

## Fixed F15 — major partitions

| Partition | Fills | Break before genuine L2 | Genuine L2 | Break after L2 | Eventual Low break after fill |
|---|---:|---:|---:|---:|---:|
| external | 441 | 33.6% | 31.7% | 73.6% | 56.9% |
| development | 589 | 31.2% | 39.0% | 66.1% | 57.0% |
| reference_validation | 228 | 36.4% | 32.5% | 78.4% | 61.8% |

## Fixed F15 by clock — pooled major

| UTC block | Fills | Break before L2 | Genuine L2 | Break after L2 | Eventual break/fill |
|---|---:|---:|---:|---:|---:|
| 00-04 | 187 | 32.6% | 35.8% | 79.1% | 61.0% |
| 04-08 | 212 | 32.1% | 32.5% | 76.8% | 57.1% |
| 08-12 | 218 | 35.8% | 32.6% | 62.0% | 56.0% |
| 12-16 | 243 | 30.9% | 43.2% | 68.6% | 60.5% |
| 16-20 | 224 | 35.3% | 33.0% | 77.0% | 60.7% |
| 20-00 | 174 | 31.0% | 33.3% | 58.6% | 50.6% |

## Development-selected fraction per clock + untouched OOS readout

| UTC block | Selected | Dev fills | Dev break/fill | External fills | External break/fill | Validation fills | Validation break/fill |
|---|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | F05 | 54 | 68.5% | 31 | 77.4% | 24 | 66.7% |
| 04-08 | F05 | 52 | 67.3% | 47 | 68.1% | 29 | 79.3% |
| 08-12 | F10 | 85 | 58.8% | 62 | 61.3% | 39 | 66.7% |
| 12-16 | F05 | 67 | 64.2% | 48 | 72.9% | 25 | 64.0% |
| 16-20 | F05 | 79 | 74.7% | 30 | 66.7% | 37 | 62.2% |
| 20-00 | F05 | 43 | 67.4% | 32 | 50.0% | 23 | 69.6% |

## Adaptive vs fixed F15 — OOS aggregates

| Scope | Adaptive fills | Adaptive break/fill | Fixed F15 fills | Fixed F15 break/fill | Lift |
|---|---:|---:|---:|---:|---:|
| external | 250 | 66.0% | 441 | 56.9% | +9.1pp |
| reference_validation | 177 | 67.8% | 228 | 61.8% | +6.0pp |
| POOLED_OOS | 427 | 66.7% | 669 | 58.6% | +8.1pp |

**Frozen verdict: `B27CA_CLOCK_ADAPTIVE_CANDIDATE_SUPPORTED`.**

B27CA separates retest-count anatomy from pre-return entry geometry. Any supported structural candidate still requires a separately preregistered economic backtest.
