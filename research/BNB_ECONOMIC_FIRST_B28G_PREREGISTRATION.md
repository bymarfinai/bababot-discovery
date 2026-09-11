# BNB Economic-First B28G Preregistration — 06:00–07:00 WIB

## Purpose
Continue the fixed-order, economic-first BNBUSDT LONG-only hour sweep into **06:00–07:00 WIB** without changing the frozen B28 methodology.

## Frozen scope
- Pair: **BNBUSDT**
- Direction: **LONG only**
- Development only; **OOS remains closed**
- Hour habitat: **06:00–07:00 WIB**
- Quarter-hour anchors: **06:00, 06:15, 06:30, 06:45 WIB**
- UTC anchors: **23:00, 23:15, 23:30, 23:45 UTC**
- UTC minute-of-day clocks: **1380, 1395, 1410, 1425**

## Frozen search space
Identical to B28A–B28F:
- causal character grammar: **90 rules**
- lookbacks: **15, 30, 60, 120, 240, 360 minutes**
- holds: **60, 120, 240, 360, 720, 960 minutes**
- total candidates: **3,240**
- same notional, fee model, feature construction, causal historical percentiles, ranking and gates as prior B28 hours

## Frozen economic/risk gates
No changes from B28A–B28F:
- per-anchor supportive gate: N>=40, WR>=52%, net>0, expectancy>0, PF>=1.05, DD<=125, max loss streak<=10
- hour anchor gate: >=3 evaluable anchors and >=3 supportive anchors
- pooled gate: N>=160, WR>=55%, net>0, expectancy>=0.50, PF>=1.20, DD<=125, max loss streak<=8
- era gate: each Development year N>=40, WR>=52%, net>0, expectancy>0, PF>=1.05, plus >=2 years WR>=55%
- ranking unchanged: min-year expectancy, anchor support, expectancy, WR, PF, DD, loss streak, hold, lookback, rule

## Integrity constraints
- No SHORT search.
- No TP/SL tuning.
- No weekday filters.
- No gate relaxation.
- No expanded grid.
- No post-result clock rescue.
- No post-result coordinate substitution.
- No OOS exposure.
- B28A–B28F winners are frozen historical observations only and receive **zero ranking preference**.
- In particular, `DRIVE_DOWN__STR_B60_80 / LB120 / hold720` from B28F is not privileged.
- B27 structural/H2/P10 information remains excluded from candidate ranking.

## Formal outcomes
- PASS: `BNB_ECONOMIC_FIRST_B28G_LONG_CHARACTER_FOUND`
- FAIL: `BNB_ECONOMIC_FIRST_B28G_NO_LONG_CHARACTER`

Regardless of PASS or FAIL, the next fixed-order habitat is **07:00–08:00 WIB** with the unchanged methodology.

Research/shadow only.