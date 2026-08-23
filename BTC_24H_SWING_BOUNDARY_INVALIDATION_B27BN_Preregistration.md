# B27BN — BTC 24H Swing-Boundary Invalidation Audit — Preregistration

## Purpose
Audit whether the current detector is declaring `SIDEWAYS` before the prior directional swing structure is actually invalidated.

The specific question is whether a frozen, already-confirmed swing boundary from the last directional 4H state distinguishes:
- continuation-like pause / RESUME; versus
- genuine opposite-direction TRANSITION.

This is regime-detector anatomy only. It does not infer accumulation/distribution participants and does not test LONG/SHORT mapping, entries, stops, targets, fees, WR, PF, PnL, session filters, or live behavior.

## Frozen parent lineage
Reuse unchanged:
- BTCUSDT 5m repository source, expected **698,112 rows / 100% coverage**;
- exact B27AG/B27BG `SwingRegime(slb=5, sa=0.5)` semantics;
- completed UTC 4H bars only, exactly 48 constituent 5m bars;
- EMA7 / EMA20 / ATR14 exact existing implementation;
- causal swing confirmation exactly as the existing detector;
- B27BH complete directionally bracketed SIDEWAYS episodes.

Mandatory parent identity before any result is accepted:
- bracketed major-partition SIDEWAYS episodes = **1,023**;
- RESUME = **527**;
- TRANSITION = **496**;
- BULL-origin = **532**;
- BEAR-origin = **491**.

## Frozen structural boundary
The boundary is frozen from the **immediately preceding completed directional 4H state**, before the first SIDEWAYS bar exists.

For a BULL-origin episode:
- frozen support boundary = detector `lsl` (latest causally confirmed swing low) recorded after processing the last completed BULL bar;
- strict wick break on a later completed 4H bar = `low < frozen_boundary`;
- strict close break = `close < frozen_boundary`.

For a BEAR-origin episode:
- frozen resistance boundary = detector `lsh` (latest causally confirmed swing high) recorded after processing the last completed BEAR bar;
- strict wick break = `high > frozen_boundary`;
- strict close break = `close > frozen_boundary`.

Equality is a HOLD, not a break. No ATR tolerance, percentage tolerance, buffer, or optimized threshold is allowed in B27BN.

The frozen boundary may not move during the SIDEWAYS episode for the primary audit. New swings confirmed after SIDEWAYS begins are reported only as diagnostics and cannot redefine the primary boundary post hoc.

## Causal timing
The boundary must already be known at the effective timestamp of the last BULL/BEAR state.

For each SIDEWAYS episode, inspect completed SIDEWAYS bars only after they become available. Primary ages are fixed before result inspection:
- age 1 = first SIDEWAYS bar / 4h;
- age 2 = second SIDEWAYS bar / 8h;
- age 3 = third SIDEWAYS bar / 12h.

For each episode record:
1. boundary price and origin state;
2. whether the first SIDEWAYS bar wick-broke the frozen boundary;
3. whether the first SIDEWAYS bar close-broke it;
4. whether the boundary was wick-broken by age 2 and by age 3;
5. whether it was close-broken by age 2 and by age 3;
6. first causal break age if any;
7. final historical label RESUME or TRANSITION.

Final outcome is used only as the historical label; it is never available to the detector at the observation point.

## Reporting cohorts
Report separately for BULL-origin and BEAR-origin in:
- `external`;
- `development` (diagnostic only for OOS support);
- `reference_validation`;
- `POOLED_OOS = external + reference_validation`;
- `POOLED_MAJOR = external + development + reference_validation`.

For every boundary event report N and eventual TRANSITION rate.

## Frozen primary hypothesis
If the user's structural hypothesis is correct, genuine transitions should violate the frozen directional swing boundary more often than same-direction resumes.

Primary tests:
1. first-SIDEWAYS **wick break** should increase eventual TRANSITION probability versus first-bar HOLD;
2. cumulative **wick break by age 3** should be more frequent in TRANSITION episodes than RESUME episodes;
3. the qualitative relationship must survive external and reference_validation separately for both BULL-origin and BEAR-origin.

Close-break statistics are preregistered secondary confirmation. They cannot rescue a failed wick-boundary primary gate.

## Frozen support gate
Verdict `B27BN_SWING_BOUNDARY_INVALIDATION_SUPPORTED` only if **all** conditions hold:

1. source identity, detector-label identity, parent episode identity, and causal boundary-timestamp assertions pass;
2. a frozen boundary exists for at least **95%** of POOLED_OOS episodes for each origin;
3. for BULL-origin and BEAR-origin separately in **POOLED_OOS**, first-bar wick-break TRANSITION rate is greater than first-bar HOLD TRANSITION rate;
4. the same first-bar wick-break direction is positive in **external and reference_validation separately** for both origins;
5. for each origin in POOLED_OOS, cumulative wick-break-by-age-3 rate is at least **10 percentage points higher in TRANSITION than RESUME**;
6. the cumulative age-3 TRANSITION-minus-RESUME break-rate difference is positive in external and reference_validation separately for both origins;
7. first-bar HOLD and first-bar BREAK each have at least 20 POOLED_OOS observations for each origin; if a cell is too sparse, the primary hypothesis is not supported rather than rescued with another threshold;
8. no close-only result, development-only result, later age, new swing boundary, ATR tolerance, optimized buffer, or changed inequality may rescue a failed primary gate.

Otherwise verdict is `B27BN_SWING_BOUNDARY_INVALIDATION_NOT_SUPPORTED`.

## Required diagnostics
Regardless of verdict, report:
- first-bar wick and close break rates by outcome;
- age-2 and age-3 cumulative break rates by outcome;
- first break age distribution;
- eventual TRANSITION rate conditional on HOLD vs BREAK;
- fraction of genuine transitions that reach the opposite detector state without ever wick-breaking the frozen origin boundary during the SIDEWAYS episode;
- fraction of RESUME episodes that temporarily wick-break the boundary before returning to the origin state.

These diagnostics describe the existing state machine only.

## Mandatory assertions
1. exactly 698,112 5m rows / 100% coverage;
2. complete 4H bars contain exactly 48 5m rows;
3. instrumented detector reproduces existing BULL/BEAR/SIDEWAYS labels exactly;
4. `lsh`/`lsl` snapshots are recorded only after causal swing confirmation in the existing detector process;
5. frozen boundary comes from the immediately preceding completed directional state, never from the first SIDEWAYS bar or later;
6. exact B27BH identity 1,023 / 527 / 496 / 532 / 491 reproduces;
7. no trading direction/economics enter the experiment;
8. live BBC remains unchanged.

## Interpretation boundary
Even a supported result would establish only that a prior confirmed swing boundary is a useful causal **regime invalidation signal**. It would not yet authorize a new production BULL/BEAR/SIDEWAYS state machine. Any detector redesign must be preregistered separately and re-audited for persistence, flip-back, and cross-era occupancy.

Research only. Live BBC unchanged.
