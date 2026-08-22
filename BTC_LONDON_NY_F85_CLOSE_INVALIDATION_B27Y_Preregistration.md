# B27Y — London -> New York F85 Close-Based Invalidation — Preregistration

## Purpose
Convert the B27W structural F85 -> second-High-arrival edge into an actual trade outcome without changing the entry.

The entry is frozen exactly from B27W:
- LONDON_TO_NEWYORK LONG
- B27Q K1 OPP0
- first High-touch episode must causally end
- F85 limit may fill only after the causal leave and strictly before H2 arrival
- B27W F85 fill identity and timestamp must reproduce exactly

B27Y changes **only the loss/invalidation rule**.

## Frozen target
TP = previous London High H, i.e. H2 arrival after the F85 fill.

## Frozen close-invalidation boundaries
Previous London Low=0 and High=1. Entry is F85 = 0.85.

Test exactly four boundaries, selected before reading B27Y results from the B27X diagnostic bracket:
- D30 -> invalidation boundary F55
- D40 -> invalidation boundary F45
- D50 -> invalidation boundary F35
- D60 -> invalidation boundary F25

No other boundary is searched in B27Y.

A stop is **not** triggered by a wick through the boundary. It triggers only when a completed raw 5m candle closes strictly below the frozen boundary.

Execution of close invalidation is at that 5m close price, not at the boundary price. This makes gap/overshoot loss explicit rather than assuming a favorable boundary fill.

## Chronology
For each frozen B27W F85 fill:
1. Start from the actual B27W F85 fill bar.
2. Scan raw 5m bars chronologically.
3. If a later bar reaches H before any prior close invalidation, TP at H.
4. If a completed bar closes below the boundary before H2, exit at that close.
5. If a bar both reaches H and closes below the boundary, score conservatively as `SAME_5M_H2_CLOSE_INVALIDATION_CONSERVATIVE`, exit at the close, and do not award the TP.
6. If neither occurs by New York session end, exit at the first available 5m open at/after session end.

The B27W rule that the original F85 fill cannot occur on the H2 bar remains frozen.

## Economics
Illustrative notional = $500.
Round-trip fee = $0.40.
Net PnL uses actual entry and exit prices.

Nominal geometry before close overshoot:
- D30: reward 0.15 range / risk 0.30 range = 0.50R
- D40: 0.375R
- D50: 0.30R
- D60: 0.25R

Because actual close invalidation may occur below the boundary, realized loss can be larger than the nominal risk.

## Outputs
For each partition / boundary report:
- frozen F85 trade count
- TP / close-invalidation / time-exit counts
- real trading WR (net PnL > 0)
- TP rate
- PF
- mean net expectancy per trade
- total net PnL
- median nominal RR
- median realized loss for invalidated trades
- number of same-5m conservative conflicts

Persist one row per F85 trade/boundary with entry, boundary, target, exit timestamp, exit price, reason, and net PnL.

## Screen
A boundary is only tagged `SCREEN_PASS` if the exact same boundary has, in external, development, and reference_validation:
- >= 30 resolved trades per partition
- trading WR >= 70%
- positive net expectancy
- PF >= 1.20

This is still historical discovery evidence, not pristine forward/OOS promotion.

## Mandatory assertions
1. B27W F85 filled-trade identity and entry timestamps reproduce exactly.
2. Entry price is exactly F85 of frozen previous London range.
3. Invalidation boundary is exact frozen fraction F55/F45/F35/F25.
4. No wick-only stop.
5. Every close-invalidation bar has close < boundary.
6. H2 target and close invalidation are evaluated only on raw 5m chronology.
7. Same-5m H2 + close-invalidation is conservative, never an automatic win.
8. No target/stop event before entry.
9. Synthetic paths for wick-through-but-close-above, close invalidation, H2 first, same-bar conflict, and time exit pass before persistence.

Research only. Live BBC unchanged.
