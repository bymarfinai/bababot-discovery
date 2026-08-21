# BTC Weekly MTF Level Atlas B11 — Preregistration

## Purpose
Test the user's support/resistance hypothesis directly: whether a causal level definition drawn from H1, H4, D1, or W1 can provide at least one historically perfect one-trade-per-complete-week setup at net RR 1:1.

This is NOT a generic order-block/confluence retry. The novel selection problem is a **persistent multi-timeframe level atlas**: explicit scalar price levels that are fully known before touch, mapped from completed source bars onto H1 execution, with first-touch/reclaim behavior measured separately by source timeframe and level family.

## Core hypothesis
BTC has enough weekly movement for +1% opportunities every complete week. If buying/selling is repeatedly organized around persistent price memory, then one or more causal MTF level families should show a materially higher first-touch rejection rate than arbitrary H1 entries. A development-only search may select the best frozen rule, but success is accepted only on independent external and reference-validation weeks.

## Data and partitions
Official Binance USD-M BTCUSDT H1 archive through the repository loader.

- External untouched: 2020-01-01 <= ts < 2022-01-01
- Development/search only: 2022-01-01 <= ts < 2025-01-01
- Reference validation untouched: 2025-01-01 <= ts < 2026-07-30
- August 2026: diagnostic only

Only complete ISO weeks are eligible. H4, D1, and W1 source candles are resampled UTC-aligned from H1. A higher-timeframe level becomes available only after its source candle/confirmation is complete.

## Execution geometry
Execution is always on H1 regardless of level source timeframe.

- Signal is a completed H1 bar that touches/rejects a causal level.
- Entry is the next H1 open.
- Round-trip fee: 0.15%.
- Modeled NET reward: +1.00%.
- Modeled NET loss: -1.00%.
- Therefore favorable gross barrier = 1.15%; adverse gross barrier = 0.85%.
- LONG: TP = entry * 1.0115, SL = entry * 0.9915.
- SHORT: TP = entry * 0.9885, SL = entry * 1.0085.
- Same-H1-bar TP+SL ambiguity is adverse-first.
- Trade may run only until the end of the same ISO week.

## Frozen level atlas
The finite search universe is preregistered before observing B11 results.

For each source TF in H1, H4, D1, W1, create causal levels from:

### A. Previous completed bar extremes
- `PREV_HIGH`: high of immediately previous completed source candle.
- `PREV_LOW`: low of immediately previous completed source candle.

### B. Rolling pre-existing extremes
Using completed source candles only and excluding the current source candle:
- `R3_HIGH`, `R3_LOW`: rolling 3-source-bar extreme.
- `R6_HIGH`, `R6_LOW`: rolling 6-source-bar extreme.
- `R12_HIGH`, `R12_LOW`: rolling 12-source-bar extreme.

### C. Confirmed swing levels
- `SWING2_HIGH`, `SWING2_LOW`: 2-left / 2-right fractal swing. A pivot at source bar j is not available until source bar j+2 has fully closed. The most recently confirmed pivot level is carried forward causally.

### D. Prior-period opens
- `PREV_OPEN`: open of immediately previous completed source candle.

No future weekly high/low, future pivot, future touch count, or hindsight level placement is allowed.

## Signal direction
Each scalar level is tested as both possible support and possible resistance based only on the completed H1 touch bar.

A LONG-support candidate requires H1 low <= level and H1 close >= level.
A SHORT-resistance candidate requires H1 high >= level and H1 close <= level.

To avoid treating a candle that spans far beyond the level as a precise reaction, distance from the signal close to the level must be <= 0.75 H1 ATR14.

## Frozen confirmation modes
Each level family/source TF is evaluated under exactly four preregistered H1 confirmation modes:

1. `HOLD`: touch and close back on the expected side of the level.
2. `RECLAIM`: price trades through the level intrabar and closes back on the expected side.
3. `BODY`: HOLD plus signal candle body direction agrees with the trade side.
4. `WICK`: HOLD plus rejecting wick on the level side is at least 50% of absolute candle body.

No threshold sweep beyond these four modes is permitted inside B11.

## First-touch semantics
For a specific active level instance, only its first H1 qualifying touch after the level becomes available is eligible. Repeated touches of the exact same level instance are ignored. This tests whether the level itself has fresh price-memory value instead of allowing repeated attempts to manufacture a win.

## Rule universe
A rule is exactly:

`source_tf + level_family + side_type + confirmation_mode`

where side_type is SUPPORT/LONG or RESISTANCE/SHORT implied by the level's touch behavior.

Rules are evaluated separately. The development search may not invent new level families after seeing results.

## Development-only discovery
For every frozen rule, route at most one trade per complete development week:

- scan Monday 00:00 UTC through Saturday 12:00 UTC chronologically;
- take the first qualifying first-touch signal for that rule;
- enter next H1 open;
- stop for that week.

Compute development coverage, WR, expectancy, PF, max losing streak, and 4 chronological blocks.

Freeze exactly one `PRIMARY_RULE` using this ordered objective:
1. 100% development weekly coverage preferred over incomplete coverage;
2. highest development weekly WR;
3. highest lower Wilson bound for win probability;
4. highest PF;
5. higher number of trades;
6. deterministic lexical rule name tie-break.

Also freeze a `TOP4_ROUTER` as a secondary test: the four highest-ranked development rules with distinct `source_tf + level_family` pairs. During a week, scan chronologically and take the first candidate emitted by the highest-ranked available rule at that timestamp. No retrospective choice of an earlier signal is allowed. If none of the four rules produces a signal by Saturday 12:00, the week is uncovered; there is no arbitrary non-level fallback.

## Independent evaluation
After PRIMARY_RULE and TOP4_ROUTER are frozen from development only, apply them unchanged to:
- external 2020-2021;
- reference validation 2025-Jul 2026;
- August 2026 diagnostic.

Report exact weekly coverage and every losing/uncovered week.

## Support/resistance atlas diagnostics
Besides selected-rule results, report for every source TF and level family:
- first-touch candidate count;
- raw candidate win rate by confirmation mode;
- weekly coverage if routed as first signal/week;
- weekly routed WR;
- LONG vs SHORT split;
- median time from signal to TP/SL;

This diagnostic is descriptive; no post-result atlas row may be promoted without a new preregistered test if it was not the frozen PRIMARY_RULE/TOP4_ROUTER.

## Acceptance gates
### `B11_ROBUST_WEEKLY_100`
PASS only if either PRIMARY_RULE or TOP4_ROUTER independently satisfies BOTH external and reference validation:
- 100% complete-week coverage;
- exactly one trade in every complete week;
- 100% weekly WR;
- zero losing weeks;
- zero uncovered weeks;
- positive expectancy;
- PF > 1;
- all four chronological blocks positive.

### `B11_HIGH_PRECISION_WEEKLY`
Secondary diagnostic PASS only if BOTH external and reference validation have:
- 100% coverage;
- WR >= 80%;
- positive expectancy;
- PF > 1;
- max losing streak <= 2;
- at least 3/4 positive blocks.

The user's active research target remains the 100% gate; >=80% is reported only to understand proximity, not as success.

## Anti-rescue
After B11 results are generated, do not rescue by:
- changing ATR distance tolerance;
- adding/removing level families;
- changing swing confirmation width;
- changing wick/body rules;
- changing target/stop/fee;
- changing scan cutoff;
- filtering weekdays/hours;
- choosing a post-hoc atlas row;
- combining rules differently;
- removing losing weeks.

Any such change requires a new preregistered experiment.

Live BBC code remains untouched.
