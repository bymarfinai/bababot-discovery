# B27BE — BTC 24H Causal 4H Regime SHORT Compatibility Atlas — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Exact B27AG causal 4H SwingRegime semantics were reused. All seven calendar days were included. The full BTC day was covered by six sequential 4H observation blocks, each using the immediately previous completed 4H range as frozen liquidity H/L.

No Asia/London/New-York session label, entry fraction, stop, target, runner, or confirmation rule was used in selection.

## Pooled-major regime atlas

| Regime | Blocks | K1 OPP0 | Low break | High break | No break | 2nd Low | Low break after 2nd |
|---|---:|---:|---:|---:|---:|---:|---:|
| BULL | 6690 | 1146 | 70.3% | 7.5% | 22.2% | 23.9% | 71.9% |
| BEAR | 5312 | 1122 | 72.3% | 6.7% | 21.0% | 24.4% | 71.5% |
| SIDEWAYS | 2407 | 499 | 69.5% | 6.4% | 24.0% | 26.1% | 77.7% |

## Major partitions by regime

| Regime | Partition | K1 OPP0 | Low break | 2nd Low | Low break after 2nd |
|---|---|---:|---:|---:|---:|
| BULL | external | 400 | 64.8% | 21.0% | 66.7% |
| BULL | development | 500 | 70.0% | 29.4% | 71.4% |
| BULL | reference_validation | 246 | 80.1% | 17.5% | 83.7% |
| BEAR | external | 203 | 66.0% | 26.1% | 69.8% |
| BEAR | development | 630 | 71.1% | 24.6% | 69.7% |
| BEAR | reference_validation | 289 | 79.2% | 22.8% | 77.3% |
| SIDEWAYS | external | 259 | 67.6% | 24.7% | 85.9% |
| SIDEWAYS | development | 134 | 70.9% | 28.4% | 60.5% |
| SIDEWAYS | reference_validation | 106 | 72.6% | 26.4% | 82.1% |

## Pooled-major clock diagnostics

| UTC block | K1 OPP0 | Low break | 2nd Low | Low break after 2nd |
|---|---:|---:|---:|---:|
| 00-04 | 444 | 72.1% | 22.3% | 80.8% |
| 04-08 | 455 | 72.3% | 25.3% | 75.7% |
| 08-12 | 476 | 68.1% | 22.9% | 67.9% |
| 12-16 | 557 | 72.4% | 27.5% | 72.5% |
| 16-20 | 461 | 72.5% | 24.1% | 74.8% |
| 20-00 | 374 | 67.9% | 24.3% | 64.8% |

## Frozen gate

Regimes passing the preregistered three-partition structural gate: **NONE**.
Clock blocks passing the same gate independently: **NONE**.

**Status: B27BE_SHORT_STRUCTURALLY_FAVORED_NONE__CLOCK_NONE.**

B27BE is structural discovery only. It does not authorize a regime trading gate or alter live BBC. Economics must be tested separately after this atlas is frozen.
