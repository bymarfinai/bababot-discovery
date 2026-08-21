# BTC Weekly Defended S/R B12 — Preregistration

## Purpose
Test a materially stricter definition of support/resistance than B11's prior/rolling/swing price levels. B12 treats support/resistance as a **stateful defended zone**: a causal displacement origin must create structural consequence first, remain fresh, then survive its first revisit with a completed-H1 failed-break/reclaim plus micro structure break.

This is not a repeat of V4-A1.3. V4-A1.3 was restricted to 1H liquidity-sweep-origin zones, 5m/15m first-retest resolution, and did not test net-fee weekly one-entry coverage. B12 uses H1/H4/D1/W1 source zones, does not require a preceding liquidity sweep, requires fresh first-revisit defense on completed H1, models fees and net ±1%, and explicitly tests complete-week feasibility plus a causal selector.

## Core questions
1. Does every complete week contain at least one causally formed defended S/R signal that subsequently reaches net +1.00% before net -1.00%?
2. If yes or nearly yes, can a development-frozen causal selector choose one such signal per week with 100% historical wins in both untouched external and reference-validation periods?
3. Which source timeframe and zone state (origin vs polarity flip) actually contributes the weekly defended reactions?

## Data and partitions
Official Binance USD-M BTCUSDT H1 archive, with 2019 prehistory only to establish causal state entering 2020.

- External untouched test: 2020-01-01 <= ts < 2022-01-01
- Development/training only: 2022-01-01 <= ts < 2025-01-01
- Reference validation untouched test: 2025-01-01 <= ts < 2026-07-30
- August 2026: diagnostic only

Only complete ISO weeks are evaluated.

## Timeframes
Source-zone timeframes are frozen as:
- H1
- H4 UTC aligned
- D1 UTC aligned
- W1 ISO Monday 00:00 UTC aligned

All trade confirmations and entries occur on H1 so different source timeframes are compared under one executable clock.

## Causal structural state
A source swing is a 2-left / 2-right pivot. It becomes usable only after both right-hand source bars have completed; no pivot is backdated for decision use.

### Demand origin
At a completed source bar that closes above the most recent already-confirmed swing high (bullish BOS), inspect only the preceding six completed source bars and choose the **last bearish candle** as the origin. It becomes a valid demand zone only if:
- the swing high was known before the BOS bar;
- BOS occurs no more than six source bars after the origin candle;
- displacement from the origin proximal edge to BOS close is >= 1.50 source ATR14;
- source ATR14 is finite and positive.

Demand zone geometry:
- distal = origin low
- proximal = max(origin open, origin close)

### Supply origin
Symmetric definition:
- completed source close below most recent already-confirmed swing low;
- last bullish candle in the preceding six completed source bars;
- displacement from origin proximal edge to BOS close >= 1.50 source ATR14.

Supply geometry:
- proximal = min(origin open, origin close)
- distal = origin high

A unique source timeframe + side + origin candle can create at most one origin zone.

## Freshness and active lifetime
An origin zone is tradable only on its **first H1 revisit after its BOS is fully completed**. Any first revisit consumes the origin zone whether defense succeeds or fails; repeated taps are never rescued.

Frozen maximum age from zone creation to first H1 revisit:
- H1 source: 168 hours
- H4 source: 336 hours
- D1 source: 720 hours
- W1 source: 2016 hours

No post-result age tuning is allowed.

## Polarity flip state
A source origin zone may create exactly one flipped zone if, before the source-age limit expires, the original zone is structurally broken and accepted beyond its distal edge by **two consecutive completed source closes**:
- broken demand -> accepted below demand distal -> same zone becomes potential SUPPLY;
- broken supply -> accepted above supply distal -> same zone becomes potential DEMAND.

The flip becomes known only after the second accepting source bar is complete. The flipped zone then receives a new freshness state and is tradable only on its first H1 revisit after acceptance, under the same source-specific maximum age.

## H1 active-defense confirmation
For either an origin or flip zone, first H1 overlap with the zone is the touch bar. Starting with that completed touch bar and for at most the next two completed H1 bars (maximum three H1 bars total), a defense signal exists only if all frozen conditions hold.

### Demand defense / LONG
- H1 price overlaps the zone;
- before confirmation, no completed H1 candle closes below the distal edge;
- a completed H1 confirmation candle closes above the proximal edge;
- confirmation candle is bullish (close > open);
- confirmation body >= 0.25 H1 ATR14;
- confirmation close > the immediately previous completed H1 high (micro bullish BOS).

### Supply defense / SHORT
Symmetric:
- no completed H1 close above distal before confirmation;
- confirmation closes below proximal;
- bearish body;
- body >= 0.25 H1 ATR14;
- confirmation close < immediately previous completed H1 low (micro bearish BOS).

A wick through the distal edge is permitted only if the candle does not close beyond distal before valid confirmation. Such events are recorded as distal sweeps, not separately optimized.

## Trade execution
Signal information ends at the completed H1 confirmation candle.

- Entry: next H1 open.
- Round-trip modeled fee: 0.15%.
- Desired net win: +1.00%.
- Desired net loss: -1.00%.
- Therefore favorable price barrier = 1.15%; adverse price barrier = 0.85%.
- LONG and SHORT are mirrored.
- Same-H1 TP+SL ambiguity is adverse-first.
- Trade can resolve only through the end of the same ISO week; otherwise TIME closes at the final H1 close of that week.

Weekly signal scan ends Saturday 12:00 UTC; outcomes may continue through the end of Sunday. This preserves material time for the 1% move and matches the existing weekly research clock.

## Stage A — defended-zone feasibility atlas
For every complete week and each partition, report:
- number of causal defended-zone signals;
- number of TP signals;
- whether >=1 defended signal exists;
- whether >=1 defended TP exists;
- combined H1/H4/D1/W1 oracle feasible coverage;
- coverage by source timeframe and origin/flip state;
- zero-signal weeks and zero-TP weeks.

The oracle may use realized outcome only to answer whether a winner existed among signals that were themselves formed causally. It is **not** a deployable selector and must never be reported as strategy WR.

### B12 structural feasibility gate
`B12_DEFENDED_ORACLE_100` passes only if BOTH external and reference validation have 100% complete-week coverage with >=1 causal defended TP signal in every week.

## Stage B — causal one-trade selector
Candidate features are frozen before results:

Categorical:
- source_tf
- zone_kind: ORIGIN or FLIP
- side: LONG or SHORT

Numeric, all known by confirmation close:
- source displacement ATR
- BOS extension beyond the broken confirmed swing in source ATR
- zone width / source ATR
- zone age hours at first revisit
- touch-to-confirm H1 bars
- maximum penetration through the zone as fraction of zone width
- distal-sweep flag
- confirmation body / H1 ATR
- confirmation micro-BOS extension / H1 ATR

Model: development-only `StandardScaler` for numeric features + one-hot categorical features + deterministic L2 LogisticRegression:
- C = 0.5
- solver = liblinear
- class_weight = balanced
- max_iter = 2000
- random_state = 20260821

Label is whether the candidate reaches TP before SL/TIME under the frozen execution.

### Threshold selection
Candidate selector thresholds are development probability quantiles:
`[0.00, 0.50, 0.60, 0.70, 0.80, 0.85, 0.90, 0.95]`.

For each threshold, scan each development week chronologically and take the first defended-zone signal at or above threshold through Saturday 12:00 UTC. No retrospective choice of an earlier signal is permitted.

Select one threshold by ordered development-only objective:
1. highest weekly coverage;
2. highest weekly TP rate among selected trades;
3. highest mean net return;
4. highest PF;
5. lower threshold.

Freeze the chosen model and threshold before reading external/reference-validation selector performance.

Also report a causal `FIRST_DEFENSE` baseline: first defended-zone signal of each week regardless of model probability.

No forced non-S/R fallback exists. A week with no selected defended-zone signal is a coverage failure.

## Acceptance gates
### `B12_ROBUST_WEEKLY_100`
PASS only if the same frozen causal selector in BOTH external and reference validation has:
- 100% complete-week coverage;
- exactly one selected trade per complete week;
- 100% TP rate;
- zero SL/TIME selected weeks;
- positive expectancy;
- PF > 1;
- every chronological quarter positive.

### `B12_HIGH_PRECISION_WEEKLY`
Secondary PASS only if BOTH untouched partitions have:
- 100% coverage;
- WR >= 80%;
- positive expectancy;
- PF > 1;
- max losing streak <= 2;
- at least 3/4 chronological quarters positive.

## Anti-rescue
After B12 result generation, do not change displacement threshold, pivot definition, origin lookback, zone geometry, source timeframes, age limits, flip acceptance, H1 defense confirmation, body threshold, micro-BOS rule, fee, barriers, week cutoff, model hyperparameters, feature set, or threshold grid to rescue the result. Any such change is a new preregistered experiment.

No result from Stage A may be converted post hoc into a selector rule. No losing/zero-signal week may be removed.

Live BBC remains untouched.
