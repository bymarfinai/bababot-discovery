# B27P — All-TF First Retest -> Midpoint Entry — Preregistration

## Purpose
Correct the prior B27O implementation and test the user's intended rule without hindsight or bar-close delay.

## Frozen market structure
- Instrument/source/partitions: same BTC 5m source and frozen partitions used by B27O/B27M.
- Session transitions remain fixed UTC:
  - Asia 00:00–08:00 -> London 08:00–13:30.
  - London 08:00–13:30 -> New York 13:30–20:00.
- Previous-session High and Low are frozen once the previous session is complete.
- Midpoint = (previous-session High + previous-session Low) / 2.
- Retest zone tolerance = ±0.20% around the corresponding frozen level.

## Exact causal signal rule
The chronological event clock is the available 5m source for every chart timeframe. This is mandatory because touching a fixed horizontal price level is a price event, not a candle-close event.

For each active session, scan 5m bars chronologically until one of the following occurs:
1. A 5m bar strictly closes above previous-session High or below previous-session Low before any valid retest -> no setup (`BREAK_BEFORE_RETEST`).
2. A 5m bar intersects both High and Low retest zones -> skip the session (`AMBIGUOUS_BOTH_ZONES`) because intrabar ordering cannot be known.
3. A 5m bar intersects the High zone, does not strictly close above High, and is not simultaneously in the Low zone -> first valid retest is High -> freeze BULL/LONG bias.
4. A 5m bar intersects the Low zone, does not strictly close below Low, and is not simultaneously in the High zone -> first valid retest is Low -> freeze BEAR/SHORT bias.

Only the first valid retest determines the setup direction. No later direction flip is allowed.

## Entry
- LONG setup: BUY limit at frozen midpoint.
- SHORT setup: SELL limit at frozen midpoint.
- To avoid unknown ordering inside the signal 5m bar, the midpoint order becomes eligible only from the NEXT 5m bar after the retest bar.
- Before midpoint fill, if any later 5m bar strictly closes outside either frozen range edge (close > High or close < Low), cancel the unfilled order (`RANGE_BROKE_BEFORE_FILL`). This prevents entering after the original range thesis has already resolved.
- A midpoint fill occurs when a later eligible 5m bar has low <= midpoint <= high.

## Exit
- LONG: SL = frozen previous-session Low; TP = frozen previous-session High.
- SHORT: SL = frozen previous-session High; TP = frozen previous-session Low.
- This is nominally 1:1 before fees.
- Fill-bar ordering is unresolved at 5m resolution. Therefore:
  - if stop is touched anywhere in the fill 5m bar, count SL;
  - target-only touch in the fill 5m bar is not awarded;
  - from the next 5m bar onward, first barrier touch resolves the trade; same-5m TP+SL -> conservative SL.
- If neither barrier resolves before active-session end, exit at first available 5m open at/after session end.

## Costs and sizing
- Illustrative notional: $500.
- Fee: $0.40 per resolved trade, same convention as prior research.

## Timeframes requested
Report rows for 5m, 15m, 1H, and 4H.

Important invariance expectation: because the setup uses fixed previous-session horizontal levels and the exact causal event ordering is intentionally resolved on the same 5m clock for every chart timeframe, the trade set SHOULD be identical across 5m/15m/1H/4H. The implementation must hard-assert this. Any cross-timeframe difference is an implementation error, not a strategy result.

## Audit assertions required before result persistence
The program must abort if any of these fail:
1. no midpoint fill occurs in the same 5m bar as its retest signal;
2. every LONG signal level is HIGH and every SHORT signal level is LOW;
3. every entry price equals the frozen midpoint;
4. every LONG SL/TP equals Low/High respectively; SHORT equals High/Low respectively;
5. no filled trade has a strict range close-break between signal bar and entry bar;
6. 5m/15m/1H/4H reported trade sets are identical on transition, partition, date, side, signal time, entry time, entry price, stop, target, and outcome.

## Evaluation
Report setup count, filled trades, fill rate, wins/losses, WR, net PF, net expectancy, total net PnL, TP rate, time-exit rate, and cancellation reasons by transition and partition.

This is a new additive experiment. Prior B27O remains unchanged and is not reused as evidence.
Research only; live BBC unchanged.
