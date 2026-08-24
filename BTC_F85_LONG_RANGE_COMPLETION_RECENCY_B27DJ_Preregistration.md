# B27DJ — F85 LONG 05:30 / 23:30 Range-Completion Recency — Preregistration

## Purpose
Test one structural discriminator emerging from the prior winner-vs-loser anatomy of the B27DH 05:30 and 23:30 Development cohorts, without threshold sweeping.

## Frozen populations
Use the exact B27DH source opportunities and semantics for:
- RAW_0530: reference 05:30–11:00 UTC, execution 11:00–17:30 UTC.
- RAW_2330: reference 23:30–05:00+1d UTC, execution 05:00–11:30+1d UTC.

Frozen primary blockers remain the B27DG PRIMARY_2ZONE stream:
- London 08:00 reference, unfiltered Same-Bar F85 baseline.
- ALT_0330 with TOUCH_FIRST_HALF.

All candidate scoring is after combining with the frozen primary stream and applying the same global one-BTC-position lock.

## Frozen structural feature
For every candidate reference window, compute final reference H and L exactly as in B27DE/B27DH from the 66 completed 5m reference bars.

Define:
- `h_formation_ts`: first 5m bar start at which the final reference H is printed.
- `l_formation_ts`: first 5m bar start at which the final reference L is printed.
- `range_completion_ts = max(h_formation_ts, l_formation_ts)`.
- `range_completion_elapsed_min = (range_completion_ts - reference_start) / 1 minute`.
- `range_completion_age_min = (execution_start - range_completion_ts) / 1 minute`.

No post-entry information is used.

## Single preregistered discriminator
`RANGE_COMPLETED_SECOND_HALF`:

`range_completion_elapsed_min >= 165`

The 165-minute boundary is exactly one half of the frozen 330-minute reference window. It is a structural boundary, not an optimized cutoff. No alternate recency threshold may be selected inside B27DJ.

## Development gate
Evaluate RAW_0530 and RAW_2330 separately after the frozen primary lock.

A zone is `DEV_75_SUPPORTED` only if the filtered zone has:
- accepted N >= 20
- accepted retention >= 60% versus the zone raw B27DH population
- WR >= 75%
- PF >= 1.30
- expectancy > 0

If a zone fails any condition, it is not promoted. B27DJ must not rescue it using another cutoff.

## Historical replication gate
External and reference-validation are read only for zones that pass the Development gate.

Each reused historical replication partition must have:
- accepted N >= 10
- accepted retention >= 45%
- WR >= 70%
- PF >= 1.20
- expectancy > 0

Only a Development-supported zone that also passes both reused historical replication partitions can be labeled `HISTORICAL_REPLICATION_SUPPORTED`.

## Portfolio rule
If any zone is historically replication-supported, combine only those supported zones with the frozen B27DG PRIMARY_2ZONE and rescore using the same chronological one-position lock.

No live BBC change is authorized by this experiment.

## Guardrails
- No threshold sweep.
- No zone-specific threshold changes.
- No candle-shape add-on.
- No use of outcome/post-entry variables in the discriminator.
- Development decides eligibility first.
- External/reference-validation are reused historical confirmation, not pristine OOS.
- Research only.