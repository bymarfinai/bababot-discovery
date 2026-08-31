# ETH B27DX V2 — M1C Time × Reference Duration Topology — Preregistration

**Status:** PREREGISTERED before result-bearing rescore.

## Trigger
M1 coarse discovery supported LONG 16:00 UTC, but M1B local 30-minute rescore found the anchor isolated: 15:30 and 16:30 looked strong in development yet failed the frozen validation gate. This means execution clock alone is not yet a stable ETH habitat.

## Objective
Test whether ETH's transferable B27DX structure appears as a **coherent 2D structural region** across execution clock × reference duration rather than as one isolated clock point.

This milestone calibrates **structural geometry only**. It does not optimize H/H2, final entry geometry, target, stop, leverage, fees, or position sizing.

## Frozen causal grammar
The BTC B27DX causal architecture remains unchanged:
- completed 5m bars only;
- reference range completes before execution and H/L freeze afterward;
- K1 OPP0 first one-sided boundary visit;
- completed non-touch leave required;
- first eligible entry bar occurs only after leave completion;
- entry must occur before same-side second arrival, opposite strict close-break, or session end;
- no future-dependent veto and no look-ahead;
- same corrected causal window resolver used by ETH B27DX V2/M1/M1B.

## Frozen diagnostic economics
These remain probes only, not final ETH parameters:
- side: LONG only;
- execution horizon: 390 minutes;
- target: E20;
- completed-close invalidation: F35;
- entry probes: F90, F85, F80;
- $500 illustrative notional;
- $0.40 round-trip fee;
- weekday execution starts only;
- exit evaluation starts on the bar after entry.

## M1C search variables
Only two variables move:

### Execution clock grid
14:00 through 18:00 UTC inclusive, every 30 minutes:
`14:00, 14:30, 15:00, 15:30, 16:00, 16:30, 17:00, 17:30, 18:00`.

### Reference duration grid
240 through 420 minutes inclusive, every 30 minutes:
`240, 270, 300, 330, 360, 390, 420` minutes.

The original M1/M1B anchor cell is `16:00 × R330`.

## Partitions
Unchanged from M1/M1B:
- external: 2020-01-01 to 2022-01-01;
- development: 2022-01-01 to 2025-01-01;
- reference_validation: 2025-01-01 to 2026-07-30;
- august: diagnostic only.

August never affects support.

## Frozen probe gates
For each clock × reference cell, score F90/F85/F80 independently.

Development-positive probe:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

Validation-positive probe on each of external and reference_validation:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

A cell is **SUPPORTED** only when all three major partitions independently have at least 2/3 positive probes (and validation partitions have at least 2/3 probes with N >= 15).

No cell is selected by maximum PF, maximum WR, H/H2 rate, or pooled-only economics.

## Preregistered topology gate
Treat supported cells as nodes on the fixed 30-minute × 30-minute grid. Two cells are adjacent only if exactly one coordinate changes by one grid step (4-neighbor adjacency; no diagonal-only connection).

Find the connected supported component containing the original anchor cell `16:00 × R330`.

M1C supports a **coherent structural topology** only if:
1. the original `16:00 × R330` anchor remains SUPPORTED;
2. its connected supported component contains at least **3 cells**;
3. the component spans at least **2 distinct execution clocks**; and
4. the component spans at least **2 distinct reference durations**.

This prevents a lone optimum, a purely clock-only stripe, or a purely duration-only stripe from being called pair geometry.

## Secondary diagnostic: reference-start anchor
For every supported cell compute `reference_start_clock = execution_clock - reference_duration` modulo 24h.
This is explanatory telemetry only. It does not alter the support gate.

If a coherent component exists, report whether its cells cluster around a common reference-start clock. Do not retroactively change the grid or support thresholds.

## Decision
- `ETH_M1C_TOPOLOGY_SUPPORTED` if all topology gates pass.
- `ETH_M1C_ANCHOR_SUPPORTED_NO_TOPOLOGY` if the anchor remains supported but its component fails the topology gates.
- `ETH_M1C_ANCHOR_NOT_SUPPORTED` if the anchor itself fails.

Only after `ETH_M1C_TOPOLOGY_SUPPORTED` may downstream work freeze a structural habitat and move to entry/target/invalidation calibration. If not supported, do not sharpen execution clock, entry fraction, or TP/SL around the isolated winner.

Research only. No exchange writes and no live BBC changes.
