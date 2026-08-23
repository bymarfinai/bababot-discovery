# B27CP — BTC 24H Clock-Specific SHORT Entry Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test the user's hypothesis that the six 4H clock zones should not be forced to share one universal SHORT entry after Low reclaim.

B27CP changes **entry only**. It does not tune SL, TP, runner, rescue duration, regime filters, weekdays, or clock inclusion.

This is **structural/anatomy research only**. Trading WR/PF/expectancy/PnL are N/A in B27CP. Any economic follow-up must be separately preregistered and preserve nominal RR >=1:1.

## Frozen source
Source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`.
Use major partitions only with `eligible == True`.
Expected source identity: external 202 / development 333 / reference_validation 194 / pooled major 729.

Raw 5m identity must be 698,112 rows and 100% coverage.

No clock/regime/weekday exclusion.

## Frozen candidate entry ladder
Reuse the exact previously-defined B27CF ladder; no new level is added after seeing clock results:
- F05 = L + 0.05*R4
- F10 = L + 0.10*R4
- F15 = L + 0.15*R4
- F25 = L + 0.25*R4
- F50 = L + 0.50*R4
where `R4 = H-L`.

## Frozen entry semantics
Preserve B27CF chronology inside the original 4H block:
1. scan raw 5m bars from `reclaim_complete_ts` through `obs_end`;
2. if candidate level is touched by bar high, the entry is considered filled at that level on that bar;
3. if completed close <L before fill, classify `LOW_BREAK_BEFORE_FILL` and cancel;
4. if completed close >H before fill, classify `HIGH_BREAK_BEFORE_FILL` and cancel;
5. no new entry after original `obs_end`.

If fill bar itself closes <L, rebreak is confirmed on that completed bar. A fill-bar favorable T10 touch is not credited.

## Frozen post-fill structural objective
B27CP asks whether the filled entry later reaches the already-supported structural T10 objective:
`T10 = L - 0.10*R4`.

Chronology after fill:
- a completed close <L confirms rebreak;
- T10 scanning begins only from the next raw 5m bar after rebreak confirmation;
- T10 is reached if a causally eligible bar low <= T10;
- before T10 is reached, first completed close >H is structural failure;
- if original block ends before T10, preserve the frozen B27CN rescue horizon of exactly +4h for this anatomy readout;
- if still unresolved at `obs_end + 4h`, classify unresolved.

No protective stop/BE/runner is simulated because B27CP isolates entry.

## Required metrics
For every candidate and scope report:
- source N;
- fills N / fill rate;
- rebreak-after-fill N/rate;
- T10 reached N;
- T10 hit/fill;
- **T10 yield/source = T10 reached / source N**;
- completed High failure before T10 N/rate;
- unresolved before frozen horizon N/rate;
- median reclaim->fill minutes;
- median fill->rebreak minutes;
- median fill->T10 minutes.

Report all six clocks independently first.

## Development-only clock selection
F05 is the baseline and remains eligible in every clock.

For each clock, an alternate entry F10/F15/F25/F50 is eligible only if:
- development fills >=20;
- its development T10 yield/source is at least **+2.0 percentage points** above F05 in the same clock.

Among eligible alternates, select the highest development T10 yield/source. Tie-break: higher T10 hit/fill, then higher fill rate, then the closer entry in order F10 -> F15 -> F25 -> F50.

If no alternate qualifies, select F05. No clock may be dropped.

## Reused-data confirmation
External and reference_validation have already been inspected in prior lineage, so they are reused-data confirmation, not untouched OOS.

A development-selected alternate is `REUSED_CONFIRMED` only if:
- external fills >=10 and validation fills >=10;
- T10 yield/source is >= F05 in both external and reference_validation for that clock.

Failure cannot change the frozen selected entry and cannot delete the clock.

## Overall interpretation
`B27CP_CLOCK_ENTRY_REUSED_CANDIDATE` requires:
1. audit PASS;
2. at least 2 of 6 clocks select an alternate entry in development;
3. at least half of the selected alternates are reused-confirmed;
4. selected-map pooled-major T10 yield/source > universal-F05 pooled-major T10 yield/source;
5. no clock exclusion.

Otherwise verdict: `B27CP_CLOCK_ENTRY_NOT_SUPPORTED`.

Even if candidate passes, this is structural anatomy only and does not authorize trading/live changes. The next step would be a separately preregistered clock-entry + causal SL economics test with RR >=1:1.

<!-- Execution trigger only; no semantic change. -->
