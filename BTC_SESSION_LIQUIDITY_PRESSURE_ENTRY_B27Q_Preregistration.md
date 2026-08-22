# B27Q — Causal Previous-Session Liquidity Pressure -> Retrace Entry Grid — Preregistration

## Purpose
Test the user's intended visual liquidity setup directly, without the prior swing/fractal/touch engines:
1. Freeze the completed previous-session High and Low.
2. During the next session, count distinct chronological visits to those exact horizontal levels using the underlying 5m price clock.
3. Ask whether repeated visits to one side create a causal directional pressure signal.
4. Only AFTER that signal is known, test whether waiting for a retrace into the frozen range improves entry quality.

This is a new additive experiment. B27C-K and B27L-P touch counts are not reused as evidence.

## Market / source / partitions
- BTCUSDT, same repository 5m Binance source.
- Same frozen scoring partitions as B22B.
- Weekdays only.
- Fixed UTC sessions, unchanged from B26C:
  - Asia 00:00-08:00 -> London 08:00-13:30.
  - London 08:00-13:30 -> New York 13:30-20:00.
- A partition is a scoring boundary only. Previous-session High/Low are constructed from the complete same-day previous-session data and are never modified by later candles.

## Frozen liquidity levels
For each transition/day:
- H = completed previous-session High.
- L = completed previous-session Low.
- Require H > L.
- Range fraction f maps to price `L + f*(H-L)`.

No fractal swing, EMA, order block, ATR band, percentage-of-range touch zone, or newly formed minor high/low may replace H or L.

## Exact chronological touch / retest definition
The event clock is the available 5m source.

Before the first confirmed range breakout:
- High visit: 5m `high >= H` while 5m `close <= H`.
- Low visit: 5m `low <= L` while 5m `close >= L`.
- Consecutive qualifying 5m bars on the same level are ONE distinct visit.
- A new distinct visit requires at least one intervening 5m bar that does not qualify for that level.
- A strict breakout bar is evaluated BEFORE touch counting and is never counted as a prior visit.
- Confirmed BULL breakout = first 5m close > H.
- Confirmed BEAR breakout = first 5m close < L.
- If one pre-breakout 5m bar qualifies as a visit to BOTH H and L, the session is marked `AMBIGUOUS_BOTH_LEVELS` and excluded because intrabar visit order is unknowable.

Every distinct visit must be persisted with its timestamp and ordinal visit number so reported counts are manually auditable.

## Causal pressure signals
For each side independently, freeze three thresholds:
- K1 = first distinct visit.
- K2 = second distinct visit.
- K3 = third distinct visit.

A LONG/BULL pressure signal occurs at completion of the 5m bar that creates High visit K.
A SHORT/BEAR pressure signal occurs at completion of the 5m bar that creates Low visit K.

At signal time persist the number of opposite-side visits already known.
Report two predeclared purity views:
- `ALL`: all signals at that K.
- `OPP0`: opposite-side visits == 0 at signal time.

No signal may be created after the first strict close breakout of either frozen boundary.

## Structural outcome after a pressure signal
Starting strictly after signal completion and ending at active-session end, classify:
- `TARGET_BREAK`: same-side frozen boundary gets the first strict close breakout.
- `OPPOSITE_BREAK`: opposite frozen boundary gets the first strict close breakout.
- `NO_BREAK`: neither strict close breakout occurs by session end.

This structural classification is independent of whether an entry order fills.

## Retrace-entry grid
Each pressure signal is evaluated independently as a research candidate. There is no portfolio overlap filter in the structural/entry atlas.

Four frozen retrace depths are tested. `f` is measured from Low=0 to High=1.

For LONG after High-pressure:
- `SHALLOW`: f = 0.75.
- `MID`: f = 0.50.
- `DEEP`: f = 0.25.
- `NEAR_OPPOSITE_EDGE`: f = 0.10.

For SHORT after Low-pressure, mirror around midpoint:
- `SHALLOW`: f = 0.25.
- `MID`: f = 0.50.
- `DEEP`: f = 0.75.
- `NEAR_OPPOSITE_EDGE`: f = 0.90.

The limit order becomes eligible only from the NEXT 5m bar after the signal bar. Because signal time is signal-bar end, the first eligible bar starts exactly at `signal_ts`.

Before fill, any later 5m strict close outside H/L cancels the order as `RANGE_BROKE_BEFORE_FILL`. A cancelled thesis may not enter after breakout.

Fill occurs when an eligible 5m bar has `low <= entry_price <= high`.

## Exit / economics
- LONG: SL = L, TP = H.
- SHORT: SL = H, TP = L.
- Therefore entry depth naturally changes reward:risk; it is not forced to one fixed RR.
- On the fill 5m bar, if stop is touched, score conservative SL. Target-only touch on the fill bar is NOT awarded because target may have occurred before the limit fill.
- From the next 5m bar onward, first barrier touch resolves; same-5m TP+SL = conservative SL.
- If unresolved by active-session end, exit at first available 5m open at/after session end.
- Illustrative notional = $500.
- Round-trip fee = $0.40 per resolved trade.

## Required outputs
Persist:
1. one-row-per-distinct-visit audit file;
2. one-row-per-pressure-signal structural file;
3. one-row-per-signal x entry-depth candidate trade file;
4. structural probability summary by transition / partition / side / K / purity;
5. entry summary by transition / partition / side / K / purity / entry depth.

Report setup count, fills, fill rate, W/L, WR, TP rate, PF, net expectancy, total net, time-exit rate, median nominal RR, and structural target/opposite/no-break probabilities.

## Provisional repeatability screen
This experiment is a discovery grid, not a promotion test. A row may be marked `SCREEN_PASS` only when the exact same `(transition, side, K, purity, entry_depth)` has in external, development, and reference_validation:
- >= 50 filled/resolved trades in EACH partition;
- positive net expectancy after fee in EACH partition;
- net PF >= 1.20 in EACH partition.

Because multiple K/depth combinations are examined, `SCREEN_PASS` means only "candidate worth independent validation" and does NOT authorize live BBC changes.

## Mandatory synthetic and real-data assertions
The program must abort before result persistence if any fail:
1. consecutive same-level 5m touches collapse to one visit;
2. leave level then return increments visit count;
3. breakout bar is excluded from visit count;
4. a both-level pre-breakout 5m bar is marked ambiguous;
5. every visit ordinal is contiguous and has an auditable timestamp;
6. no signal occurs after first breakout;
7. every order is first eligible only after signal-bar completion;
8. every entry price equals its frozen range fraction exactly;
9. LONG SL/TP = L/H and SHORT SL/TP = H/L;
10. no filled order has a strict close breakout between signal completion and the fill bar;
11. every signal/trade is derived from raw 5m chronology, not from 15m/1H/4H touch aggregation.

Research only. Live BBC unchanged.
