# B27BX — BTC Four Fixed H1 Hours × Causal 24H BULL LOW_REJECT — Result

**Audit status: PASS.** Directional anatomy only; no TP/SL/RR/fee or live-rule optimization.

Raw BTCUSDT 5m identity: **698,112 rows / 100.0000% coverage**.

Fixed hours: **11:00 / 15:00 / 01:00 / 02:00 WIB**. Event = 1H LOW_REJECT versus the exact completed prior3H range. Primary filter = latest causally available 24H regime is **BULL** at event completion.

## Major-partition pooled four-hour readout

| Partition | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | BULL lift | BULL mean +3H return |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 412 | 56.3% | 202 | 52.0% | 56.4% | +0.1pp | 0.1% |
| development | 532 | 61.8% | 213 | 54.5% | 62.4% | +0.6pp | 0.1% |
| reference_validation | 278 | 59.0% | 114 | 52.6% | 50.0% | -9.0pp | -0.1% |

## Pooled readout

| Pool | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | Lift |
|---|---:|---:|---:|---:|---:|---:|
| POOLED_OOS | 690 | 57.4% | 316 | 52.2% | 54.1% | -3.3pp |
| POOLED_MAJOR | 1222 | 59.3% | 529 | 53.1% | 57.5% | -1.9pp |

## Per-hour pooled OOS

| WIB hour | Control N | Control +3H | BULL N | BULL +1H | BULL +3H | Lift |
|---|---:|---:|---:|---:|---:|---:|
| 11:00 | 192 | 55.2% | 82 | 57.3% | 53.7% | -1.5pp |
| 15:00 | 179 | 54.7% | 83 | 55.4% | 51.8% | -2.9pp |
| 01:00 | 155 | 61.3% | 76 | 55.3% | 57.9% | -3.4pp |
| 02:00 | 164 | 59.1% | 75 | 40.0% | 53.3% | -5.8pp |

## Frozen support gate

- Pooled-OOS BULL N >=40: **PASS**.
- Pooled-OOS BULL +3H >=65%: **FAIL**.
- External and validation BULL +3H each >=60%: **FAIL**.
- Positive BULL-vs-control lift in pooled OOS + external + validation: **FAIL**.
- At least 3/4 hours have OOS BULL N>=10 and +3H >50%: **PASS** (4/4).

**Frozen verdict: `B27BX_FOUR_HOUR_BULL_LOW_REJECT_NOT_SUPPORTED`.**

A supported result would only justify a separately preregistered execution experiment.

Research only. Live BBC unchanged.
