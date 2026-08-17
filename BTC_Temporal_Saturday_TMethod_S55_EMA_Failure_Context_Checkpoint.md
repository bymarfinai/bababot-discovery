# BTC Temporal Saturday T-Method S5.5 — EMA Failure Context

**Date:** 2026-08-17 WIB  
**Status:** COMPLETE — CONTEXT GATE FAIL; NO EMA ACTION PROMOTED  
**Research only:** live BBC untouched

## Frozen parity
- +0.50 hinge trades: **89** = 61 future-deep / 28 shallow
- Static parent all-trade PnL: **+$87.200**
- A7.19 full-coverage PnL: **+$103.383**

## Predeclared Saturday-native geometry
S5.4 showed Saturday is not Tuesday-style EMA overextension. Stronger future runners are slightly stronger above EMA at the +0.50 hinge, while shallow runners tend to lose EMA structure sooner afterward.

S5.5 therefore tested only three predeclared contexts, with no threshold sweep:
- weak hinge = completed +0.50-hinge candle closes with progress **< +0.50%**
- early EMA loss = causal event occurs within **60 minutes** after hinge

Contexts:
1. `WEAK_FIRST_BELOW20_60`
2. `WEAK_TWO_BELOW7_60`
3. `WEAK_TWO_BELOW20_60`

Promotion gate required all of:
- >=5 observations in discovery and validation;
- shallow rate >50% in both chronology halves;
- A7.19 cohort PnL <=0 in both halves.

## Results
| Context | N | Shallow rate | Discovery N / shallow / A7.19 PnL | Validation N / shallow / A7.19 PnL | Gate |
|---|---:|---:|---:|---:|---:|
| WEAK_TWO_BELOW20_60 | 16 | 50.00% | 9 / 55.56% / **+$21.72** | 7 / 42.86% / **+$22.00** | FAIL |
| WEAK_FIRST_BELOW20_60 | 24 | 41.67% | 14 / 35.71% / **+$41.11** | 10 / 50.00% / **+$21.63** | FAIL |
| WEAK_TWO_BELOW7_60 | 34 | 41.18% | 21 / 38.10% / **+$57.71** | 13 / 46.15% / **+$8.91** | FAIL |

## Controls
- `WEAK_HINGE_ONLY`: N48, shallow **39.58%**; discovery 34.48%, validation 47.37%.
- `STRONG_HINGE_ONLY`: N41, shallow **21.95%**; discovery 24.00%, validation 18.75%.
- `EARLY_FIRST_BELOW20_ONLY`: N46, shallow **36.96%**; discovery 32.26%, validation 46.67%.
- `EARLY_TWO_BELOW7_ONLY`: N62, shallow **33.87%**; discovery 30.95%, validation 40.00%.
- `EARLY_TWO_BELOW20_ONLY`: N29, shallow **41.38%**; discovery 44.44%, validation 36.36%.

## Interpretation
1. S5.4's descriptive relation is real but **not sufficient as a hard failure context**.
2. A weak +0.50 hinge does enrich shallow outcomes relative to a strong hinge, but many weak-hinge trades still become deep runners.
3. Early EMA loss adds only modest failure enrichment and does not transfer strongly enough from discovery to validation.
4. Most importantly, every predeclared context remains **strongly profitable under A7.19 in both chronology halves**. Therefore these states are not economically broken enough to justify a direct S5.6 EMA exit/confirmation action.
5. Do not tune 45m/75m, EMA periods, hinge thresholds, or combine post-hoc states on this sample.

## S5.5 verdict
**FAIL the predeclared context gate. No EMA action is promoted.**

The clean positive lesson is asymmetric: `strong hinge` is meaningfully runner-like (only ~22% shallow), but the inverse `weak hinge + early EMA loss` is not precise enough to identify failures.

## Correct continuation
Do **not** force a S5.6 action test from these failed contexts. Preserve S5.4 as forensic knowledge and move to the next independent Saturday T-Method branch: **S5.7 giveback-sequence forensic**, unless a separately predeclared S5.6 diagnostic (no action) is explicitly desired.

A7.19 remains the official full-coverage Saturday champion; A7.26 remains the preserved selective benchmark.
