# BNB Execution-Duration Geometry Grid — B27FQ Preregistration

## Purpose
B27FQ is the final temporal-geometry audit before freezing time structure. It tests whether the B27FP 05:00 WIB reference-end habitat remains structurally strong when the execution window ends at 08:00, 09:00, or 10:00 WIB.

This milestone does **not** define a trading entry, TP, SL, fee model, PnL, weekday filter, or holdout rule.

## Frozen data universe
- Symbol: BNBUSDT
- Source: existing repository 5-minute loader
- Timezone: Asia/Jakarta
- Local dates: 2022-01-02 through 2024-12-31 inclusive
- Expected complete sessions per geometry cell: 1095
- Raw coverage gate: >=99.5%
- All weekdays
- No external/reference-validation/August/holdout data

## Frozen reference geometries
Reference end is fixed at **05:00 WIB**. Three already-strong, representative B27FP reference starts are used:
1. 01:00–05:00 WIB
2. 01:30–05:00 WIB
3. 02:00–05:00 WIB

No other reference starts may be added after results are seen.

## Frozen execution-duration grid
Execution always begins at **05:00 WIB**. Test exactly:
- 3h: 05:00–08:00 WIB
- 4h: 05:00–09:00 WIB
- 5h: 05:00–10:00 WIB

This yields a preregistered 3 × 3 grid of nine geometry cells.

Changing execution duration changes both how long the state machine may form a causal leave and how long H2/opposite/no-H2 outcomes may resolve. Therefore B27FQ is a full execution-geometry comparison, not a pure isolated holding-horizon experiment.

## Frozen state machine
For every geometry, H/L/R come only from its completed reference window. The exact inherited BNB LONG state machine remains unchanged:
- SEEK_K1: close outside H/L before K1 => BREAK_BEFORE_K1
- H visit: high>=H and close<=H
- L visit: low<=L and close>=L
- simultaneous H+L => AMBIGUOUS_BOTH_BOUNDARIES
- K1 only on first H visit with zero prior L visits
- K1 signal known only after completed K1 candle
- K1_EPISODE persists while high>=H and close<=H
- first completed candle not in same H episode = causal leave
- AFTER_LEAVE: H2 arrival if high>=H; opposite break if close<L; both same candle => AMBIGUOUS_H2_VS_OPPOSITE_BREAK; otherwise NO_H2_BY_END at execution end
- no favorable same-bar ordering

## Mandatory inherited reproduction gates
The 4h execution cells must reproduce B27FP exactly before 3h/5h are interpreted:
- 01:00–05:00 reference, 05:00–09:00 execution: sessions 1095, causal leaves 162, H2 132
- 01:30–05:00 reference, 05:00–09:00 execution: sessions 1095, causal leaves 167, H2 137
- 02:00–05:00 reference, 05:00–09:00 execution: sessions 1095, causal leaves 167, H2 135

Any mismatch aborts the milestone.

## Required outputs
For each of nine cells report:
- sessions
- K1 qualified
- causal leaves
- H2
- opposite break before H2
- ambiguous H2 vs opposite break
- no H2 by end
- H2/leave structural rate
- resolved H2 share
- median leave→H2 time

Also report execution-duration summaries across the three frozen references:
- unweighted mean H2/leave
- minimum and maximum H2/leave
- spread
- descriptive pooled counts/rate, explicitly marked non-independent because references overlap

## Frozen duration stability rule
An execution duration is `STABLE_EXECUTION_DURATION` iff all are true:
- every reference cell has >=100 causal leaves
- unweighted mean H2/leave >=75%
- minimum H2/leave >=72.5%
- max-minus-min spread <=7.5pp

## Frozen overall classification
Rank execution durations by unweighted mean H2/leave. If means are within 0.25pp, tie-break by higher minimum rate, then smaller spread, then greater total causal leaves, then shorter execution duration.

- `CLEAR_EXECUTION_DURATION_PREFERENCE` if top duration is stable and its mean exceeds runner-up by >=2.0pp.
- `EXECUTION_DURATION_PLATEAU` if at least two durations are stable and top-vs-runner mean gap is <2.0pp.
- otherwise `MIXED_EXECUTION_GEOMETRY`.

## Interpretation boundary
H2/leave is a structural outcome rate, **not trading win rate**. B27FQ establishes no economic edge.

After B27FQ completes, temporal exploration stops. The next research stage must freeze one robust temporal geometry and proceed to causal executable-entry/economic testing rather than adding more clock/range variants.
