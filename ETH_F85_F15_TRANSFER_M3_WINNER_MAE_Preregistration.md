# ETH F85/F15 Transfer — M3 Winner MAE / Path Audit

**Status: PREREGISTERED before M3 result-bearing execution.**

## Blocking upstream requirement
M3 may run only if:

`ETH_F85_F15_TRANSFER_M2_PRE_H2_ENTRY_GRID_Status.txt`

contains exactly:

`ETH_M2_PRE_H2_ENTRY_GRID_COMPLETED_CORRECTED_CHRONOLOGY`

The original M2 +10-minute eligibility output is superseded and forbidden as M3 input.

## Candidate set
M3 must read the corrected M2 summary and automatically select every habitat x level whose pooled-major row is tagged `SCREEN_PASS`.

No manual addition, removal, or cherry-picking of levels is allowed after corrected M2 results are known.

## Purpose
For each corrected-M2 structural survivor, answer only:

> After a valid pre-H2 fill, how far do eventual H2 winners move adversely, and how does that adverse path compare with non-H2 fills?

This mirrors BTC B27X, generalized across every corrected ETH M2 survivor.

M3 is a path diagnostic, not an economic backtest and not a stop optimizer.

## Frozen upstream identity
- Instrument: Binance USD-M ETHUSDT perpetual.
- Raw event clock: 5m.
- Reference/exec clocks, H/L/R, K1 OPP0, causal leave, H2, opposite break, and fill identity are imported unchanged from corrected M2.
- Entry price is the exact frozen range-fraction level from corrected M2.
- No new candidate may be created in M3.

## Winner definition
A filled corrected-M2 candidate is an `H2_WINNER` only when corrected M2 outcome is `H2`.

Winner status is after-the-fact diagnostic labeling only; it cannot alter fill identity.

## LONG adverse-path measurements
For LONG level fraction `f`:
- `pre_h2_min_frac`: minimum 5m low from fill bar through last bar strictly before H2; fill bar included.
- `through_h2_min_frac`: minimum 5m low from fill bar through H2 bar inclusive for H2 winners.
- `next_bar_pre_h2_min_frac`: same pre-H2 path excluding the fill bar when a later pre-H2 bar exists.
- required adverse distance = `max(0, f - min_fraction)`.

## SHORT adverse-path measurements
Exact directional mirror:
- `pre_h2_max_frac`: maximum 5m high from fill bar through last bar strictly before H2.
- `through_h2_max_frac`: maximum 5m high through H2 bar inclusive.
- `next_bar_pre_h2_max_frac`: same excluding fill bar where available.
- required adverse distance = `max(0, max_fraction - f)`.

## Conservative H2-bar treatment
The H2 target bar is included in the conservative winner path because intrabar ordering between an adverse boundary and H2 is unknowable on raw 5m.

Therefore an adverse boundary touched on the H2 bar counts as touched before conservative survival can be claimed.

## Winner distribution outputs
For every survivor x partition and pooled-major report:
- filled N;
- H2 winner N / H2 rate;
- winner required-distance P50, P75, P90, P95, maximum using conservative through-H2 path;
- corresponding pre-H2-only quantiles;
- median next-bar-only adverse distance for context;
- median minutes fill -> H2.

## Failure comparison
For every filled non-H2 candidate:
- measure adverse path from fill through opposite/ambiguous terminal bar inclusive, or through execution end for no-H2;
- report failure required-distance P25, P50, P75, P90;
- report overlap diagnostics against winner P90 distance.

No failure path may be used to modify winner identity or fill timing.

## Diagnostic survival curve
For each survivor, report frozen adverse distances:
`D05, D10, D15, ..., D85` in 0.05R increments.

LONG survivor at distance D:
- boundary fraction = `f - D`;
- conservative winner survives only if minimum fraction through H2 is strictly greater than boundary.

SHORT survivor at distance D:
- boundary fraction = `f + D`;
- conservative winner survives only if maximum fraction through H2 is strictly less than boundary.

Equality counts as a touch and therefore does not survive.

The curve is descriptive only. M3 must not choose or promote a stop distance.

## Candidate comparison
M3 may display side-by-side diagnostics such as:
- winner P90 required distance;
- failure median required distance;
- `failure_P50 - winner_P90` separation;
- fill count and H2 rate inherited from corrected M2.

These diagnostics do **not** promote a winning level in M3. Level selection, if needed, requires the next separately authorized milestone.

## Prohibited in M3
- TP / E20 / E20_DOWN;
- stop selection or optimization;
- F35/F65 promotion;
- reclaim/rejection confirmation;
- next-open execution redesign;
- runner logic;
- fees, PnL, PF, expectancy, leverage;
- new clock/level discovery.

## Mandatory assertions
1. Corrected M2 status gate passes before any data work.
2. Candidate set equals corrected M2 `SCREEN_PASS` set exactly.
3. Every M3 fill reproduces a corrected M2 filled identity; no new fills.
4. H2 winners have H2 terminal strictly after fill.
5. Pre-H2 metric excludes H2 bar; conservative metric includes it.
6. Fill bar is included in primary/conservative path.
7. LONG/SHORT adverse-distance formulas are exact mirrors.
8. Survival equality counts as touched / non-survival.
9. Raw 5m coverage >=99.5%.
10. Synthetic tests cover LONG and SHORT fill-bar/H2-bar adverse ambiguity.

**Research only. Stop after M3 result persistence. No M4 automatic execution.**
