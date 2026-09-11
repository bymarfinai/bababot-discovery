# SOL H23 06:45 WIB Anchor-Local Forward Shadow — Preregistration Amendment 1

## Reason for amendment

The first execution attempt stopped at the explicit data-completeness guard **before any forward outcomes were calculated or inspected**.

Technical diagnostic from run 34630279437:

- Frozen original target end: `2026-09-12 00:00 UTC` exclusive.
- Required final bar for that target: `2026-09-11 23:55 UTC`.
- Latest complete Binance Vision 5m bar available to the runner: `2026-09-10 23:55 UTC`.
- Runtime stopped with `forward data incomplete`; no forward trade result artifact was produced.

This amendment is therefore based only on source-data availability, not on strategy outcomes.

## Frozen interim cutoff

For the current executable shadow observation, freeze the complete-data subset as:

- Start: **2026-08-01 00:00 UTC**.
- Interim end: **2026-09-11 00:00 UTC exclusive**.
- Required last bar: **2026-09-10 23:55 UTC**.

The original `2026-09-12 00:00 UTC` target remains part of the audit trail and is not reinterpreted as having been tested. This interim run reports only the fully available subset through 2026-09-10.

## Candidate and evaluation rules remain unchanged

No strategy parameter changes are permitted:

- 23:45 UTC / 06:45 WIB only.
- LONG only.
- `DRIVE_DOWN__STR_B80_100`.
- LB15.
- hold120m.
- exact 5m-open entry and exact 5m-open time exit.
- $500 notional and $0.75 round-trip fee.
- same causal state construction.
- N < 40 => `FORWARD_INSUFFICIENT_SAMPLE` regardless of observed economics.
- N >= 40 => evaluate the original frozen supportive gate.

No forward outcome has been used to choose this amended cutoff or to change the candidate.
