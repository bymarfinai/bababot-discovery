# SOL Options Wall Forward Validation V1 — Preregistration

## Purpose

Test whether prospectively recorded SOL options concentration walls behave like real reaction/liquidity levels after the map exists.

This study is downstream of SOL_OPTIONS_LIQUIDITY_MAP_V1. It does not modify the frozen map formula.

## Causal sample

Only snapshots saved prospectively at or before the evaluated price path are eligible.

Historical detector trades or candles may never be assigned an options map captured later.

The first eligible map timestamp is 2026-09-22T02:29:31.999Z.

## Observation unit

To avoid overweighting repeated captures of the same map, snapshots are collapsed into map regimes.

A new regime begins when any of these change:
- expiry tuple;
- top-three lower put strikes and rank order;
- top-three upper call strikes and rank order.

Only the first snapshot of each regime is used as the regime start.

## Levels

For each regime, evaluate:
- lower top-1, top-2, top-3 put concentration strikes;
- upper top-1, top-2, top-3 call concentration strikes.

Top-1 is the primary wall. Top-2 and top-3 are descriptive secondary levels.

## Price source

Binance SOLUSDT spot 1-minute candles.

## Frozen horizon

Each regime is evaluated for 240 minutes after its start, unless a new regime starts sooner.

An incomplete horizon is CENSORED, not a failure.

## First touch

A lower or upper wall is touched when a 1-minute candle satisfies:

low <= wall <= high

Only the first touch in the eligible regime window is used.

## Post-touch measurements

For each first touch, compute side-normalized favorable and adverse excursions at:
- 15 minutes;
- 30 minutes;
- 60 minutes;
- end of eligible regime window.

Lower-wall favorable direction = upward.
Upper-wall favorable direction = downward.

Report:
- MFE percent from wall;
- MAE percent through wall;
- close displacement from wall;
- favorable/adverse excursion ratio.

No single MFE/MAE threshold is promoted from the pilot sample.

## Symmetric first-passage tests

Without tuning, report first passage at three pre-frozen symmetric bands:
- 0.25%
- 0.50%
- 1.00%

For a lower wall:
- FAVORABLE_FIRST if price reaches wall*(1+band) before wall*(1-band)
- ADVERSE_FIRST if price reaches wall*(1-band) first
- NONE if neither is reached in the eligible horizon

For an upper wall the directions are reversed.

All three bands are reported. No band may be selected after results as the sole winner.

## IV overlay

For each level retain:
- concentration score;
- mean OI share;
- mean gamma share;
- nearest IV-band distance;
- confluence label;
- nearest IV expiry.

IV_CONFLUENT remains descriptive. It is not a gate in this validation.

## Detector alignment

Future SOL detector events may be joined only to the latest saved options snapshot with:

snapshot_time <= detector_decision_time

No event before 2026-09-22T02:29:31.999Z is eligible for options-map attribution.

## Output status

Allowed study statuses:
- FORWARD_SAMPLE_CENSORED
- FORWARD_NO_TOUCH
- FORWARD_TOUCH_OBSERVED
- FORWARD_SAMPLE_ACCUMULATING
- FORWARD_EVIDENCE_SUPPORTED
- FORWARD_EVIDENCE_NOT_SUPPORTED

No READY_TO_TRADE label is allowed from one or two wall touches.
