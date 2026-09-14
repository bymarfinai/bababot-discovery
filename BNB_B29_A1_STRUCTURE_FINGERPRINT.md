# BNB B29 A1 — Causal Structure Fingerprint

## Status before execution
**PREREGISTERED — REPRESENTATION ONLY**

A1 is not a trading-system backtest. It must not select direction, entry, TP, SL, holding period, win rate, PnL, or a Ready-to-Trade candidate.

## Purpose
Build one reusable, causal BNBUSDT market-structure representation on a global 15-minute decision grid. The representation will become the input to B29 A2 Character Memory and later walk-forward work.

The objective is to describe **what the market looks like at decision time**, not whether a future trade wins.

## Frozen data boundary
- Symbol: `BNBUSDT` USD-M futures.
- Raw bars: Binance Vision 5-minute OHLC through the already-used B28 research boundary.
- Frozen loader end: `2026-08-26T00:00:00Z`.
- No data after that boundary may be downloaded or inspected by A1.
- Historical data in A1 is methodology/discovery material, not untouched final OOS.
- Final RTD evidence must later come from forward-only data after the complete B29 engine is frozen.

## Decision-time semantics
Binance kline timestamp is the **bar-open timestamp**. A1 converts every raw row to:

`bar_close_ts = bar_open_ts + 5 minutes`

A fingerprint at decision time `t` may use only bars with `bar_close_ts <= t`.

Decision grid: every 15 minutes on UTC close time. No future shift, centered window, future-filled value, forward label, or outcome column is allowed in A1.

## Frozen feature families
All thresholds below are semantic/fixed before execution. A1 is not allowed to optimize them against trade outcomes.

### 1. Trend / geometry
- Price displacement and return over 15m / 30m / 60m / 120m / 360m.
- ATR-normalized displacement over the same horizons.
- Directional efficiency over 30m / 60m / 120m / 360m.
- Up-bar persistence over 30m / 60m / 120m.
- Two-block 60-minute high/low geometry classified as `HH_HL`, `LH_LL`, `HH_LL`, `LH_HL`, or `OVERLAP`, with a fixed 0.10 ATR360 significance tolerance.

### 2. Volatility / displacement quality
- True range.
- ATR30 / ATR60 / ATR120 / ATR360.
- ATR30/ATR360 and ATR60/ATR360 ratios.
- Realized volatility over 30m / 60m / 120m / 360m.
- RV60/RV360 ratio.
- Candle body/range and close-location value.

### 3. Location / liquidity behavior
- Position inside rolling 60m / 120m / 360m high-low ranges.
- Distance from **prior** 60m and 120m highs/lows in ATR360 units.
- Current closed-bar sweep-high / sweep-low behavior versus prior 60m extrema.
- Current closed-bar close-break above/below prior 60m extrema.

Prior extrema explicitly exclude the current bar.

### 4. Path / time context
- Relationship between 360m displacement and 60m displacement.
- UTC hour/minute and WIB hour/quarter.
- Day of week.
- Cyclical time-of-day sine/cosine.
- Fixed WIB six-hour bucket.

## Frozen coarse state map
These states are diagnostic/hierarchical handles. A2 must retain access to the numeric vector and must not rely only on an exact concatenated token.

### `trend_state`
Based on `disp_atr_120`:
- `< -1.00`: `STRONG_DOWN`
- `[-1.00, -0.35)`: `DOWN`
- `[-0.35, +0.35]`: `FLAT`
- `(0.35, 1.00]`: `UP`
- `> +1.00`: `STRONG_UP`

### `efficiency_state`
Based on 120m directional efficiency:
- `< 0.25`: `LOW`
- `[0.25, 0.55)`: `MID`
- `>= 0.55`: `HIGH`

### `vol_state`
Based on `ATR60 / ATR360`:
- `< 0.80`: `COMPRESS`
- `[0.80, 1.25]`: `NORMAL`
- `> 1.25`: `EXPAND`

### `range_state`
Based on 120m range position:
- `< 1/3`: `LOW`
- `[1/3, 2/3]`: `MID`
- `> 2/3`: `HIGH`

### `liquidity_state`
Priority from the current fully closed 5m bar versus prior 60m extrema:
1. `SWEEP_BOTH`
2. `SWEEP_LOW`
3. `SWEEP_HIGH`
4. `BREAK_LOW`
5. `BREAK_HIGH`
6. `NONE`

### `path_state`
Uses long displacement (`disp_atr_360`) and short displacement (`disp_atr_60`) with fixed 0.75 / 0.25 ATR thresholds to distinguish continuation, pullback, pause, and mixed/range paths.

### `structure_state`
Two adjacent 60-minute blocks compare their highs and lows with 0.10 ATR360 tolerance:
- `HH_HL`
- `LH_LL`
- `HH_LL`
- `LH_HL`
- `OVERLAP`

## Character token
A diagnostic token may concatenate:

`structure | trend | efficiency | volatility | range | liquidity | path | WIB bucket`

This token is **not** a trading rule and is not allowed to be ranked by future PnL in A1.

## Anti-leak invariant
A1 must run the same fingerprint function twice:
1. full frozen history through `2026-08-26`;
2. raw history truncated before `2025-01-01T00:00:00Z`.

For all overlapping completed decision timestamps through the cutoff:
- all categorical features must be exactly identical;
- all numeric features must agree to numerical tolerance (`rtol=1e-12`, `atol=1e-12`).

Any mismatch is an **A1 failure**.

This test detects accidental globally fitted normalization, centered windows, future-dependent transforms, or other hidden future dependency.

## A1 acceptance gates
A1 passes only if all are true:
1. frozen raw 5m coverage >= 99.5%;
2. raw timestamps and decision timestamps are unique and monotonic;
3. the causal full-vs-prefix invariant passes;
4. all exported numeric features are finite after the declared warm-up;
5. all required categorical features are populated;
6. each core state family has at least two observed states on frozen history;
7. no outcome/trade/entry/TP/SL/PnL feature is present in the fingerprint schema.

Pass status:

`BNB_B29_A1_STRUCTURE_FINGERPRINT_PASS`

Any data, causality, schema, or representation failure:

`BNB_B29_A1_STRUCTURE_FINGERPRINT_FAIL`

## A1 artifacts
- full compressed fingerprint table for reproducibility / A2 input;
- compact sanity report;
- state coverage table;
- schema table;
- status file.

## Stop rule
A1 ends when the representation gates pass or a representation defect is found.

Do **not** tune thresholds because a state later looks unprofitable. Do **not** inspect post-boundary forward data. Do **not** start entry or TP/SL optimization inside A1.
