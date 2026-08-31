# ETH B27DX V2 — M1B Clock / Habitat Stability — Preregistration

**Status:** PREREGISTERED before any M1B result-bearing rescore.

## Objective
Test whether the ETH M1-supported LONG execution start at **16:00 UTC** is part of a locally stable temporal habitat rather than an isolated hourly-grid winner.

M1B calibrates **clock stability only**. It does not optimize reference duration, entry geometry, target, invalidation, H/H2 rate, or final ETH parameters.

## Frozen causal architecture
Exactly the same completed-bar causal chronology as ETH B27DX V2 / M1:
- completed 5m bars only;
- reference range completes before execution and H/L freeze afterward;
- K1 OPP0 first one-sided boundary visit;
- completed non-touch leave required;
- first eligible entry bar is the next 5m bar after leave completion;
- entry must occur before same-side second arrival, opposite strict close-break, or session end;
- no future veto / no look-ahead;
- exit evaluation starts on the bar after entry.

## Frozen diagnostic economics
No economic parameter may change from M1:
- reference duration: **5h30m / 330 minutes**;
- execution horizon: **6h30m / 390 minutes**;
- target: **E20**;
- completed-close invalidation: **LONG F35**;
- LONG entry probes: **F90, F85, F80**;
- illustrative notional: **$500**;
- round-trip fee: **$0.40**;
- weekday execution starts only;
- 0 bps stress for habitat identification.

SHORT is not re-optimized in M1B because M1 produced no supported SHORT anchor. M1B is a local stability test around the already-supported **LONG 16:00 UTC** anchor only.

## Search grid
Evaluate every 30 minutes from **14:00 through 18:00 UTC**, inclusive:

`14:00, 14:30, 15:00, 15:30, 16:00, 16:30, 17:00, 17:30, 18:00`.

This search interval and spacing are frozen before results.

## Partitions
Same M1 partitions:
- external: 2020-01-01 to 2022-01-01;
- development: 2022-01-01 to 2025-01-01;
- reference_validation: 2025-01-01 to 2026-07-30;
- august: diagnostic only and cannot affect support.

## Per-clock support rule
For each 30-minute clock point, score all three frozen LONG entry probes.

### Development pass
A probe is development-positive only when:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

The clock point passes development when at least **2 of 3 probes** are development-positive.

### Validation pass
In each of `external` and `reference_validation`, a probe is validation-positive only when:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

The clock point passes a validation partition when:
- at least **2 of 3 probes** have N >= 15; and
- at least **2 of 3 probes** are validation-positive.

A clock point is **SUPPORTED** only when it passes development, external, and reference_validation simultaneously.

## Local habitat gate
M1B supports a stable local ETH habitat only if all of the following hold:
1. **16:00 UTC itself remains SUPPORTED** under the exact M1B rescore;
2. there are at least **3 consecutive SUPPORTED 30-minute clock points**;
3. that consecutive run **contains 16:00 UTC**;
4. therefore the supported contiguous width is at least **60 minutes from first to last clock point** (for example 15:30, 16:00, 16:30).

No isolated winner, non-contiguous collection, or run that excludes 16:00 qualifies as local habitat support.

## Reporting
Persist:
- probe-level scores for every grid point and partition;
- clock-level pass/fail summary;
- the contiguous supported run containing 16:00, if one exists;
- diagnostic August scores separately;
- final status.

Possible terminal statuses:
- `ETH_M1B_LOCAL_HABITAT_SUPPORTED`;
- `ETH_M1B_ANCHOR_SUPPORTED_BUT_ISOLATED`;
- `ETH_M1B_ANCHOR_NOT_SUPPORTED`.

## Interpretation
A supported M1B habitat freezes only the **ETH temporal neighborhood** for the next milestone. Reference duration, final entry geometry, target and invalidation remain deliberately unfrozen and must be calibrated later without using August as a selection partition.

Research only. No exchange writes and no live BBC changes.
