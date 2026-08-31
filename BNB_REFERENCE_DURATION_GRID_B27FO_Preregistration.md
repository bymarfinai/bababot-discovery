# BNB Reference-Duration Geometry Grid — B27FO Preregistration

## Purpose

B27FO follows B27FN, which identified a high-strength contiguous temporal region from 01:00 through 02:00 WIB under the inherited 4h reference + 4h execution geometry.

B27FO tests whether that structural strength is specific to a 4-hour reference window or whether a shorter/longer reference range is comparably or more robust. This is a geometry audit only. It does not define a trading entry or economic rule.

## Frozen data and universe

- Symbol: BNBUSDT
- Raw 5m loader: unchanged inherited repository loader
- Development partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC exclusive
- Common normalized local-date universe: **2022-01-02 through 2024-12-31 inclusive**
- Expected sessions per geometry cell: **1095**
- Timezone: Asia/Jakarta (WIB, UTC+7)
- All seven weekdays included
- No external, reference-validation, August, or holdout data may be used

## Frozen start-zone grid

Reference-window starts are fixed to the B27FN high-strength contiguous region:

- 01:00 WIB
- 01:30 WIB
- 02:00 WIB

No other start times may be added after results are observed.

## Frozen reference-duration grid

For each of the three start times, test exactly:

- 3-hour reference range
- 4-hour reference range
- 5-hour reference range

This creates exactly **9 geometry cells**.

For every cell:

1. Reference window starts at the frozen start time.
2. Reference window lasts exactly the tested duration.
3. `H` = maximum 5m high inside the completed reference window.
4. `L` = minimum 5m low inside the completed reference window.
5. `R = H - L` and must be positive.
6. Execution begins immediately after the reference window ends.
7. Execution duration is fixed at **4 hours** for all cells.
8. Reference and execution windows are half-open `[start, end)`.

Examples:

- start 01:00, 3h reference => reference 01:00–04:00, execution 04:00–08:00
- start 01:00, 4h reference => reference 01:00–05:00, execution 05:00–09:00
- start 01:00, 5h reference => reference 01:00–06:00, execution 06:00–10:00

B27FO therefore tests the full reference-duration geometry. Because execution start necessarily moves when reference duration changes, the result must not be interpreted as a pure isolated duration effect.

## Frozen structural state machine

Use the exact inherited B27EM/B27FA–B27FN LONG state machine without modification:

### SEEK_K1

- close > H or close < L before K1 => BREAK_BEFORE_K1
- H structural visit: high >= H and close <= H
- L structural visit: low <= L and close >= L
- simultaneous H+L event => AMBIGUOUS_BOTH_BOUNDARIES
- K1 qualifies only when the first H visit occurs with zero prior L visits

### K1_EPISODE

- while high >= H and close <= H, remain in the same K1 episode
- first completed 5m candle not belonging to the same H episode is the causal leave
- `leave_ts` = end of the completed leave candle

### AFTER_LEAVE

- H2 arrival: high >= H
- opposite structural break: close < L
- same-bar H2 + opposite => AMBIGUOUS_H2_VS_OPPOSITE_BREAK
- neither by execution end => NO_H2_BY_END
- no favorable same-bar ordering assumption

## Mandatory 4-hour reproduction gates

Before any 3h/5h duration comparison is accepted, the 4h cells must reproduce B27FN exactly on the same normalized universe:

- 01:00 / 4h: sessions 1095, causal leaves **162**, H2 **132**
- 01:30 / 4h: sessions 1095, causal leaves **170**, H2 **133**
- 02:00 / 4h: sessions 1095, causal leaves **162**, H2 **126**

Any mismatch aborts B27FO.

## Frozen outputs per geometry cell

Report for all 9 cells:

- sessions
- K1 qualified count/rate
- causal leaves
- H2 arrivals
- opposite break before H2
- ambiguous H2 vs opposite
- no H2 by end
- H2/leave structural outcome rate
- resolved H2 share
- median leave→H2 minutes

## Frozen duration-level aggregation

For each duration (3h, 4h, 5h), using the three frozen start times:

- unweighted mean H2/leave rate across the three cells
- minimum and maximum cell H2/leave rate
- max-minus-min spread in percentage points
- total leaves and total H2 across the three overlapping cells, shown as a descriptive pooled count/rate only

The pooled count must **not** be treated as an independent-sample enlargement because the three start-time cells overlap heavily by date and market path.

## Frozen stability criterion per duration

A duration is labeled `STABLE_DURATION` only if all are true:

1. every one of its three start-time cells has >=100 causal leaves;
2. unweighted mean H2/leave >=75.0%;
3. minimum cell H2/leave >=72.5%;
4. max-minus-min spread <=7.5 percentage points.

Otherwise it is labeled `UNSTABLE_DURATION`.

## Frozen duration ranking and overall classification

Rank durations by unweighted mean H2/leave across the three starts. If means are tied within 0.25 percentage points, break the tie by:

1. higher minimum cell H2/leave;
2. then smaller max-minus-min spread;
3. then higher total causal leaves.

Overall classification:

- `CLEAR_DURATION_PREFERENCE` if the top-ranked duration is `STABLE_DURATION` and exceeds the runner-up mean by >=2.0 percentage points.
- `DURATION_PLATEAU` if at least two durations are `STABLE_DURATION` and the top-vs-runner-up mean gap is <2.0 percentage points.
- `MIXED_DURATION_GEOMETRY` otherwise.

These labels are structural prioritization only, not profitability claims.

## Interpretation boundary

B27FO may identify whether a 3h, 4h, or 5h reference geometry is structurally more robust inside the already-frozen 01:00–02:00 WIB start zone. It must not:

- call H2/leave a trading win rate;
- define an entry;
- define TP/SL;
- compute fees, slippage, PnL, PF, expectancy, leverage, or position sizing;
- select weekdays;
- expand the start-time grid;
- reveal or use holdout data.

## Stop rule

Persist all B27FO outputs and STOP. Any executable entry hypothesis or economic test requires a new preregistered milestone after reviewing B27FO.