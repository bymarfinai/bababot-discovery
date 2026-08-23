# B27BX — BTC Four Fixed H1 Hours × Causal 24H BULL LOW_REJECT — Preregistration

## Purpose

Test whether the previously observed four fixed H1 LOW_REJECT reaction hours become materially cleaner when SIDEWAYS/BEAR are excluded and the event is accepted only while the latest causally available 24H regime state is BULL.

This is directional anatomy only. No TP/SL/RR/fee optimization and no live BBC change.

## Frozen clocks

Use exactly these event-candle START hours:
- 04:00 UTC = 11:00 WIB;
- 08:00 UTC = 15:00 WIB;
- 18:00 UTC = 01:00 WIB;
- 19:00 UTC = 02:00 WIB.

No shifted clocks or extra hours are allowed.

## Frozen H1 event

Aggregate raw BTCUSDT 5m into complete UTC-aligned 1H candles.
For each fixed event hour:
- causal prior3H high/low use only the three completed 1H candles immediately before the event candle;
- LOW_REJECT iff event `low < prior3_low` AND event `close >= prior3_low` AND it does not also sweep prior3_high;
- event is known only when the 1H candle completes.

Reference LONG entry coordinate for directional measurement is the next completed-hour candle OPEN, exactly one hour after event start. No actual trade is authorized.

## Frozen causal 24H BULL filter

Reuse the existing completed-4H SwingRegime(5,0.5) detector from B27BG/B27BN.
At event completion `event_ts + 1h`, assign the latest regime row whose `effective_ts <= event_completion_ts`.
Only rows with `regime == BULL` enter the primary cohort.
No future 4H state, state-age filter, swing boundary filter, or SIDEWAYS transition label is allowed.

## Reporting partitions

Reuse frozen B21 partitions:
- external: 2020-01-01 to 2022-01-01 UTC;
- development: 2022-01-01 to 2025-01-01 UTC;
- reference_validation: 2025-01-01 to 2026-07-30 UTC.

Primary OOS pool = external + reference_validation.

## Frozen directional outcomes

From next-1H open:
- `LONG_POSITIVE_1H`: next 1H candle close > entry open;
- `LONG_POSITIVE_3H`: close of the third completed post-entry H1 candle > entry open.

Report for each partition and each fixed hour:
- unfiltered LOW_REJECT control N, +1H rate, +3H rate;
- BULL-filtered N, +1H rate, +3H rate;
- BULL minus control +3H lift.

Also report pooled four-hour rows for each partition, pooled OOS, and pooled major.

## Frozen support gate

Call `B27BX_FOUR_HOUR_BULL_LOW_REJECT_SUPPORTED` only if ALL hold:
1. raw 5m identity reproduces 698,112 rows / 100% coverage;
2. all H1 source/prior/future windows are exactly continuous;
3. regime mapping uses only latest `effective_ts <= event completion`;
4. pooled-OOS BULL LOW_REJECT N >= 40;
5. pooled-OOS BULL +3H LONG-positive rate >= 65%;
6. external and reference_validation BULL +3H rates are each >= 60%;
7. BULL-minus-control +3H lift is positive in pooled OOS, external, and reference_validation;
8. at least three of the four fixed hours have pooled-OOS BULL N >= 10 and +3H LONG-positive rate > 50%;
9. no trading/economic/live rule is changed.

Otherwise call `B27BX_FOUR_HOUR_BULL_LOW_REJECT_NOT_SUPPORTED`.

A supported result would only justify a new preregistered execution experiment. It would not authorize a trade.

Research only. Live BBC unchanged.
