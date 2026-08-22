# BTC 4H Regime + 15m EMA TP/SL Sweep B25B — Preregistration

## Question
Does the frozen B25A entry have a repeatable edge under a small, predeclared TP/SL grid?

## Frozen entry
BTCUSDT LONG only.

1. B21 4H bull regime must already be ON at the completed 15m EMA20/EMA50 bullish cross.
2. After the cross, ignore red candles while EMA20 remains above EMA50.
3. First later green 15m candle while 4H bull regime is still ON is the signal.
4. Enter at the next 15m open.
5. At most one entry per 15m EMA20/EMA50 bull cycle.

No entry feature or regime definition may be changed after seeing results.

## Frozen TP/SL grid
- TP 0.50% / SL 0.50%
- TP 0.75% / SL 0.75%
- TP 1.00% / SL 0.50%
- TP 1.00% / SL 0.75%
- TP 1.50% / SL 1.00%
- TP 2.00% / SL 1.00%
- TP 2.00% / SL 1.50%

5m bars determine which barrier is touched first. If TP and SL are both touched inside the same 5m bar, count it conservatively as SL.

## Partitions
Use the frozen B22/B25 partitions: external, development, reference_validation, August.

## Cost model
$10 margin x 50x = $500 notional. Illustrative round-trip fee = $0.40 per resolved trade.

## Decision rule
A configuration is a repeatable clue only if external, development, and reference_validation each have at least 50 resolved trades and positive fee-sensitive expectancy. For equal-RR configurations, also report WR. No configuration is promoted merely because it is best in one partition.

Research only. Live BBC unchanged.
