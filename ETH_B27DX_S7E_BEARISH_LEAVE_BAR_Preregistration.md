# ETH B27DX — S7E Bearish Leave-Bar Quality — Preregistration

## Purpose
Test one scale-free causal rejection-quality discriminator: after the H-side K1 episode ends, does a bearish completed leave candle identify higher-quality LONG retrace setups?

No prior gate is relaxed. S7E introduces no numeric threshold.

## Frozen strategy
- LONG, R300, X360.
- Clocks 05:00, 09:00, 10:00, 16:00 UTC.
- F75 entry, E25 target, F20 completed-close invalidation.
- Same data, partitions, weekdays, fees, notional, corrected B27DX chronology and global lock semantics as S7A-S7D.
- No runner, leverage, or live-code changes.

## Feature
`leave_bar_start` is returned by the corrected causal B27DX state machine and is completed before `eligible_start`.

Define `BEARISH_LEAVE_BAR` when the completed leave candle has `close < open`.

The condition is fully known before the first legal post-leave entry bar. No body-size, wick-size, or close-location threshold is tested.

BASE is reported but cannot be promoted.

## Development promotion gate
For each clock independently:
- N >= 20,
- retention >= 50%,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

## Replication gate
Only Development-promoted clocks are opened in External and Reference Validation. Both independently require:
- N >= 10,
- retention >= 40%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

## Portfolio
Replicated filtered clocks only; rerun one-position chronological lock. Report 0 bps and 5 bps.

## BTC-quality diagnostic
Pooled-major 0 bps: WR >=71.9%, PF >=2.22, expectancy >=+$1.26/trade, each major partition PF>1/net>0, pooled 5 bps PF>=1/net>=0.

## Statuses
- `ETH_S7E_CAUSAL_AUDIT_FAILED`
- `ETH_S7E_NO_DEV_BEARISH_LEAVE_FILTER`
- `ETH_S7E_DEV_FILTERS_NOT_REPLICATED`
- `ETH_S7E_BEARISH_LEAVE_FILTERS_REPLICATED_BELOW_BTC`
- `ETH_S7E_BEARISH_LEAVE_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only.