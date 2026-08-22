# B27AN — BTC London->NY SHORT F15 Extension Economic Backtest — Preregistration

## Purpose
Test whether the independently discovered SHORT F15 entry can be converted into a repeatable economic trade while preserving the frozen structure:

**Touch Low #1 -> causal leave -> SELL F15 before H2 -> H2 Low is a milestone, not TP -> target downside extension below previous London Low.**

B27AN does not alter B27Q/B27AD/B27AK detector chronology or F15 entry identity.

## Frozen cohort and entry
Primary cohort only:
- BTCUSDT
- LONDON_TO_NEWYORK
- SHORT
- B27Q K1 OPP0
- B27AK F15 entries with `filled=True`
- no 4H regime gate

For every trade:
- H = frozen previous London High
- L = frozen previous London Low
- R = H-L
- entry = L + 0.15*R
- entry timestamp must reproduce B27AK/B27AD exactly
- entry must be strictly before H2 when H2 exists

No confirmation entry filter is introduced.

## H2 treatment
H2 / the second arrival at previous London Low is a milestone only. The position remains open through H2 unless target or invalidation exits it.

## Frozen downside targets
Selected directly from the preregistered B27AM atlas before B27AN execution:
- E10_DOWN: TP = L - 0.10*R
- E15_DOWN: TP = L - 0.15*R
- E20_DOWN: TP = L - 0.20*R

No E05, E25, intermediate target, or post-result target is searched.

## Frozen close-invalidation boundaries
Selected as the exact SHORT mirror of the coarse B27Z distance grid, with entry F15:
- D30 -> boundary F45 = L + 0.45*R
- D40 -> boundary F55 = L + 0.55*R
- D50 -> boundary F65 = L + 0.65*R
- D60 -> boundary F75 = L + 0.75*R

A loss is not triggered by a wick above the boundary. Invalidation occurs only when a completed raw 5m candle closes strictly ABOVE the frozen boundary. Close invalidation exits at that candle's actual close so overshoot is not hidden.

## Chronological execution
For each frozen F15 fill and each of the 12 target/boundary pairs:
1. Position is active from the exact F15 fill bar.
2. Beginning with the fill-bar close, completed `close > boundary` invalidates at actual close.
3. Target is not allowed on the fill bar; from subsequent raw 5m bars onward, if `low <= target_px`, the limit TP fills exactly at target.
4. On any post-entry bar where target is reached intrabar and the same bar later closes above invalidation, TP takes precedence because close invalidation is only known at completion.
5. H2 alone never exits the trade.
6. If neither event occurs by NY session end, exit at the first available 5m open at/after session end.
7. No post-session event may influence the result.

## Economics
- illustrative notional: $500
- round-trip fee: $0.40
- SHORT gross return = `(entry_px - exit_px) / entry_px`
- net PnL = gross return * $500 - $0.40
- trading win = net PnL > 0

Nominal reward in range units from F15:
- E10_DOWN = 0.25R
- E15_DOWN = 0.30R
- E20_DOWN = 0.35R

Nominal boundary risks:
- D30 = 0.30R
- D40 = 0.40R
- D50 = 0.50R
- D60 = 0.60R

## Frozen discovery screen
A target/boundary pair is SCREEN_PASS only if the exact same pair has in EACH major partition (`external`, `development`, `reference_validation`):
- >=30 resolved trades
- WR >=70%
- positive mean net expectancy
- PF >=1.20

August is telemetry only and cannot rescue a pair. If none pass, report none. No new grid values may be added after seeing PnL.

## Mandatory assertions
1. Full raw 5m archive coverage reproduces.
2. B27AK F15 identities reproduce exactly before economics: external 50 fills/37 H2; development 79/59; reference_validation 34/24; august 1/1.
3. Every entry price equals exact F15.
4. Every existing H2 is strictly after entry.
5. E10/E15/E20 downside geometry exact.
6. D30/D40/D50/D60 upward boundary geometry exact.
7. Wick-only boundary penetration does not invalidate.
8. Every close invalidation has raw `close > boundary` and exits at that exact close.
9. Every TP has raw `low <= target` and exits at exact target.
10. H2 alone never exits.
11. Post-entry TP takes precedence over same-bar later close invalidation.
12. No post-session event is used.
13. Synthetic tests cover wick-only survival, close invalidation, H2-without-exit, target after H2, target+close-invalidation same bar, and time exit.

Research only. Live BBC unchanged.
