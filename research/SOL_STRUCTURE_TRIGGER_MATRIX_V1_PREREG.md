# SOL Structure × Trigger Matrix V1 — Preregistration

## Purpose
Separate **market structure/context** from **entry trigger**. A structure is not an entry. This experiment asks which explicit post-structure trigger, if any, turns a known SOL structure into an economically viable LONG entry.

## Data and validation lock
- Pair: SOLUSDT Binance Futures 5m public data through repository loader.
- Evaluation universe: 2020-01-01 through 2024-12-31 UTC.
- 2025+ remains CLOSED and MUST NOT be touched.
- LONG only.
- Structure and trigger detection are causal using completed 5m bars only.
- Entry = next 5m open after trigger bar closes.
- Diagnostic exit = fixed +60m from entry.
- Round-trip cost = 0.15%.
- Notional = $500.
- No hour/day/regime/indicator filters.
- No TP/SL optimization.
- No threshold sweep or rescue after seeing results.

## Structural contexts
Each setup becomes active when the structure is complete. A trigger must occur strictly AFTER setup completion.

### 1. SWEEP_RECLAIM
- Use a confirmed 2-left/2-right pivot low.
- A later completed bar trades below that pivot low and closes back above it.
- Context completion = reclaim bar close.
- Invalidation = subsequent close below the swept pivot low before trigger.

### 2. HL_SETUP
- Two consecutive confirmed pivot lows L1 then L2 with L2 > L1.
- At least one confirmed pivot high H1 lies between L1 and L2.
- Context completion = L2 confirmation bar close.
- Invalidation = subsequent close below L2 before trigger.

### 3. BREAKOUT_PULLBACK_SETUP
- A confirmed pivot high is broken by a completed bar closing above it.
- The first subsequently confirmed pivot low must have touched/undercut the breakout level intrabar while its pivot bar closed back above the level.
- No completed close may lose the breakout level between breakout and pullback confirmation.
- Context completion = confirmation of that first pullback pivot low.
- Invalidation = subsequent close below breakout level before trigger.

### 4. FAILED_BREAKDOWN_RECLAIM
- Use a confirmed pivot low.
- A later completed bar closes below that pivot low.
- Within the next 3 completed bars, price closes back above the pivot low.
- Context completion = reclaim bar close.
- Invalidation = subsequent close below pivot low before trigger.

A newer same-family structure may supersede an older still-pending setup. Each completed setup may fire at most one trigger entry.

## Frozen trigger window
- Trigger must occur 5–30 minutes after structure completion: post-structure bars +1 through +6.
- No trigger is allowed on the structure completion bar.

## Frozen entry triggers
All three triggers are tested independently for every structural context, giving 12 structure×trigger combinations.

### A. MICRO_BOS
- Eligible starting on post-structure bar +4.
- Current close > maximum high of the immediately preceding 3 completed post-structure bars.
- First occurrence only.

### B. BULLISH_DISPLACEMENT
- Current candle is bullish (close > open).
- Body >= 1.5 × median absolute candle body of the 20 completed bars ending at structure completion.
- Close location within current candle range >= 0.75.
- First occurrence only.

### C. PULLBACK_RESUME
- At least one prior post-structure bar has closed below its immediately preceding bar close (a pullback has occurred).
- Current candle is bullish and closes above the immediately preceding candle high.
- First occurrence only.

## Future-path diagnostics
For every triggered entry:
- fixed +60m gross and net return;
- WR after cost;
- PF, PnL, max drawdown, max loss streak;
- MFE60, MAE60, MFE/|MAE|, time to MFE/MAE;
- adaptive clean-up-impulse diagnostic reused only as a descriptive path metric: upside threshold = max(0.75%, 1.5× trailing sigma60), clean if upside barrier occurs before downside barrier at 0.5× threshold.

## Promotion gate — applied independently to each of the 12 combinations
PASS_TO_CHARACTERIZATION only if ALL hold:
1. N >= 100 over 2020–2024.
2. Net +60m expectancy > 0.
3. PF >= 1.15.
4. Positive PnL in >=4 of 5 calendar years.
5. Median MFE/|MAE| >= 1.20.

Any combination failing any gate is `REJECTED_AS_DEFINED`.

## Interpretation / stop rule
- A rejected combination MUST NOT be rescued on 2020–2024 by changing trigger thresholds, trigger window, pivot order, structure definition, hours, indicators, regime filters, TP or SL.
- A PASS means only that the exact structure×trigger pair deserves separate structure-specific execution / TP / SL characterization.
- 2025+ remains CLOSED until a full structure×trigger execution policy is frozen.
