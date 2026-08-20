# BTC H1 AMD + FVG Mitigation AMD2 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: test the materially different execution sequence requested after AMD1 failed as a chase-entry design:

`Accumulation -> Manipulation -> opposite FVG forms -> wait for first FVG mitigation/retest -> enter -> Distribution target`

This is NOT a rescue of AMD1 by changing FVG geometry. AMD1's exact 1H accumulation/manipulation/FVG definitions are retained; only the post-FVG entry/target mechanism is changed.

## Market / timeframe
- BTCUSDT USD-M perpetual
- Decision/signal timeframe: **1H only**
- No 1m / 5m / 15m signal logic
- Historical data: official Binance Data Vision 1H

## Fixed session opens
- Asia: 00:00 UTC = 07:00 WIB
- London: 07:00 UTC = 14:00 WIB
- New York: 13:00 UTC = 20:00 WIB

## Frozen sequence
### 1. Accumulation
- Exactly the three completed 1H candles immediately preceding the fixed session open.
- `acc_high = max(high)` of those 3 candles.
- `acc_low = min(low)` of those 3 candles.

### 2. Manipulation
Only the first 1H candle of the session may be the manipulation candle.
- Bearish setup / SHORT: candle high > `acc_high`, low >= `acc_low`, and close returns inside `[acc_low, acc_high]`.
- Bullish setup / LONG: candle low < `acc_low`, high <= `acc_high`, and close returns inside `[acc_low, acc_high]`.
- Both-side sweeps / ambiguous bars are excluded.

### 3. Exact opposite FVG
FVG uses the manipulation candle plus the immediately following two completed 1H candles. No later-FVG search.
- SHORT: middle candle bearish AND third-candle high < manipulation-candle low. FVG zone = `[third_high, manipulation_low]`.
- LONG: middle candle bullish AND third-candle low > manipulation-candle high. FVG zone = `[manipulation_high, third_low]`.
- No minimum FVG size/body/range threshold.

### 4. FVG mitigation entry
After the third FVG candle has completed, wait at most **6 completed 1H candles** for the first touch of the near FVG boundary.
- SHORT limit entry = FVG lower boundary (`third_high`), reached when a later candle high >= entry.
- LONG limit entry = FVG upper boundary (`third_low`), reached when a later candle low <= entry.
- If no touch within 6 hours after FVG confirmation, event is `NO_FILL`.
- The FVG-forming three candles themselves cannot fill the mitigation entry; entry search starts on the next completed 1H candle.

### 5. Stop
- SHORT SL = manipulation high.
- LONG SL = manipulation low.
- Entry is invalid if it is already beyond/equal to the structural SL.

### 6. Distribution target — PRIMARY
- SHORT Distribution TP = original accumulation low.
- LONG Distribution TP = original accumulation high.
- A primary Distribution trade is eligible only if the raw target distance is large enough that, after modeled 0.15% round-trip fee, **net reward >= net risk (minimum net RR 1:1)**.
- Algebraically this requires target-distance >= structural-risk + 0.30% of entry.
- Events whose opposite accumulation boundary is too close are `RR_INELIGIBLE`, not forced into a trade.

### 7. Fixed net-1R diagnostic — SECONDARY ONLY
For every valid mitigation fill, separately test a synthetic target at `structural risk + 0.30%` raw distance, so net reward equals net loss after 0.15% fee. This diagnostic does not replace the Distribution TP and is not used to select sessions/sides.

### 8. Exit timing
- Maximum hold: **6 completed 1H candles from the mitigation fill candle**.
- Same-hour ambiguity is adverse-first.
- On the fill candle, if both entry and SL are contained in the OHLC range, assume fill then SL. If entry and TP are both reachable on the same candle, adverse-first ordering applies.
- TIME exits use the sixth candle close in signed trade direction, less fee.

## Evidence partitions
- External untouched: 2020-01-01 through 2021-12-31.
- Reference: 2022-01-01 through 2026-07-29.
- August post-cutoff: 2026-08-01 through available completed archive data before 2026-08-20.
- No threshold/clock/side is selected using validation, external, or August.

## Required outputs
For each partition and for each side/session:
- exact-FVG count;
- mitigation fill rate within 6H;
- RR-eligible Distribution-trade count;
- Distribution TP / SL / TIME, decisive WR, PnL, expectancy, median risk, median raw RR;
- fixed net-1R diagnostic performance;
- external chronological blocks.

## Promotion gates
`AMD2_DISTRIBUTION_SUPPORTED = PASS` only if the same frozen aggregate mechanism has:
- reference-validation RR-eligible N >= 25, decisive WR >= 60%, PnL > 0;
- external RR-eligible N >= 40, decisive WR >= 60%, PnL > 0;
- at least 3/4 external chronological blocks with N >= 8 and PnL > 0.

`AMD2_80_CANDIDATE = PASS` only if:
- validation RR-eligible N >= 20 and decisive WR >= 80%;
- external RR-eligible N >= 30 and decisive WR >= 80%;
- at least 3/4 external blocks N >= 5 and WR >= 70%;
- positive validation and external PnL.

`AMD2_NET1R_SUPPORTED = PASS` uses the same N/PnL/block gates but decisive WR >= 60% for the fixed net-1R diagnostic.

## Anti-rescue lock
After seeing AMD2 results, do NOT:
- change accumulation length;
- allow manipulation on later session candles;
- search for later FVGs;
- choose midpoint/25%/75% FVG entries;
- change the 6H mitigation window or 6H hold;
- add FVG-size/body/ATR/std-dev filters;
- isolate a clock/side because it looks good;
- alter the fee or RR requirement.

Any such idea requires a genuinely new preregistered experiment and independent evidence.