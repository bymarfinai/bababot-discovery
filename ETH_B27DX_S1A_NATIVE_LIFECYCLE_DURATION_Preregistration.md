# ETH B27DX — S1A Native Lifecycle Duration Discovery — Preregistration

## Purpose
Test whether ETH's native B27DX lifecycle is materially different from the BTC-derived 330-minute reference / 390-minute execution template.

S1A calibrates **structural timescale only** at the two ETH execution anchors independently supported by M1R: **09:30 UTC** and **16:00 UTC**.

This is not an entry, TP, stop, runner, leverage, or H/H2 optimization.

## Frozen causal grammar
The following remain unchanged from the B27DX-corrected ETH scorer:
- completed 5m causality only;
- reference H/L frozen before execution;
- K1 OPP0 event identity;
- completed causal leave;
- first eligible pre-terminal retrace fill;
- no future-dependent veto/look-ahead;
- terminal precedence/ambiguity handling;
- exit evaluation begins after the entry/fill bar according to the existing scorer.

## Frozen economics / diagnostic probes
- side: LONG only;
- execution anchors: 09:30 UTC and 16:00 UTC only;
- entry probes: F90, F85, F80;
- target: E20;
- completed-close invalidation: F35;
- notional: $500;
- round-trip fee: $0.40;
- slippage stress: 0 bps for structural discovery;
- weekdays only;
- same historical partitions as M1/M1R.

The three entry levels remain **diagnostic probes**, not candidates to optimize in S1A.

## Structural duration grid
Reference duration (minutes):
- 120, 180, 240, 300, 330, 360

Execution horizon (minutes):
- 180, 240, 300, 360, 390, 420

Total structural cells per anchor: 36.
Total anchor × duration cells: 72.

The legacy BTC-derived point `R330 / X390` is retained only as a benchmark cell.

## Partition scoring
Major partitions:
- development: 2022-01-01 to 2025-01-01;
- external: 2020-01-01 to 2022-01-01;
- reference_validation: 2025-01-01 to 2026-07-30.

August is diagnostic only if reported and never affects support.

### Development probe positive
A probe is positive if all are true:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

A structural cell passes Development if at least 2 of 3 probes are positive.

### Validation probe positive
For each validation partition, a probe is positive if all are true:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

A structural cell passes a validation partition if:
- at least 2 of 3 probes have N >= 15; and
- at least 2 of 3 probes are positive.

### Supported structural cell
A cell is `SUPPORTED` only if it passes:
- Development;
- External; and
- Reference Validation.

No score-maximization override is allowed.

## Topology gate
For each execution anchor independently, supported cells are connected orthogonally on the preregistered grid (adjacent reference duration or adjacent execution horizon).

A **native lifecycle component** requires:
1. at least 3 supported cells;
2. span at least 2 distinct reference durations; and
3. span at least 2 distinct execution horizons.

This prevents a single magic duration or one-dimensional stripe from being called an ETH-native lifecycle family.

## Cross-anchor replication
After per-anchor topology is fixed, report whether the two anchors share any identical supported duration cells and whether their largest supported components overlap in duration space.

Cross-anchor overlap is evidence of a reusable ETH timescale, but it is not required for an anchor-specific native component.

## Opportunity-density diagnostic
For every supported cell, report Development raw opportunity density as:

`median probe N / elapsed Development weeks`.

Also report the sum of the two anchor densities for identical supported duration cells as a **raw two-anchor opportunity-density diagnostic**.

The user's hypothesis that ETH may support roughly ~2 opportunities/week is treated as a diagnostic target, **not a selection gate**. A cell may not be promoted merely because it produces more trades.

## Decision states
- `ETH_S1A_NATIVE_LIFECYCLE_SUPPORTED` — at least one anchor has a qualifying 2D native lifecycle component.
- `ETH_S1A_SUPPORTED_CELLS_NO_2D_FAMILY` — supported duration cells exist but no qualifying 2D component.
- `ETH_S1A_NO_SUPPORTED_DURATION_CELL` — no structural cell survives all historical gates.

## Guardrails
- Do not optimize entry fraction, TP, stop, runner, leverage, or fees in S1A.
- Do not select the maximum PF cell as the answer.
- Do not use H/H2 as a selection gate.
- Do not change live BBC code.
- S1B full 48-clock rotation is allowed only after S1A results are frozen and interpreted.
