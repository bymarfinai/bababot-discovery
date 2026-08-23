# B27CR — BTC 24H Clock-Specific TP Depth Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the six 4H clock zones have different natural downside follow-through depths after the same F05 SHORT entry.

B27CR changes **target depth only**. Entry remains F05 for all clocks. No SL, BE, confirmation gate, runner, regime filter, weekday filter, or clock exclusion is tuned here.

This is structural/anatomy research only. Trading WR/PF/expectancy/PnL are N/A. Any economic follow-up must be separately preregistered and preserve nominal RR >=1:1.

## Data-reuse caveat
External and reference_validation have been inspected repeatedly in prior lineage, so they are reused-data confirmation only, not untouched OOS. No production/live rule may be changed from B27CR.

## Frozen source and raw data
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`, major partitions only with `eligible == True`.
Expected source identity: external 202 / development 333 / reference_validation 194 / pooled major 729.
Raw 5m identity must be exactly 698,112 rows with 100% coverage.

No clock/regime/weekday exclusion.

## Frozen entry
For each event:
- `R4 = H-L`
- F05 = `L + 0.05*R4`.

Preserve B27CP F05 chronology exactly inside the original 4H block:
1. scan raw 5m bars from `reclaim_complete_ts`;
2. first bar high >= F05 fills the structural entry;
3. completed close <L before fill cancels `LOW_BREAK_BEFORE_FILL`;
4. completed close >H before fill cancels `HIGH_BREAK_BEFORE_FILL`;
5. no new entry after original `obs_end`.

Expected structural F05 fill identity must reproduce B27CP exactly: external 183 / development 297 / reference_validation 173 / pooled major 653.

## Frozen target ladder
Only these four target depths are allowed:
- T5 = `L - 0.05*R4`
- T7.5 = `L - 0.075*R4`
- T10 = `L - 0.10*R4`
- T15 = `L - 0.15*R4`

No target is added after clock results are seen.

## Causal post-fill chronology
For each filled F05 event and each target independently:
- a completed close <L confirms the Low rebreak;
- target scanning begins only on the next raw 5m bar after rebreak confirmation;
- a target is reached when an eligible bar low <= that target;
- before the target is reached, first completed close >H is structural failure;
- if unresolved at original `obs_end`, preserve the frozen B27CP/B27CN anatomy horizon of exactly +4h;
- if still neither target nor High failure at `obs_end+4h`, classify unresolved.

If the fill bar itself closes <L it may confirm rebreak, but no target touch on that same fill/rebreak bar is credited. On a later eligible bar, favorable intrabar target touch is credited before a same-bar completed-close High invalidation because the low is observable during that bar before the close is known, matching B27CP chronology.

No stop/BE/profit-lock/runner is simulated in B27CR.

## Required metrics
For every target, partition, and clock report:
- source N;
- F05 fills N / fill rate;
- rebreak-after-fill N/rate;
- target reached N;
- target hit/fill;
- target yield/source;
- High failure before target N/rate;
- unresolved N/rate;
- median reclaim->fill;
- median fill->rebreak;
- median fill->target.

Report all six clocks independently first.

## Development-only clock selection
For each clock, select the **deepest** target among T5/T7.5/T10/T15 satisfying both:
1. development F05 fills >=30;
2. development target hit/fill >=70.0%.

Because fills are identical across target candidates inside a clock, no additional retention adjustment is needed.

If no target qualifies, select T5 as fallback. No clock may be dropped.

## Reused-data confirmation
Apply the frozen development-selected target map unchanged to external and reference_validation.

A selected target is `REUSED_CONFIRMED` only if in both external and reference_validation:
- F05 fills >=15;
- selected-target hit/fill >=65.0%.

Failure cannot change the selected target and cannot delete the clock.

## Overall interpretation gate
`B27CR_CLOCK_TP_REUSED_CANDIDATE` requires all:
1. audit PASS and exact B27CP F05 fill reproduction;
2. at least 4 of 6 selected clock targets are reused-confirmed;
3. selected-map development target-hit/fill >=70%;
4. selected-map pooled-major target-hit/fill >=65%;
5. no clock exclusion.

Otherwise verdict: `B27CR_CLOCK_TP_NOT_SUPPORTED`.

Even a candidate PASS remains anatomy-only reused-data evidence. The next step is a separately preregistered economic test that freezes this clock-TP map and derives causal SL geometry with nominal RR >=1:1.

Research only. Live BBC unchanged.

<!-- Execution trigger only; no semantic change. -->
