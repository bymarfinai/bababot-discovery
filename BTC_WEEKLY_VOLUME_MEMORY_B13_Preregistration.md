# BTC Weekly Volume-Memory Levels B13 — Preregistration

## Motivation
B11 showed that causal OHLC-derived H1/H4/D1/W1 price levels (previous extremes, rolling extremes, confirmed swings, opens) are not sufficient for a robust weekly 1R setup. B13 introduces materially new information: **where trading volume was concentrated inside completed prior periods**, approximating participant cost basis / accepted value rather than geometric extrema alone.

## Core hypothesis
If support/resistance is partly created by inventory and remembered transaction prices, then prior-period VWAP and volume-profile levels (POC/VAH/VAL) may act as stronger reaction/role-flip levels than static highs/lows.

## Data
Official Binance USD-M BTCUSDT 15-minute futures klines, including OHLC and base volume, from 2019-09 through 2026-08-19. H1 execution bars are UTC-aligned resamples of the official 15m archive. Source periods H1/H4/D1/W1 are also UTC aligned.

Partitions:
- external: 2020-01-01 <= ts < 2022-01-01
- development/search only: 2022-01-01 <= ts < 2025-01-01
- reference validation: 2025-01-01 <= ts < 2026-07-30
- August 2026 diagnostic

As with B12, these are independent within this experiment, but prior research has already exposed aggregate behavior from the same historical periods; they are not claimed to be never-before-seen market history.

## Frozen source-period volume levels
For each completed source period in H1, H4, D1, W1, calculate from its constituent 15m bars:

1. `VWAP`: sum(typical_price * base_volume) / sum(base_volume), where typical_price=(high+low+close)/3.
2. `POC`: volume-profile point of control. Divide the completed source-period low-high range into exactly 24 equal-width price bins; assign each 15m bar's typical price and entire base volume to one bin; POC is center of highest-volume bin. Ties choose lower-price bin deterministically.
3. `VAL` and `VAH`: starting at POC, expand contiguously one neighboring bin at a time toward the neighbor with larger volume (tie -> lower-price neighbor) until cumulative included volume >=70% of total. VAL/VAH are the lower/upper outer bin centers of that contiguous value area.

A source period's levels become available only after that source period is fully complete. The immediately previous completed source period is carried forward until a newer period completes. No current incomplete period volume may contribute to its own levels.

For H1 source periods the profile has four constituent 15m bars; for H4 16; D1 96; W1 up to 672.

## Signal / role semantics
Execution remains on completed H1 bars.

Each active VWAP/POC/VAL/VAH scalar level is allowed to act as either:
- SUPPORT/LONG: signal H1 low <= level and close >= level;
- RESISTANCE/SHORT: signal H1 high >= level and close <= level.

Signal close must be within 0.75 H1 ATR14 of level.

Only the first qualifying touch per source-period level instance + role is eligible.

Frozen confirmation modes:
1. HOLD
2. RECLAIM (intrabar trades through level then closes expected side)
3. BODY (HOLD plus candle body agrees with trade side)
4. WICK (HOLD plus rejecting wick >= 50% of absolute candle body)

## Execution geometry
- signal = completed H1;
- entry = next H1 open;
- round-trip fee=0.15%;
- favorable gross barrier=1.15% => net +1.00%;
- adverse gross barrier=0.85% => net -1.00%;
- adverse-first if both hit inside one H1;
- exit no later than end of same ISO week.

## Frozen rule universe
A rule is exactly:
`source_tf + volume_level(VWAP/POC/VAL/VAH) + role(SUPPORT/RESISTANCE) + confirmation_mode`.

No post-result profile-bin, value-area percentage, proximity, source-window, or confirmation sweep is allowed.

## Development-only selection
For each rule, scan every complete development ISO week Monday 00:00 through Saturday 12:00 UTC; take the first qualifying event and max one trade/week.

Freeze `PRIMARY_RULE` by ordered objective:
1. 100% development coverage preferred;
2. highest development weekly WR;
3. highest Wilson lower bound;
4. highest PF;
5. larger N;
6. lexical tie-break.

Freeze secondary `TOP4_ROUTER`: top four development rules with distinct `source_tf + volume_level`; chronologically take the first event emitted by the highest-ranked available rule at that timestamp. No fallback if no level event exists.

## Reporting
For PRIMARY_RULE, TOP4_ROUTER, and descriptive atlas:
- coverage, N, TP/SL/TIME, WR, expectancy, PF, max losing streak
- four chronological blocks
- per source TF/level/mode raw candidate WR and first-signal-per-week coverage/WR
- long/short counts and median hours to resolution

No descriptive row may be promoted post hoc inside B13.

## Acceptance gates
`B13_ROBUST_WEEKLY_100` PASS only if PRIMARY_RULE or TOP4_ROUTER has BOTH external and reference validation:
- 100% complete-week coverage
- exactly one trade every complete week
- 100% WR
- zero losing/uncovered weeks
- positive expectancy, PF>1
- all 4 blocks positive.

Secondary `B13_HIGH_PRECISION_WEEKLY`: both partitions 100% coverage, WR>=80%, positive expectancy, PF>1, max losing streak<=2, >=3/4 blocks positive. It is diagnostic only; current target remains 100%.

## Anti-rescue
No changes after result to 24 bins, 70% value area, volume field, typical-price definition, TFs, level types, touch tolerance, modes, target/stop/fee, scan cutoff, or selection logic. Any change requires a new preregistered experiment.

Live BBC remains untouched.
