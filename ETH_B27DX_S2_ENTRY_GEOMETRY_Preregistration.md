# ETH B27DX — S2 Native Entry Geometry — Preregistration

## Purpose
Calibrate ETH-native LONG retrace entry geometry after S1A/S1B established that the native-center lifecycle `R300 / X360` expands the supported clock surface to four independently validated execution habitats: **05:00, 09:00, 10:00, 16:00 UTC**.

S2 changes **entry fraction only**. It does not tune reference duration, execution horizon, target, invalidation, runner, leverage, fees, H/H2, or live code.

## Frozen structure and causal grammar
- side: LONG only;
- exact B27DX corrected causal grammar;
- completed 5m causality only;
- reference duration: **300 minutes**;
- execution horizon: **360 minutes**;
- execution clocks: **05:00, 09:00, 10:00, 16:00 UTC** only;
- K1 OPP0;
- completed causal leave;
- first eligible pre-terminal retrace fill;
- no future-dependent veto/look-ahead;
- same terminal precedence/ambiguity handling as the frozen scorer;
- exit evaluation starts after the entry/fill bar.

## Frozen economics
- target: **E20**;
- completed-close invalidation: **F35**;
- notional: **$500**;
- round-trip fee: **$0.40**;
- slippage: **0 bps** for S2 discovery;
- weekdays only;
- same Development / External / Reference Validation partitions used in S1B.

These exits are diagnostic scaffolding in S2. They are intentionally not optimized until an entry family is frozen.

## Entry grid
Test a preregistered **5-percentage-point fraction grid** across the frozen reference range:

`F95, F90, F85, F80, F75, F70, F65, F60`

where `Fxx = L + xx% * (H-L)` for LONG.

No intermediate fraction may be added after results are seen.

## Exact per-clock/per-entry gates
Development positive for a given clock and entry fraction if:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

External / Reference Validation positive if:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

A clock is `ROBUST` for an entry fraction only if that exact fraction is positive in **Development + External + Reference Validation**.

## Entry-fraction support
An entry fraction is `SUPPORTED` if it has at least **2 ROBUST clocks** among the four frozen ETH-native habitats.

This prevents one excellent clock from defining ETH-wide entry geometry.

## Entry-family topology gate
Supported fractions are ordered by the preregistered 5-percentage-point grid. A qualifying ETH-native entry family requires:
1. at least **2 adjacent SUPPORTED entry fractions**; and
2. at least **2 robust clocks** represented within that adjacent family.

No highest-WR or highest-PF isolated fraction may be promoted over this topology rule.

## Reporting
For each fraction report:
- robust clock count and labels;
- Development / External / Reference Validation median WR and PF across the four frozen clocks;
- median N and raw opportunity-density diagnostic;
- whether the fraction is SUPPORTED.

Also report every robust clock/fraction pair.

## BTC benchmark — diagnostic only
BTC B27DX corrected LONG final benchmark is frozen as:
- WR **71.9%**;
- PF **2.22**;
- expectancy **+$1.26/trade**;
- max loss streak **3**.

S2 must report the gap to these values, but **BTC-level performance is not a promotion gate at entry-only stage** because target/invalidation remain intentionally frozen. Final ETH acceptance later must meet or exceed BTC-quality expectations after trade-geometry and portfolio-lock calibration.

## Decision states
- `ETH_S2_NATIVE_ENTRY_FAMILY_SUPPORTED` — qualifying adjacent supported entry family exists.
- `ETH_S2_SUPPORTED_ENTRIES_NO_FAMILY` — supported fractions exist but are isolated.
- `ETH_S2_NO_SUPPORTED_ENTRY` — no fraction is robust across at least two clocks.

## Guardrails
- Do not optimize TP, stop, runner, leverage, or lifecycle duration.
- Do not choose a fraction by maximum PF/WR alone.
- Do not use raw opportunity density as a selection gate.
- Do not use H/H2 as a selection gate.
- Do not modify live BBC code.
