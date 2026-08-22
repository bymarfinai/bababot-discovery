# BTC Previous-Session Direct Sweep B26C — Preregistration

## Question
Does a direct sweep-and-reclaim of the completed previous session high/low create a repeatable BTC 5m trading edge without ChoCH/BOS, FVG, or retest requirements?

## Frozen data / partitions
Use the same BTCUSDT 5m source and frozen partitions already used by B26B.

## Frozen session windows (UTC)
- Asia: 00:00-08:00
- London: 08:00-13:30
- New York: 13:30-20:00
- Weekdays only.

## Frozen transitions
1. ASIA_TO_LONDON: completed Asia high/low become London liquidity levels.
2. LONDON_TO_NEWYORK: completed London high/low become New York liquidity levels.

## Frozen signal / entry
During the active next session:
- SHORT signal: a completed 5m candle trades above previous-session HIGH and closes back below that HIGH.
- LONG signal: a completed 5m candle trades below previous-session LOW and closes back above that LOW.
- No ChoCH, BOS, FVG, order block, EMA, or retest filter.
- Earliest valid signal wins if both sides trigger on the same day.
- Entry is the next 5m candle OPEN.
- Maximum one trade per transition per weekday.

## Frozen risk / exit
- SHORT stop: signal/sweep candle HIGH.
- LONG stop: signal/sweep candle LOW.
- Target: 2R from actual next-open entry.
- If TP and SL are both touched in the same 5m candle, count as SL conservatively.
- If neither is touched by active-session end, exit at that session-end open.
- $500 illustrative notional and $0.40 round-trip fee sensitivity, matching recent experiments.

## Frozen reporting
Report N, wins/losses, net WR, TP rate, net PF, fee-sensitive expectancy/trade, total net, median risk %, hold time, time-exit rate, and same-bar ambiguity by transition and partition.

## Frozen gate
A transition is repeatable only if external, development, and reference_validation each have:
- >=100 trades,
- fee-sensitive expectancy > 0,
- net PF >= 1.20.

No rule changes after results. Research only; live BBC unchanged.
