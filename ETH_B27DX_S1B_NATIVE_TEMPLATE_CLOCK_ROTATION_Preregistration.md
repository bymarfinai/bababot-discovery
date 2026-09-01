# ETH B27DX — S1B Native-Template Full Clock Rotation — Preregistration

## Purpose
Determine whether the ETH-native lifecycle family identified in S1A reveals more repeatable daily habitats than the BTC-derived R330/X390 template when rotated across the full 24-hour clock surface.

S1B changes **structural duration template and clock placement only**. It does not optimize entry, target, stop, runner, leverage, or H/H2.

## S1A evidence frozen before S1B
S1A produced one qualifying 2D native lifecycle component at the 16:00 UTC anchor:
- supported reference durations: 240, 300, 330, 360 minutes;
- supported execution horizons: 240, 300, 360, 390, 420 minutes;
- 18 connected supported cells.

The 09:30 UTC anchor produced supported one-dimensional stripes but no qualifying 2D native component, so those stripes are not promoted into the primary S1B template set.

## Deterministic S1B template selection
No maximum-PF template is selected.

Three preregistered templates are derived deterministically from S1A topology:

1. `NATIVE_SHORT = R240 / X300`
   - shortest reference duration in the qualifying S1A component;
   - shortest horizon supported at that reference duration.

2. `NATIVE_CENTER = R300 / X360`
   - nearest lower-grid reference value to the median of distinct supported reference values;
   - median supported execution-horizon grid value.

3. `LEGACY_BENCHMARK = R330 / X390`
   - frozen BTC-derived benchmark used in M1/M1R.

No other duration templates may be added after seeing S1B results.

## Frozen causal/economic rules
- side: LONG only;
- exact B27DX-corrected causal grammar;
- completed 5m bars only;
- K1 OPP0;
- completed causal leave;
- first eligible pre-terminal retrace fill;
- no future veto/look-ahead;
- entry probes: F90, F85, F80;
- target: E20;
- completed-close invalidation: F35;
- $500 notional;
- $0.40 round-trip fee;
- weekdays only;
- 0 bps structural discovery score;
- same Development / External / Reference Validation partitions as M1R.

## Clock grid
For each of the three frozen duration templates, test all 48 UTC execution starts:

`00:00, 00:30, 01:00, ... 23:30`.

Reference start is always `execution start - reference duration`.

## Per-clock gates
Development probe positive:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

Development clock pass: >=2/3 probes positive.

Validation probe positive in External and Reference Validation:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

Validation clock pass in each partition:
- >=2/3 probes have N >=15; and
- >=2/3 probes positive.

A clock is `SUPPORTED` only if Development + External + Reference Validation all pass.

## Template-level reporting
For each template report:
- all supported clocks;
- contiguous 30-minute supported runs;
- median Development PF across supported clocks;
- raw opportunity density per supported clock = median probe N / Development weeks;
- sum of supported-clock raw densities as an **upper-bound structural opportunity-density diagnostic**.

The density sum is not a portfolio trade count because clocks can overlap or represent the same market move. It is never a selection gate.

## Native-template evidence
`NATIVE_CLOCK_EXPANSION` is supported if either native template (`NATIVE_SHORT` or `NATIVE_CENTER`) produces:
- more supported clocks than `LEGACY_BENCHMARK`, or
- a contiguous supported run of >=2 clock points that the legacy benchmark does not produce.

This tests whether shorter ETH-native structural duration exposes additional repeatable habitats.

## Decision states
- `ETH_S1B_NATIVE_CLOCK_EXPANSION_SUPPORTED`
- `ETH_S1B_NATIVE_TEMPLATES_NO_EXPANSION`
- `ETH_S1B_NO_SUPPORTED_CLOCKS`

## Guardrails
- Do not select a clock by highest PF alone.
- Do not tune F-entry, TP, stop, runner, or leverage.
- Do not use raw opportunity density as a promotion gate.
- No live BBC changes.
