# BTC Weekly Liquidity Sweep B18 True Microstructure R1 — Preregistration

**Protocol:** `B18_MICRO_R1`  
**Status:** FROZEN BEFORE MICROSTRUCTURE RESULT  
**Historical B18 result:** preserved; not overwritten.  
**Live BBC:** untouched.

## Research question

Does true event-time microstructure improve the classification of the same objective-level breach/reclaim and continuation events studied in B18, when the old 15m aggregated `breach_flow` proxy is replaced by tick trades plus replayed L2 order-book state?

B18 historically tested a valid structural event plus aggregate kline taker flow. R1 tests the microstructure mechanism that B18 could not observe.

## Frozen structural event universe

Reuse B18 exactly:
- instrument: Binance BTCUSDT USD-M perpetual;
- structural execution timeframe: H1;
- objective pools: `PDH`, `PDL`, `PWH`, `PWL`, `W1_VAH`, `W1_VAL`;
- source level must be known before signal H1 begins;
- first qualifying event per active level instance + archetype only;
- scan cutoff: Monday 00:00 UTC through Saturday 12:00 UTC;
- no equal-high/low, session, swing-cluster, or manually selected levels.

Upper pool:
- signal H1 open <= level;
- H1 high > level;
- close < level => `REV_SHORT`;
- close > level => `CONT_LONG`.

Lower pool mirrored:
- signal H1 open >= level;
- H1 low < level;
- close > level => `REV_LONG`;
- close < level => `CONT_SHORT`.

Outcome economics and same-week execution remain exactly B18.

## Frozen partitions

Reuse B18:
- external 2020-01-01 through 2021-12-31 complete weeks;
- development 2022-01-01 through 2024-12-31;
- reference validation 2025-01-01 through 2026-07-29;
- August 2026 diagnostic only.

Insufficient CoinDesk historical coverage blocks R1. Partitions cannot be silently moved after outcomes are inspected.

## True breach timestamp

Unlike B18, R1 locates the breach inside the signal H1 from **tick trades**.

Upper pool breach timestamp:
- first trade during the frozen signal H1 with `PRICE > level`.

Lower pool breach timestamp:
- first trade during the frozen signal H1 with `PRICE < level`.

If the tick feed does not contain a breach consistent with the structural H1 event, the event fails data-integrity validation and is not imputed from the H1 high/low.

## Causal data window

All entry features must be known before the frozen next-H1-open entry.

For each event acquire:
- tick trades: signal-H1 start through entry;
- L2 replay: max(signal-H1 start, breach-5m) through entry;
- timestamped OI: signal-H1 start through entry.

Also compute frozen local windows relative to breach:
- `[-5m, breach)`;
- `[-60s, breach)`;
- `[breach, breach+10s)`;
- `[breach, breach+60s)`;
- `[breach, entry)`.

Any post-breach window is clipped strictly before entry. No post-entry message enters a feature.

## Tick-trade feature families

For each eligible window:
- aggressive BUY/SELL base and quote volume;
- signed quote delta and delta ratio;
- trade count;
- first/last trade price and return;
- top-5%-trade quote concentration;
- liquidation-tagged count/quote when supplied;
- price progress per unit signed delta.

Direction-signed versions are allowed only by the already-frozen structural archetype direction, never by outcome.

## L2 feature families

At replay start, breach-nearest causal state, +10s, +60s and entry-nearest state where available:
- bid/ask depth and imbalance at 5/10/25 bps;
- spread;
- objective-level-neighborhood bid/ask quantity within +/-25 bps;
- cumulative bid/ask quantity added and removed;
- replenishment ratios;
- depletion ratios;
- start-to-breach and breach-to-entry pressure change;
- CCSEQ/integrity diagnostics.

### Mechanism-sign features

For an upper-pool event:
- positive pre-breach trade delta = aggression into upper liquidity;
- ask replenishment despite aggressive buying = absorption evidence;
- ask depletion with positive price progress = continuation evidence.

For a lower-pool event these are mirrored.

These mechanism signs are descriptive/frozen orientations. No numeric magnitude threshold is hand-tuned from OOS results.

## OI features

- first/last settlement OI;
- first/last quote OI;
- absolute/percentage changes over signal H1 and breach-to-entry where timestamp resolution permits.

OI is auxiliary; L2 + tick trades are mandatory.

## Coverage gates

Before label analysis:
- L2-complete >=90% in each frozen partition;
- tick-trade complete >=90% in each partition;
- breach timestamp agreement >=95% of structurally eligible events;
- OI >=75% in each partition to admit OI features;
- zero timestamp leakage.

Failure of mandatory access => `BLOCKED_DATA_ACCESS`.  
Failure of mandatory historical completeness => `BLOCKED_DATA_COVERAGE`.

## Frozen comparisons

R1 must report each structural archetype with:
1. its raw B18-equivalent structural baseline on the same covered cohort;
2. true-microstructure forensic features;
3. development-frozen selector evaluated untouched on external and reference validation.

One shallow tree per archetype family is allowed:

`DecisionTreeClassifier(max_depth=2, min_samples_leaf=12, class_weight='balanced', random_state=20260821)`

Development selects one positive leaf with N>=15 by Wilson lower bound, then WR, N, leaf id. No OOS threshold rescue.

## Gates

`B18_MICRO_USEFUL` requires the frozen microstructure selector in both external and reference validation:
- N>=15;
- WR>=70%;
- positive expectancy;
- PF>1.5;
- strictly better WR than its own same-covered RAW structural archetype;
- max losing streak <=2.

`B18_MICRO_ROBUST_100` diagnostic:
- N>=10 each OOS partition;
- WR=100%;
- zero losses.

Tiny perfect samples do not qualify.

## Prohibited rescue

After results are visible do not change:
- objective pools or first-event semantics;
- breach definition;
- event windows;
- depth/imbalance bands;
- neighborhood width;
- execution economics;
- partitions;
- model depth/min-leaf;
- direction mapping;
- data source fallback.

Any change is a new protocol.
