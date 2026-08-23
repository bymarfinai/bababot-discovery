# B27BG — BTC 24H Causal Regime Detector Audit — Preregistration

## Purpose
Audit the **regime detector itself first**, before any directional, entry, stop, target, runner, or PnL research.

B27BG does not ask whether a regime should trade LONG or SHORT. It asks only whether the existing causal 4H regime state behaves like a usable adaptive market-state detector across the full BTC week.

B27BE and B27BF remain frozen historical diagnostics and are not modified or replaced.

## Frozen detector semantics
Reuse the exact existing B27AG/B27BE 4H `SwingRegime(lookback=5, swing_atr=0.5)` implementation:
- completed 4H bars only; exactly 48 complete 5m constituents per bar;
- EMA7, EMA20, ATR14 calculated causally on completed 4H bars;
- causal swing counters are updated sequentially;
- `BULL` requires `hh>=2`, `hl>=2`, `EMA7>EMA20`, and close>EMA20;
- `BEAR` requires `lh>=2`, `ll>=2`, `EMA7<EMA20`, and close<EMA20;
- otherwise `SIDEWAYS`;
- a regime produced by a 4H bar becomes available only at that bar's close (`available_ts = bar_start + 4h`) and remains the active state until the next completed 4H state becomes available.

The fixed UTC 4H boundaries are **state refresh timestamps only**, not trading windows.

## Frozen data universe
- BTCUSDT 5m repository source.
- Expected source identity: 698,112 rows / 100% coverage.
- All seven calendar days.
- Existing partitions:
  - external: 2020-01-01 through 2021-12-31;
  - development: 2022-01-01 through 2024-12-31;
  - reference_validation: 2025-01-01 through 2026-07-29;
  - August telemetry: 2026-08-01 through 2026-08-20.
- Warmup bars before a partition may form indicators/swing state, but every reported effective-state timestamp is attributed by the timestamp at which the state was actually available.

## What B27BG measures — regime identity only
For every effective 4H state interval:
- active regime;
- source 4H bar start and availability timestamp;
- partition;
- weekday/weekend;
- state age in consecutive 4H intervals.

Report, per major partition and pooled-major:
1. state occupancy count and percentage for BULL / BEAR / SIDEWAYS;
2. regime episode count;
3. episode duration in completed 4H intervals and hours: median / P75 / P90 / maximum;
4. next-state persistence `P(state[t+1] = state[t] | state[t])`;
5. full transition matrix between BULL / BEAR / SIDEWAYS;
6. direct BULL<->BEAR transition rate versus transitions through SIDEWAYS;
7. one-interval excursion / flip-back rate (`A -> B -> A`, A != B);
8. regime changes per week;
9. weekday versus weekend occupancy as a descriptive diagnostic only;
10. maximum absolute state-occupancy percentage-point difference across the three major partitions.

No future return, High/Low break, liquidity touch, LONG/SHORT label, entry fraction, stop, target, fee, WR, PF, or PnL may be used in B27BG.

## Frozen detector-quality gate
Call the existing detector `B27BG_REGIME_DETECTOR_STABLE` only if all conditions below hold:

1. each of BULL / BEAR / SIDEWAYS has at least 100 effective 4H intervals in **each** major partition;
2. BULL next-state persistence is >=60% in each major partition;
3. BEAR next-state persistence is >=60% in each major partition;
4. pooled-major one-interval flip-back rate is <=20% of all state-change-centered triples;
5. pooled-major median BULL episode duration is >=2 completed 4H intervals (>=8h);
6. pooled-major median BEAR episode duration is >=2 completed 4H intervals (>=8h);
7. no state has an occupancy share differing by more than 20 percentage points between any two major partitions.

If any condition fails, verdict is `B27BG_REGIME_DETECTOR_NEEDS_REDESIGN`. No detector threshold may be changed after seeing B27BG results.

SIDEWAYS is intentionally not required to have a two-bar median episode because it is the residual state under the frozen detector semantics; its persistence/duration are reported but not used to rescue or reject the detector post hoc.

## Mandatory audit assertions
1. Source identity is exactly 698,112 5m rows with 100% coverage.
2. Every effective state timestamp is >= its source bar availability timestamp; no state is usable before the 4H source bar completes.
3. Complete 4H bars have exactly 48 5m constituents.
4. State labels are only BULL / BEAR / SIDEWAYS.
5. Episode segmentation is chronological and partition reporting does not reset detector state.
6. Transition statistics are calculated only on consecutive complete effective 4H intervals.
7. B27BE persisted result remains present and unchanged.
8. No live BBC file or live trade rule is modified.

## Next step — explicitly out of scope
Only if the detector audit is accepted do we proceed to a separate preregistered experiment asking what **directional behavior** characterizes each frozen regime. Entry-location research comes later still.

Research only. Live BBC unchanged.
