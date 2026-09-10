# ETH Economic-First E11 — Market-State Character Discovery Preregistration

## Purpose
E10A/E10B showed that the two strongest E9 cross-era coordinates were narrow clock/lookback/hold ridges rather than stable three-dimensional plateaus. E11 therefore does **not** search for another magic clock.

The scientific question is:

> Is there a causal pre-entry market-state/path-shape rule whose **MOMENTUM or REVERSAL economics remain positive across many different UTC clocks and across 2022, 2023, and 2024**, so clock can be treated as context rather than the defining edge?

This is research/shadow only. No live promotion or profit guarantee.

## Data and fixed economics
- ETHUSDT Binance Futures raw 5m data.
- Development partition only. External and Reference Validation remain closed in E11.
- Weekdays only, matching the existing economic-first lineage.
- Entry at exact 5m bar open for each half-hour clock context.
- Exit at exact 5m bar open after the selected fixed hold.
- $500 fixed notional.
- $0.75 round-trip fee.
- Net PnL = gross directional PnL - $0.75.
- Net win iff net PnL > 0.
- No TP, SL, H/L, breakout, retest, EMA, Fibonacci, or post-entry filter.

## Clock treatment
All 48 half-hour UTC clocks are evaluated as a **panel of contexts**. Clock is never part of candidate identity and is never ranked as the winner in E11.

A market-state candidate must show breadth across the clock panel. E11 therefore does not pool overlapping clock trades into one portfolio PnL and does not claim that all 48 clocks can be traded simultaneously. Economics are summarized **per clock**, then aggregated robustly by medians/fractions across clocks.

## Candidate horizons
Lookback minutes: `15, 30, 60, 120, 240, 360`.

Hold minutes: `60, 120, 240, 360, 720, 960`.

Modes: `MOMENTUM`, `REVERSAL`.

The outer lookback/hold values are sentinels. E11 may identify a state grammar at a boundary, but such a result is explicitly marked boundary-open and is not eligible for downstream freezing without refinement.

## Causal pre-entry state features
For each `(clock, lookback)` observation, all path features use only prices known by the entry open. No future bar is used.

1. **EFF — directional path efficiency**
   - numerator: absolute move from lookback-start open to entry open;
   - denominator: sum of absolute 5m open-to-open path moves through the same interval;
   - bounded approximately 0..1.

2. **RV — realized volatility**
   - standard deviation of 5m log open-to-open returns over the lookback interval.

3. **RANGE — realized range**
   - `(max high - min low) / lookback-start open` over completed bars before the entry open.

4. **EXT — directional terminal location**
   - position of the entry open within the pre-entry high-low range, aligned with the sign of the pre-entry drive;
   - high values mean the drive ends near its directional extreme.

For each feature separately, its state percentile is calculated causally against the previous 60 observations of the **same clock and lookback**, requiring at least 40 prior observations. Current observation is excluded from its own reference history.

Percentile bins are frozen as:
- `LOW`: [0, 1/3)
- `MID`: [1/3, 2/3)
- `HIGH`: [2/3, 1]

## Frozen state-rule universe
Single-feature rules:
- EFF_LOW / MID / HIGH
- RV_LOW / MID / HIGH
- RANGE_LOW / MID / HIGH
- EXT_LOW / MID / HIGH

Two-feature interaction rules:
- EFF x RV: 9 tercile combinations
- EFF x RANGE: 9 combinations
- EFF x EXT: 9 combinations
- RV x RANGE: 9 combinations

Total state rules per `(lookback, hold, mode)`: **48**.

Total E11 candidate identities: `6 lookbacks × 6 holds × 2 modes × 48 rules = 3,456`.

Each candidate identity is evaluated across all 48 clock contexts independently.

## Per-clock summary
For each candidate and clock on Development, calculate:
- trades
- net WR
- net PnL
- expectancy
- PF
- max DD
- max loss streak

A clock is `evaluable` if it has at least **60 trades**.

An evaluable clock is `supportive` if:
- WR >= 52%
- net PnL > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

## Cross-clock and cross-era candidate gate
Candidate must satisfy all of:

### Breadth
- at least 36/48 clocks evaluable;
- at least 28 supportive clocks;
- supportive fraction among evaluable clocks >= 60%;
- at least 32 evaluable clocks with positive expectancy;

### Median economics across evaluable clocks
- median WR >= 53%;
- median expectancy >= +$0.20/trade;
- median PF >= 1.10;
- median max DD <= $90;

### Era stability
For each of 2022, 2023, 2024, using the same frozen candidate and calculating each clock separately within that calendar year:
- at least 30 clocks with >= 18 trades in that year;
- median clock WR >= 51%;
- median clock expectancy > 0;
- at least 55% of era-evaluable clocks have positive expectancy.

### Clock-block breadth
The 48 clocks are split into six fixed 4-hour UTC blocks. In at least **5 of 6** blocks, >=50% of evaluable clocks must be supportive.

## Selection
Among full-gate passers, select lexicographically by:
1. highest minimum annual median expectancy across 2022–2024;
2. highest supportive-clock fraction;
3. highest median clock expectancy;
4. highest median clock WR;
5. highest median PF;
6. lower median DD;
7. lower median loss streak;
8. more evaluable clocks;
9. shorter hold;
10. shorter lookback;
11. MOMENTUM before REVERSAL as deterministic tie-break only;
12. state-rule name alphabetically.

No post-hoc second-best substitution.

## Boundary handling
If selected candidate uses lookback 15/360 or hold 60/960, status is `ETH_ECONOMIC_FIRST_E11_STATE_BOUNDARY_OPEN`.

If selected candidate is interior, status is `ETH_ECONOMIC_FIRST_E11_STATE_SUPPORTED`.

If none passes, status is `ETH_ECONOMIC_FIRST_E11_NO_STATE_CANDIDATE`.

## Holdout handling
External and Reference Validation are **not opened in E11**, even if a state passes. E11 discovers the invariant state grammar only. A later preregistered experiment must translate a supported state into a non-overlapping executable clock/deployment rule before any OOS exposure.

## Integrity rules
- No gate relaxation after seeing results.
- No choosing a raw top performer that failed breadth or era gates.
- No OOS inspection in E11.
- No interpretation of overlapping panel medians as portfolio return.
- Persist the exact scientific verdict in this branch after the run.