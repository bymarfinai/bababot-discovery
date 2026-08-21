# BTC ORB B2 — Simple Filter Preregistration

Goal: improve the frozen B1 H4 20:00 UTC CLASSIC T050_S100 baseline without over-filtering.

Frozen parent:
- BTCUSDT
- 4H reference candle anchored 20:00 UTC
- CLASSIC breakout: next 4H candle closes outside prior 4H high/low
- entry next 4H open
- TP = 0.50 × prior 4H range
- SL = 1.00 × prior 4H range
- fee = B1/B0 frozen fee

Only these simple filters are allowed:
1. BODY50: breakout candle body / candle range >= 0.50.
2. EXT10: breakout close extends at least 0.10 × prior 4H range beyond the broken boundary.
3. BODY50 + EXT10: both filters together.

No EMA, funding, OI, macro, session sub-filter, day-of-week, retuning TP/SL, or additional indicators.

Evaluation:
- chronological 70/30 discovery/validation split
- report N, WR, expectancy, PF for BASE and the three frozen variants
- candidate improvement requires validation N >= 70, validation WR >= 0.67, validation expectancy > 0, validation PF > 1.10, and at least 3/4 chronological blocks positive
- preferred candidate must also retain at least 50% of parent trades in validation

Research only. Live BBC untouched.
