# B27DE — Generic F85 LONG Clock-Rotation Scan — Preregistration

## Purpose
Abstract the existing London -> New York F85 LONG continuation setup into a clock-agnostic structure detector, then test whether the same structure exists at other UTC clock locations without changing its geometry.

This experiment changes **clock location only**. It does not change the structural sequence, F85/F35/E20 levels, 5m chronology, exit economics, regime logic, or instrument.

## Frozen instrument / source / partitions
- BTCUSDT perpetual.
- Same raw 5m Binance source and `b21.load5()` coverage rules.
- Same frozen scoring partitions as B22B/B27Q:
  - external: 2020-01-01 to 2022-01-01 UTC
  - development: 2022-01-01 to 2025-01-01 UTC
  - reference_validation: 2025-01-01 to 2026-07-30 UTC
  - august: 2026-08-01 to 2026-08-21 UTC
- Weekday eligibility is determined by execution-window start UTC.
- A scored window must have its complete reference and execution windows inside one scoring partition.

## Frozen clock geometry
The London -> New York baseline has:
- completed reference range: 5h30m
- following execution window: 6h30m

B27DE preserves those durations exactly and rotates only the reference-window start around the 24h UTC clock.

Frozen scan grid:
- reference start every 30 minutes: 00:00, 00:30, ..., 23:30 UTC
- reference duration = 5h30m
- execution starts immediately when reference ends
- execution duration = 6h30m
- total tested clock placements = 48

The known London -> New York parity cell is reference 08:00-13:30 UTC -> execution 13:30-20:00 UTC.

No result-dependent clock refinement, 15-minute offsets, alternative durations, or neighboring-window rescue is allowed in B27DE.

## Generic LONG structural sequence
For each eligible day/clock placement:
1. Freeze completed reference-window High `H` and Low `L`; require `H > L`.
2. In the following execution window, use raw 5m chronology.
3. Before the first strict close breakout of either boundary, define:
   - High visit: `high >= H` and `close <= H`
   - Low visit: `low <= L` and `close >= L`
   - consecutive qualifying bars at one level are one visit
   - a both-level bar is ambiguous and rejected
4. LONG K1 OPP0 signal = first distinct High visit while zero Low visits have occurred.
5. The K1 High-touch episode must causally end with a completed 5m bar that no longer qualifies as a High visit.
6. Only after that leave-bar completion is the pullback entry window eligible.
7. H2 = first later raw 5m bar whose `high >= H`, even if that bar also becomes a strict High breakout.
8. A completed `close < L` before H2 is the opposite structural failure.
9. Entries are only allowed strictly before the H2 bar / opposite-break terminal bar.

This is the same B27Q K1 OPP0 -> B27W pre-H2 LONG structure, generalized to an arbitrary completed reference range.

## Frozen F85 Same-Bar Rejection entry
For each clean K1 OPP0 window:
- `R = H - L`
- `F85 = L + 0.85R`
- `F35 = L + 0.35R`
- `E20 = H + 0.20R`

Search only after the causal K1 leave and strictly before H2/opposite-break/session end.

A Same-Bar Rejection requires:
- raw 5m bar touches F85: `low <= F85 <= high`
- that same completed 5m bar closes strictly above F85
- the touch bar itself is still pre-H2 by construction

Entry:
- next raw 5m bar open
- reject if next open `>= H` (`MISSED_H2_AT_OPEN`)
- require `F35 < entry < H`
- equality with the H2 bar start is allowed when the entry open is `< H`, because the open is chronologically before the later intrabar H2 high

No EMA, ATR, volume, candle-body threshold, wick threshold, 4H regime, or other filter is part of the detector.

## Frozen economics
Exactly reproduce B27AA fixed-E20 economics:
- LONG target = E20 resting limit
- structural invalidation = completed raw 5m close strictly below F35
- wick-only F35 breaches do not stop the trade
- if E20 high and F35 close-invalidation occur on the same bar, credit E20 first because the resting target can fill intrabar before close-based invalidation becomes known
- if unresolved by execution-window end, exit at first available 5m open at/after execution end
- illustrative notional = $500
- round-trip fee = $0.40
- trading win = `net_pnl_usd > 0`

## Mandatory London parity gate
Before any rotated-clock result may be interpreted, the 08:00 UTC reference-start cell must reproduce the persisted London -> New York SAME_BAR_REJECTION cohort.

Required pooled-major parity:
- N = 68
- WR = 73.5% (47/68)
- PF approximately 1.70
- expectancy approximately +$0.91/trade
- total net approximately +$61.80

Required partition trade counts:
- external = 27
- development = 30
- reference_validation = 11
- august = 1

The implementation must also compare the exact persisted B27AA SAME_BAR entry timestamps by partition when the persisted trade file is available. Any parity failure aborts before clock ranking is persisted.

## Frozen discovery selection
Clock selection is development-only.

A clock is `DEV_ELIGIBLE` only if development has:
- >= 25 executed Same-Bar trades
- WR >= 70%
- PF >= 1.30
- positive mean net expectancy/trade

Among eligible development clocks, select one primary clock by:
1. highest PF
2. then higher WR
3. then higher expectancy
4. then larger N
5. then earlier UTC reference start

The known 08:00 London baseline remains in the table but is excluded from being called a **new** clock candidate.

## Historical replication label
After development selection only, inspect the frozen selected clock in external and reference_validation.

Tag `HISTORICAL_REPLICATION_SUPPORTED` only if:
- external: N >= 15, WR >= 65%, PF >= 1.20, expectancy > 0
- reference_validation: N >= 10, WR >= 65%, PF >= 1.20, expectancy > 0

These are reused historical partitions, not pristine untouched OOS. This label is discovery evidence only and does not authorize live promotion.

If no development clock passes the eligibility gate, status is `NO_NEW_CLOCK_CANDIDATE`.

## Required outputs
Persist:
1. one row per eligible day x clock with structural timestamps/status and trade outcome
2. summary by clock x partition
3. development leaderboard for all 48 placements
4. selected candidate readout if any
5. London parity audit
6. status file

Report at minimum:
- K1 OPP0 count
- clean-window count
- F85 touch count
- Same-Bar executed trade count
- WR
- PF
- expectancy/trade
- total net PnL
- TP rate
- time-exit rate

## Guardrails
- Long only in B27DE.
- No SHORT mirror.
- No 4H regime filtering.
- No changed F85/F35/E20.
- No duration sweep.
- No sub-30-minute clock refinement.
- No threshold rescue after results.
- No live BBC changes.
- Any next hypothesis after B27DE requires a new experiment ID.

Research only; live BBC unchanged.
