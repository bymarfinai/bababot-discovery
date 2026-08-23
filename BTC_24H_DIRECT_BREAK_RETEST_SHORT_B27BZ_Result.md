# B27BZ — BTC 24H Direct-Break Retest SHORT Anatomy — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Exact B27BE K1+OPP0 identities were reused. Direct path means first Low close-break occurs before any distinct Low #2. No session/regime filter, trading stop/TP, fee, PF, PnL, or live change was used.

Frozen continuation geometry: direct `close < L` -> first retest `high >= L` -> retest must complete `close <= L` -> from next 5m bar require `EXT15 = L - 0.15*(H-L)` before a completed reclaim `close > L`.

## Major partitions

| Partition | K1 OPP0 | Direct break | Direct rate | Retest | Retest/direct | Accepted | Accept/retest | EXT15 | EXT15/accepted | Break->retest | Accept->EXT15 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 862 | 420 | 48.7% | 372 | 88.6% | 170 | 45.7% | 99 | 58.2% | 0.0m | 0.0m |
| development | 1264 | 657 | 52.0% | 602 | 91.6% | 266 | 44.2% | 129 | 48.5% | 0.0m | 0.0m |
| reference_validation | 641 | 393 | 61.3% | 361 | 91.9% | 165 | 45.7% | 93 | 56.4% | 0.0m | 0.0m |

## Pooled readout

| Pool | K1 | Direct | Retest | Accepted | EXT15/accepted | Reclaim | Ambiguous | Unresolved |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| POOLED_OOS | 1503 | 813 | 733 | 335 | 57.3% | 122 | 18 | 3 |
| POOLED_MAJOR | 2767 | 1470 | 1335 | 601 | 53.4% | 232 | 40 | 8 |

## Regime diagnostics — pooled major

| Regime | Direct | Accepted | EXT15/accepted |
|---|---:|---:|---:|
| BULL | 609 | 245 | 50.2% |
| BEAR | 615 | 252 | 55.6% |
| SIDEWAYS | 246 | 104 | 55.8% |

## Clock diagnostics — pooled major

| UTC block | Direct | Accepted | EXT15/accepted |
|---|---:|---:|---:|
| 00-04 | 240 | 103 | 65.0% |
| 04-08 | 242 | 100 | 47.0% |
| 08-12 | 250 | 99 | 51.5% |
| 12-16 | 292 | 115 | 50.4% |
| 16-20 | 251 | 102 | 51.0% |
| 20-00 | 195 | 82 | 56.1% |

## Frozen gate

- Support gate: **FAIL**.
- High-quality >=70% in every major partition: **FAIL**.

**Frozen verdict: `B27BZ_DIRECT_BREAK_RETEST_NOT_SUPPORTED`.**

A structural pass only permits a separately preregistered economic experiment. Research only. Live BBC unchanged.
