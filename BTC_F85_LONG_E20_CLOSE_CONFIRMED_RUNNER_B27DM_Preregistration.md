# B27DM — F85 LONG E20 Close-Confirmed Runner — Preregistration

## Purpose
Test whether requiring completed 5m acceptance at or above E20 improves the B27DL runner while preserving causality. Entry logic, four operating zones, reference geometry, notional, fee, F35 invalidation, and the global one-position lock remain unchanged.

## Frozen operating zones
- ALT_0330: frozen TOUCH_FIRST_HALF eligibility.
- RAW_0530: B27DJ RANGE_COMPLETED_SECOND_HALF.
- LONDON 08:00: frozen Same-Bar F85 eligibility.
- RAW_2330: B27DJ RANGE_COMPLETED_SECOND_HALF.

## Baseline
Fixed `E20 = H + 0.20R`, where `R = H-L`. A high touch of E20 exits at E20. Before E20, completed 5m close below F35 invalidates. Otherwise time exit at execution end.

## Frozen variant
Name: `E20_CLOSE_CONFIRMED_STEP10_RUNNER`.

1. No E20 limit TP is assumed while an unconfirmed 5m bar is still forming.
2. Before confirmation, F35 completed-close invalidation remains unchanged when E20 was not touched during that bar.
3. On the first 5m bar whose high reaches E20:
   - if that same completed 5m bar closes >= E20, the runner is confirmed at that close; no exit is taken on that bar;
   - if that bar closes < E20, exit at that completed bar close. The backtest MUST NOT retroactively assign an E20 fill because the final close was not knowable at the intrabar E20 touch.
4. Once confirmed, protective floor starts at E20 and becomes effective from the next 5m bar.
5. On subsequent bars, if open <= floor, exit at open; else if low <= floor, exit at floor.
6. Floor ratchets only from completed 5m closes in 0.10R milestones, one step behind: close >= E40 -> floor E30; close >= E50 -> floor E40; close >= E60 -> floor E50; and so on. Close >= E30 alone keeps floor E20.
7. Floor never decreases.
8. If no exit occurs, use the same execution-end time exit.
9. No alternate confirmation timeframe, step size, threshold, floor offset, or zone-specific variation is tested inside B27DM.

## Causality guardrail
The attractive but impossible rule `wick-only gets E20 TP, while a candle later known to close >= E20 remains open` is explicitly prohibited for a full-size single position because it requires knowing the future 5m close at the earlier intrabar touch. B27DM uses only information available at each decision time.

## Exact portfolio rescore
B27DM must replay all 242 B27DK candidates on raw Binance Futures BTCUSDT 5m data and rerun the global chronological one-position lock. Results may not be obtained by simply altering PnL on the previously accepted trades.

## Frozen reporting
Report fixed E20 versus close-confirmed runner by partition, pooled-major, and zone. Also report confirmed-runner count, wick-reject exits, floor exits, time exits, milestone reach rates, accepted/blocked changes, WR, PF, expectancy, total net, and maximum loss streak.

## Decision label
`B27DM_CLOSE_CONFIRMED_RUNNER_SUPPORTED` only if pooled-major:
- total net PnL > fixed-E20 B27DK baseline;
- PF >= 1.80;
- WR >= 70%;
- accepted N >= 80% of B27DK baseline accepted N;
- every major partition remains net positive.
Otherwise label `B27DM_CLOSE_CONFIRMED_RUNNER_NOT_SUPPORTED`.

This is a research/operating exit experiment only. No live BBC change is authorized.