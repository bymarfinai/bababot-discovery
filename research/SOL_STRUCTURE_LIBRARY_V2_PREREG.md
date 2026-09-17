# SOL Structural Detector Library V2 — Preregistration

## Purpose
Test a second library of explicit, independent SOL long market-structure detectors. Each detector is evaluated standalone; no model combines them and no detector may be rescued after seeing results.

## Data / execution freeze
- SOLUSDT 5m only.
- Evaluation: 2020-01-01 through 2024-12-31.
- 2025+ remains CLOSED.
- Causal confirmed pivots: order 2 left / 2 right.
- Signal uses only completed 5m bars; entry is next 5m open.
- Diagnostic exit fixed +60m (12 bars), round-trip cost 0.15%, notional $500.
- Future-path metrics: MFE60, MAE60, MFE/|MAE|, time to MFE/MAE, adaptive clean-up-impulse diagnostic identical to Library V1.

## Frozen detectors

### 1. FAILED_BREAKDOWN_RECLAIM
- Maintain latest confirmed pivot low.
- After confirmation, require at least one completed candle close strictly below that pivot-low price (actual breakdown, not wick-only sweep).
- Reclaim must occur within the next 3 completed 5m bars and close strictly back above the same pivot-low level.
- Signal on the reclaim close; then consume that breakdown episode.

### 2. INSIDE_BAR_COMPRESSION_BREAKOUT
- A mother bar is followed by two completed bars whose highs are <= mother high and lows are >= mother low.
- The immediately following bar must close strictly above the mother-bar high.
- Signal on that breakout close.
- This is an exact 4-bar event; no range/ATR filter is added.

### 3. MATURE_HH_HL_CONTINUATION
- Use causal confirmed pivots.
- Require an ordered pivot sequence L1 < H1 < L2 < H2 < L3 in time with:
  - L2.price > L1.price (first HL)
  - H2.price > H1.price (HH)
  - L3.price > L2.price (second HL)
- After L3 is confirmed, signal on the first close strictly above H2 while no close has broken below L3 since L3 confirmation.
- Candidate is consumed on signal or invalidation.

### 4. BREAKOUT_HOLD_CONTINUATION
- Use latest unconsumed confirmed pivot high as breakout level.
- First completed close strictly above the level starts a breakout-hold episode.
- Require the next 3 completed bars to each close strictly above the breakout level.
- Signal on the third hold bar.
- Any close <= breakout level before the third hold bar invalidates the episode.

## No rescue
Do not alter pivot order, reclaim window, number of inside bars, mature-structure leg count, hold-bar count, hours, volatility filters, indicators, TP, SL, or exit horizon after observing 2020-2024 results.

## Promotion gate per detector
PASS_TO_CHARACTERIZATION only if all are true:
1. N >= 100.
2. Fixed +60m expectancy > 0 after 0.15% cost.
3. PF >= 1.15.
4. Positive PnL in >=4 of 5 years (2020-2024).
5. Median MFE60/|MAE60| >= 1.20.

Otherwise REJECTED_AS_DEFINED and move to a different explicitly defined structure family.
