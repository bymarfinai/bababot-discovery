# BTC SR83 — All-Day Support/Resistance High-Confidence Walk-Forward

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
Search for a robust BTCUSDT support/resistance **level-confidence identifier**, not a trade strategy.

The question is:

> Using only information available before a frozen level's first touch, can an annual expanding model identify a selective bucket of levels whose next first-touch reaction HOLD rate is >=80% out-of-sample?

This is materially different from SR80–SR82:
- SR80 was Friday-only tree selection on one fixed split;
- SR81 was a deterministic prior-proof rule;
- SR82 externally rejected the post-hoc support-only SR81 clue;
- SR83 uses **all WIB calendar days** and **annual expanding pseudo-OOS** level-confidence testing with no Friday restriction.

## Data
- BTCUSDT USD-M perpetual, official Binance Data Vision 5m archives.
- warmup begins 2019-12-01 UTC.
- event days: 2020-01-01 through 2026-07-29 WIB inclusive.
- daily candidate levels frozen at 00:00 WIB.
- 1H bars = exact completed 5m aggregates.
- ATR14(1H) = Wilder smoothing, alpha=1/14.
- EMA20(1H) = EWM span20 adjust=False.

## Frozen daily level universe
At each 00:00 WIB freeze, generate only:
1. previous-WIB-day high (`PDH`)
2. previous-WIB-day low (`PDL`)
3. prior-7-WIB-day high (`W7H`)
4. prior-7-WIB-day low (`W7L`)
5. up to three most recent confirmed 1H swing highs from prior 7 days (`SWING_H`)
6. up to three most recent confirmed 1H swing lows from prior 7 days (`SWING_L`)

Confirmed swing pivot = centered 1H pivot with 3 completed 1H bars on each side.

Raw levels within `0.10 x daily-start ATR14(1H)` are clustered; cluster price = median member price. Cluster provenance and confluence count are retained.

- cluster below daily open = SUPPORT
- cluster above daily open = RESISTANCE
- equality excluded

Only the **first touch during that WIB day** counts for each frozen cluster.

## Frozen level correctness label
Same scale as SR80–SR82:
- daily-start ATR14(1H)
- reaction distance = 0.50 ATR
- outcome horizon = 6 hours after first touch

SUPPORT:
- HOLD: level +0.50 ATR before level -0.50 ATR
- BREAK: opposite boundary first

RESISTANCE:
- HOLD: level -0.50 ATR before level +0.50 ATR
- BREAK: opposite boundary first

Touch candle reaching either outcome boundary = AMBIGUOUS.
Later 5m candle reaching both boundaries = AMBIGUOUS.
Neither boundary in 6h = UNRESOLVED.
Primary denominator = HOLD + BREAK only.

## Frozen pre-reaction features
All are available before reaction outcome. Touch-state features use completed 5m bars strictly before the first-touch candle.

### Level structure
- `is_support`
- `has_pday`
- `has_w7`
- `has_swing`
- `confluence_count`
- `distance_open_atr`
- `prior_near_count_7d` within 0.10 ATR
- `age_hours` youngest source

### Approach state
- signed 30m return toward level
- signed 60m return toward level
- signed 120m return toward level
- 30m range / ATR
- 60m range / ATR
- fraction prior six 5m bars moving toward level
- fraction prior twelve 5m bars moving toward level
- 30m quote volume / prior24h non-overlapping 30m median
- side-aligned completed 1H EMA20 slope over prior 3h
- side-aligned completed 1H EMA20 slope over prior 6h
- ATR / daily-open price
- hours from daily freeze to first touch

No day-of-week feature. No post-touch feature. No funding/OI. No outcome-derived feature.

## Frozen model
One `sklearn.tree.DecisionTreeClassifier` per expanding annual fold:
- criterion=`gini`
- max_depth=4
- min_samples_leaf=50
- random_state=20260819
- no class weights
- discovery-median imputation from that fold's training history only
- no hyperparameter sweep

The tree is deliberately shallow and leaf-supported so any high-confidence state is human-readable.

## Annual expanding pseudo-OOS folds
Resolved events only.

- train 2020–2022 -> test 2023
- train 2020–2023 -> test 2024
- train 2020–2024 -> test 2025
- train 2020–2025 -> test 2026 through Jul29

For each fold, after fitting on training history, define `HIGH_CONFIDENCE_HOLD` as **every tree leaf** that satisfies on training data:
- predicted class HOLD
- training resolved N >= 50
- empirical training HOLD rate >=80%

The eligible leaf set is frozen before scoring that fold's test year. No best-leaf selection from test data.

If a fold has no eligible leaf, its high-confidence coverage is zero and this is recorded, not rescued.

## Primary promotion gate
Combine all pseudo-OOS test events classified HIGH_CONFIDENCE_HOLD across the four folds.

Verdict `BTC_SR83_OOS_80_LEVEL_IDENTIFIER` only if ALL:
1. pseudo-OOS resolved high-confidence N >= 100
2. aggregate pseudo-OOS HOLD rate >=80%
3. aggregate high-confidence HOLD rate > aggregate unconditional pseudo-OOS HOLD rate by >=10 percentage points
4. at least 3 of the 4 folds have >=15 high-confidence resolved events
5. every fold with >=15 high-confidence events has HOLD rate >=65%
6. at least 3 of 4 folds with any high-confidence events have HOLD rate > unconditional same-fold rate
7. zero causality/integrity violations

Wilson 95% intervals are reported for aggregate and per-fold high-confidence reliability.

### Secondary descriptive checks
Not promotion gates and cannot rescue failure:
- support vs resistance high-confidence rates
- source-family composition
- coverage = high-confidence resolved / all pseudo-OOS resolved
- training eligible leaf rules per fold

## Guardrails
- no deeper tree, smaller leaf, threshold lower than 80, probability threshold sweep, or feature addition after result
- no support-only/resistance-only, source-family-only, day/hour/year-only rescue
- no reaction-distance/horizon/pivot/clustering changes
- no reranking leaves using test-year outcomes
- no PnL/TP/SL optimization at this stage
- if SR83 passes, freeze the **process** and test unchanged on ETH/SOL/BNB or true-forward BTC; a historical 80% rate is never a guarantee
