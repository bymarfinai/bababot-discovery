# B27BY — BTC 24H Adaptive F15 Pre-Second-Low SHORT — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Exact persisted B27BE K1+OPP0 identities were reused. This is a direct F15 transfer test; no fraction search, session filter, regime filter, stop, target, fee, PF, PnL, or live change was used.

Adaptive entry: **F15 = previous completed 4H Low + 0.15 × (High − Low)** after a completed causal leave from Low Touch #1 and strictly before Low Arrival #2.

## Major-partition transfer

| Partition | K1 OPP0 | Clean leave | F15 fills | Fill/clean | L2 hits | L2/fill | Median fill->L2 |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 862 | 641 | 441 | 68.8% | 288 | 65.3% | 20.0m |
| development | 1264 | 907 | 589 | 64.9% | 414 | 70.3% | 20.0m |
| reference_validation | 641 | 405 | 228 | 56.3% | 157 | 68.9% | 20.0m |

## Pooled readout

| Pool | K1 OPP0 | Clean leave | F15 fills | Fill/clean | L2/fill | Median fill->L2 |
|---|---:|---:|---:|---:|---:|---:|
| POOLED_OOS | 1503 | 1046 | 669 | 64.0% | 66.5% | 20.0m |
| POOLED_MAJOR | 2767 | 1953 | 1258 | 64.4% | 68.3% | 20.0m |

## Regime diagnostics — pooled major

| Regime | K1 OPP0 | F15 fills | L2/fill | Median fill->L2 |
|---|---:|---:|---:|---:|
| BULL | 1146 | 530 | 68.7% | 20.0m |
| BEAR | 1122 | 487 | 69.4% | 20.0m |
| SIDEWAYS | 499 | 241 | 65.1% | 20.0m |

## Clock diagnostics — pooled major

| UTC block | K1 OPP0 | F15 fills | L2/fill | Median fill->L2 |
|---|---:|---:|---:|---:|
| 00-04 | 444 | 187 | 68.4% | 15.0m |
| 04-08 | 455 | 212 | 64.6% | 30.0m |
| 08-12 | 476 | 218 | 68.3% | 20.0m |
| 12-16 | 557 | 243 | 74.1% | 15.0m |
| 16-20 | 461 | 224 | 68.3% | 20.0m |
| 20-00 | 374 | 174 | 64.4% | 20.0m |

## Frozen gates

- F15 transfer gate across external/development/reference_validation: **FAIL**.
- Six-clock full-24H stability gate: **FAIL**.
- BULL/BEAR/SIDEWAYS pooled-major stability gate: **PASS**.

**Frozen verdict: `B27BY_F15_NOT_SUPPORTED`.**

A structural pass only permits a separately preregistered economic experiment. L2 is a structural milestone, not a TP.

Research only. Live BBC unchanged.
