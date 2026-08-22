# B27AO — BTC London->NY SHORT F15 Early-Reject Confirmation Audit — Preregistration

## Purpose
Continue the independently rebuilt SHORT lineage after B27AK/B27AL/B27AM/B27AN and test the confirmation stage equivalent to LONG B27AA.

Question: **does requiring the earliest causal completed 5m rejection below independently discovered F15 improve entry quality versus blind F15, without changing the liquidity detector, retrace zone, target, stop geometry, or regime universe?**

This is an entry-confirmation audit. It is not a new liquidity detector, retrace-zone search, exit search, regime filter, or runner study.

## Frozen source cohort
- BTCUSDT, raw repository 5m chronology.
- `LONDON_TO_NEWYORK`, SHORT, B27Q K1, OPP0.
- Frozen previous-London H/L.
- B27AK independent SHORT retrace discovery result is frozen: **F15 is the only passing zone**.
- Use exactly B27AK F15 filled opportunities and reproduce their touch timestamps/H2 labels before interpreting confirmation results.
- No 4H regime gate.

Frozen B27AK F15 structural identities that must reproduce:
- external: 50 fills / 37 H2
- development: 79 / 59
- reference_validation: 34 / 24
- august: 1 / 1

## Frozen levels
With `R = H-L`:
- F15 = `L + 0.15R`
- fixed close-invalidation boundary F65 = `L + 0.65R` (D50 from F15)
- fixed target E20_DOWN = `L - 0.20R`

The fixed E20/D50 pair is carried forward from B27AN only to isolate the effect of confirmation. No exit re-sweep is allowed.

## Primary confirmation — EARLY_REJECT
Starting on the exact raw 5m bar where B27AK first fills F15:
1. The F15 touch bar may confirm if its completed close is **strictly below F15**.
2. Otherwise wait for the first later completed raw 5m bar with `close < F15`.
3. No previous-bar-low break, candle-body threshold, wick ratio, EMA, ATR, volume, swing state, or other indicator is required.
4. If H2 (`low <= L`) occurs before a qualifying confirmation completes, the setup expires.
5. If opposite invalidation (`close > H`) occurs before confirmation, the setup expires.
6. If New York session ends first, the setup expires.

## Secondary diagnostic — SAME_BAR_REJECTION
Strict subset of EARLY_REJECT:
- the original F15 touch bar itself has `close < F15`.
- entry is next raw 5m bar open.

Diagnostic only; it cannot be promoted by this audit.

## Entry execution
- Entry = open of the raw 5m bar immediately after the completed confirmation bar.
- If that next open is `<= L`, H2 has effectively arrived at the open and the setup is rejected as `MISSED_H2_AT_OPEN`.
- If next open is `> L`, entry may occur even if that same bar later becomes the H2 bar.
- Actual entry must satisfy `L < entry < F65`; otherwise reject as invalid geometry.

## Frozen exit economics
For every executed confirmation trade:
- TP = E20_DOWN = `L - 0.20R`, resting limit.
- invalidation = first completed raw 5m `close > F65`.
- close invalidation exits at that actual completed close.
- wick-only penetration above F65 does not stop the trade.
- H2 is milestone only, never TP.
- on the same post-entry bar, an intrabar E20 target touch has precedence over a later close-based invalidation.
- if neither occurs before New York session end, exit at first available 5m open at/after session end.

Economics:
- illustrative notional $500
- round-trip fee $0.40
- SHORT gross return = `1 - exit/entry`
- trading win = net PnL > 0

## Required outputs
By partition and variant report:
- original B27AK F15 opportunities
- confirmation count/rate
- executed count/rate
- same-bar and later-reject counts
- median minutes touch->confirmation and touch->entry
- E20 TP rate
- WR, PF, mean expectancy/trade, total PnL
- median actual entry fraction
- median nominal reward:risk to E20 vs F65
- H2-before-exit rate
- close-invalidation and time-exit counts

Persist one row per original F15 opportunity per confirmation variant.

## Selection gate
Only `EARLY_REJECT` can be tagged `SCREEN_PASS`, and only if the same frozen rule has in EACH external/development/reference_validation partition:
- >=30 executed trades
- WR >=70%
- PF >=1.20
- positive mean net expectancy/trade

If it fails, report failure. Do not add F14/F16, new candle thresholds, regime gates, or alternative exits.

## Mandatory assertions
1. B27AK F15 fill identity, fill timestamps, and H2 classifications reproduce exactly.
2. Every confirmation close is strictly below F15.
3. No confirmation bar is H2 or after H2/opposite terminal.
4. Entry is exactly next raw 5m open after confirmation completion.
5. Entry at H2-bar open is allowed only if open > L; open <= L is rejected.
6. Every executed entry satisfies L < entry < F65.
7. TP is exact E20_DOWN; close invalidation boundary is exact F65.
8. Wick-only F65 penetration cannot invalidate.
9. Same-bar target/close-invalidation ordering credits the resting target first.
10. Full 5m archive coverage reproduces.
11. Synthetic tests cover same-bar rejection, later rejection, H2 expiry, missed-H2-at-open, and fixed-exit ordering.

Research only. Live BBC unchanged.
