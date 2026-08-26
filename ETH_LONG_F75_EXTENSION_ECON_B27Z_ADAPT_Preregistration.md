# ETH LONG B27Z-Adapt — F75 Extension Economic Backtest — Preregistration

## Purpose
Adapt BTC B27Z economics to the ETH-specific LONG structure already frozen by B27Q/W/X/Y.

Frozen cohort:
- ETHUSDT
- LONDON_TO_NEWYORK LONG
- K1 OPP0
- causal leave after first High-touch episode
- F75 pre-H2 entry
- exact B27W-Adapt F75 fill identity
- H2 remains a milestone, not TP

## Frozen target grid
Chosen from the completed ETH B27Y-Adapt atlas before economic execution:
- E05 = H + 0.05R
- E10 = H + 0.10R
- E15 = H + 0.15R

Reason: with F75 entry these correspond to gross reward distances of 0.30R, 0.35R, and 0.40R from entry, while still spanning the high-reach plateau observed across all three major partitions. No target outside this grid may be introduced after economic results are seen.

## Frozen close-invalidation grid
Chosen from the completed ETH B27X-Adapt MAE audit before economic execution:
- D30 -> boundary F45
- D40 -> boundary F35
- D50 -> boundary F25
- D60 -> boundary F15

Invalidation is completed-5m close strictly below the frozen boundary; wick-only penetration does not exit. Exit price is the actual close.

## Chronology
For every target/boundary pair:
1. Position is active from the exact B27W F75 entry.
2. On the entry bar, completed-close invalidation may occur after entry.
3. From subsequent bars, intrabar target touch fills the target before any same-bar completed-close invalidation.
4. H2 does not exit the trade.
5. If neither target nor invalidation occurs by session end, exit at the first available 5m open at session end.
6. No post-session event is used.

## Economics
- notional USD 500
- round-trip fee USD 0.40
- net PnL = gross return * 500 - 0.40
- win = net PnL > 0

## Frozen screen
A pair passes only if the exact same target/boundary pair has in external, development, and reference_validation:
- at least 30 trades each
- WR >= 70%
- positive net expectancy
- PF >= 1.20

August is telemetry only and cannot rescue a failed pair.

If multiple pairs pass, rank by:
1. highest minimum PF across major partitions;
2. highest minimum expectancy;
3. higher pooled-major net PnL.

No new target, boundary, clock, entry confirmation, candle filter, EMA, ATR, volume, regime, or runner may be introduced in B27Z-Adapt.

Research only; no live changes.