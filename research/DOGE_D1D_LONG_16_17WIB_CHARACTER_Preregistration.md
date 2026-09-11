# DOGE D1D — 16:00–17:00 WIB LONG Pair-Native Character Discovery Preregistration

## Purpose
Continue the DOGEUSDT pair-native LONG character sweep into the next contiguous one-hour habitat. This experiment changes **only the clock habitat** from D1C. D1A–D1C results are descriptive context only and may not seed candidate selection or alter any threshold.

## Frozen scope
- Symbol: **DOGEUSDT** Binance Futures raw 5m
- Direction: **LONG only**
- Habitat: **16:00–17:00 WIB** = **09:00–10:00 UTC**
- Fixed anchors: **09:00, 09:15, 09:30, 09:45 UTC** (16:00, 16:15, 16:30, 16:45 WIB)
- Entry: exact 5m open at the anchor
- Exit for character probe: exact 5m open after the frozen hold horizon
- Development only; **OOS closed**
- Required raw 5m coverage: **>=99.5%**
- Fixed notional: **$500**
- Frozen round-trip fee: **$0.75**
- No TP / no SL / no post-entry filter
- No SHORT
- No one-position selector

## Frozen causal grammar
Use the same pair-agnostic causal 90-rule grammar as D1A–D1C:
- ALL
- DRIVE_UP / DRIVE_DOWN
- causal drive-strength percentile bands STR_B0_20, STR_B20_40, STR_B40_60, STR_B60_80, STR_B80_100
- EFF LOW/MID/HIGH
- RV LOW/MID/HIGH
- RANGE LOW/MID/HIGH
- EXT LOW/MID/HIGH
- preregistered interactions and baseline exactly as encoded in the frozen engine

Percentiles remain causal and must use prior information only. Efficiency remains absolute path efficiency, not directional momentum.

## Frozen search grid
- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**
- Payoff-horizon holds: **60, 120, 240, 360, 720, 960 minutes**
- Rules: **90**
- Total candidates: **90 × 6 × 6 = 3,240**

Hold is a payoff-horizon character probe only, not a final live exit design.

## Frozen gates
### Per-anchor supportive gate
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- max DD <= $125
- max loss streak <= 10

### Hour anchor gate
- evaluable anchors >= 3
- supportive anchors >= 3

### Pooled gate
- trades >= 160
- WR >= 55%
- net > 0
- expectancy >= +$0.50/trade
- PF >= 1.20
- max DD <= $125
- max loss streak <= 8

### Cross-era Development gate
Each 2022 / 2023 / 2024:
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05

Additionally at least **2 eras must have WR >=55%**.

Formal candidate gate = **anchor gate AND pooled gate AND era gate**.

## Ranking
Among formal passers only, preserve the frozen deterministic ranking: minimum-era expectancy, supportive anchors, pooled expectancy, WR, PF, lower DD, lower loss streak, lower hold, lower lookback, lexical rule.

If no formal passer exists, report the strongest preregistered near-miss descriptively only. A near-miss must not be retroactively promoted.

## Integrity / stop rules
- no gate relaxation
- no hand-picked rescue after seeing results
- no OOS exposure
- no TP/SL tuning
- no SHORT mixing
- no selector/execution optimization
- no D1A/D1B/D1C coordinate seeding
- do not stop the 24-hour sweep after a PASS

Allowed status:
- `DOGE_D1D_NO_LONG_CHARACTER`
- `DOGE_D1D_LONG_CHARACTER_FOUND`

The next hour after D1D, regardless of PASS/FAIL, is D1E **17:00–18:00 WIB** using the same frozen engine and only the next four anchors.