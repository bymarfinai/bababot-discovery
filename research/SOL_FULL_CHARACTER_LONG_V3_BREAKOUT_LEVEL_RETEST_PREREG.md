# SOL Full-Character Long V3 — Breakout-Level Retest Preregistration

## Objective
Test a new independent LONG structural character:

**H1 bullish impulse -> break prior confirmed H1 swing high / create new high -> broken resistance becomes support context -> first 5m retest sweeps below the broken H1 level and reclaims it -> LONG next 5m open.**

This is not a filter on Full-Character Long V1. It uses a different structural location: the broken H1 swing-high itself, not the impulse-origin demand candle.

## Frozen data and evaluation
- Symbol: SOLUSDT.
- Parent timeframe: H1 built causally from existing 5m data.
- Entry trigger timeframe: 5m.
- Evaluation: 2020-2024.
- 2025+ remains CLOSED.
- Long only.
- Entry: next 5m open after completed trigger candle.
- Fixed +60m diagnostic exit.
- Round-trip cost: 0.15%.
- $500 notional.
- No hour, EMA, RSI, Fibonacci, volume, regime, H4, TP/SL, or post-result rescue.

## Frozen H1 breakout context
Use the same causal 2-left/2-right H1 pivot semantics as Full-Character Long V1.

A candidate requires:
- confirmed prior H1 swing high H0,
- latest confirmed H1 swing low L1 has pivot time strictly after H0,
- first later completed H1 close strictly above H0.

Each H0 pivot may be consumed only once by its first close-break.

### Impulse quality
For L1 pivot through H1 breakout bar:
- leg length 1-12 completed H1 bars,
- median_range20 = median H1 high-low over the 20 H1 bars immediately before L1,
- displacement = breakout close - L1 low,
- require displacement >= 1.5 x median_range20,
- close-path efficiency = (breakout close - close at L1 pivot) / sum(abs(diff(close))) across leg,
- require efficiency >= 0.60.

After breakout close, the frozen structural support level is exactly H0 price.

## Frozen first-retest lifecycle
Starting immediately after the H1 breakout close:
- observe at most 24 completed H1 hours / 288 completed 5m bars,
- if any completed H1 candle closes strictly below H0 before a valid trigger, invalidate the setup,
- identify the first completed 5m candle whose low is <= H0.

The first touch is the only eligible retest.
- If that first-touch 5m candle has low < H0 AND close > H0, it is the valid LONG trigger.
- If first touch merely touches, closes at/below H0, or otherwise fails the exact sweep/reclaim condition, the setup is rejected with no later second-chance retest.

This makes the character explicitly **first retest of broken resistance**, not repeated level interaction.

## Entry
- Signal time = close of the valid first-touch 5m sweep/reclaim candle.
- Entry = next 5m open.
- No extra confirmation.

## Outputs
- number of qualifying impulsive H1 breakouts,
- number reaching first retest,
- number whose first retest is valid sweep/reclaim,
- trigger conversion rate,
- pooled WR, expectancy, PF, PnL, max DD, max loss streak,
- clean-up-impulse incidence, median MFE, MAE, MFE/MAE, time-to-MFE/MAE,
- yearly 2020/21/22/23/24 economics,
- breakout-to-retest delay distribution.

## Frozen promotion gates
All required:
1. Triggered N >= 100.
2. Pooled net +60m expectancy > 0.
3. PF >= 1.15.
4. Positive PnL in >= 4 of 5 years.
5. Median MFE/|MAE| >= 1.20.

`PASS_TO_CHARACTERIZATION` requires all five.
`REJECTED_AS_DEFINED` rejects only this exact full character.
Do not rescue by changing pivot order, impulse thresholds, 24H lifecycle, first-touch rule, reclaim semantics, hours, indicators, TP or SL after results.

2025_PLUS=CLOSED