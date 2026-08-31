# ETH B27DX Pair Calibration V2 — Preregistration

## Objective
Find ETHUSDT trades that are economically profitable and robust using the causal architecture proven in BTC B27DX, while allowing ETH-specific market parameters to differ.

**Primary objective is trading edge, not H/H2 rate.** H2 is only a chronology boundary used to prevent late entry.

## Frozen causal architecture from BTC
- Raw event clock: 5m completed bars.
- Reference range must be complete before execution; H/L are immutable afterward.
- K1 OPP0 = first one-sided boundary visit while the opposite boundary has zero prior visits.
- Consecutive same-boundary touches are one episode.
- A completed non-touch leave is mandatory.
- Entry search starts on the next 5m bar after completed leave.
- Entry must occur before same-side second arrival, opposite strict close-break, or session end.
- No future veto/look-ahead.
- LONG and SHORT are calibrated independently.
- One trade maximum per session/configuration.

## ETH parameters allowed to calibrate
The following BTC values are **not** frozen:
- habitat / execution start time;
- reference duration;
- execution horizon;
- entry fraction;
- target extension;
- close-invalidation fraction.

## Frozen search grid
### Execution starts
Every 2 hours UTC: 00:00, 02:00, 04:00, 06:00, 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00, 22:00.

### Reference durations
- 3h
- 4h30m
- 5h30m
- 7h

Reference window ends exactly at execution start.

### Execution horizons
- 4h
- 6h30m
- 8h

### Entry grid
LONG: F95, F90, F85, F80, F75.
SHORT exact mirror: F05, F10, F15, F20, F25.

### Target grid
LONG: E10, E20, E30 above H.
SHORT mirror: E10, E20, E30 below L.

### Completed-close invalidation grid
LONG: F50, F35, F20.
SHORT mirror: F50, F65, F80.

## Execution assumptions
- Limit entry fills at the exact level when a causally eligible 5m bar spans the level.
- Exit scoring starts on the following 5m bar to avoid unknown same-bar intrabar ordering.
- Target touch has priority over close invalidation only on bars after the entry bar.
- Otherwise exit at the next available open at session end.
- Illustrative notional: $500.
- Round-trip fee: $0.40.
- Weekday execution starts only.

## Partitions
- external: 2020-01-01 to 2022-01-01
- development: 2022-01-01 to 2025-01-01
- reference_validation: 2025-01-01 to 2026-07-30
- august: 2026-08-01 onward

Only **development** may choose parameters.
External and reference_validation are untouched validation partitions.
August is diagnostic only and never rescues a failed candidate.

## Discovery gate
A development configuration is eligible for validation only if:
- N >= 40;
- WR >= 60%;
- PF >= 1.25;
- expectancy > 0;
- net > 0.

Rank eligible configurations by:
1. PF;
2. expectancy;
3. N.

To reduce parameter-clone overfitting, advance at most one configuration per `side × execution_start × reference_duration`, maximum 12 configurations total.

## Frozen validation gate
A candidate is a survivor only if **both external and reference_validation** independently satisfy:
- N >= 15;
- WR >= 55%;
- PF >= 1.10;
- expectancy > 0;
- net > 0.

Pooled validation must also satisfy:
- WR >= 60%;
- PF >= 1.25;
- expectancy > 0.

## 5 bps execution stress
For validation survivors only:
- adverse 5 bps on entry;
- adverse 5 bps on stop/time exit;
- limit target remains at exact target.

Stress gate:
- pooled validation PF >= 1.00;
- pooled validation net >= 0.

## Interpretation
The experiment succeeds only if at least one frozen ETH configuration survives untouched validation and 5 bps stress.

A high H2 rate, high raw WR with PF < 1, or development-only success is **not** sufficient.

Research only. No live BBC changes.