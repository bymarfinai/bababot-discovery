# BTC Temporal Saturday T-Method S5.2E — Timing / Path Robustness

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — ROBUSTNESS GATE FAIL; NO IMMUNITY ACTION  
**Research only:** live BBC untouched

## Frozen cohort
- Exact S5.2B FLOW_EMA warning cohort: **43** = 28 discovery / 15 validation
- Latent future-deep >=+0.80: **19**
- True nondeep: **24**
- S5.2B deep-damage / nondeep-rescue parity passed before interpretation.
- No PnL threshold optimization and no future label was used in a trading rule.

## Predeclared robustness design
Natural bins were fixed from existing strategy geometry / clock windows, not optimized from S5.2D:
- +0.50 hinge age: <=120m / 125–240m / >240m
- warning age: <=240m / 245–360m / >360m
- retained post-hinge floor: <+0.20 / +0.20..<+0.30 / >=+0.30
- post-hinge high-water close: <+0.40 / +0.40..<+0.50 / >=+0.50
- EMA7 / EMA20 slope: positive vs nonpositive
- four contiguous chronological warning folds

Predeclared mechanism-support gate:
1. at least 4/6 core continuous features match the expected latent-runner direction in >=3/4 chronological folds; AND
2. warning-age natural bins are monotonic in the expected direction in both discovery and validation.

## Natural-bin deep rates

### Hinge age
| Bin | N | Deep | Discovery | Validation |
|---|---:|---:|---:|---:|
| <=120m | 13 | 53.8% | 10 / 50.0% | 3 / 66.7% |
| 125–240m | 16 | 50.0% | 9 / 55.6% | 7 / 42.9% |
| >240m | 14 | 28.6% | 9 / 44.4% | 5 / 0.0% |

The coarse full-sample and validation direction supports earlier impulse, but discovery is not monotonic.

### Warning age
| Bin | N | Deep | Discovery | Validation |
|---|---:|---:|---:|---:|
| <=240m | 20 | 50.0% | 15 / 53.3% | 5 / 40.0% |
| 245–360m | 10 | 60.0% | 4 / 75.0% | 6 / 50.0% |
| >360m | 13 | 23.1% | 9 / 33.3% | 4 / 0.0% |

This is **not monotonic** in full, discovery, or validation. The strongest stable statement is only that very late warnings (>360m) are poorer; `earlier is always more latent-deep` is too simple.

### Retained post-hinge floor
| Bin | N | Deep | Discovery | Validation |
|---|---:|---:|---:|---:|
| <+0.20 | 18 | **22.2%** | 9 / **22.2%** | 9 / **22.2%** |
| +0.20..<+0.30 | 25 | **60.0%** | 19 / **63.2%** | 6 / **50.0%** |
| >=+0.30 | 0 | NA | 0 / NA | 0 / NA |

This is the cleanest S5.2E clue. A runner that had already allowed completed-close progress below +0.20 before the generic warning was much less likely to be a latent deep runner, and the 22.2% deep rate is exactly the same in discovery and validation. This remains forensic / shadow only; no immunity threshold is promoted.

### Post-hinge high-water close
| Bin | N | Deep | Discovery | Validation |
|---|---:|---:|---:|---:|
| <+0.40 | 9 | 11.1% | 6 / 16.7% | 3 / 0.0% |
| +0.40..<+0.50 | 9 | 44.4% | 6 / 66.7% | 3 / 0.0% |
| >=+0.50 | 25 | **56.0%** | 16 / **56.2%** | 9 / **55.6%** |

The >=+0.50 state itself transfers unusually well, but the three-bin ordering is not monotonic in discovery.

### EMA slope sign
EMA7 slope positive:
- N34 / deep 50.0%
- discovery 56.5%
- validation 36.4%

EMA7 slope nonpositive:
- N9 / deep 22.2%
- discovery 20.0%
- validation 25.0%

EMA20 sign is not useful because 40/43 warnings already have positive EMA20 slope and the tiny nonpositive group reverses chronology.

## Four chronological folds
| Feature | Expected direction | Matching folds | Match rate | Median fold AUC |
|---|---|---:|---:|---:|
| time_to05_min | DEEP_LOW | 3/4 | 75% | 0.425 |
| warning_min | DEEP_LOW | 3/4 | 75% | 0.375 |
| posthinge_max_close_progress | DEEP_HIGH | 3/4 | 75% | 0.758 |
| posthinge_min_close_progress | DEEP_HIGH | 2/4 | 50% | 0.634 |
| warning_ema20_slope60 | DEEP_HIGH | 2/4 | 50% | 0.488 |
| warning_ema7_slope60 | DEEP_HIGH | 3/4 | 75% | 0.571 |

Four of six core features pass the fold component, exactly meeting the first half of the predeclared gate:
- time-to-+0.50
- warning age
- post-hinge max close-progress
- EMA7 slope

But warning-age bin monotonicity fails in both discovery and validation, so the combined gate fails.

## Natural-bin monotonicity
| Family | Full | Discovery | Validation |
|---|---|---|---|
| HINGE_AGE | EXPECTED | NOT MONOTONIC | EXPECTED |
| WARNING_AGE | NOT MONOTONIC | NOT MONOTONIC | NOT MONOTONIC |
| RETAINED_FLOOR | EXPECTED | EXPECTED | EXPECTED |
| HIGH_WATER_CLOSE | EXPECTED | NOT MONOTONIC | EXPECTED |

## S5.2E verdict
**FAIL the predeclared mechanism-support gate.**

The S5.2D mechanism is partly real, but it is not robust enough in its original combined form to justify an immunity ACTION test. In particular:
- `early warning = latent runner` is too simple;
- very late warnings (>360m) are clearly weak, but the middle 245–360m bucket is actually richer in latent runners than <=240m;
- EMA20 slope does not add robust routing value;
- retained path quality is more stable than raw clock timing.

The strongest preserved shadow clues are:
1. retained floor <+0.20 before warning: only 22.2% latent deep in **both** discovery and validation;
2. post-hinge max close >=+0.50: ~56% latent deep in both chronology halves;
3. EMA7 nonpositive slope: ~22% latent deep with similar D/V direction.

These are not promoted or combined post hoc.

## Research decision
Do **not** proceed directly to a S5.2F immunity action or tune timing cutoffs on this sample. The +0.20 protection architecture has not earned promotion.

A7.19 remains the official full-coverage Saturday champion and A7.26 remains the preserved selective benchmark. The next clean branch should return to the predeclared Saturday T-Method sequence rather than optimize S5.2 further.
