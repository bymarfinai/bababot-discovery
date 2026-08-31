# ETH B27DX V2 — M1 Habitat Discovery — Preregistration

## Objective
Identify ETHUSDT UTC execution habitats that show repeatable **economic trading edge** under the frozen BTC B27DX causal architecture.

M1 optimizes **time habitat only**. It does not optimize H/H2 rate and does not claim final ETH parameters.

## Frozen causal architecture
Same causal chronology as BTC B27DX / ETH V2:
- completed 5m bars only;
- reference range completes before execution and H/L freeze afterward;
- K1 OPP0 first one-sided boundary visit;
- completed non-touch leave required;
- first eligible entry bar is the next 5m bar after leave completion;
- entry must occur before same-side second arrival, opposite strict close-break, or session end;
- no future veto / no look-ahead.

## M1 search variable
Execution start is tested every hour UTC:
00:00 through 23:00.
LONG and SHORT are scored independently.

## Frozen economic probe for M1 only
These values are diagnostic probes, not final ETH parameters:
- reference duration: 5h30m;
- execution horizon: 6h30m;
- target: E20;
- completed-close invalidation: LONG F35 / SHORT F65;
- LONG entry probes: F90, F85, F80;
- SHORT mirrors: F10, F15, F20;
- $500 illustrative notional;
- $0.40 round-trip fee;
- weekday execution starts only.

Exit evaluation starts on the bar after entry to avoid same-bar ordering assumptions.

## Partitions
- external: 2020-01-01 to 2022-01-01
- development: 2022-01-01 to 2025-01-01
- reference_validation: 2025-01-01 to 2026-07-30
- august: diagnostic only

Only development ranks habitats.

## Development habitat screen
For each `side × UTC hour`, score all 3 entry probes.
A probe is positive when:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

A habitat advances only if at least **2 of 3 probes** are positive.
Rank advancing habitats by:
1. number of positive probes;
2. median PF across 3 probes;
3. median expectancy across 3 probes;
4. total N.

Advance maximum top 4 habitats per side.

## Validation habitat screen
For each advanced habitat, re-score all 3 frozen probes on external and reference_validation.
A habitat is M1-supported only if, in **each** validation partition:
- at least 2 of 3 probes have N >= 15;
- at least 2 of 3 probes have PF > 1.00, expectancy > 0, and net > 0.

M1 output is a shortlist of supported UTC habitats. Entry geometry, reference duration, target and invalidation remain unfrozen for later milestones.

Research only. No live BBC changes.
