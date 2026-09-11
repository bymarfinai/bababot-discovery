# BNB Economic-First B28D Preregistration — 03:00–04:00 WIB

## Purpose
Continue the clean BNB hour-by-hour economic-first LONG discovery. B28D changes only the time habitat from B28C; all scientific rules, candidate grammar, economic/risk gates, ranking, and OOS restrictions remain frozen.

## Frozen scope
- Pair: BNBUSDT
- Direction: LONG only
- Development only
- OOS closed
- Habitat: 03:00–04:00 WIB
- Quarter-hour anchors: 03:00, 03:15, 03:30, 03:45 WIB = 20:00, 20:15, 20:30, 20:45 UTC
- Notional: $500
- Fee model: identical to B28A–B28C
- No TP / no SL; causal fixed-horizon exits

## Candidate grid
Use the exact same neutral 90-rule causal grammar as B28A–B28C, with no prior-hour winner preference.
- Lookbacks: 15, 30, 60, 120, 240, 360 minutes
- Holds: 60, 120, 240, 360, 720, 960 minutes
- Total candidates: 90 × 6 × 6 = 3,240

## Frozen gates
Identical to B28A–B28C:
- Anchor supportive: N>=40, WR>=52%, net>0, expectancy>0, PF>=1.05, DD<=125, max loss streak<=10
- Hour anchor gate: >=3 evaluable anchors and >=3 supportive anchors
- Pooled: N>=160, WR>=55%, net>0, expectancy>=0.50, PF>=1.20, DD<=125, max loss streak<=8
- Era: each year N>=40, WR>=52%, net>0, expectancy>0, PF>=1.05; at least 2 years WR>=55%
- Ranking: min-year expectancy, supportive anchors, expectancy, WR, PF, DD, loss streak, hold, lookback, rule

## Integrity locks
- No SHORT search.
- No TP/SL tuning.
- No weekday filtering.
- No gate relaxation.
- No expanded grid.
- No clock rescue after result.
- No B27 H2/leave/P10 structural objective in selection.
- B28A/B28B/B28C winners are descriptive only and receive zero ranking preference.
- Attractive near-misses remain failures.
- OOS remains unopened.

## Stop / continuation rule
If no B28D candidate passes all frozen gates, persist the failure and move to 04:00–05:00 WIB. Do not rescue the hour.
