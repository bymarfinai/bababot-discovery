# BTC Weekly W1 VAH Acceptance-Retest B16 — Preregistration

## Purpose
Test whether the only value-area breakout family with positive performance across development, external, and reference-validation in B15 — **W1 VAH break LONG** — improves when entry is delayed until the prior completed week's VAH is accepted above and then successfully retested as support.

This is a causal executable strategy test. It is not an oracle feasibility study.

## Data and partitions
- Instrument: Binance USD-M BTCUSDT perpetual.
- Source data: official Binance Futures 15m archives, resampled to H1 execution bars.
- W1 value-area levels use the exact frozen B13/B15 volume-profile definition: 24 equal-width bins using 15m typical price and base volume; contiguous 70% value area around POC.
- A W1 VAH becomes available only after that source week has fully completed. Therefore the active W1 VAH during a week is from a previously completed week.
- External: 2020-01-01 to 2022-01-01.
- Development: 2022-01-01 to 2025-01-01.
- Reference validation: 2025-01-01 to 2026-07-30.
- August 2026 is diagnostic only.

## Frozen structural sequence
All timestamps refer to completed H1 bars. Entry is always the next H1 open after the retest-confirmation bar.

1. **Breakout**
   - Active W1 VAH must already exist before the H1 breakout bar begins.
   - Breakout bar must open at or below VAH and close strictly above VAH.
   - Only the first qualifying VAH breakout in the ISO week is considered.

2. **Acceptance**
   Four preregistered variants are tested:
   - `A1_HOLD`: at least **1 additional consecutive completed H1 close** above VAH after the breakout.
   - `A1_BODY`: same as A1_HOLD.
   - `A2_HOLD`: at least **2 additional consecutive completed H1 closes** above VAH after the breakout.
   - `A2_BODY`: same as A2_HOLD.
   Acceptance must occur before any H1 close back below VAH. If a close below VAH occurs before the required acceptance count, that breakout is invalid for the variant.

3. **First retest after acceptance**
   - Starting only after the acceptance requirement is completed, the first H1 bar whose low is at or below VAH is the retest bar.
   - The retest must occur while the same W1 VAH instance is active and no later than Saturday 12:00 UTC of that ISO week.
   - Retest must **hold**: completed H1 close is at or above VAH.
   - `BODY` variants additionally require close > open on the retest bar.
   - If the first retest closes below VAH, the setup is invalid. No later retest rescue is allowed for that breakout/variant.

4. **Entry**
   - LONG at the next H1 open after the valid retest-confirmation bar.
   - Maximum one trade per ISO week per rule.
   - No forced fallback trade.

## Execution
- Fee/cost: 0.15% round-trip.
- Target: net +1.00%, implemented as +1.15% gross favorable barrier for LONG.
- Stop: net -1.00%, implemented as -0.85% gross adverse barrier for LONG.
- Same-bar TP+SL ambiguity: adverse-first.
- Exit at TP, SL, or final completed H1 bar before end of same ISO week.

## Development selection
The four rules are ranked using development only, in this order:
1. Highest weekly coverage.
2. Highest TP win rate.
3. Highest Wilson lower bound.
4. Highest profit factor.
5. Deterministic rule name tie-break.

The top development rule becomes `PRIMARY_RULE` and is frozen before external/reference-validation reporting.

## Baseline comparison
Report the B15 direct `W1|VAH_BREAK_LONG` baseline alongside B16 where possible. B16 succeeds conceptually only if delaying for acceptance/retest materially improves precision without relying on OOS tuning.

## Gates
`B16_ROBUST_WEEKLY_100` requires on BOTH external and reference-validation:
- 100% weekly coverage,
- 100% TP win rate,
- zero losing weeks,
- positive expectancy,
- PF > 1,
- all four chronological blocks positive.

`B16_HIGH_PRECISION` requires on BOTH external and reference-validation:
- WR >= 80%,
- positive expectancy,
- PF > 1,
- max losing streak <= 2,
- at least 3/4 chronological blocks positive.
Coverage is reported separately; no fallback is allowed to manufacture coverage.

## Anti-hindsight rules
- No OOS retuning.
- No later-retest rescue after a failed first retest.
- No using W1 levels before the source week completes.
- No live BBC changes in this experiment.
