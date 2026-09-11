# DOGE D1F — 18:00–19:00 WIB LONG Character Discovery Preregistration

## Purpose
Continue the mandatory DOGEUSDT pair-native 24-hour LONG character sweep by testing exactly one new clock habitat: **18:00–19:00 WIB**.

## Frozen scope
- Pair: **DOGEUSDT**
- Direction: **LONG only**
- Development only; **OOS remains closed**
- Clock anchors only: **18:00, 18:15, 18:30, 18:45 WIB** = **11:00, 11:15, 11:30, 11:45 UTC**
- Same frozen pair-agnostic causal grammar used in D1A–D1E
- Character rules: **90**
- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**
- Payoff-horizon probes: **60, 120, 240, 360, 720, 960 minutes**
- Total grid: **90 × 6 × 6 = 3,240 candidates**
- No TP/SL tuning
- No SHORT search
- No one-position execution selector

## Frozen gates
### Per-anchor supportive
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05
- DD <= $125
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
- DD <= $125
- max loss streak <= 8

### Era gate
For each Development era 2022, 2023, 2024:
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05

Additionally, at least **2 eras must have WR >= 55%**.

Formal character definition remains:

`candidate_gate = anchor_gate AND pooled_gate AND era_gate`

No high WR, PnL, PF, or attractive narrative may override a gate failure.

## Integrity lock
D1A–D1E results are comparison context only. Their winning or near-miss rules, lookbacks, holds, volatility states, range states, or payoff horizons **must not seed or restrict D1F ranking**. D1F must evaluate the complete frozen 3,240-candidate grid independently.

No gate relaxation, post-result rescue, OOS exposure, TP/SL tuning, SHORT mixing, or execution-stage optimization is allowed.
