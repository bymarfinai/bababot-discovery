# BTC Weekly 1% Direction Detector B10 — Preregistration

## Purpose
Test whether the weekly 1% opportunity documented by the prior diagnostics can be converted into a causal one-trade-per-complete-week selector. This is a selector experiment, not another confluence-count experiment.

## Core question
At each completed BTCUSDT H1 bar, using only information available through that completed bar, can a frozen model decide which side is more likely to produce a net +1.00% outcome before a net -1.00% outcome from the next H1 open?

## Data and partitions
Official Binance USD-M BTCUSDT H1 archive loaded through the existing repository loader.

- External: 2020-01-01 <= ts < 2022-01-01
- Development/training only: 2022-01-01 <= ts < 2025-01-01
- Reference validation: 2025-01-01 <= ts < 2026-07-30
- August 2026: diagnostic only

Only complete ISO weeks are eligible.

## Execution geometry
Round-trip fee = 0.15%.

The modeled trade target is NET +1.00% and the modeled loss is NET -1.00%, therefore price barriers are frozen as:

- favorable price move: +1.15%
- adverse price move: -0.85%

For SHORT the signs are mirrored. Intrabar TP+SL ambiguity is adverse-first. Entry is always the next H1 open after the completed signal bar. A trade can run only until the end of that same ISO week.

## Labels
For every eligible completed H1 signal bar, evaluate both sides from the next H1 open until the end of the same ISO week using the frozen execution geometry.

- `LONG`: LONG reaches its favorable barrier before its adverse barrier, while SHORT does not win.
- `SHORT`: SHORT reaches its favorable barrier before its adverse barrier, while LONG does not win.
- `NONE`: neither side is an unambiguous winner (including adverse-first same-bar ambiguity).

No future-derived field is allowed in any feature.

## Causal feature set
All features are computed from OHLC available through the completed signal bar only:

1. Multi-horizon close returns: 1, 2, 4, 8, 12, 24, 48 H1 bars.
2. ATR14 / price and current true-range / ATR14.
3. EMA8, EMA21, EMA55 distance from close normalized by ATR14, plus 3-bar EMA slopes.
4. Rolling range position for 12, 24, and 48 bars.
5. Distance to rolling 24-bar high and low normalized by ATR14.
6. Current candle body, upper wick, and lower wick normalized by true range.
7. Current ISO-week running range position, running range size, and return from Monday open.
8. Current UTC-day running range position, running range size, and return from daily open.
9. Previous complete ISO-week high/low distances normalized by ATR14 and previous-week range percentage.
10. Known clock context: UTC hour and weekday encoded with sine/cosine.

No order-flow, derivatives, news, future weekly extremes, future volatility, or future range information may enter the feature matrix.

## Frozen models
Two development-only Random Forest classifiers, both deterministic with `random_state=20260821`:

### Opportunity model
Predicts `decisive = label in {LONG, SHORT}`.

### Direction model
Trained only on decisive development rows. Predicts `LONG` versus `SHORT`.

Hyperparameters for both models are frozen:

- n_estimators = 400
- max_depth = 8
- min_samples_leaf = 50
- max_features = `sqrt`
- class_weight = `balanced_subsample`
- n_jobs = -1

For each signal:

- `p_opp` = probability that one side is decisive
- `p_long` = conditional probability of LONG among decisive rows
- predicted side = LONG if `p_long >= 0.5`, otherwise SHORT
- selector confidence = `p_opp * max(p_long, 1-p_long)`

## Development-only threshold selection
The candidate confidence quantiles are frozen as:

`[0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99]`.

For each candidate quantile, calculate its confidence threshold from development signals only and run the weekly router below on development only.

Choose exactly one threshold by the following ordered objective:

1. highest development weekly win rate;
2. then highest development mean net return;
3. then highest development profit factor;
4. then fewer forced fallbacks;
5. then lower quantile.

The chosen threshold is frozen before any external/reference-validation result is inspected.

## Weekly router
Each complete ISO week is scanned chronologically from Monday 00:00 UTC through Saturday 12:00 UTC completed H1 bars.

- Take the first signal whose selector confidence is >= the frozen threshold.
- Enter its predicted side at the next H1 open.
- Stop scanning after that one trade; maximum one selected trade per week.
- If no threshold trigger has occurred by the Saturday 12:00 completed signal bar, force one trade from that signal using the model-predicted side. This preserves exactly one trade per complete week without retrospective selection.

No earlier signal may be selected retrospectively after observing later confidence scores.

## Reported diagnostics
Per partition report:

- complete weeks / selected trades / coverage
- trigger versus fallback count
- TP / SL / TIME
- weekly win rate
- mean net return
- profit factor
- maximum losing streak
- 4 chronological block results
- per-bar decisive rate
- direction accuracy on decisive rows
- predicted-side realized win rate across all scanned rows

Also persist the selected weekly trades and development threshold table.

## Acceptance gates
### `B10_ROBUST_WEEKLY_100`
PASS only if BOTH external and reference validation satisfy all of:

- 100% complete-week coverage
- exactly one selected trade per complete week
- 100% weekly win rate
- zero losing selected weeks
- positive expectancy
- PF > 1
- every chronological block positive

### `B10_HIGH_PRECISION_WEEKLY`
Secondary PASS only if BOTH external and reference validation satisfy:

- 100% complete-week coverage
- WR >= 80%
- positive expectancy
- PF > 1
- max losing streak <= 2
- at least 3/4 chronological blocks positive

## Anti-rescue / no post-result retuning
After results are generated, do NOT rescue B10 by changing model hyperparameters, feature subset, clock window, target/stop, fee, threshold grid, threshold objective, fallback time, weekday filter, or partition dates. Any such change is a new preregistered experiment.

Live BBC code remains untouched.
