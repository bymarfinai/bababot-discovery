# B27F — BTC 4H Frozen Swing-Level Repeated Touch Breakout — Preregistration

## Clarified pattern
This corrects B27E's level-reset interpretation. The user's intended setup is:
- establish ONE swing high resistance level;
- keep that exact level frozen while price rejects/tests it repeatedly;
- count distinct visits to that SAME frozen high (1, 2, 3, ...);
- later close above that original high = LONG breakout.

Symmetric for one frozen swing low support level and SHORT breakdown.

A newer minor swing on the same side does NOT replace/reset the frozen level while it remains unbroken.

## Data / partitions
Same BTCUSDT 5m source and frozen partitions as B27E/B27A. Resample to 4H using the repository convention.

## Causal swing seed
3-bar fractal pivot, known only after the right-hand 4H candle completes:
- swing high k: high[k] > high[k-1] and high[k] > high[k+1]
- swing low k: low[k] < low[k-1] and low[k] < low[k+1]

When there is no active frozen high, the next causally confirmed swing high becomes the frozen high. Once active, later swing highs are ignored until that level closes through. Same logic independently for lows.

After a high is broken, that high is retired; only a FUTURE causally confirmed swing high after retirement may become the next active high. Same for low.

## Touch count
Frozen high H:
- rejection touch = high >= H AND close <= H.
- consecutive touching 4H candles count as ONE visit.
- after leaving the touching state, a later return counts another visit.
- final breakout candle close > H is not counted as a touch.

Frozen low L:
- rejection touch = low <= L AND close >= L.
- same distinct-visit logic.

Primary buckets: 0, 1, 2, 3, 4+ prior visits.
No tolerance band and no maximum-age rule in this preregistration.

## Trading rule
Breakout: completed 4H close beyond frozen level.
Entry: next 4H open.
SL: opposite extreme of breakout candle.
TP: fixed 2R.
5m underlying resolves first barrier; same-5m TP+SL = conservative SL.
Notional $500; round-trip fee $0.40.
No overlapping positions.

## Output and gate
Report N/W/L/WR/net PF/net expectancy/total net/median SL/median hold for each touch bucket in external, development, reference_validation, august, plus LONG/SHORT counts.

A bucket is repeatable only if SAME bucket has >=30 resolved trades, positive net expectancy, and net PF >=1.20 in external, development, and reference_validation.

Research only; live BBC unchanged.
