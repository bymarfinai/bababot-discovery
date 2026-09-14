# SOL ORB H01 Character Lock v1

Purpose: lock the first structurally interpretable candidate found for the 01:00 WIB / 18:00 UTC SOL session before opening any confirmation data.

## Development universe
- SOLUSDT 5m
- Weekdays only
- 2022-01-01 <= timestamp < 2025-01-01
- Session anchor: 18:00 UTC = 01:00 WIB
- LONG only
- Reference validation 2025+ remains closed

## Frozen structure
1. Build a 15-minute ORB from 18:00, 18:05, 18:10 UTC.
2. Require ORB range <= 1.00% of the first ORB candle open.
3. Find the first 5m close above ORB High from 18:15 through 18:55 UTC.
4. Within 30m after breakout, require a retest touch of ORB High.
5. After the retest, define the micro-BOS level as max(retest candle high, immediately previous 5m candle high).
6. Within the next three 5m candles, require the first close above the micro-BOS level, above ORB High, and above anchored VWAP from 18:00 UTC.
7. Require BOS-close displacement >= +0.60% above ORB High.
8. Enter LONG at the next 5m open.
9. Diagnostic exit is fixed at +60 minutes from entry, with 0.15% roundtrip cost and $500 reference notional.

No bullish-reaction candle requirement is added: this candidate is specifically the SMALL_BOS_VWAP path.

## Robustness audit only
Report neighboring cells, without changing the lock:
- ORB max: 0.90%, 1.00%, 1.10%
- BOS displacement min: 0.50%, 0.60%, 0.70%

These neighbors are descriptive only. The frozen candidate remains 1.00% / 0.60%.

## Promotion gate to confirmation
Candidate may be sent to untouched external confirmation only if development shows:
- pooled net WR >= 60%
- pooled PF > 1
- positive net PnL
- representation in 2022, 2023, and 2024
- no year with net WR < 60%

If confirmation later fails, do not retune against confirmation data; reject the H01 candidate and move on.