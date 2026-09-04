# SOL LONG 15:00 UTC Native Recovery — A23 Preregistration

## Purpose
Test whether the A20-supported `R360 / 15:00 UTC` SOL parent habitat has a **native** bounded recovery visit. This is not a transfer of A4 H2. The recovery visit is calibrated independently inside the 15:00 habitat.

## Frozen parent
- Symbol: SOLUSDT
- Data: same 5m source/partitions/cost convention as A2/A20
- Central habitat: `R360 / 15:00 UTC`
- Clock support: `R360 / 16:00 UTC`
- Reference support: `R300 / 15:00 UTC`
- Parent family: `E0_RESTING_H`
- Target: `H + 0.40R`
- Lifecycle: frozen A2 semantics
- Maximum recovery watch: 720 minutes

## Recovery family
Exactly one later resting-H recovery entry is tested per losing parent episode:
1. `REC_H2`
2. `REC_H3`
3. `REC_H4`

No averaging, no overlapping retries, no second recovery after the selected recovery trade, and no Stage-11 exit interventions.

Each recovery uses the same H/L/R and E40 target as its parent, with the frozen A4 recovery lifecycle and cost accounting.

## Development gate
A lane is eligible only if:
- recovery N >= 60
- raw PF > 1.15 and raw expectancy/net > 0
- 5bps PF > 1.00 and 5bps expectancy/net > 0
- raw rescue rate >= 20%
- overlay PF and net improve versus parent-only, raw and 5bps
- >=4 adequate half-year Development blocks are positive raw
- >=4 adequate half-year Development blocks are positive after 5bps

Among eligible lanes freeze one by: highest 5bps net, then 5bps PF, raw net, rescue rate, then lower visit number.

## OOS gate
Only the frozen Development winner is tested on Central External + Reference Validation and the frozen A20 clock/reference supports.

Support requires:
- Central External and Central Reference Validation recovery net > 0 raw and 5bps
- Central overlay PF/net improve versus parent-only raw and 5bps
- >=3/4 support cells recovery net > 0 raw
- >=3/4 support cells recovery net > 0 after 5bps

No OOS retuning.

## Decision
A23 can promote at most one native recovery visit for the 15:00 habitat. If none passes Development or OOS, A20 remains parent-only.

Research only. Live Baba Bot remains unchanged.
