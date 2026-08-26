# ETH LONG B27DE-Adapt — Generic F75 LONG Clock-Rotation Scan — Preregistration

## Purpose
Adapt BTC B27DE to ETH by rotating only the reference-window clock while preserving the ETH-specific structure already frozen in B27Q/W/AA/Z.

## Frozen instrument / source / partitions
- ETHUSDT perpetual, raw 5m Binance source.
- same frozen partitions:
  - external: 2020-01-01 to 2022-01-01 UTC
  - development: 2022-01-01 to 2025-01-01 UTC
  - reference_validation: 2025-01-01 to 2026-07-30 UTC
  - august: 2026-08-01 to 2026-08-21 UTC
- weekdays only by execution-window start.
- complete reference+execution windows must fit inside one partition.

## Frozen clock geometry
Preserve BTC/ETH London baseline durations exactly:
- reference duration 5h30m
- execution duration 6h30m immediately after reference
- scan reference start every 30 minutes across 24h: 48 placements
- known London parity cell = 08:00 reference -> 13:30 execution.

No duration sweep, 15-minute refinement, or neighbor rescue in this milestone.

## Frozen generic ETH LONG structure
For each reference range H/L:
1. first distinct High visit K1 while zero Low visits occurred (K1 OPP0);
2. K1 touch episode causally ends with a completed non-touch bar;
3. only after leave completion is pullback search eligible;
4. H2 = first later high>=H; close<L is opposite structural terminal;
5. both-level ambiguous bars are rejected.

## Frozen ETH-specific entry
- F75 = L + 0.75R (selected B27W-Adapt)
- EARLY_RECLAIM confirmation (primary B27AA-Adapt semantics): first F75-touch bar or first later eligible pre-H2 bar whose completed close > F75
- entry = next raw 5m open
- reject if entry open >= H
- require F15 < entry < H

Only the clock rotates; F75 and confirmation semantics do not.

## Frozen economics
- target E10 = H + 0.10R
- completed-close invalidation below F15 = L + 0.15R, exit at actual close
- E10 is resting intrabar target and takes precedence over same-bar close invalidation on later bars
- unresolved trades exit at execution-window-end open
- notional USD 500, round-trip fee USD 0.40

No B27AG BEAR regime filter in the clock scan. Regime attribution may be applied only in a later preregistered milestone.

## Mandatory London parity
08:00 cell must reproduce B27AA-Adapt EARLY_RECLAIM exact executed entries and economics:
- external N40, WR72.5%, PF ~1.21, net ~+$20.02
- development N54, WR74.1%, PF ~1.07, net ~+$8.00
- reference_validation N28, WR71.4%, PF ~1.02, net ~+$1.75
- august N2
Exact entry timestamps must match persisted B27AA-Adapt rows.

Any parity failure aborts interpretation.

## Development-only clock selection
A non-08:00 clock is DEV_ELIGIBLE only if development has:
- N >=25 executed trades
- WR >=70%
- PF >=1.30
- positive expectancy

Select one primary new clock by:
1. highest PF
2. higher WR
3. higher expectancy
4. larger N
5. earlier UTC start.

## Historical replication
After development-only selection, tag `HISTORICAL_REPLICATION_SUPPORTED` only if selected clock has:
- external N>=15, WR>=65%, PF>=1.20, expectancy>0
- reference_validation N>=10, WR>=65%, PF>=1.20, expectancy>0

These are reused historical partitions, not pristine OOS.

Research only; no live changes.