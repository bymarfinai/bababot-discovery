# ETH E13D — Winner-Hour Sequential Selection Preregistration

## Purpose
Determine whether a static subset of the four formal E12 LONG winner-hours improves the real one-position sequential portfolio relative to E13C, without changing any E12 character, lookback, hold, fee, direction, or entry semantics.

Development only. OOS CLOSED.

## Frozen parent baseline
E13C FORMAL_PASS_ONLY sequential:
- N 476
- WR 55.25%
- net +$622.52
- expectancy +$1.31/trade
- PF 1.351
- max DD $131.02
- max loss streak 6
- 2022/2023/2024 all positive; at least two years WR>=55%

Frozen E12 winner coordinates:
- K / 23–00 WIB: DRIVE_UP__STR_B60_80, LB60, H720
- L / 00–01 WIB: EFF_LOW__RANGE_HIGH, LB30, H720
- M / 01–02 WIB: EFF_HIGH__RV_LOW, LB240, H960
- O / 03–04 WIB: RV_HIGH__RANGE_MID, LB360, H240

Economics remain NOTIONAL=$500, FEE=$0.75.

## Candidate universe — frozen
Evaluate all 15 non-empty static subsets of {K,L,M,O}:
K; L; M; O; K+L; K+M; K+O; L+M; L+O; M+O; K+L+M; K+L+O; K+M+O; L+M+O; K+L+M+O.

No candidate may be added/removed after results.

## Sequential semantics
For each subset:
1. Build exactly the frozen E12 opportunities belonging to its enabled winner-hours.
2. Sort causally by entry timestamp.
3. If flat at a valid signal, execute at frozen E12 entry timestamp/price.
4. Hold exactly for that hour's frozen native E12 hold.
5. Ignore every valid signal while position is open.
6. Re-arm only at/after frozen exit timestamp.
7. No TP, SL, profit-floor, early exit, re-entry, or future-aware waiting.

E13D changes only which formal winner-hours are allowed to compete for the single position slot.

## Mandatory metrics
For every subset persist:
- raw opportunities
- executed N; skipped-busy count/rate
- WR
- net PnL
- expectancy/trade
- PF
- max DD
- max loss streak; max win streak
- 2022/2023/2024 N/WR/net/expectancy/PF
- minimum yearly expectancy
- number of years WR>=55%
- executed contribution by source hour

## ROBUST gate
A candidate is ROBUST only if all are true.

Pooled:
- N >= 160
- WR >=55%
- net >0
- expectancy >=$0.50/trade
- PF >=1.20
- max DD <= E13C baseline $131.02
- max loss streak <= E13C baseline 6

Era, for each 2022/2023/2024:
- N >=40
- WR >=52%
- net >0
- expectancy >0
- PF >=1.05

And at least 2/3 years WR>=55%.

## Strict baseline Pareto test
Mark STRICT_PARETO_IMPROVER only if ROBUST and:
- WR >=55.25%
- net >=+$622.52
- expectancy >=+$1.31
- PF >=1.351
- DD <=$131.02
- max loss streak <=6
and at least one of WR/net/expectancy/PF/DD/loss-streak improves beyond rounding tolerance.

A smaller N is not itself an improvement; robustness minimums still apply.

## Ranking — frozen
Among ROBUST candidates rank by:
1. minimum yearly expectancy descending
2. years WR>=55 descending
3. expectancy descending
4. PF descending
5. WR descending
6. max DD ascending
7. max loss streak ascending
8. net PnL descending
9. N descending
10. fewer enabled hours ascending
11. lexical subset name

The highest headline PnL or WR alone is not the winner.

## Interpretation
- No gate relaxation after results.
- If no subset is ROBUST, E13C remains the reference baseline.
- ROBUST but not strict Pareto = trade-off candidate, not unqualified improvement.
- E13D does not authorize live deployment and does not open OOS.
