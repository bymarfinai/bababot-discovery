# ETH B27DX — S8L Loss Anatomy — Preregistration

## Purpose
Explain why the frozen executable ETH portfolio loses trades before proposing any new filter, geometry, runner, or regime rule.

This is an attribution/diagnostic study, not an optimization study.

## Frozen strategy universe
- LONG only.
- R300 / X360.
- Entry F75.
- Target E25.
- Completed-close invalidation F20.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Global one-position lock exactly as S4.
- Partitions remain External, Development, Reference Validation.
- 0 bps is primary; existing 5 bps stress is not re-optimized.

## Primary question
Among S4 accepted executable trades, what characteristics distinguish losses from wins?

## Causal pre-entry feature set — frozen before results
No threshold sweep is allowed. Continuous features are analyzed as distributions, not converted into optimized cutoffs.

### Pre-reference context
1. 4h return before reference start.
2. 24h return before reference start.
3. 24h realized close-to-close volatility.
4. 24h high-low range as percent of starting price.

### Frozen reference anatomy
5. Reference net return.
6. Reference range as percent of opening price.
7. Reference closing location inside L-H.
8. Final range-completion time as fraction of the 300m reference.
9. Time spacing between first H and first L as fraction of reference.
10. Formation order: HIGH_BEFORE_LOW vs LOW_BEFORE_HIGH.

### K1 / leave / retrace anatomy
11. K1 start time as fraction of X360.
12. Leave time as fraction of X360.
13. Number of contiguous K1 touch bars before leave.
14. Maximum K1-episode overshoot above H, normalized by R.
15. Leave-bar drop below H, normalized by R.
16. K1-to-fill delay as fraction of X360.
17. Eligible-after-leave-to-fill delay as fraction of X360.
18. Single-bar K1 episode indicator.

Natural categorical diagnostics may additionally report whether pre-4h/pre-24h/reference return is positive and whether reference closes in its upper half. These are descriptive natural splits only; they cannot be promoted as rules in S8L.

## Ex-post loss-path diagnostics — NOT entry features
These are explicitly non-causal diagnostics and cannot be used to filter entries in this study:
- exit reason,
- holding time,
- maximum favorable excursion (MFE/R),
- maximum adverse excursion (MAE/R),
- MFE as fraction of fixed target distance.

Their purpose is to identify whether losses are immediately wrong, fail by timeout, or nearly reach target before reversing.

## Association scoring
### Continuous features
For each partition and pooled-major, compute a rank-based loss association effect:
- effect = 2*AUC(loss-higher-than-win) - 1.
- positive = feature tends to be higher on losses.
- negative = feature tends to be lower on losses.

A feature is called `DIRECTIONALLY_REPLICATED` only when:
- every major partition contains at least 5 losses and 5 wins with non-missing values for that feature,
- effect sign is the same in External, Development, and Reference Validation,
- |effect| >= 0.05 in each partition,
- pooled-major |effect| >= 0.15.

This criterion is frozen before results and does not create a trading cutoff.

### Binary/categorical features
Report loss rate by category and risk ratio. A binary association is called directionally replicated only if:
- both binary groups contain at least 5 observations in every major partition,
- risk-ratio direction agrees across all three partitions,
- each partition differs from 1.0 by at least 5%,
- pooled risk ratio is at least 1.25 or at most 0.80.

## Required outputs
- accepted-trade feature dataset,
- loss concentration by clock and partition,
- continuous loss-association table,
- categorical loss-association table,
- ex-post loss-path table,
- causal/parity audit,
- written result identifying replicated associations and explicitly separating causal pre-entry evidence from ex-post diagnostics.

## Guardrails
- No new entry/target/stop/runner values.
- No feature cutoff optimization.
- No choosing the best historical subset.
- No use of future-dependent information as an entry explanation.
- No live-code change.
- Any S8L finding is a hypothesis for a separately preregistered validation experiment; it is not automatically a trading rule.
