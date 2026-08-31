# BNB 01:00 WIB Post-Leave Sequence Diagnosis — B27FM Preregistration

## Purpose

B27FM is a structural discovery milestone after completion of the full 24-hour clock sweep (B27FK) and its comparability/normalization audit (B27FL).

The normalized leader is frozen as **01:00 WIB**. B27FM does not re-select the clock and does not define a trading entry. It diagnoses the causal path after the already-defined B27FL causal leave to identify where an executable future hypothesis may plausibly exist.

## Frozen data and universe

- Symbol: BNBUSDT
- Raw 5m loader: unchanged inherited repository loader
- Development partition only: 2022-01-01 00:00 UTC through 2025-01-01 00:00 UTC exclusive
- Normalized common local-date universe from B27FL: **2022-01-02 through 2024-12-31 inclusive**
- Expected complete sessions: **1095**
- Timezone: Asia/Jakarta (WIB, UTC+7)
- Anchor: **01:00 WIB only**
- Reference window: 01:00 <= t < 05:00 WIB
- Execution window: 05:00 <= t < 09:00 WIB
- All seven weekdays included
- No external, reference-validation, August, or holdout data may be used

## Frozen structural state machine

Use the exact B27EM/B27FA–B27FL LONG state machine without modification:

1. SEEK_K1
   - close > H or close < L before K1 => BREAK_BEFORE_K1
   - H structural visit: high >= H and close <= H
   - L structural visit: low <= L and close >= L
   - simultaneous H+L event => AMBIGUOUS_BOTH_BOUNDARIES
   - K1 qualifies only when the first H visit occurs with zero prior L visits
2. K1_EPISODE
   - while high >= H and close <= H, remain in the same K1 episode
   - first completed 5m candle not belonging to that same H episode is the causal leave
   - leave_ts = end of that completed leave candle
3. AFTER_LEAVE
   - H2 arrival: high >= H
   - opposite structural break: close < L
   - same-bar H2 + opposite => AMBIGUOUS_H2_VS_OPPOSITE_BREAK
   - neither by execution end => NO_H2_BY_END
   - no favorable same-bar ordering assumption

## Mandatory reproduction gate before sequence analysis

On the normalized universe, the runner must reproduce the B27FL 01:00 result exactly:

- Sessions: 1095
- Causal leaves: **162**
- H2 arrivals: **132**
- H2/leave: 132/162 = **81.48148...%**

Any mismatch aborts B27FM.

## Causal post-leave observation rule

For each causal leave:

- The leave candle is already completed at `leave_ts`.
- Post-leave analysis begins at the first 5m candle whose **start timestamp equals leave_ts**.
- A terminal H2/opposite candle is terminal as soon as its completed OHLC is observed under the frozen state machine.
- For pullback/threshold analysis, the terminal candle itself is **not** allowed to establish a prior pullback threshold. This prevents pretending to know within-bar ordering relative to H2 or opposite-break events.

## Frozen sequence outputs

### A. Terminal path

Report across all 162 causal leaves:

- H2_ARRIVAL
- OPPOSITE_BREAK_BEFORE_H2
- AMBIGUOUS_H2_VS_OPPOSITE_BREAK
- NO_H2_BY_END

### B. H2 arrival timing

For H2 arrivals, report exact bars/minutes from leave to H2 and these frozen buckets:

- 1 bar = 5m
- 2 bars = 10m
- 3 bars = 15m
- 4–6 bars = 20–30m
- 7–12 bars = 35–60m
- 13+ bars = 65m+

Also report median and quartiles of leave→H2 minutes.

### C. Pre-H2 pullback depth

For H2 arrivals only, using **strictly non-terminal bars before the H2 candle**:

- `pre_h2_low_depth_R = max(0, (H - min(low))/R)`
- `pre_h2_close_depth_R = max(0, (H - min(close))/R)`
- if H2 occurs on the first post-leave candle, both prior-depth values are defined as 0

Report p25 / median / p75 / p90 for both low-depth and close-depth.

These are descriptive path statistics only; the H2 terminal candle low/close is excluded from prior-depth calculations.

### D. Frozen completed-close pullback grid

Evaluate the following thresholds only:

- P10: completed close <= H - 0.10R
- P20: completed close <= H - 0.20R
- P35: completed close <= H - 0.35R
- P50: completed close <= H - 0.50R

A threshold counts only if it is first observed on a **completed non-terminal post-leave candle before the frozen terminal event**. The same terminal candle may not count as a threshold arrival.

For each threshold report:

- number and share of all 162 causal leaves that reach it before terminal
- eventual terminal distribution from that subset
- H2 recovery count/rate from that subset
- median and quartiles of threshold completion → H2 completion time for recoveries
- nested consistency checks (P50 subset of P35 subset of P20 subset of P10)

No threshold is selected as an entry inside B27FM.

### E. First post-leave completed candle

For all causal leaves where a post-leave candle exists, report:

- first post-leave close depth: `(H - close)/R`
- whether first post-leave candle is the H2 terminal candle
- H2 outcome rates by preregistered first-close-depth bins:
  - <= 0.10R below H
  - >0.10R to 0.20R
  - >0.20R to 0.35R
  - >0.35R to 0.50R
  - >0.50R

This is descriptive segmentation, not a filter recommendation.

## Interpretation boundary

B27FM may identify a descriptive post-leave sequence and one or more plausible causal pullback regions for a future preregistered executable hypothesis. It must **not**:

- call H2/leave or recovery rate a trading win rate
- define a final entry
- define stop/target
- compute fees, slippage, PnL, PF, expectancy, leverage, or position sizing
- select weekdays
- change the 01:00 clock
- use holdout data

## Stop rule

Persist all B27FM outputs and STOP. Any actual entry rule must be defined in a new preregistered milestone after reviewing B27FM.
