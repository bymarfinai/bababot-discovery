# B27DS — F15 SHORT 20:00 UTC Local Clock Stability — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
B27DR found a low-frequency but unusually strong historical SHORT candidate at reference start 20:00 UTC (execution 01:30-08:00 UTC next day): external, development, and reference_validation were all profitable with high WR/PF, but the clock failed B27DR's frozen development minimum-N gate because development had only 19 trades.

B27DS asks one narrow question:

**Is the 20:00 UTC result part of a causal local timing basin, or is it an isolated 30-minute clock spike?**

This is a clock-stability experiment only. The bearish structure, F15 SAME_BAR_REJECTION entry, F65 completed-close invalidation, E20_DOWN target, 5m event clock, 5h30 reference duration, 6h30 execution duration, fee, and sizing remain unchanged from B27DR.

## Frozen local clock grid
Scan exactly these 7 reference starts:

- 19:30 UTC
- 19:40 UTC
- 19:50 UTC
- 20:00 UTC
- 20:10 UTC
- 20:20 UTC
- 20:30 UTC

All starts are aligned to the repository 5m raw clock.

For each start:
- reference duration = 5h30m;
- execution duration = 6h30m immediately after reference completion;
- skip execution starts on Saturday/Sunday using the same convention as B27DR;
- same frozen partition boundaries.

No other local time may be added after results are seen.

## Frozen SHORT structure
Reuse B27DR exactly:

`reference range -> first Low pressure visit K1 OPP0 -> causal leave -> pre-H2 F15 touch -> touch bar closes < F15 -> SHORT next 5m open -> Low/H2 return -> E20_DOWN continuation or F65 close invalidation/time exit`.

Geometry remains:
- F15 = L + 0.15R;
- F65 = L + 0.65R;
- E20_DOWN = L - 0.20R.

No EMA, ATR, volume, body, wick, regime, entry-fraction, target, stop, or runner tuning is allowed.

## Parity requirement
The exact 20:00 UTC row must reproduce the persisted B27DR partition metrics within numeric tolerance before neighboring clocks are interpreted:
- external N=27, WR=74.0741%, PF≈2.2217, net≈+$31.35;
- development N=19, WR=78.9474%, PF≈3.9934, net≈+$39.46;
- reference_validation N=10, WR=80.0%, PF≈2.6998, net≈+$6.91;
- August N=1, WR=100%, net≈+$1.24.

Abort before interpretation if parity fails.

## Development candidate gate
A clock is development-eligible if:
- N >= 15;
- WR >= 70%;
- PF >= 1.50;
- expectancy > 0.

Select exactly one primary clock by:
1. higher PF;
2. higher WR;
3. higher expectancy;
4. higher N;
5. smaller absolute distance from 20:00 UTC;
6. earlier UTC as final tie-break.

## Local-basin stability gate
The selected clock is only tagged `LOCAL_BASIN_SUPPORTED` if at least one immediate 10-minute neighbor also has development:
- N >= 15;
- WR >= 65%;
- PF >= 1.20;
- expectancy > 0.

This prevents calling one isolated time spike a stable timing habitat.

## Historical replication gate
After development selection, the exact selected clock must satisfy:
- external: N >= 15, WR >= 70%, PF >= 1.50, expectancy > 0;
- reference_validation: N >= 8, WR >= 70%, PF >= 1.50, expectancy > 0.

Historical replication is `SUPPORTED` only if both partitions pass.

External/reference_validation have already been used in earlier historical research and are not pristine unseen OOS. This remains exploratory historical evidence.

## Outputs
For every clock and partition report:
- K1 OPP0;
- clean windows;
- F15 touches;
- H2-after-F15 rate;
- SAME_BAR confirmations/trades;
- wins, WR, PF, expectancy, total net;
- TP rate and time-exit rate.

Also report:
- development ranking;
- exact selected clock;
- neighbor stability result;
- external/reference_validation replication;
- pooled-major selected-clock metrics.

Persist detailed cases, summary, leaderboard, parity audit, and status.

## Decision labels
- `B27DS_NO_LOCAL_SHORT_CLOCK` — no development clock passes.
- `B27DS_LOCAL_CLOCK_ISOLATED` — a development clock passes but no immediate neighbor supports a basin.
- `B27DS_LOCAL_BASIN_NOT_REPLICATED` — local basin exists in development but selected clock fails historical replication.
- `B27DS_LOCAL_BASIN_HISTORICAL_REPLICATION_SUPPORTED` — local basin exists and selected clock passes external + reference_validation gates.

Research only. Live BBC unchanged.
