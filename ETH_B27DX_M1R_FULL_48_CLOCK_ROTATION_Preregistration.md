# ETH B27DX V2 — M1R Full BTC-Parity 48-Clock Rotation — Preregistration

## Purpose
Close the remaining clock-discovery resolution gap between ETH and the original BTC B27DE lineage.

BTC B27DE scanned the full UTC day in 30-minute increments (48 placements) with a frozen 330-minute reference range and 390-minute execution horizon. ETH M1 scanned all 24 integer UTC execution hours but therefore left the half-hour placements untested outside the later 14:00–18:00 M1B zoom.

M1R performs the full 48-clock ETH rotation before any downstream entry, target, invalidation, or mechanism sharpening.

## Frozen causal grammar
No change from ETH B27DX M1/M1B/M1C:
- completed 5m causality only;
- reference H/L frozen before execution;
- K1 OPP0 semantics;
- completed causal leave before eligibility;
- first causal fill chronology;
- terminal precedence / ambiguity handling;
- no future-dependent veto or look-ahead.

## Frozen diagnostic economics
- Side: LONG only, matching the successful BTC B27DE/B27DQ long operating lineage being replicated.
- Reference duration: 330 minutes (5h30m).
- Execution horizon: 390 minutes (6h30m).
- Entry probes: F90, F85, F80.
- Target: E20.
- Close invalidation: F35.
- Notional: $500.
- Round-trip fee: $0.40.
- Stress slippage: 0 bps in this milestone.
- Weekday execution starts only.
- Exit evaluation starts on the next completed 5m bar as already implemented in the frozen scorer.

## Only variable
Execution clock, every 30 minutes across the complete UTC day:

`00:00, 00:30, 01:00, 01:30, ... , 23:00, 23:30`

Because the reference duration is frozen at 330 minutes, each execution clock uniquely implies a reference start 5h30m earlier. This is mathematically equivalent to the 48-placement clock rotation used by BTC B27DE, expressed in execution-clock coordinates.

## Historical partitions
Same frozen ETH partitions:
- external: 2020-01-01 to 2022-01-01;
- development: 2022-01-01 to 2025-01-01;
- reference_validation: 2025-01-01 to 2026-07-30;
- August 2026: diagnostic only and never affects support.

## Per-probe gates
Development probe positive only if all are true:
- N >= 30;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

External/reference-validation probe positive only if all are true:
- N >= 15;
- PF > 1.00;
- expectancy > 0;
- net > 0.

## Clock support gate
A clock is `SUPPORTED` only if:
- at least 2/3 probes are positive in Development;
- at least 2/3 probes are positive in External, with at least 2/3 probes having N >= 15;
- at least 2/3 probes are positive in Reference Validation, with at least 2/3 probes having N >= 15.

All 48 clocks are scored in all three major partitions. There is no Development top-k pruning before validation.

## Range / neighborhood reporting
After the frozen support decision only:
- report every supported 30-minute clock;
- group adjacent supported clocks into contiguous 30-minute runs;
- do not invent a broader time range across unsupported gaps;
- do not select a clock merely because it has the highest PF;
- the original 16:00 UTC M1 anchor is reported but receives no special pass privilege.

## Interpretation guardrail
This is still reused historical discovery/replication, not pristine unseen OOS confirmation. Multiple supported clocks may be treated as ETH-native temporal candidates; isolated clocks remain isolated until later mechanism/stability work.

H/H2 remains telemetry only and is not an optimization target.

## Live deployment
Research only. No exchange writes and no live BBC configuration changes.
