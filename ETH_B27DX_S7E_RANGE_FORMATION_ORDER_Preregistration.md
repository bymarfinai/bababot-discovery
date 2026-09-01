# ETH B27DX — S7E Reference Range Formation Order — Preregistration

## Purpose
Test whether LONG B27DX event quality depends on the directional order in which the frozen reference range was formed.

Previous S7 filters improved PF in places but did not raise WR to the frozen promotion gate without excessive retention loss. S7E therefore tests a categorical reference-structure feature known entirely before execution, with no numeric cutoff.

## Frozen signal/economic layer
- ETH LONG.
- R300/X360.
- Execution starts 05:00, 09:00, 10:00, 16:00 UTC.
- F75 entry / E25 target / F20 completed-close invalidation.
- Same B27DX causal grammar, data, partitions, sizing, fees and chronology as S7A–S7D.

## Frozen range-order feature
From the completed 300-minute reference window:
- `low_formation_ts` = first raw 5m bar containing the final frozen L.
- `high_formation_ts` = first raw 5m bar containing the final frozen H.

Categorical anatomy:
1. `LOW_BEFORE_HIGH`: `low_formation_ts < high_formation_ts`.
2. `HIGH_BEFORE_LOW`: `high_formation_ts < low_formation_ts`.
3. `SAME_BAR_EXTREMES`: both final extremes first appear in the same 5m bar (diagnostic only).

For LONG, the preregistered promotion hypothesis is `LOW_BEFORE_HIGH`, representing a reference range whose final low is established before its final high. `HIGH_BEFORE_LOW` and same-bar cases are diagnostics only.

No alternate ordering rule, recency cutoff, price slope, range width, entry, target, stop or clock is tested in S7E.

## Causal/parity audit
- H/L must reproduce the frozen candidate H/L from raw reference bars.
- Both extreme timestamps must be strictly before execution start.
- Feature must be known before execution and therefore before entry.
- Candidate PnL/chronology must remain unchanged versus S7A BASE.

## Frozen Development promotion gate
`LOW_BEFORE_HIGH` advances for a clock only if Development has:
- N >= 20,
- retention >= 50% of BASE,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

No fallback is selected.

## Historical replication gate
Only Development-promoted clocks are opened to External and Reference Validation. Each must have:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.
Both must pass.

## Portfolio / BTC gate
If clocks replicate, combine only their `LOW_BEFORE_HIGH` candidates and rerun global one-position chronological locking at 0 and 5 bps.
BTC benchmark remains WR 71.9%, PF 2.22, expectancy +$1.26/trade; all major partitions must be positive and 5 bps pooled PF >=1 with non-negative net.

## Status labels
- `ETH_S7E_CAUSAL_OR_PARITY_AUDIT_FAILED`
- `ETH_S7E_NO_DEV_RANGE_ORDER_FILTER`
- `ETH_S7E_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7E_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7E_FILTER_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only; no live-code changes.
