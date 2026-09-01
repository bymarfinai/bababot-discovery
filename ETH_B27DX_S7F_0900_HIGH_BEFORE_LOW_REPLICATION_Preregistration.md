# ETH B27DX — S7F 09:00 HIGH_BEFORE_LOW Historical Replication — Preregistration

## Evidence label
Exploratory hypothesis generated from inspected S7E Development data.

Observed in S7E Development at 09:00 UTC under frozen R300/X360 · F75/E25/F20:
- `HIGH_BEFORE_LOW`: N 24, WR 79.2%, PF 2.38, expectancy +$1.23, net +$29.53.

Because this direction was not the preregistered S7E promotion hypothesis, S7F does not treat the Development result as validation. It freezes the rule now and opens only the untouched historical replication partitions for accept/reject.

## Frozen rule
- ETH LONG only.
- Execution start: 09:00 UTC only.
- Reference duration: 300 minutes.
- Execution horizon: 360 minutes.
- Entry F75.
- Target E25.
- Completed-close invalidation F20.
- Same B27DX causal grammar and first-eligible chronology.
- Reference range-order filter: `HIGH_BEFORE_LOW`, meaning the first raw 5m occurrence of the final frozen H occurs before the first raw 5m occurrence of the final frozen L.
- No other event-quality filter.
- No runner.
- No alternate geometry, clock, order definition, threshold, leverage or fee change.

## Required parity
Reproduce the persisted S7E 09:00 Development `HIGH_BEFORE_LOW` result before interpreting replication:
- N 24,
- WR 79.1666667%,
- PF approximately 2.38,
- expectancy approximately +$1.23,
- net approximately +$29.53.

Any material mismatch fails the audit.

## Historical replication gate
Score the frozen rule independently on:
1. External (2020-01-01 to 2022-01-01)
2. Reference Validation (2025-01-01 to 2026-07-30)

Each partition must have:
- N >= 10,
- retention >= 20% of 09:00 BASE candidates,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Both partitions must pass for historical replication support.

Retention floor is 20% because the Development hypothesis itself is a categorical minority state (~27%); this threshold is frozen before either validation partition is inspected and is not an optimization sweep.

## Stress and BTC diagnostic
If replication passes:
- report pooled Development + External + Reference Validation for the frozen rule as a diagnostic only,
- report 5 bps adverse execution stress,
- compare to BTC B27DX LONG benchmark WR 71.9%, PF 2.22, expectancy +$1.26/trade.

Do not use pooled metrics to alter the rule.

## Status labels
- `ETH_S7F_DEVELOPMENT_PARITY_FAILED`
- `ETH_S7F_0900_HIGH_BEFORE_LOW_NOT_REPLICATED`
- `ETH_S7F_0900_HIGH_BEFORE_LOW_REPLICATED_BELOW_BTC`
- `ETH_S7F_0900_HIGH_BEFORE_LOW_REPLICATED_BTC_CLASS`

Research only. No live-code changes.
