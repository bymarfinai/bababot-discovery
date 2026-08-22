# B27Z — London -> New York F85 Extension Economic Backtest — Preregistration

## Purpose
Test whether the frozen B27W entry can be converted into a repeatable economic trade while preserving the intended structure:

**Touch High #1 -> causal leave -> BUY F85 before H2 -> H2 is a milestone, not TP -> target a breakout extension above previous London High.**

B27Z does not alter the B27Q detector, B27W entry window, or F85 entry identity.

## Frozen cohort and entry
Primary cohort only:
- BTCUSDT
- LONDON_TO_NEWYORK
- LONG
- B27Q K1 OPP0
- B27W F85 entries with `filled=True`

For every trade:
- H = frozen previous London High
- L = frozen previous London Low
- range R = H-L
- entry = L + 0.85*R
- entry timestamp must reproduce B27W exactly
- entry must be strictly before H2 when H2 exists

No new entry filter or confirmation is introduced.

## H2 treatment
H2 / the second arrival at previous London High is a **milestone only**.
The position remains open through H2 unless a breakout-extension target is reached.

## Frozen breakout targets
Selected directly from the preregistered B27Y atlas before B27Z execution:
- E10: TP = H + 0.10*R
- E15: TP = H + 0.15*R
- E20: TP = H + 0.20*R

No E05, E25, or intermediate target is searched in B27Z.

## Frozen close-invalidation boundaries
Selected from the B27X adverse-excursion bracket before B27Z execution. Entry is F85.

- D30 -> boundary F55 = L + 0.55*R
- D40 -> boundary F45 = L + 0.45*R
- D50 -> boundary F35 = L + 0.35*R
- D60 -> boundary F25 = L + 0.25*R

A loss is not triggered by a wick through the boundary. Invalidation occurs only when a completed raw 5m candle **closes strictly below** the frozen boundary.

Close invalidation exits at that candle's actual close, so overshoot/gap loss is not hidden.

## Chronological execution
For each frozen B27W F85 fill and each of the 12 target/boundary pairs:
1. Position is active from the B27W F85 fill.
2. On the fill bar, the exact F85 entry is frozen from B27W. B27W guarantees this bar is strictly before H2.
3. Beginning with the fill bar close, a completed 5m close below the invalidation boundary exits at that close.
4. From subsequent raw 5m bars onward, if `high >= target_px`, the limit TP fills at `target_px`.
5. Close invalidation is evaluated at bar completion. Therefore, on any bar after the entry bar, if the target is reached intrabar and the same bar later closes below the boundary, the TP has already executed and the trade is a TP win.
6. If no TP or close invalidation occurs by New York session end, exit at the first available 5m open at/after session end.
7. No event after session end may affect the result.

## Economics
- illustrative notional: $500
- round-trip fee: $0.40
- net PnL = gross return * $500 - $0.40
- trading win = net PnL > 0

Nominal target reward from F85:
- E10 reward = 0.25R
- E15 reward = 0.30R
- E20 reward = 0.35R

Nominal boundary risks before close overshoot:
- D30 risk = 0.30R
- D40 risk = 0.40R
- D50 risk = 0.50R
- D60 risk = 0.60R

Thus nominal reward:risk spans approximately 0.42R to 1.17R depending on the exact pair.

## Outputs
For each partition / target / boundary report:
- frozen F85 trade count
- TP count and rate
- close-invalidation count
- time-exit count
- real trading WR (`net_pnl_usd > 0`)
- PF
- mean net expectancy per trade
- total net PnL
- median realized winner and loser PnL
- median hold minutes
- H2-before-exit rate
- breakout-close-above-H-before-exit rate

Persist one row per trade/pair with entry, H2, target, invalidation boundary, exit timestamp, exit price, reason, gross return, net PnL, and hold time.

## Frozen discovery screen
A pair is tagged `SCREEN_PASS` only if the exact same target/boundary pair has in **external, development, and reference_validation**:
- >=30 resolved trades per partition
- WR >=70%
- positive net expectancy
- PF >=1.20

Selection may use only these three major historical partitions. August remains telemetry only and cannot rescue a failed pair.

If no pair passes, report none. Do not create additional targets or stop boundaries in B27Z.

## Mandatory assertions
1. B27W F85 filled-trade identity and entry timestamps reproduce exactly.
2. Entry equals F85 exactly for every trade.
3. Entry is before H2 whenever H2 exists.
4. E10/E15/E20 geometry is exact.
5. D30/D40/D50/D60 geometry is exact.
6. Wick-only boundary penetration never triggers invalidation.
7. Every close-invalidation exit has raw 5m `close < boundary` and exits at that exact close.
8. Every TP exit has raw 5m `high >= target` and exits at the exact target.
9. H2 alone never exits a trade.
10. Post-entry target touch on a bar takes precedence over that same bar's later close invalidation because close invalidation is only known at bar completion.
11. No target or invalidation event after New York session end is used.
12. Synthetic tests cover: wick-through/close-above survival, close invalidation, H2-without-exit, H2-plus-extension target, target-and-close-invalidation same bar, and time exit.

Research only. Live BBC unchanged.
