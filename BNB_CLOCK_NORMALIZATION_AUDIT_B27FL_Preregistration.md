# B27FL — BNB 24H Clock Comparability / Normalization Audit

Status: PREREGISTERED BEFORE ANY B27FL NORMALIZED RESULT REVEAL

## Intent
Audit whether the completed B27FA–B27FK 24-hour BNB structural clock sweep is apples-to-apples across anchors. The original sweep used a frozen UTC discovery partition and per-anchor local-session eligibility. Because WIB is UTC+7, anchors near the UTC partition boundary can contain a different number of complete local sessions.

B27FL is an audit/normalization milestone only. It does not define an entry, TP, SL, PnL, fee model, weekday filter, holdout test, or live rule.

## Frozen source state
- Symbol: BNBUSDT
- Source: existing repository 5m historical loader
- Discovery partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC, exclusive
- Required raw 5m coverage: >=99.5%
- Timezone: Asia/Jakarta (WIB, UTC+7)
- Structural state machine: exact causal B27EM / B27FA–B27FK LONG K1 -> causal leave -> H2 logic
- All seven weekdays remain included
- External/reference-validation/August/other holdout partitions remain unused

## Audit question 1 — why session counts differ
For every anchor A in 00:00–23:00 WIB, reconstruct the original eligible local dates using the exact original geometry:
- reference window: A <= t < A+4h
- execution window: A+4h <= t < A+8h
- retain a local date only when reference_start >= DEV_START and execution_end <= DEV_END
- reference and execution must each contain exactly 48 raw 5m bars

Report for each anchor:
- original eligible session count
- first eligible local date
- last eligible local date
- local dates unique to that anchor relative to the all-clock intersection

This diagnosis is geometric only and must be computed before normalized outcome comparison is interpreted.

## Audit question 2 — normalize to one identical local-date universe
Compute the exact set intersection of eligible local dates across all 24 anchors. That intersection becomes the frozen normalized universe for every anchor.

Expected from boundary geometry, before outcome inspection:
- common start should be 2022-01-02 local date
- common end should be 2024-12-31 local date
- expected common session count: 1095 local dates

The code must assert the derived intersection rather than silently hard-code a favorable subset. If the derived universe differs from the expectation above, report it and use the derived intersection only.

For every anchor 00:00–23:00, rerun the exact same structural state machine on exactly this common local-date universe and report:
- sessions
- K1 qualified count/rate
- causal leaves
- H2 arrivals
- opposite breaks
- ambiguous events
- no-H2-by-end
- H2/causal-leave rate
- resolved H2 share
- median minutes leave->H2

## Frozen original benchmark
Original 24-hour pooled structural outcomes from B27FK:
- 00: leaves 137, H2 105, rate 76.6%
- 01: leaves 162, H2 132, rate 81.5%
- 02: leaves 162, H2 126, rate 77.8%
- 03: leaves 142, H2 96, rate 67.6%
- 04: leaves 142, H2 108, rate 76.1%
- 05: leaves 141, H2 94, rate 66.7%
- 06: leaves 148, H2 104, rate 70.3%
- 07: leaves 149, H2 114, rate 76.5%
- 08: leaves 143, H2 113, rate 79.0%
- 09: leaves 161, H2 118, rate 73.3%
- 10: leaves 175, H2 136, rate 77.7%
- 11: leaves 159, H2 120, rate 75.5%
- 12: leaves 161, H2 117, rate 72.7%
- 13: leaves 183, H2 139, rate 76.0%
- 14: leaves 162, H2 126, rate 77.8%
- 15: leaves 178, H2 132, rate 74.2%
- 16: leaves 157, H2 107, rate 68.2%
- 17: leaves 142, H2 94, rate 66.2%
- 18: leaves 127, H2 89, rate 70.1%
- 19: leaves 133, H2 91, rate 68.4%
- 20: leaves 129, H2 89, rate 69.0%
- 21: leaves 145, H2 107, rate 73.8%
- 22: leaves 147, H2 114, rate 77.6%
- 23: leaves 145, H2 109, rate 75.2%

Original leader: 01:00 WIB, 132/162 = 81.5% H2/leave.
Original top six by H2/leave: 01, 08, 02, 14, 10, 22.

## Frozen comparison outputs
For each anchor compare original vs normalized:
- original sessions vs normalized sessions
- original leaves/H2/rate
- normalized leaves/H2/rate
- rate delta in percentage points
- original rank and normalized rank

Also report:
- normalized 24-hour ranking
- whether the leader identity changes
- whether the top-six composition changes
- maximum absolute H2/leave delta across anchors

## Frozen materiality flags
These flags are descriptive audit gates, fixed before results:
- LEADER_CHANGED if normalized #1 anchor is not 01:00 WIB
- TOP6_CHANGED if normalized top-six anchor set differs from {01,08,02,14,10,22}
- MATERIAL_RATE_SHIFT if any anchor changes by >= 1.0 percentage point in absolute H2/leave rate after normalization
- COMPARABILITY_STABLE if none of the three flags above are triggered

No threshold above is a profitability claim.

## Integrity rules
- No weekday selection.
- No clock selection before all 24 normalized anchors are run.
- No state-machine modification.
- No entry/economic test.
- No holdout reveal.
- Do not delete or overwrite the original B27FA–B27FK results; B27FL must preserve both original and normalized tables.

## Stop rule
Stop after the 24-clock comparability diagnosis, normalized rerun, ranking comparison, and materiality flags are persisted. Any post-leave sequence study or executable-entry research requires a new preregistered milestone.
