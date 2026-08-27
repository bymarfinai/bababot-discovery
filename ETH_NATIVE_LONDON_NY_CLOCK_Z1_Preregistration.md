# ETH Native London->New York Clock Discovery — Z1 Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Discover the native ETHUSDT clock placement for the same session-liquidity geometry that produced the BTC London -> New York lineage, without assuming that BTC's 08:00 UTC London reference start is optimal for ETH.

Z1 changes **clock location only**. It is structural discovery only. It does not discover or test entry level, confirmation, breakout entry, TP, SL, fee, leverage, PnL, PF, expectancy, regime filter, or portfolio logic.

This milestone is LONG only. SHORT clock discovery requires a separate experiment.

## Instrument / source / partitions
- Instrument: Binance USD-M ETHUSDT perpetual.
- Event clock: raw 5m.
- Source: Binance Vision USD-M futures archives.
- Analysis span: 2020-01-01 through available data before 2026-08-26 UTC.
- Frozen scoring partitions:
  - `external`: 2020-01-01 to 2022-01-01 UTC
  - `development`: 2022-01-01 to 2025-01-01 UTC
  - `reference_validation`: 2025-01-01 to 2026-07-30 UTC
  - `august`: 2026-08-01 through available August data
- Weekday eligibility is determined by execution-window start UTC.
- Reference start and execution end must both lie inside the same scoring partition.
- Raw 5m coverage must be >=99.5%.

## Frozen clock geometry
BTC London -> New York geometry is preserved exactly:
- completed reference range duration = **5h30m** (66 raw 5m bars)
- execution begins immediately after the reference completes
- execution duration = **6h30m** (78 raw 5m bars)

Only the reference-window start is rotated.

Frozen scan grid:
- every 30 minutes around the complete UTC clock: `00:00, 00:30, ..., 23:30`
- total placements = **48**
- no 15-minute refinement
- no duration sweep
- no result-dependent neighboring rescue

The known BTC-style London baseline is retained as a control/parity cell:
- reference `08:00-13:30 UTC` = `15:00-20:30 WIB`
- execution `13:30-20:00 UTC` = `20:30-03:00 WIB`

The London cell is **not privileged in selection**. ETH must earn its own clock from development data.

## Frozen reference range
For each eligible clock/day:
- `H = max(high)` over the completed 5h30 reference
- `L = min(low)` over the completed 5h30 reference
- require `H > L`
- H/L are immutable before execution begins

## Exact LONG pressure signal
During the following 6h30 execution window, before the first strict close breakout of either frozen boundary:
- High visit: raw 5m `high >= H` and `close <= H`
- Low visit: raw 5m `low <= L` and `close >= L`
- consecutive qualifying bars at the same level are one distinct visit episode
- a new distinct visit requires at least one intervening non-touch bar
- strict BULL breakout = completed raw 5m `close > H`
- strict BEAR breakout = completed raw 5m `close < L`
- strict breakout is evaluated before touch counting and cannot create a visit
- a pre-breakout bar touching both H and L is ambiguous and cannot create a signal

A LONG `K1 OPP0` pressure signal is born at completion of the bar creating the first distinct High visit **only when zero Low visits are known at that moment**.

No F-level, EMA, ATR, volume, body, wick threshold, order block, or future candle is consulted.

## Structural outcome
Starting strictly after signal completion and ending at execution-window end:
- `TARGET_BREAK`: first strict close breakout is `close > H`
- `OPPOSITE_BREAK`: first strict close breakout is `close < L`
- `NO_BREAK`: neither occurs by execution end

This is not trading WR. There is no entry in Z1.

## Mandatory London parity gate
Before any clock ranking may be interpreted, the `08:00 UTC` reference-start cell must reproduce the persisted ETH London->NY M1 engine over the same frozen partitions.

Required exact counts:
- external: complete sessions 523; K1 OPP0 120; target 103; opposite 3; no-break 14
- development: complete sessions 782; K1 OPP0 173; target 137; opposite 21; no-break 15
- reference_validation: complete sessions 411; K1 OPP0 85; target 69; opposite 12; no-break 4
- pooled major: K1 OPP0 378; target 309; opposite 36; no-break 33

Any parity failure aborts before candidate selection is persisted.

## Development-only clock selection
Selection uses **development (2022-2024) only**.

For every one of the 48 clock placements report:
- complete sessions
- K1 OPP0 signals
- target / opposite / no-break counts
- target-break rate using all K1 OPP0 signals as denominator
- resolved same-side rate = target / (target + opposite)
- median minutes signal -> target
- 95% Wilson lower bound for target-break rate

A clock is `DEV_ELIGIBLE` only if development has:
- K1 OPP0 N >= 80
- target-break rate >= 75%
- resolved same-side rate >= 80%

To avoid promoting an isolated 30-minute spike, an eligible clock is `LOCAL_STABLE` only when both immediate +/-30m neighboring clock placements in development each have:
- K1 OPP0 N >= 60
- target-break rate >= 70%
- resolved same-side rate >= 78%

Among `DEV_ELIGIBLE + LOCAL_STABLE` clocks, select exactly one primary ETH clock by:
1. highest 95% Wilson lower bound of target-break rate
2. higher raw target-break rate
3. higher resolved same-side rate
4. larger K1 OPP0 N
5. earlier UTC reference start

If no clock passes, status is `ETH_NATIVE_CLOCK_Z1_NO_DEV_CANDIDATE`.

## Historical replication gate
Only after development selection, inspect the exact selected clock in `external` and `reference_validation`.

The selected clock is tagged `HISTORICAL_REPLICATION_SUPPORTED` only if **both** partitions independently satisfy:
- K1 OPP0 N >= 50
- target-break rate >= 70%
- resolved same-side rate >= 80%
- target breaks > opposite breaks

These are reused historical partitions, not pristine future OOS. The label is structural discovery evidence only.

Overall status:
- `ETH_NATIVE_LONDON_NY_CLOCK_Z1_SUPPORTED` when a development-selected clock passes both historical replication partitions
- `ETH_NATIVE_LONDON_NY_CLOCK_Z1_CANDIDATE_NOT_REPLICATED` when development selects a clock but replication gate fails
- `ETH_NATIVE_CLOCK_Z1_NO_DEV_CANDIDATE` when no development clock qualifies

## Required outputs
Persist to artifact only on the research branch:
1. one row per eligible day x clock structural window
2. summary by clock x partition
3. development leaderboard for all 48 placements
4. exact London parity audit
5. selected candidate / replication readout
6. result markdown and status file

Human-facing clock labels must include WIB. Except for the known `LONDON` control label, discuss other placements by WIB clock time rather than internal UTC code names.

## Guardrails
- LONG only.
- Clock location only.
- No entry level or confirmation.
- No F90/F85/F35/F15.
- No TP/SL or economic backtest.
- No breakout-entry optimization.
- No threshold changes after results.
- No automatic next milestone.
- No merge/persistence to `main` without explicit user approval.

**Research only. Stop after Z1.**
