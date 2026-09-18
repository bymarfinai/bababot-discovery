# SOL Full-Character Long V1 — Preregistration

## Objective
Test one complete LONG structural character inspired by the supplied price-action example:

**H1 bullish impulse -> break prior H1 swing high / create new high -> mark impulse-origin demand -> first fresh retracement back into demand -> wait for a separate 5m LONG entry trigger.**

This experiment explicitly separates **structure/context** from **entry**. It does not treat a demand touch as an automatic buy.

## Frozen data and evaluation
- Symbol: SOLUSDT.
- Parent structure timeframe: **1H**, built causally from the existing SOLUSDT 5m dataset.
- Entry trigger timeframe: **5m**.
- Evaluation universe: 2020-2024.
- 2025+ remains CLOSED.
- Long only.
- Entry: next 5m open after a completed trigger bar.
- Diagnostic exit: fixed +60m from entry.
- Round-trip cost: 0.15%.
- $500 notional for PnL reporting.
- No hour filter, EMA, RSI, Fibonacci, volume filter, regime filter, TP/SL optimization, or post-result threshold rescue.

## Frozen H1 structural character

### 1. Causal swings
Use the same symmetric **2-left / 2-right** pivot definition already used by the SOL structural library.
A pivot is usable only after its two right-hand H1 bars have completed.

### 2. Prior high -> pullback low -> bullish break
A candidate bullish impulse requires:
- a previously confirmed H1 swing high H0,
- the latest confirmed H1 swing low L1 has a pivot time strictly after the H0 pivot,
- a later completed H1 bar closes strictly above the H0 price.

Each H0 pivot may be consumed only once by its first qualifying breakout.

### 3. Impulse quality
For the H1 leg from L1 pivot through the breakout bar:
- leg length must be 1-12 completed H1 bars,
- median_range20 = median H1 high-low range over the 20 H1 bars ending immediately before L1,
- displacement = breakout close - L1 low,
- require displacement >= **1.5 x median_range20**,
- close-path efficiency = (breakout close - close at L1 pivot) / sum(abs(diff(close))) across the leg,
- require efficiency >= **0.60**.

These are frozen character-definition constants, not parameters to sweep.

### 4. Demand/origin zone
Within H1 bars from L1 pivot through the bar immediately before breakout, find the **last bearish H1 candle** (close < open).
Require one to exist.
Freeze:
- demand low = that candle's low,
- demand top = that candle's open.

The zone is fixed after breakout and is not redrawn later.

### 5. Fresh retracement to demand
Starting with the H1 bar after breakout:
- observe at most **24 completed H1 bars**,
- if any completed H1 close is strictly below demand low before a valid return, invalidate the candidate,
- the **first** H1 bar whose low is <= demand top is the first demand return,
- it completes the structure only if its close is >= demand low.

structure_ready_time is the close of this first-return H1 bar.
No later retest replaces it.

## Frozen 5m entry triggers
After structure_ready_time, observe at most **24 completed 5m bars / 120 minutes**.
Before entry, any completed 5m close strictly below demand low invalidates that trigger opportunity.
Each trigger is evaluated independently on the same frozen structure event.

### A. DEMAND_SWEEP_RECLAIM
Trigger on the first completed 5m bar with:
- low < demand low, and
- close > demand low.

This allows a wick below the demand zone but requires a completed-candle reclaim.

### B. BULLISH_DISPLACEMENT_EXIT_ZONE
At structure-ready time, freeze median_body20 from the 20 completed 5m bars immediately before structure-ready time.
Trigger on the first completed 5m bar with:
- close > open,
- bullish body >= **1.5 x median_body20**,
- candle close-location (close-low)/(high-low) >= **0.75**,
- close > demand top.

### C. BREAK_LAST_RETRACE_PIVOT_HIGH
At structure-ready time, inspect the prior **12 completed 5m bars**.
Using the same causal 2-left/2-right pivot-high definition, freeze the **latest confirmed pivot high** available inside that 12-bar retracement window.
Require one to exist.
Trigger on the first later completed 5m close strictly above that frozen pivot-high price.

No post-ready pivot may replace the frozen reference high.

## Outputs
Report:
- number of completed full-character H1 structures,
- structure counts by year,
- impulse displacement / efficiency diagnostics,
- demand-return delay,
- for each of the three exact entry triggers:
  - eligible structure count,
  - triggered entry count and conversion rate,
  - trigger delay,
  - WR +60m,
  - net expectancy after cost,
  - PF,
  - PnL,
  - max drawdown,
  - max loss streak,
  - clean-up-impulse incidence,
  - median MFE, MAE, MFE/|MAE|,
  - yearly 2020/21/22/23/24 economics.

## Frozen promotion gates
An exact structure + trigger detector advances to execution / TP / SL characterization only if **all** hold:
1. Triggered N >= 100.
2. Pooled +60m net expectancy > 0.
3. Pooled PF >= 1.15.
4. Positive PnL in >= 4 of 5 years.
5. Median MFE/|MAE| >= 1.20.

REJECTED_AS_DEFINED rejects only that exact entry trigger for this full structural character.
Do not rescue on 2020-2024 by changing pivot order, impulse thresholds, demand definition, retracement horizon, trigger thresholds/window, hours, indicators, regime filters, TP, or SL after results.