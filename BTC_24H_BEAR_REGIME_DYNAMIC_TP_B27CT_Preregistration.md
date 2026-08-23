# B27CT — BTC 24H BEAR Regime-Filter + Dynamic Clock-TP Economics — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test one frozen SHORT strategy that applies the existing causal 4H regime state as a pre-entry filter and converts the already-selected B27CR clock-specific target into a dynamic profit floor/runner.

This experiment does **not** tune the F05 entry, clock inclusion, clock TP map, regime definitions, extra horizon, fees, or pre-target fixed price SL after results are seen.

External and reference_validation have been inspected repeatedly in this lineage and are reused-data confirmation only, not untouched OOS. Research only; live BBC unchanged.

## Frozen source and audit identities
- Event source: `BTC_24H_RECLAIM_FOLLOWTHROUGH_B27CE_Detail.csv`, major partitions, `eligible == True`.
- Causal regime provenance must be cross-checked against `BTC_24H_4H_REGIME_SHORT_ATLAS_B27BE_Detail.csv` by partition + `obs_start`; selected `regime_available_ts` must be `<= obs_start` and regime labels must match.
- Expected source events: external 202 / development 333 / reference_validation 194 / pooled major 729.
- Raw 5m rows: exactly 698,112 with 100% coverage.
- Exact executable B27CS F05 fill identity before filtering must reproduce: external 183 / development 297 / reference_validation 172 / pooled major 652.

## Frozen regime filter
The filter is fixed from prior causal regime evidence before this run:
- `BEAR`: ALLOW SHORT.
- `SIDEWAYS`: ALLOW SHORT.
- `BULL`: BLOCK SHORT.

No regime may be reclassified, and no clock/regime intersection may be dropped after results are seen.

## Frozen entry and clock TP map
Entry remains F05 for every clock using exact B27CS executable semantics.

Clock TP map is frozen from B27CR:
- 00-04 UTC / 07-11 WIB: T5.
- 04-08 UTC / 11-15 WIB: T15.
- 08-12 UTC / 15-19 WIB: T15.
- 12-16 UTC / 19-23 WIB: T10.
- 16-20 UTC / 23-03 WIB: T10.
- 20-00 UTC / 03-07 WIB: T15.

Definitions:
- `R4 = H-L`.
- `F05 = L + 0.05*R4`.
- `T5 = L - 0.05*R4`.
- `T7.5 = L - 0.075*R4`.
- `T10 = L - 0.10*R4`.
- `T15 = L - 0.15*R4`.

## Frozen executable entry chronology
Preserve B27CS `BASE_H` semantics:
1. New entries are allowed only inside the original 4H block.
2. If a raw 5m open is already `>= H`, cancel before fill.
3. Else if high touches F05, fill SHORT at F05, or at actual open if the bar opens above F05 but below H.
4. Completed close `< L` before fill cancels as rebreak-before-fill.
5. Completed close `> H` before fill cancels as High-break-before-fill.

## Frozen pre-target management
There is **no added fixed price SL** before T5. B27CO/B27CS already rejected that family.

Before the final clock target:
- first completed close `> H` while no active protection exists is the full structural loss;
- completed close `< L` confirms rebreak;
- favorable milestone scanning begins only on the next raw 5m bar after rebreak confirmation;
- existing protection is resting and wins same-bar ambiguity conservatively;
- if final target is deeper than T5: T5 touch earns an `L` protection ceiling starting next raw bar;
- if final target is deeper than T7.5: T7.5 touch earns a `T5` protection ceiling starting next raw bar;
- if final target is deeper than T10: T10 touch earns a `T10` protection ceiling starting next raw bar;
- protection never loosens upward.

## Frozen variants
Evaluate exactly two variants on the **same BEAR+SIDEWAYS filtered fills**.

### FIXED_CLOCK_TP
Exact B27CS `BASE_H` clock-TP architecture: first valid final clock-target touch exits the full position at the target (or actual favorable gap-open if below target).

### DYNAMIC_CLOCK_TP
The final clock target becomes a milestone, not a final TP:
1. First valid final-target touch does **not** exit.
2. On the next raw 5m bar, the final target becomes the active minimum-profit ceiling.
3. If the next/later bar opens above the active ceiling, exit at actual open; otherwise if its high touches the ceiling, exit at the ceiling.
4. After final target is reached, a newly confirmed strict 3-bar 5m pivot high may ratchet the ceiling downward only if that pivot high is below the current/pending ceiling.
5. A pivot uses only three fully causal bars after target activation; no pivot formed before target activation may be used.
6. The ceiling never moves upward.
7. No lower fixed TP is added.
8. If still open, exit at the fixed anatomy horizon `obs_end + 4h` using the boundary open when available, otherwise the final completed close.

A target-touch bar itself cannot immediately activate the new final-target ceiling; activation starts on the next raw bar. A completed High structural invalidation on the target-touch bar may therefore still close the trade if no prior protection was active.

## Economics
- Fixed notional: $500 per trade.
- Round-trip fee: $0.40.
- No additional slippage assumption.
- SHORT gross return: `(entry - exit) / entry`.
- Win: net PnL `> 0`.

## Required reporting
Report all six clocks independently first for `DYNAMIC_CLOCK_TP`, with:
- trades;
- WR;
- PF;
- expectancy/trade;
- total net PnL;
- average win/loss;
- max drawdown;
- max loss streak;
- final target reached N;
- target-floor exits;
- structural-ratchet exits;
- full High losses;
- time exits.

Then report major partitions and pooled major for both FIXED and DYNAMIC.

Also report:
- filter effect: all-regime FIXED vs BEAR+SIDEWAYS FIXED;
- dynamic effect: filtered FIXED vs filtered DYNAMIC;
- BEAR and SIDEWAYS filtered components separately;
- counts per 100 filtered trades for win / High full loss / target reached / runner exit / time exit.

## Frozen interpretation gate
`B27CT_BEAR_FILTER_DYNAMIC_REUSED_CANDIDATE` requires all:
1. audit PASS and exact B27CS all-regime fill reproduction;
2. at least 30 filtered DYNAMIC trades in each major partition;
3. DYNAMIC expectancy `> 0` and PF `> 1.0` in external, development, and reference_validation;
4. pooled-major DYNAMIC expectancy `> 0`, PF `>= 1.20`, and total net PnL `> 0`;
5. pooled-major DYNAMIC expectancy strictly exceeds filtered FIXED expectancy;
6. pooled-major DYNAMIC PF strictly exceeds filtered FIXED PF;
7. no clock exclusion.

Otherwise verdict: `B27CT_BEAR_FILTER_DYNAMIC_NOT_SUPPORTED`.

`HIGH_QUALITY_70` is reported separately as an aspiration: WR >=70% in all three major partitions. It does not override the economics gate.

No post-hoc filter, TP, pivot, SL, clock, or horizon adjustment is allowed inside B27CT. Live BBC unchanged.