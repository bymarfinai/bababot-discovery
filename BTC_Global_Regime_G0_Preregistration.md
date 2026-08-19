# BTC Global/Pooled Regime Engine — G0 Preregistration

**Status: PREREGISTERED BEFORE EXECUTION — research only; live BBC untouched.**

## Why this exists
The Tuesday-only anchored walk-forward gate did not improve economic expectancy and did not reject the Aug 4/11/18 failures. The next hypothesis is deliberately different: learn market state from the full BTC timeline, then use that state as an execution compatibility layer under a frozen temporal prior.

This document locks G0 **before its result is generated**. Any later change to labels, features, sample cadence, cutoff, or acceptance rules must be treated as a new experiment rather than silently replacing G0.

## Frozen downstream strategy context
G0 does **not** retune Tuesday or A5.11.

- Temporal prior: BTCUSDT Tuesday 06:00 WIB SELL.
- Frozen management reference: A5.11 unchanged.
- Existing August replay remains untouched.
- Existing Tuesday-only ML gate remains rejected as an economic gate.
- Existing August compression guard remains shadow/post-hoc only.

## G0 question
Can we construct a large, causal, market-only BTC state dataset whose labels describe whether the market develops a meaningful SELL-direction or BUY-direction impulse from each state, without using weekday-specific outcomes as the training universe?

G0 is a **dataset + label audit**, not a model-selection contest.

## Universe and decision cadence
- Instrument: Binance Futures BTCUSDT.
- Source: the same official Binance Data Vision / REST 5m kline lineage already used by the frozen Tuesday replay.
- Historical data begins with the existing Nov-2023 warmup.
- Primary historical research cutoff: **2026-07-30 UTC**, matching the frozen Tuesday research cutoff.
- August 2026 data is report-only / post-cutoff and is not allowed to alter G0 definitions.
- Decision states: **one state every clock hour at minute 00**.
- Entry/reference price for the label: the open of the 5m bar at the decision timestamp.
- Every feature must use data with timestamp strictly **before** the decision timestamp. No current/future candle data may enter a feature.

## Primary regime label — locked before execution
The label is intentionally independent of A5.11 PnL.

For each hourly decision state at time `t`, examine the next **6 hours** of completed 5m bars and find the first unambiguous directional development of **0.50%** from the reference price.

Let:
- downside barrier = entry × (1 - 0.0050)
- upside barrier = entry × (1 + 0.0050)

Classify:

1. **SELL_COMPATIBLE**
   - a future 5m bar reaches the downside barrier before any prior bar reaches the upside barrier.

2. **BUY_COMPATIBLE**
   - a future 5m bar reaches the upside barrier before any prior bar reaches the downside barrier.

3. **NEUTRAL**
   - neither barrier is reached within 6 hours, **or**
   - both barriers are touched inside the same first-hit 5m candle, because intrabar ordering is unknowable from OHLCV and must not be invented.

This is a symmetric **first-passage directional-development** label. It is not a TP/SL backtest and does not assume an intrabar execution order.

### Why 0.50% / 6h is locked
- 0.50% is the already-frozen Tuesday A5.x development/hinge scale, so it has prior strategy meaning rather than being selected after seeing pooled results.
- 6h is the frozen Tuesday parent horizon.
- Neither value may be swept inside G0.

## Primary feature set — market-only, pre-entry, locked
No weekday, hour-of-day, `mon_ret`, or Tuesday-specific `overnight_ret` is allowed in the primary G0 feature matrix.

All features are computed only from data strictly before `t`:

### Momentum
- `ret1h`
- `ret3h`
- `ret6h`
- `ret12h`
- `ret24h`

### EMA / trend state
- `ema_spread` = last completed 5m EMA7 / EMA20 - 1
- `dist_ema20` = last completed close / EMA20 - 1
- `ema20_slope1h` = current pre-entry EMA20 / EMA20 approximately 1h earlier - 1

### Location / range
- `loc24` = location of last completed close inside prior 24h high-low range
- `range6`
- `range24`
- `range6_to_24` = range6 / range24

### Flow
- `taker1h`
- `taker4h`

### Volatility / expansion
- `rv1h` = standard deviation of completed 5m log returns over prior 1h
- `rv6h` = standard deviation of completed 5m log returns over prior 6h
- `atr20_pct` = 20-bar 5m ATR / last completed close

No feature selection is performed in G0.

## Dataset integrity rules
A row is eligible only if:
- all required pre-entry history exists,
- the full 6h label horizon exists,
- the 5m bars needed for the horizon are complete and contiguous,
- the decision timestamp itself exists in the source data.

Rows failing integrity are excluded and counted explicitly.

Because adjacent hourly rows have overlapping 6h label horizons, G0 must **not** pretend they are independent observations. The report must explicitly show sample count and class distribution, but effective independence is deferred to the walk-forward modeling stage where embargoed training will be required.

## Required G0 outputs
1. Total eligible pooled hourly states through the Jul-30 cutoff.
2. Class counts/rates for SELL_COMPATIBLE / BUY_COMPATIBLE / NEUTRAL.
3. Yearly class distribution.
4. Feature missingness / finite-value audit.
5. Number of excluded rows and reasons.
6. Tuesday 06:00 WIB cross-check:
   - label distribution over the 139 frozen historical Tuesdays,
   - Aug 4/11/18 labels reported separately,
   - no Tuesday outcome may alter the label definition.
7. Save a compact pooled dataset or reproducible row-level output sufficient for the next walk-forward stage.

## G0 acceptance gate — locked
G0 is allowed to advance to G1 only if all of the following pass:

- **Causal integrity:** zero feature uses data at/after the decision timestamp.
- **Label integrity:** zero invented intrabar ordering; same-bar dual touches are NEUTRAL.
- **Coverage:** at least **15,000** eligible historical hourly states through the Jul-30 cutoff.
- **Class viability:** both directional classes are at least **20%** of eligible historical rows.
- **Finite features:** every locked primary feature is finite on at least **99%** of eligible rows after warmup/integrity filtering.
- **Parity anchor:** the frozen Tuesday A5.11 historical replay still passes its existing parity checks before G0 output is accepted.

If any gate fails, G0 stops and reports the failure. It does not tune thresholds to force a pass.

## Explicitly prohibited in G0
- XGBoost / Random Forest / neural nets.
- threshold sweeps.
- feature selection.
- using August labels to design a feature or boundary.
- modifying Tuesday A5.11.
- promoting the compression guard.
- changing live BBC code/config.
- claiming tradable edge from G0 class frequencies alone.

## Planned next stage if G0 passes
**G1 — Embargoed pooled walk-forward regime baseline.**

G1 will use the frozen G0 rows/features and a simple predeclared baseline model to predict directional regime causally from historical pooled states, with training rows embargoed so their 6h outcome windows are fully known before each prediction period. Only after that pooled model is evaluated independently will its frozen outputs be overlaid on Tuesday 06:00 opportunities to test whether `SELL_COMPATIBLE / conflict / neutral` improves the frozen A5.11 economics.
