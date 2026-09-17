# SOL Structural Detector Library V1 — Preregistration

## Purpose
Reset SOL discovery around explicit market structures. Each structure is an independent detector and is evaluated independently. This is not a classifier search, cluster search, hour search, or threshold sweep.

## Data and execution
- Pair: SOLUSDT Binance Futures 5m data from the repository loader.
- Research/evaluation universe: 2020-01-01 through 2024-12-31 UTC.
- 2025+ remains CLOSED reference validation.
- Long only.
- Signal exists only after the event bar is fully closed / the required pivot is causally confirmed.
- Entry = next 5m bar open after signal.
- Fixed diagnostic exit = close of the 12th 5m bar after entry (+60m).
- Round-trip cost = 0.15%.
- Notional = $500.
- No EMA, RSI, Fibonacci, hour filter, regime filter, ML model, or TP/SL optimization.

## Common structural primitives
### Confirmed pivot
Use pivot order 2 left / 2 right.
- Pivot low at bar j iff low[j] is strictly below both two left lows and less-than-or-equal to both two right lows.
- Pivot high analogously.
- A pivot becomes usable only at close of bar j+2. No future pivot knowledge may be used before confirmation.

### Future-path diagnostics
For every detected event, measure from actual next-bar-open entry:
- net +60m return after 0.15% cost and fixed-hold WR;
- MFE60 and MAE60;
- MFE/abs(MAE);
- time to MFE / time to MAE;
- clean upside impulse incidence using the frozen Winner-First definition: up barrier = max(0.75%, 1.5 * trailing sigma60), downside barrier = 0.5 * upside barrier, clean win iff upside barrier touches first within 60m;
- annual counts and economics.
Trailing sigma60 is derived causally from the preceding 288 completed 5m bars.

## Frozen detector definitions

### A. SWEEP_RECLAIM
Bullish liquidity sweep of an active confirmed swing low.
1. Maintain the latest confirmed pivot low as the active level.
2. The level remains active only while no completed bar has closed below it.
3. A signal occurs on the first later bar whose low trades below the active level but whose close finishes back above the active level.
4. One signal maximum per active pivot-low level. After signal, the level is consumed; wait for a newly confirmed pivot low.

### B. HL_CONTINUATION
Classic higher-low continuation through the intervening swing high.
1. On confirmation of a pivot low L2, find the previous confirmed pivot low L1 before it and the latest confirmed pivot high H1 located between L1 and L2.
2. Candidate exists only if L2.price > L1.price.
3. From L2 confirmation onward, invalidate if any completed bar closes below L2.price.
4. Signal on the first completed bar closing above H1.price.
5. A newer confirmed pivot low replaces any still-pending HL candidate.

### C. BREAKOUT_FIRST_PULLBACK
Breakout of a confirmed swing high followed by the first structurally confirmed retest.
1. Maintain the latest confirmed pivot high H as breakout level.
2. Breakout occurs on first completed bar closing above H after H confirmation.
3. After breakout, inspect the first confirmed pivot low whose pivot bar occurs after the breakout bar.
4. The setup qualifies only if that first pullback pivot low traded at-or-below H, its pivot-bar close is above H, and no completed bar closed below H between breakout and pivot-low confirmation.
5. Signal occurs when that first pullback pivot low becomes confirmed (j+2 close).
6. If the first confirmed pullback low does not retest/reclaim H, the breakout event is rejected; do not wait for a second pullback.

### D. LL_REVERSAL_BREAK
Lower-low reversal confirmed by reclaiming/breaking the intervening swing high.
1. On confirmation of pivot low L2, find previous pivot low L1 and latest pivot high H1 between L1 and L2.
2. Candidate exists only if L2.price < L1.price.
3. Invalidate if any completed bar closes below L2.price before reversal confirmation.
4. Signal on first completed bar closing above H1.price.
5. A newer confirmed pivot low replaces any pending LL reversal candidate.

## Duplicate / overlap handling
- Each detector is evaluated independently; the same market timestamp may legitimately be detected by more than one detector.
- Within one detector, exact duplicate entry timestamps are removed, keeping the earliest signal definition.
- An overlap table between detector entry timestamps is diagnostic only and cannot filter trades.

## PASS_TO_CHARACTERIZATION gate — per detector
All must pass:
1. Total N >= 100 across 2020-2024.
2. Fixed +60m net expectancy > 0 after cost.
3. Fixed +60m PF >= 1.15.
4. Positive annual net PnL in at least 4 of 5 calendar years (2020-2024).
5. Median MFE60 / abs(MAE60) >= 1.20.

A detector that fails is REJECTED_AS_DEFINED. Do not rescue it on 2020-2024 by tuning pivot order, adding penetration thresholds, timing windows, hours, indicators, TP/SL, or regime filters.

## Interpretation
This V1 library is a first structural inventory, not a final live system. A detector passing these pre-exit-optimization gates may advance to structure-specific entry/TP/SL characterization while 2025+ remains closed.