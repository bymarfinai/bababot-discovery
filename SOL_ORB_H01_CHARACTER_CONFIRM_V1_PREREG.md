# SOL ORB H01 Character Confirmation v1 — Preregistered

This confirmation test opens only the historical external window 2020-01-01 through 2021-12-31. The 2025+ reference-validation window remains closed.

## Frozen rule from development
- Session anchor: 18:00 UTC = 01:00 WIB
- Weekdays, LONG only
- 15m ORB from 18:00/18:05/18:10 UTC
- ORB range <= 1.00% of first ORB candle open
- First upside close breakout during 18:15-18:55 UTC
- Retest touch of ORB High within 30m
- Small BOS within next three 5m candles above the micro-BOS level, ORB High, and anchored VWAP
- BOS close displacement >= +0.60% above ORB High
- Entry next 5m open
- Fixed diagnostic exit +60m from entry
- Roundtrip cost 0.15%; reference notional $500

No thresholds, timing windows, indicator rules, or exit parameters may be changed during this confirmation.

## PASS gate
PASS only if the external pooled result has:
- N >= 5
- net WR >= 60%
- profit factor > 1
- positive net PnL

Year-by-year results are reported descriptively. If the gate fails, reject this H01 candidate and do not tune it against the confirmation set.