# BTC H4 AMD + FVG Path Map H4P1 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: determine whether the path-dependency observed in the H1 AMD/FVG research persists when the same market structure is expressed on session-anchored 4H candles. This is a descriptive trajectory study, not a trading-strategy optimization.

## Market / source
- BTCUSDT USD-M perpetual.
- Source data: official completed Binance Futures 1H archive already used by the H1 research.
- Synthetic 4H bars are built from four consecutive completed 1H candles so Asia/London/New York session opens remain exact.

## Session-anchored 4H streams
For each session-day independently:
- Asia anchor: 00:00 UTC = 07:00 WIB.
- London anchor: 07:00 UTC = 14:00 WIB.
- New York anchor: 13:00 UTC = 20:00 WIB.
- A synthetic H4 bar at offset `k` contains the four H1 candles starting `anchor + 4*k hours`.
- Events with any missing H1 component needed for the frozen primary 24H map are excluded.

## Frozen H4 AMD/FVG event
### Accumulation
Exactly the three completed synthetic H4 bars immediately before the session anchor: offsets -3,-2,-1 (12H context).
- `acc_high = max(high)`.
- `acc_low = min(low)`.

### Manipulation
Only H4 offset 0 may qualify.
- Bearish setup / original SHORT bias: high > acc_high, low >= acc_low, close back inside [acc_low, acc_high].
- Bullish setup / original LONG bias: low < acc_low, high <= acc_high, close back inside [acc_low, acc_high].
- Ambiguous/neither events excluded.

### Exact opposite H4 FVG
Uses H4 offsets 0,1,2 only; no later search.
- Bearish FVG: offset1 candle bearish and high(offset2) < low(offset0). Zone = [high(offset2), low(offset0)].
- Bullish FVG: offset1 candle bullish and low(offset2) > high(offset0). Zone = [high(offset0), low(offset2)].
- No minimum gap/body/ATR/volume filter.

## Frozen post-confirmation path horizon
FVG is known only after H4 offset2 completes. Primary path observation uses exactly offsets +3 through +8 = **six H4 bars / 24 hours**.

For bearish FVG/original SHORT:
- NEAR = lower FVG edge = high(offset2); touched if later high >= NEAR.
- FAR = upper FVG edge = low(offset0); touched if later high >= FAR.
- MANIP_EXTREME = manipulation high; revisited if later high >= it.
- OPP_BOUNDARY = accumulation low; reached if later low <= it.

For bullish FVG/original LONG:
- NEAR = upper FVG edge = low(offset2); touched if later low <= NEAR.
- FAR = lower FVG edge = high(offset0); touched if later low <= FAR.
- MANIP_EXTREME = manipulation low; revisited if later low <= it.
- OPP_BOUNDARY = accumulation high; reached if later high >= it.

## Path ordering
- Record the first H4 offset at which each frozen level is touched.
- If multiple previously untouched levels are first reached inside the same H4 candle, label them as a SAME_BAR group; do not infer intrabar order.
- Primary two-sided/churn diagnostic: whether both FAR and OPP_BOUNDARY are visited within 24H, plus whether FAR first, OPP_BOUNDARY first, or same-bar ambiguous.

## Failed-FVG diagnostic
Within offsets +3..+8:
- bearish FVG failure close = first completed H4 close > FAR;
- bullish FVG failure close = first completed H4 close < FAR.
After a failure close, inspect at most the next six completed synthetic H4 bars (24H) for a retest of FAR from the opposite side:
- bearish failure retest if later low <= FAR;
- bullish failure retest if later high >= FAR.
This diagnostic is descriptive and does not create an entry.

## Partitions
- External untouched: 2020-01-01 through 2021-12-31.
- Development: 2022-01-01 through 2025-03-17.
- Reference validation: 2025-03-18 through 2026-07-29.
- August diagnostic: 2026-08-01 through available completed archive before 2026-08-20.

## Required outputs
For every partition and fixed session/side:
- manipulation count and exact-H4-FVG count;
- NEAR touch rate;
- FAR touch rate;
- MANIP_EXTREME revisit rate;
- OPP_BOUNDARY reach rate;
- BOTH(FAR + OPP_BOUNDARY) rate and first-order breakdown;
- failure-close rate;
- failure-close -> FAR-retest rate;
- most common first-touch path signatures with SAME_BAR ambiguity preserved.

## 80% descriptive flag
`H4P1_80_TRANSITION_FOUND` may be true only if at least one of these predeclared aggregate transitions is >=80% in BOTH reference validation and external with denominator >=20 in each:
1. exact FVG -> NEAR within 24H;
2. NEAR -> FAR within 24H;
3. failure close -> FAR retest within next 24H.
This flag is descriptive only and is not a tradable promotion.

## Anti-rescue lock
After results, do not change:
- H4 construction/alignment;
- accumulation length;
- manipulation bar;
- FVG triplet or gap definition;
- 24H primary horizon;
- failure-close/retest windows;
- session/side selection;
- add ATR, body, volatility, weekday or other filters.
Any strategy derived later must be separately preregistered from a causal state transition identified here.