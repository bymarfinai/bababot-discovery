# BNB B39-S1 — Real Expansion Universe Preregistration

## Objective
Build a detector-independent universe of economically meaningful long-side expansion events from the full frozen H1-demand / 15m-touch structural family.

B39-S1 does NOT search for a detector, entry filter, TP rule, or optimized threshold.
It only labels what happened after a causal structural opportunity became observable.

## Parent universe
Use the same causal H1 demand-zone + 15m visual-family construction used in B38:
- H1 demand zones
- first 15m touch
- visual-family requirements frozen from `bnb_b38_s1_lower_tf_demand_rebound.py`
- full history from 2022-01-01 through the latest accepted raw-data endpoint
- DEV = 2022-2024
- REF = 2025-2026

Expected parent parity from prior frozen work:
- DEV visual family: 788
- REF visual family: 463
- total: 1,251

No E2 detector requirement is applied.

## Causal event anchor
The opportunity becomes observable only at completion of the first 15m demand-touch bar.

For each event:
- `anchor_ts = first_touch_ts`
- `anchor_price = touch_close`
- `structural_floor = demand_low`
- `risk_unit = anchor_price - demand_low`

Require `risk_unit > 0`.

This risk unit is an event-normalization unit for discovery, NOT a final trade entry/SL recommendation.

## Path start and invalidation
Path measurement begins strictly after the completed 15m anchor bar.

Hard invalidation:
- first subsequent raw 5m bar whose low touches or breaks `demand_low`.

The invalidation bar is excluded from MFE/MAE because intrabar ordering is unknown.

## Expansion measurements
For every event measure:
- MFE and MAE through 4h, 12h, 24h, and pre-invalidation
- first-touch time for +0.50R, +0.75R, +1.00R, +1.50R, +2.00R
- whether each threshold is reached before invalidation
- adverse excursion observed before each successful threshold touch
- time-to-threshold
- peak time and giveback

## Frozen outcome labels
Primary 24h label based only on post-anchor path before hard invalidation:

- `FAILURE`: MFE < 0.50R
- `LOCAL_ONLY`: 0.50R <= MFE < 1.00R
- `EXPANDER_1R`: 1.00R <= MFE < 1.50R
- `STRONG_EXPANDER`: 1.50R <= MFE < 2.00R
- `EXTREME_EXPANDER`: MFE >= 2.00R

Additional non-exclusive clean-expansion flags:
- `CLEAN_0_75R`: +0.75R reached before first -0.50R adverse excursion
- `CLEAN_1R`: +1.00R reached before first -0.50R adverse excursion
- `CLEAN_1_5R`: +1.50R reached before first -0.50R adverse excursion

These clean flags are diagnostics; no detector is selected from them in S1.

## Real-liquidity objectives known at anchor
Audit causal objectives already known by anchor time:
1. prior frozen 15m `expansion_high` when above anchor
2. nearest confirmed H1 pivot high above anchor
3. `major_nearest = min(expansion_high, h1_nearest)` when available

For each objective report:
- distance in event R
- hit before invalidation
- hit within 24h
- time to hit

No future pivot is allowed.

## Required outputs
- parent parity and year census
- class counts/rates DEV vs REF and by year
- MFE/MAE distributions by class
- threshold reach rates DEV vs REF
- clean-expansion rates
- time-to-expansion distributions
- causal liquidity-objective reach map
- cross-period stability of the outcome distribution

## Interpretation boundary
B39-S1 answers only:
"What post-touch moves are economically large enough to deserve backward structural discovery?"

It does NOT answer:
- which setup to trade
- where to enter
- where to place final SL
- which TP policy to use

B39-S2 may only study structural anatomy after this universe is frozen.
