# BNB Economic-First B28F Preregistration — 05:00–06:00 WIB LONG Character

## Scope
- Pair: BNBUSDT
- Direction: LONG only
- Habitat: 05:00–06:00 WIB
- Anchors: 05:00, 05:15, 05:30, 05:45 WIB = 22:00, 22:15, 22:30, 22:45 UTC
- Development only; OOS remains closed
- Same neutral B28 90-rule causal grammar, lookbacks, holds, fees, ranking and gates as B28A–B28E
- Total candidates: 90 × 6 lookbacks × 6 holds = 3,240

## Frozen parameters
Lookbacks: 15, 30, 60, 120, 240, 360 minutes.
Holds: 60, 120, 240, 360, 720, 960 minutes.
Notional: $500. Fee: $0.75. No TP/SL tuning.
Development eras: 2022, 2023, 2024.

## Frozen gates
Per-anchor supportive gate: N>=40, WR>=52%, net>0, exp>0, PF>=1.05, DD<=125, max loss streak<=10.
Hour anchor gate: >=3 evaluable anchors and >=3 supportive.
Pooled gate: N>=160, WR>=55%, net>0, exp>=0.50, PF>=1.20, DD<=125, max loss streak<=8.
Era gate: each year N>=40, WR>=52%, net>0, exp>0, PF>=1.05, plus >=2 years WR>=55%.
Ranking: min-year expectancy, anchor support, expectancy, WR, PF, DD, loss streak, hold, lookback, rule.

## Integrity constraints
B28D/B28E both selected `RV_HIGH__RANGE_MID / LB120 / hold720`, but B28F gives that coordinate no preference. It must compete neutrally with all other candidates.
B27 structural coordinates remain excluded from candidate selection and ranking.
No SHORT search, no TP/SL tuning, no weekday filter, no gate relaxation, no expanded grid, no post-result clock rescue, no OOS exposure, and no substitution of attractive failed rows.

PASS status: `BNB_ECONOMIC_FIRST_B28F_LONG_CHARACTER_FOUND`.
FAIL status: `BNB_ECONOMIC_FIRST_B28F_NO_LONG_CHARACTER`.
If FAIL, persist the failure and continue fixed order to 06:00–07:00 WIB without rescue.
