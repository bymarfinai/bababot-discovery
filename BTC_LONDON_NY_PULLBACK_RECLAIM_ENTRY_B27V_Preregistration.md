# B27V — London -> New York Pullback Reclaim Entry — Preregistration

## Purpose
Test whether the frozen B27Q London->New York High-pressure signal becomes tradeable when entry waits for evidence that an upper-range pullback has finished, instead of using a blind limit or arbitrary fixed stop.

B27Q signal identity is frozen. B27V changes only post-signal entry confirmation and stop placement.

## Cohorts
- Primary: `LONDON_TO_NEWYORK`, `LONG`, K1 High-pressure, `OPP0` (opposite-side visits = 0 at signal time).
- Secondary diagnostic: same cohort at K2 OPP0.
- Partitions: external, development, reference_validation, August.

## Frozen previous-session geometry
For each signal:
- `H` = completed previous London High.
- `L` = completed previous London Low.
- Range fraction is Low=0, High=1.
- Require `H > L`.
- TP remains exactly `H`.

No B27Q touch/retest definition is changed.

## Pullback activation zones
Exactly three predeclared upper-range levels are tested independently:
- `Z75` = `L + 0.75*(H-L)`
- `Z80` = `L + 0.80*(H-L)`
- `Z85` = `L + 0.85*(H-L)`

A zone becomes activated on the first eligible 5m bar after signal completion whose low is <= the zone price, provided no strict 5m close has already broken H or L.

The signal bar itself can never activate or fill a B27V setup.

## Frozen bullish reclaim confirmation
After a zone has activated, track `pullback_low` as the lowest 5m low from the activation bar through the current bar.

A bullish reclaim is confirmed only on a LATER 5m bar when all are true:
1. 5m close >= the activated zone price;
2. 5m close > the immediately previous 5m bar high;
3. 5m close <= H and 5m close >= L (the frozen range has not close-broken).

The confirmation bar is used only to establish the signal. There is no same-bar entry.

## Entry
- Entry is the OPEN of the next available 5m bar after confirmation completion.
- Entry is valid only if `pullback_low < entry < H`.
- If the next bar does not exist before New York session end, status = `NO_ENTRY_BAR`.
- If next-bar open is >= H or <= pullback_low, status = `INVALID_NEXT_OPEN_GEOMETRY`; no hypothetical fill is created.

## Stop and target
- SL = the frozen `pullback_low` known at confirmation completion.
- TP = previous London High `H`.
- No buffer, ATR, percentage stop, trailing stop, or breakout-extension target is permitted in this experiment.
- Nominal RR is `(H-entry)/(entry-pullback_low)` and is allowed to vary naturally.

## Invalidation before confirmation
Before reclaim confirmation:
- strict 5m close > H -> `TARGET_BROKE_BEFORE_CONFIRMATION`;
- strict 5m close < L -> `OPPOSITE_BROKE_BEFORE_CONFIRMATION`;
- no confirmation by session end -> `NO_CONFIRMATION`.

## Trade resolution
From the entry 5m bar onward:
- TP touch = high >= H;
- SL touch = low <= frozen pullback_low;
- if TP and SL occur in the same 5m bar, score conservative SL;
- otherwise first barrier touch resolves;
- if unresolved by New York session end, time-exit at first available 5m open at/after session end.

Illustrative notional = $500. Round-trip fee = $0.40.

## Required outputs
Persist one row per signal x zone with:
- signal identity and partition;
- activation timestamp;
- confirmation timestamp;
- pullback low and its range fraction;
- entry timestamp/price;
- stop/target;
- nominal RR;
- exit reason and PnL.

Summarize by partition / K / zone:
- setups;
- activations;
- confirmations;
- confirmation rate;
- trades;
- WR;
- TP rate;
- PF;
- net expectancy;
- total net;
- median nominal RR;
- median pullback-low fraction.

## Provisional screen
A primary K1 zone is `SCREEN_PASS` only if the identical zone has in external, development, and reference_validation:
- >= 30 resolved trades in EACH partition;
- positive net expectancy in EACH partition;
- PF >= 1.20 in EACH partition.

This remains discovery evidence, not independent OOS promotion.

## Mandatory assertions
The program must abort before persistence if any fail:
1. B27Q K1/K2 OPP0 signal identities are reused unchanged.
2. Activation cannot occur on the B27Q signal bar.
3. Confirmation must occur strictly after activation.
4. Confirmation close is >= zone and > prior 5m high.
5. Entry occurs exactly on the next 5m bar after confirmation.
6. `pullback_low` uses only bars from activation through confirmation, never future bars.
7. `pullback_low < entry < H` for every filled trade.
8. Stop equals the frozen pullback low exactly.
9. No trade is created after a strict H/L close-break before confirmation.
10. Same-5m TP+SL ambiguity is scored conservatively as SL.
11. All chronology uses raw 5m data; no aggregated B27 touch counts are used for entry timing.

Research only. Live BBC unchanged.
