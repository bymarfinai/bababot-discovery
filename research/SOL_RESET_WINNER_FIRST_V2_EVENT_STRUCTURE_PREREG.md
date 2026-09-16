# SOL Reset — Winner-First V2 Event-Relative Structure Preregistration

## Purpose
Test whether economically meaningful SOL LONG winners share repeatable **event-relative precursor sequences** even when their raw 5m candle paths are not geometrically similar.

This is a representation test. It is not a TP/SL optimization, hour search, cluster-count sweep, precursor-length sweep, or rescue of Winner-First V1.

## Frozen research universe
- Pair: SOLUSDT Binance Futures 5m.
- Research data: 2020-01-01 <= timestamp < 2025-01-01.
- `2025+` remains CLOSED.
- Decision opportunities: every :00, :15, :30, :45 UTC.
- Precursor window: 24 completed 5m bars = 120 minutes, ending at the signal candle.
- Hypothetical entry: next 5m open.
- Future diagnostic window: 60 minutes / 12 bars.
- Round-trip cost: 0.15%.
- Notional: $500.
- Walk-forward test years: 2022, 2023, 2024.
- Training window: prior 2 calendar years only; outcomes must be fully known before the test-year boundary.

## Frozen clean-LONG winner definition
Identical to Winner-First V1:
- trailing volatility known at signal = prior 24h 5m log-return SD scaled to 60m;
- adaptive upside barrier = `max(0.75%, 1.5 * trailing_sigma60_pct)` above entry;
- downside diagnostic barrier = `0.50 * upside_barrier_pct` below entry;
- clean LONG winner = upside barrier touched within +60m before downside barrier;
- same-bar up/down first touch is conservatively NOT a winner.

No TP/SL trading policy is implied by these diagnostic barriers.

## Event-relative precursor representation
Raw candle position-to-position similarity is discarded. Each 120m precursor is converted to an ordered structural-event stream using only bars completed by signal time.

### Structural event types
1. `HH` — confirmed local pivot high above previous confirmed pivot high.
2. `LH` — confirmed local pivot high at/below previous confirmed pivot high.
3. `HL` — confirmed local pivot low above previous confirmed pivot low.
4. `LL` — confirmed local pivot low at/below previous confirmed pivot low.
5. `SWEEP_LOW_RECLAIM` — current low takes the prior 6-bar low and current close reclaims above that prior low.
6. `SWEEP_HIGH_REJECT` — current high takes the prior 6-bar high and current close rejects below that prior high.
7. `BULL_DISP` — bullish body >= 1.5x median absolute body of the prior up-to-12 bars and candle close-location >= 0.65.
8. `BEAR_DISP` — bearish body magnitude >= 1.5x median absolute body of the prior up-to-12 bars and candle close-location <= 0.35.

### Pivot confirmation
- order = 2 bars on each side;
- a pivot event is emitted only when both right-side confirmation bars already exist inside the completed precursor window;
- therefore no post-signal information is used.

### Event stream encoding
- Collect all emitted events chronologically.
- If multiple events occur on the same bar, deterministic order is: sweep-low, sweep-high, pivot-high, pivot-low, bull-displacement, bear-displacement.
- Keep the **12 most recent events** before the signal.
- Each event slot contains:
  - one-hot event identity including `NONE` padding;
  - event recency as `(signal_bar - event_bar) / 24`;
  - event strength, clipped to a fixed finite range.
- Add frozen summary counts for each of the 8 non-NONE event types across the 120m precursor.
- No hour/day/session variables are allowed in family discovery.

## Winner-family discovery
Identical family architecture to V1 except for the representation:
- RobustScaler fit on training opportunities only.
- MiniBatchKMeans fit **only on clean winners**.
- Number of families: 12.
- random_state: 42.
- Family radius: 75th percentile of training-winner distance within each family.
- All training/test opportunities are assigned to nearest winner-family centroid.

## Frozen family eligibility gate — training only
A family is eligible only if all hold inside the training fold:
- within-radius match N >= 80;
- clean-winner precision lift >= 1.50x training baseline;
- fixed +60m net expectancy > 0;
- fixed +60m PF >= 1.10;
- at least one training year has >=20 matched cases;
- every represented training year with >=20 cases has non-negative +60m expectancy.

No family eligibility rule may use the test year.

## OOS selection
For each test opportunity:
- assign nearest winner-family using the frozen training scaler/centroids;
- require distance <= frozen family radius;
- require family was training-eligible;
- selected LONG = both conditions true.

## Frozen success gates — pooled OOS 2022-2024
All must pass:
1. selected OOS N >= 100;
2. clean-winner precision lift >= 1.50x OOS baseline;
3. fixed +60m net expectancy > 0;
4. fixed +60m PF >= 1.15;
5. positive selected PnL in at least 2 of 3 test years;
6. median MFE/|MAE| >= 1.25;
7. at least 2 distinct selected family keys across OOS folds.

## Stop rule
If V2 fails, do NOT rescue it on 2022-2024 by sweeping:
- pivot order;
- 6-bar sweep lookback;
- displacement multiplier / close-location threshold;
- event-slot length;
- number of families;
- family radius;
- family support;
- winner barriers;
- precursor length;
- hour/session filters;
- future horizon;
- TP/SL.

A failed V2 requires a new semantic hypothesis, not retuning this representation.
