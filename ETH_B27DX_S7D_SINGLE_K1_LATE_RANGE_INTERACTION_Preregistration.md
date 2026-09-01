# ETH B27DX — S7D Single-K1 × Late-Range Interaction — Preregistration

## Evidence label
Exploratory interaction generated from already-inspected historical evidence:
- S7A showed `RANGE_COMPLETED_SECOND_HALF` / related early-event combinations generally improved PF in several ETH habitats but did not meet the frozen Development promotion gate.
- S7C showed `SINGLE_BAR_K1_EPISODE` materially outperformed its multi-bar complement in 05:00, 09:00 and 10:00 Development, but WR remained below the promotion gate.

S7D tests exactly one interaction between those two independently observed causal features. It is not pristine OOS evidence.

## Frozen signal/economic layer
- ETH LONG.
- R300/X360.
- Execution starts 05:00, 09:00, 10:00, 16:00 UTC.
- F75 entry / E25 target / F20 completed-close invalidation.
- Same B27DX causal grammar, data, partitions, sizing, fees and first-eligible chronology as S7A/S7C.

## Frozen features
1. `SINGLE_BAR_K1_EPISODE`: exactly one raw 5m same-side K1 boundary-touch bar before the causal leave.
2. `RANGE_COMPLETED_SECOND_HALF`: the final frozen reference H/L range is completed at/after minute 150 of the 300-minute reference window.
3. `SINGLE_K1__LATE_RANGE`: both conditions are true.

No alternate K1 episode length, range-completion cutoff, OR/AND logic, clock, entry, target or stop is tested.

For context only, report BASE and each individual feature. Only `SINGLE_K1__LATE_RANGE` is eligible for promotion.

## Required parity / causal audit
- S7A and S7C candidate universes must merge one-to-one on partition, execution clock, execution start and entry bar.
- 0 bps and 5 bps PnL must match between the source candidate sets.
- Range completion is known before execution starts.
- K1 episode classification is known by entry.
- No terminal/future information is used.

## Frozen Development promotion gate
The interaction advances for a clock only if Development has:
- N >= 20,
- retention >= 50% of BASE,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

No fallback candidate is selected if the gate fails.

## Historical replication gate
Only Development-promoted clocks are opened to External and Reference Validation.
Each must have:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Both partitions must pass.

## Portfolio / BTC gate
If one or more clocks replicate, combine only those interaction-filtered candidates and rerun the global one-position chronological lock.
Report 0 and 5 bps.
BTC-quality benchmark remains WR 71.9%, PF 2.22, expectancy +$1.26/trade, all major partitions positive, and 5 bps pooled PF >=1 with non-negative net.

## Status labels
- `ETH_S7D_PARITY_OR_CAUSAL_AUDIT_FAILED`
- `ETH_S7D_NO_DEV_INTERACTION`
- `ETH_S7D_DEV_INTERACTIONS_NOT_REPLICATED`
- `ETH_S7D_INTERACTION_REPLICATED_BELOW_BTC`
- `ETH_S7D_INTERACTION_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only; no live-code changes.
