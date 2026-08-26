# ETH LONG B27X-Adapt — F75 Winner MAE / Stop-Distance Audit — Preregistration

## Purpose
Follow the BTC B27X milestone on the ETH-specific entry level selected by ETH B27W-Adapt.

Frozen cohort:
- ETHUSDT
- LONDON_TO_NEWYORK LONG
- K1 OPP0
- causal leave after first High-touch episode
- pre-H2 entry at F75 = L + 0.75R
- exact B27W-Adapt fill identities/timestamps

This milestone is diagnostic only. It does not select or promote a stop.

## Measurements
For every filled F75 path:
- classify H2 winner vs non-H2 path exactly as B27W-Adapt;
- for H2 winners, measure adverse excursion from F75 before the H2 bar and conservatively through the H2 bar;
- for non-H2 fills, measure adverse excursion through their structural terminal/session end.

Distance D is measured downward from F75 in prior-London-range units. A hypothetical floor/stop fraction equals 0.75-D.

Frozen survival curve:
D05, D10, D15, D20, D25, D30, D35, D40, D45, D50, D55, D60, D65, D70, D75.
Equality with a stop level counts as stopped.

## Outputs by partition
- number of F75 fills
- H2 winner count
- winner adverse D P50/P75/P90/P95/max pre-H2
- winner adverse D P50/P75/P90/P95/max conservative-through-H2
- winner survival rate at each frozen D
- non-H2 adverse D P50/P75/P90/P95/max

Persist one row per F75 path and the full survival curve.

## Guardrails
- Exact B27W-Adapt F75 fill identity must reproduce.
- No stop is chosen here.
- No TP/runner/clock/filter tuning.
- No live changes.

Research only.