# BTC Weekly Structural Confluence B8 — Preregistration

Status: **FROZEN BEFORE RESULT**

Purpose: search for a causal BTC entry process that produces at least one trade in every complete ISO week and tests whether historical external + validation win rate can reach 100% with modeled net RR >= 1:1. This is a research target, not a guarantee of future wins.

## Why this is a new study
The repository already covers generic ORB, S/R, FVG, Fibonacci, and many filter families separately. B8 does **not** retune those old studies. The materially new object is a **weekly causal router** that lets four frozen structural theories vote on each completed H1/H4 bar, takes the first multi-theory confluence in a week, and uses one fixed weekly fallback checkpoint when no confluence has appeared. No retrospective best-trade-of-week selection is allowed.

## Market / source
- BTCUSDT USD-M perpetual.
- Official completed Binance Futures H1 archive used by existing research.
- Native H1 and UTC-aligned H4 aggregated from H1.
- External untouched partition: 2020-01-01 through 2021-12-31.
- Development: 2022-01-01 through 2024-12-31.
- Reference validation: 2025-01-01 through 2026-07-29.
- August diagnostic: 2026-08-01 onward through available completed archive.

## Frozen structural theories
All signals use completed bars only and entry is always the next bar open.

### 1. ORB retest continuation
- UTC daily opening range = 00:00-04:00 UTC.
- H1 OR uses the four completed H1 bars starting 00:00, 01:00, 02:00, 03:00 UTC.
- H4 OR uses the completed 00:00-04:00 H4 bar.
- LONG vote only after a completed close broke above OR high and the next completed bar retests the OR high and closes back above it.
- SHORT symmetric below OR low.

### 2. Support / resistance rejection
- Prior 20 completed bars define causal rolling resistance high and support low.
- LONG vote when current bar touches within 0.15 ATR of prior support, closes bullish, and has a non-trivial lower rejection wick.
- SHORT symmetric at resistance.

### 3. FVG mitigation
- Standard 3-bar FVG only, created strictly before the signal bar.
- Search only the most recent qualifying FVG in the prior 12 completed bars.
- Bullish FVG vote LONG when current bar mitigates into the gap and closes above its midpoint.
- Bearish FVG symmetric SHORT.
- No later post-result gap-width/body/session filter.

### 4. Fibonacci retracement
- Use the prior 12 completed bars, excluding the signal bar.
- A bullish impulse exists only when the prior-window swing low occurs before the swing high and total swing range >= 2 ATR; bearish impulse requires high before low.
- Frozen retracement zone = 50.0%-61.8% of that impulse.
- LONG/SHORT vote only when the signal bar trades into that zone and closes back in the impulse direction.

## Weekly causal router
For each timeframe separately:
1. ISO week begins Monday 00:00 UTC.
2. Scan completed bars in chronological order.
3. If at least 2 frozen theories vote the same direction on one completed bar, take the **first** such event of the week at the next bar open; ignore all later opportunities that week.
4. If no 2-of-4 confluence has occurred by the fixed Friday checkpoint:
   - H1 checkpoint signal bar = Friday 12:00 UTC completed bar; entry = Friday 13:00 UTC open.
   - H4 checkpoint signal bar = Friday 12:00-16:00 UTC completed H4 bar; entry = Friday 16:00 UTC open.
5. At fallback, use the majority of any structural votes on that checkpoint bar. If there are no votes or a tie, use frozen S/R location: close above prior-20 midpoint -> SHORT mean-reversion; close below/equal midpoint -> LONG mean-reversion.
6. Maximum one trade per ISO week in this first B8 study.

This fallback intentionally forces weekly coverage rather than hiding difficult weeks as NO TRADE.

## Execution
- Structural risk distance = 1.0 ATR(14), calculated causally before entry from completed data.
- Modeled round-trip fee = 0.15%.
- TP raw distance is set so modeled **net reward equals net loss**, i.e. net RR = 1:1 after fee.
- H1 maximum hold = 12 completed H1 bars / 12h.
- H4 maximum hold = 6 completed H4 bars / 24h.
- Same-bar TP+SL ambiguity = adverse-first / SL.
- TIME exit = final frozen hold-bar close.
- No trailing stop, breakeven, management, or rescue layer.

## Frozen variants
Only two variants are allowed:
- `CONF2_FORCED`: first >=2 agreeing theories; otherwise fixed Friday fallback. This is the primary weekly-coverage test.
- `CONF3_FORCED`: first >=3 agreeing theories; otherwise the same fixed Friday fallback. This tests whether stronger confluence helps without introducing new indicators.

No threshold grid, weekday tuning, session carve-out, alternative Fib levels, FVG widths, OR duration, ATR multiple, RR, or hold sweep is allowed after results.

## Required reporting
For H1 and H4, each variant and partition:
- complete weeks represented;
- selected trade count and weekly coverage;
- confluence vs fallback trade count;
- TP / SL / TIME;
- positive-return WR;
- decisive TP-vs-SL WR;
- expectancy and profit factor in net-return units;
- max losing streak;
- chronological blocks;
- exact losing weeks.

## Gates
`B8_ROBUST_WEEKLY_100=PASS` only if at least one timeframe/variant has all of:
- external complete-week coverage = 100%;
- reference-validation complete-week coverage = 100%;
- external selected N >= 20 and all-trade positive-return WR = 100%;
- validation selected N >= 20 and all-trade positive-return WR = 100%;
- positive expectancy and PF > 1 in both external and validation;
- zero losing weeks in both external and validation.

`B8_HIGH_PRECISION_WEEKLY=PASS` if the same coverage and N gates hold with external and validation WR >= 80%, positive expectancy/PF > 1 in both, and max losing streak <= 2 in both.

## Anti-rescue lock
If B8 fails, do not cherry-pick a weekday, remove fallback losing weeks, change Fib to 38.2/78.6, alter OR hours, add order blocks, widen/tighten ATR stop, change RR/hold, choose the best signal after seeing the week, or isolate H1/H4 sub-sessions from this same result. Any follow-up must be separately preregistered and materially different.

Live BBC untouched.