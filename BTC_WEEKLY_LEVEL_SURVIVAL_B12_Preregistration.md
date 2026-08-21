# BTC Weekly Level Survival B12 — Preregistration

## Motivation
B11 tested static causal H1/H4/D1/W1 support-resistance level families and found that static level identity plus simple hold/reclaim/body/wick confirmation does not produce a robust one-trade-per-week edge. B12 asks a materially different question: **given a pre-existing causal level that is being touched, what is the current survival state of that level?**

This is an entity-lifecycle / hold-vs-break selection problem, not another level-family or confluence sweep.

## Core hypothesis
A price level is not permanently support or resistance. Its probability of holding depends on its causal history: age, prior approaches, time spent around it, crossing/acceptance behavior, approach speed, penetration/reclaim geometry, and current volatility. Modeling that lifecycle can separate strong first-touch/role-reversal events from levels that are being accepted through and are likely to break.

## Data and partitions
Official Binance USD-M BTCUSDT H1 data and the exact preregistered B11 level atlas definitions.

- External: 2020-01-01 <= ts < 2022-01-01
- Development only: 2022-01-01 <= ts < 2025-01-01
- Reference validation: 2025-01-01 <= ts < 2026-07-30
- August 2026: diagnostic only

These partitions are independent within B12 model fitting, although B11 aggregate results from these historical periods are already known at the research-program level. Therefore they are not claimed as never-before-seen market history.

## Candidate events
Reuse B11 causal level families for source TF H1/H4/D1/W1:
- PREV_HIGH / PREV_LOW / PREV_OPEN
- R3_HIGH / R3_LOW
- R6_HIGH / R6_LOW
- R12_HIGH / R12_LOW
- SWING2_HIGH / SWING2_LOW

Use only B11 `HOLD` first-touch events as the candidate universe. A candidate is LONG when the H1 signal bar touches the level and closes on/above it; SHORT when it touches and closes on/below it. Distance from close to level remains <=0.75 H1 ATR14. One first HOLD event is allowed per active level-instance + role.

The B12 model does NOT use B11 BODY/WICK/RECLAIM rule identity as a categorical input; their candle geometry is represented numerically instead.

## Execution
Unchanged from B11:
- signal on completed H1;
- entry next H1 open;
- round-trip fee 0.15%;
- favorable gross barrier 1.15% = net +1.00%;
- adverse gross barrier 0.85% = net -1.00%;
- adverse-first intrabar;
- exit no later than the end of the same ISO week.

Label `WIN=1` only when the candidate reaches TP before SL; TIME and SL are `WIN=0`.

## Frozen causal feature set
All features are known through the completed signal H1 bar only.

### Level identity
- source TF one-hot: H1/H4/D1/W1
- family one-hot: the 11 frozen B11 families
- role: LONG-support vs SHORT-resistance

### Level age / lifecycle
- hours from the timestamp encoded in the causal level instance to signal time, clipped at 8 weeks
- raw H1 range-touch count over the prior 12, 24, 48, 72 bars (`low <= level <= high`)
- near-level close count over prior 12, 24, 48, 72 bars within 0.25 ATR and 0.50 ATR
- close-crossing count of the level over prior 12, 24, 48, 72 bars
- fraction of closes on the candidate's expected side of level over prior 6, 12, 24, 48 bars
- bars since the most recent close-cross of the level, capped at 72
- maximum absolute close distance from level over prior 12, 24, 48 bars, normalized by current ATR

### Approach geometry
- side-aligned close returns over 1, 2, 4, 8, 12, 24 bars
- side-aligned prior close distance from level at 1, 2, 4, 8, 12, 24 bars, normalized by current ATR
- absolute distance compression toward level from 6 bars ago and 12 bars ago to signal close

### Signal reaction geometry
- side-aligned signal body / ATR
- rejecting wick / ATR
- opposing wick / ATR
- penetration through level / ATR
- close reclaim distance from level / ATR
- signal true range / ATR

### Volatility / clock / remaining opportunity
- ATR14 / close
- current ATR14 divided by trailing median ATR over 24 and 72 H1 bars
- current ISO-week realized range / close
- hours remaining until ISO-week end
- known weekday and UTC hour encoded sine/cosine

No future extreme, future volatility, future touch count, future role flip, order flow, derivatives, or outcome-derived field is permitted.

## Frozen model
Development-only `RandomForestClassifier`:
- n_estimators=600
- max_depth=10
- min_samples_leaf=25
- max_features='sqrt'
- class_weight='balanced_subsample'
- random_state=20260821
- n_jobs=-1

Categorical identities are deterministic one-hot columns with the full preregistered category set, so train/test columns are fixed.

## Development-only weekly threshold selection
Score every development HOLD candidate with `p_hold = P(WIN=1)`.

Frozen probability threshold candidates are the development score quantiles:
`[0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99, 0.995]`.

For each threshold, route development weeks chronologically Monday 00:00 through Saturday 12:00 UTC:
- at each signal timestamp, if multiple level events qualify, choose highest p_hold, then deterministic lexical event key;
- take the first timestamp whose best event p_hold >= threshold;
- enter next H1 open and stop scanning that week;
- if no threshold event occurs, the week is uncovered; no arbitrary fallback.

Freeze one threshold by ordered objective:
1. 100% development week coverage preferred;
2. highest development weekly WR;
3. highest Wilson lower bound;
4. highest PF;
5. lower threshold quantile.

No external or reference-validation result may affect threshold/model selection.

## Report
Per partition:
- complete weeks / selected trades / coverage
- TP/SL/TIME
- WR, expectancy, PF, max losing streak
- 4 chronological blocks
- selected source-TF/family/role distribution
- candidate-level model AUC and accuracy are diagnostic only
- top feature importances are descriptive only

Persist selected trades and threshold table.

## Acceptance
### `B12_ROBUST_WEEKLY_100`
PASS only if BOTH external and reference validation have:
- 100% complete-week coverage
- exactly one selected trade every complete week
- 100% WR
- zero losing/uncovered weeks
- positive expectancy
- PF > 1
- all four blocks positive

### `B12_HIGH_PRECISION_WEEKLY`
Secondary diagnostic only: both partitions 100% coverage, WR>=80%, positive expectancy, PF>1, max losing streak<=2, >=3/4 positive blocks.

## Anti-rescue
After B12 output exists, no retuning of:
- level families/source TFs
- lifecycle lookbacks
- ATR proximity
- model parameters
- threshold grid/objective
- clock cutoff
- target/stop/fee
- role definitions
- feature subset
is allowed inside B12. Any change is a new preregistered experiment.

Live BBC remains untouched.
