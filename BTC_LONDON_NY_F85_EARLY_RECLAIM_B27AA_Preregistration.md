# B27AA — London -> New York Early F85 Rejection / Reclaim Filter — Preregistration

## Purpose
Test one narrow remaining hypothesis without changing the B27Q/B27W structural detector:

**A blind F85 touch mixes healthy pullbacks with continuation-down paths. Requiring the earliest causal 5m reclaim of F85 may filter the bad touches before H2 without waiting for the slower B27V previous-5m-high confirmation.**

This is an entry-quality test, not a new liquidity detector.

## Frozen source cohort
Use exactly the B27W filled F85 opportunities:
- BTCUSDT
- LONDON_TO_NEWYORK
- LONG
- B27Q K1 OPP0
- first High-touch episode has causally ended
- F85 was touched/filled before H2 under B27W chronology
- same frozen external / development / reference_validation / August partitions

B27AA must reproduce the B27W F85 touch identity and touch timestamps exactly. No F84/F86 or other entry-location sweep is allowed.

## Frozen levels
For completed previous London session:
- L = previous London Low
- H = previous London High
- R = H-L
- F85 = L + 0.85R
- structural close-invalidation boundary = F35 = L + 0.35R (same D50 geometry as the current B27Z ranking leader)
- breakout target = E20 = H + 0.20R (same target as the current B27Z ranking leader)

H2 remains a milestone, not TP.

## Primary confirmation — EARLY_RECLAIM
Starting with the exact raw 5m bar on which B27W first touched/filled F85:

1. The F85 touch bar itself is allowed to confirm if its completed close is strictly above F85.
2. If the touch bar closes at/below F85, wait for the first later completed raw 5m bar whose close is strictly above F85.
3. No requirement for `close > previous 5m high`, bullish body, wick ratio, EMA, ATR, volume, or any other indicator.
4. If H2 occurs before a qualifying confirmation completes, the setup expires.
5. If a completed 5m close < L occurs before confirmation, the setup expires.
6. If New York session ends before confirmation, the setup expires.

This directly tests the incremental value of the earliest F85 reclaim and avoids B27V's deliberately later micro-high confirmation.

## Secondary diagnostic — SAME_BAR_REJECTION
A strict subset of EARLY_RECLAIM:
- the original B27W F85 touch bar itself has `close > F85`.
- entry is next raw 5m bar open.

This is diagnostic only and is not a separate threshold search.

## Entry execution
Entry is the OPEN of the raw 5m bar immediately after the completed confirmation bar.

Causality rule around H2:
- if that next bar opens at or above H, H2 has effectively arrived at the open and the entry is rejected as `MISSED_H2_AT_OPEN`;
- if that next bar opens below H, the trade may enter at the open even when that same bar later becomes the H2 bar, because the bar open is chronologically before its later intrabar high.

Require actual entry price > F35 and < H. Otherwise reject the entry as invalid geometry.

## Frozen exit economics
To isolate the confirmation filter, B27AA does NOT re-sweep exits.

Primary economics are frozen to the current B27Z ranking leader:
- TP = E20 = H + 0.20R, resting limit;
- invalidation = completed raw 5m close strictly below F35;
- close-invalidation exits at that completed close price;
- no wick-only stop;
- H2 is not an exit;
- if TP high and close-invalidation occur on the same 5m bar, TP is credited because the resting target can execute intrabar before the close-based invalidation becomes observable;
- if neither occurs by New York session end, exit at first available 5m open at/after session end.

Economics:
- illustrative notional $500;
- round-trip fee $0.40;
- no leverage assumption is needed for PnL comparison.

## Outputs
For each partition and confirmation variant report:
- original B27W F85 opportunities;
- confirmed count and confirmation rate;
- executed trades and execution rate;
- same-bar vs later-reclaim counts;
- median minutes from F85 touch to confirmation and entry;
- H2-before-exit rate;
- E20 TP rate;
- trading WR (`net_pnl_usd > 0`);
- PF;
- mean net expectancy/trade;
- total net PnL;
- median realized entry fraction in London range;
- median realized nominal RR to E20 vs F35;
- close-invalidation and time-exit counts.

Persist one row per original F85 opportunity with touch, confirmation, entry, H2, exit and PnL timestamps/values.

## Selection gate
Only EARLY_RECLAIM can be tagged `SCREEN_PASS`, and only if the exact frozen rule has in each of external, development, reference_validation:
- >= 30 executed trades;
- WR >= 70%;
- PF >= 1.20;
- positive mean net expectancy/trade.

Reference_validation has been inspected previously and is not pristine OOS; this remains historical discovery evidence, not live promotion.

## Mandatory assertions
1. B27W F85 filled-opportunity identity and original touch timestamps reproduce exactly.
2. Every confirmation close is strictly > F85.
3. No confirmation completes after H2; a bar that is already H2 cannot confirm.
4. No confirmation after completed close < L.
5. Entry is exactly the next raw 5m open after confirmation completion.
6. Entry at H2-bar open is allowed only when that open < H; entry at/open above H is rejected.
7. Actual entry must satisfy F35 < entry < H.
8. TP is exact E20; close-invalidation boundary is exact F35.
9. Wick through F35 without a close below F35 does not stop the trade.
10. All chronology is raw 5m.
11. Synthetic tests must cover same-bar reclaim, later reclaim, H2-before-confirmation expiry, entry-on-H2-bar-open, missed-H2-at-open, wick-through stop survival, TP vs close-stop same-bar ordering, and session-end exit before real results persist.

Research only. Live BBC unchanged.
