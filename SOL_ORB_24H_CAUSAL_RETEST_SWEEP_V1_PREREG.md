# SOL ORB 24H Causal Retest Sweep v1 — Preregistration

## Goal

Sweep the frozen 15-minute ORB LONG structure across all 24 UTC clock hours to determine where SOLUSDT has a repeatable, economically useful breakout-retest character.

This experiment is **Development-only**. Reference/OOS remains closed.

## Important causal correction

The earlier E2 entry-coordinate diagnostic compared ORB-high retest entry inside the subset that later completed BREAK->RETEST->ACCEPT. That is useful for structural anatomy, but a live bot entering on the retest cannot know yet whether later acceptance will occur.

Therefore this 24h sweep uses a causal E2 population:

- E2 enters on **every valid retest that is knowable at the retest**, whether or not later acceptance occurs.
- Acceptance is recorded only as a later diagnostic; it is not required for E2 eligibility.
- This prevents future-acceptance selection bias.

## Frozen session grammar

For every UTC hour H00..H23 and every Development weekday:

1. Session begins exactly at `HH:00` UTC.
2. ORB = first 3 complete 5m bars (`HH:00`, `HH:05`, `HH:10`), therefore complete at `HH:15`.
3. `BREAK_HIGH` = first 5m candle starting from `HH:15` through `HH:55` whose **close > ORB High**.
4. `RETEST_HIGH` = within the next 6 complete 5m bars (30m) after the breakout, a bar whose:
   - low <= ORB High, and
   - close >= ORB midpoint.
5. Causal E2 fill = ORB High when the retest bar trades through that level. For forward-return clocks, measurement begins after the retest bar closes (`retest timestamp + 5m`) to avoid using unknown intrabar ordering.
6. Later `ACCEPT_HIGH` = first later 5m close > ORB High within the same 30m post-breakout observation window. This is diagnostic only.

## Boundary / right-censor correction

The anchor hour determines ORB and breakout habitat only. The preregistered 30m post-breakout retest/acceptance observation window is allowed to cross the next UTC hour. This fixes the hour-boundary truncation present in the first H23 prevalence runner and does not change rules based on outcomes.

## Economics

No TP/SL optimization. Fixed time exits only:

- +15m
- +30m
- +60m
- +120m

Economic assumptions:

- reference notional: `$500/trade`
- round-trip cost: `0.15%`
- LONG only
- one causal E2 event per session/hour maximum

Report per hour:

- Development sessions
- breakout count / rate
- causal retest count / rate
- later acceptance rate among causal retests
- for each fixed exit: N, net WR, net PnL, expectancy/trade, PF, max DD, max loss streak
- 2022/2023/2024 net PnL and PF diagnostics

## No tuning rules

- No VWAP, EMA, Fibonacci, volume, regime, or retest-quality filter.
- No ORB-duration sweep.
- No threshold sweep.
- No hour dropping after seeing results.
- No OOS/reference opening.
- The existing H23 findings are context only; all 24 hours are evaluated under the exact same grammar.

## Interpretation

The sweep maps **where** the frozen ORB retest behavior is economically supportive. It does not by itself create a production rule. Any hour selection or quality filter derived from this map requires a separate preregistered confirmation step.