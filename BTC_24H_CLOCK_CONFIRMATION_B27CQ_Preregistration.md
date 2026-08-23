# B27CQ — BTC 24H Clock-Specific F05 Confirmation Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the six 4H clock zones should use different **causal confirmation gates** while keeping the SHORT entry price fixed at F05.

B27CQ changes only whether an already-defined F05 setup is allowed to enter. It does not tune entry level, SL, TP, runner, rescue duration, regime, weekday, or clock inclusion.

This is structural/anatomy research only. Trading WR/PF/expectancy/PnL are N/A. Any economic follow-up must be separately preregistered with nominal RR >=1:1.

## Data-reuse caveat
B27CG/B27CM/B27CN/B27CP already inspected external and reference_validation behavior. Therefore external/reference_validation in B27CQ are reused-data confirmation only, not untouched OOS. No live or production rule may be changed from this experiment.

## Frozen source and raw data
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`, major partitions only, `eligible == True`.
Expected source identity: external 202 / development 333 / reference_validation 194 / pooled major 729.
Raw 5m identity must be exactly 698,112 rows with 100% coverage.
No clock/regime/weekday exclusion is permitted.

## Frozen F05 entry and objective
For each event:
- `R4 = H-L`
- entry `F05 = L + 0.05*R4`
- structural objective `T10 = L - 0.10*R4`.

Preserve B27CP F05 chronology exactly:
1. after reclaim completes, scan raw 5m bars inside the original 4H block;
2. if active F05 is touched by bar high, fill at F05;
3. completed close <L before fill cancels as `LOW_BREAK_BEFORE_FILL`;
4. completed close >H before fill cancels as `HIGH_BREAK_BEFORE_FILL`;
5. no new entry after original `obs_end`.

After fill:
- completed close <L confirms rebreak;
- T10 scanning begins only on the next raw 5m bar after rebreak confirmation;
- T10 is reached if an eligible bar low <= T10;
- first completed close >H before T10 is structural failure;
- if unresolved at original block end, preserve exactly the B27CP/B27CN +4h anatomy horizon;
- if still neither T10 nor High failure at `obs_end+4h`, classify unresolved.

## Frozen confirmation candidates
Only signals already defined causally in B27CG and observable no later than reclaim completion are allowed. No new indicator or combination may be added after clock results are seen.

- `BASE`: no confirmation filter; universal F05 baseline.
- `WEAK_C05`: require reclaim close extension `< +0.05 R4` (logical inverse of B27CG `RECLAIM_C05`).
- `WEAK_C10`: require reclaim close extension `< +0.10 R4` (inverse of `RECLAIM_C10`).
- `NOT_STRONG_BODY`: require B27CG `RECLAIM_STRONG_BODY == False`; strong body is defined as bullish reclaim candle with body/range >=0.50 and close position >=0.75.
- `QUICK_RECLAIM`: require break-to-reclaim time <=10 minutes, identical to B27CG.
- `TIME_LEFT_120`: require at least 120 minutes from reclaim completion to original block end, identical to B27CG.

All five non-BASE gates are fully known at `reclaim_complete_ts`, before the first eligible post-reclaim F05 entry bar. Therefore there is no delayed-entry ambiguity and no look-ahead.

## Required metrics
For every gate, partition, and clock report:
- source events N;
- gate-pass events N / pass rate;
- F05 fills N;
- retained fills versus BASE;
- fill rate among gate-pass events;
- rebreak-after-fill N/rate;
- T10 reached N;
- T10/fill;
- T10 yield/source;
- High failure N/rate;
- unresolved N/rate;
- median reclaim->fill, fill->rebreak, fill->T10 minutes.

Report all six clocks independently first.

## Development-only clock selection
For each clock, BASE is always eligible.

A non-BASE gate is eligible only if all are true on development:
1. filled N >=20;
2. retained fills >=50% of that clock's BASE fills;
3. T10/fill >= BASE T10/fill +5.0 percentage points;
4. High-failure/fill <= BASE High-failure/fill.

Among eligible gates select highest development T10/fill. Tie-break in order:
1. higher T10 yield/source;
2. higher retained-fill share;
3. fixed simpler order `WEAK_C05 -> WEAK_C10 -> NOT_STRONG_BODY -> QUICK_RECLAIM -> TIME_LEFT_120`.

If none qualifies, select BASE. No clock may be dropped.

## Reused-data confirmation
Apply the frozen development-selected gate map unchanged to external and reference_validation.

A selected non-BASE gate is `REUSED_CONFIRMED` only if in both external and reference_validation:
- fills >=10;
- T10/fill >= BASE T10/fill;
- High-failure/fill <= BASE High-failure/fill;
- retained fills >=40% of BASE fills.

Failure cannot change the gate or delete the clock.

## Overall interpretation gate
`B27CQ_CLOCK_CONFIRM_REUSED_CANDIDATE` requires all:
1. audit PASS;
2. at least 2 of 6 clocks select a non-BASE gate;
3. at least half of selected non-BASE gates are reused-confirmed;
4. selected-map development T10/fill >= universal BASE +5pp;
5. selected-map pooled-major T10/fill > universal BASE;
6. selected-map pooled-major retained fills >=60% of BASE fills;
7. selected-map pooled-major High-failure/fill <= BASE;
8. no clock exclusion.

Otherwise verdict: `B27CQ_CLOCK_CONFIRM_NOT_SUPPORTED`.

Even a candidate PASS remains anatomy-only reused-data evidence. The next step would be a separately preregistered economic test combining the frozen clock-confirmation map with causal SL management and RR >=1:1.

Research only. Live BBC unchanged.

<!-- Execution trigger only; no semantic change. -->
