# BTC Weekly W1 VAH True Microstructure R1 — Preregistration

**Protocol:** `W1_VAH_MICRO_R1`  
**Status:** FROZEN BEFORE MICROSTRUCTURE RESULT  
**Live BBC:** untouched.

## Research question

Can **true pre-entry microstructure** distinguish winners from losers of the already-frozen B15 direct W1 VAH breakout LONG setup better than the aggregate-flow features tested in B17?

This experiment does not search for a new structural setup. Candidate timestamps, VAH levels, entry timestamps, outcomes, and frozen partitions come from the existing B15/B17 direct W1 VAH candidate universe.

## Why this is a rerun rather than a rescue

B17/B18 used real Binance taker-buy aggregates, but not tick-by-tick trade flow plus reconstructed Level-2 order-book state. R1 adds a materially richer information set while keeping the underlying event fixed. Historical B15-B19 results remain unchanged.

## Frozen candidate source

Primary candidate file:

`BTC_WEEKLY_W1_VAH_FALSE_BREAK_B17_Candidates.csv`

Required fields:
- `week`, `signal_ts`, `entry_ts`, `level`, `partition`, `reason`, `win`;
- candidate construction must already reproduce the B15/B17 direct W1 VAH baseline.

No new breakout-distance, wick, retest, time-of-week, regime, or outcome-derived event filter is permitted in R1.

## Frozen partitions

Reuse B17 exactly:
- external: 2020-01-01 through 2021-12-31 complete weeks;
- development: 2022-01-01 through 2024-12-31 complete weeks;
- reference validation: 2025-01-01 through 2026-07-29 complete weeks;
- August 2026 remains diagnostic only and cannot select features/rules.

If CoinDesk entitlement or historical coverage cannot support these partitions, R1 is **BLOCKED**, not repartitioned after labels are inspected. A different coverage-limited study would require a separately frozen protocol.

## Data sources

### Structure / label
Existing frozen Binance-based B15/B17 candidate file only.

### True trade flow
CoinDesk Futures tick trades for Binance BTC perpetual.

### True L2
CoinDesk Futures Order Book Replay L2:
- initial book snapshot;
- ordered L2 updates;
- fixed requested depth: **1000** levels;
- no kline reconstruction or fallback if replay is unavailable.

### Open interest
CoinDesk Futures timestamped OI update messages.

Default mapped instrument is `BTC-USDT-VANILLA-PERPETUAL`, but the runner must first verify the configured Binance instrument through CoinDesk metadata. A different instrument identifier is allowed only as a technical mapping correction to the same Binance BTCUSDT perpetual contract, recorded before result generation.

## Causal feature window

For every candidate:
- `T = entry_ts`, the frozen next-H1-open entry;
- feature acquisition window = `[T-60m, T)`;
- no message timestamp `>= T` may enter an entry feature;
- objective price level = frozen W1 VAH from the candidate row.

Post-entry data are prohibited from the feature set.

## Frozen trade-flow features

For windows 60m, 15m, 5m and 60s ending at T:
- BUY and SELL aggressive base volume;
- BUY and SELL aggressive quote volume;
- signed quote delta;
- signed delta ratio;
- trade count;
- liquidation-tagged count and quote volume when source supplies the field;
- price return from first to last trade;
- price-per-delta efficiency;
- top-5%-by-trade-count quote-volume concentration.

No magnitude threshold is optimized before the development model.

## Frozen L2 features

At replay start and replay end:
- mid price;
- spread bps;
- bid depth and ask depth within 5, 10 and 25 bps of mid;
- signed depth imbalance `(bid-ask)/(bid+ask)` at 5/10/25 bps;
- start-to-end imbalance change.

Around frozen W1 VAH, within +/-25 bps:
- start and end bid quantity;
- start and end ask quantity;
- cumulative bid quantity added / removed;
- cumulative ask quantity added / removed;
- bid and ask update counts;
- replenishment ratio = added / removed when denominator exists.

Integrity diagnostics:
- snapshot count;
- update count;
- CCSEQ gap count when CCSEQ is supplied;
- first/last replay timestamp;
- captured-book depth span.

An event is L2-complete only if a usable initial snapshot exists, replay updates are non-empty, and the requested 25-bps bands are represented by the captured book on both sides. No incomplete event can be silently imputed from candles.

## Frozen OI features

Across `[T-60m,T)`:
- number of OI updates;
- first and last settlement OI;
- absolute and percentage settlement-OI change;
- first and last quote OI;
- absolute and percentage quote-OI change.

Missing OI is reported separately. L2 remains mandatory for the true-microstructure cohort; OI is an auxiliary layer and may be absent only if the OI-coverage gate below still passes.

## Data-access / coverage gates before label analysis

The runner first performs a coverage phase without computing winner-vs-loser statistics.

Required:
1. CoinDesk API key exists through environment/secret;
2. configured Binance BTC perpetual resolves;
3. Order Book Replay entitlement succeeds;
4. tick trades are available;
5. L2-complete coverage >=90% of baseline candidates in **each** external, development and reference-validation partition;
6. tick-trade coverage >=90% in each partition;
7. OI coverage >=75% in each partition for OI features to be admitted;
8. no systematic timestamp leakage (`feature_message_ts >= entry_ts`) is permitted.

If 1-4 fail: `BLOCKED_DATA_ACCESS`.  
If 5-7 fail: `BLOCKED_DATA_COVERAGE` (OI failure alone drops the OI feature family rather than L2/trade R1, provided L2/trade gates pass).

## Frozen forensic analysis

For every numeric true-microstructure feature, report by partition:
- winner median;
- loser median;
- standardized mean difference (winner minus loser);
- orientation-free univariate ROC AUC `max(AUC, 1-AUC)`.

A `stable differentiator` requires:
- development absolute SMD >=0.25;
- external absolute SMD >=0.10;
- reference-validation absolute SMD >=0.10;
- identical SMD sign in all three partitions.

This is descriptive evidence, not itself a strategy pass.

## Frozen selector

One shallow classifier may be fitted on **development only**:

`DecisionTreeClassifier(max_depth=2, min_samples_leaf=12, class_weight='balanced', random_state=20260821)`

Feature pool:
- only true-trade and true-L2 features listed above;
- OI features only if the frozen 75% coverage gate passes in every partition;
- no legacy B17 aggregate-flow feature is admitted to the primary MICRO tree.

Development chooses one positive leaf among leaves with N>=15 by:
1. highest Wilson lower bound of TP win rate;
2. higher win rate;
3. larger N;
4. lower numeric leaf id.

The fitted tree and selected leaf are frozen before external and reference-validation evaluation.

## Baselines and success gates

Always report the unfiltered direct W1 VAH baseline on the same data-covered candidate subset and on the original candidate universe.

### `R1_USEFUL_MICROSTRUCTURE_FILTER`
PASS only if the frozen selected leaf has:
- external N>=12 and reference-validation N>=10;
- WR>=65% in both;
- PF>1 in both;
- filtered WR strictly exceeds its same-covered baseline in both partitions;
- no data-integrity failure.

### `R1_HIGH_PRECISION_MICROSTRUCTURE`
PASS only if:
- external N>=10 and validation N>=10;
- WR>=80% in both;
- PF>1 in both;
- max losing streak <=2 in both.

### `R1_ROBUST_100`
Aspirational diagnostic only:
- 100% WR in both OOS partitions;
- zero losses;
- N>=10 in each.

A tiny 2/2 or 6/6 result is never treated as robust-100 evidence.

## Prohibited rescue

After any label-conditioned result is visible, do not:
- change the 60m feature window;
- change 5/10/25-bps bands;
- change +/-25-bps VAH neighborhood;
- change replay depth;
- change candidate timestamps or outcome economics;
- add post-entry features;
- sweep tree depth/min-leaf;
- invent hand thresholds from OOS winners/losers;
- repartition based on CoinDesk performance;
- substitute aggregate kline flow when L2/ticks are missing.

Any such change requires a new preregistered protocol.
