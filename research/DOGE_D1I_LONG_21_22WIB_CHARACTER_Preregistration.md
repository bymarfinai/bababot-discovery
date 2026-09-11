# DOGE D1I — 21:00–22:00 WIB LONG Character Discovery Preregistration

## Purpose
Continue the mandatory DOGEUSDT pair-native 24-hour LONG character sweep by testing exactly one new clock habitat: **21:00–22:00 WIB**.

## Frozen scope
- Pair: **DOGEUSDT**
- Direction: **LONG only**
- Development only; **OOS remains closed**
- Clock anchors only: **21:00, 21:15, 21:30, 21:45 WIB** = **14:00, 14:15, 14:30, 14:45 UTC**
- Same frozen pair-agnostic causal grammar used in D1A–D1H
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

No high WR, PnL, PF, volatility narrative, or attractive near-miss may override a gate failure.

## Integrity lock
D1A–D1H results are comparison context only. Their winning or near-miss rules, lookbacks, holds, volatility states, range states, or payoff horizons **must not seed or restrict D1I ranking**. D1I must evaluate the complete frozen 3,240-candidate grid independently.

No gate relaxation, post-result rescue, OOS exposure, TP/SL tuning, SHORT mixing, or execution-stage optimization is allowed.

## D1 → D2 reset policy
D1I is **not** a restart. The current D1 temporal atlas must continue unchanged through **D1X** so the 24-hour map is complete.

If, after D1X, the D1 sweep still fails to reveal a sufficiently robust formal DOGE LONG character / coherent temporal cluster under the frozen grammar, the next scientific stage will be **DOGE D2 — Pair-Native Structure Discovery From Zero**. D2 will treat the current 90-rule grammar as a baseline/comparator rather than an assumed correct DOGE coordinate system, and will rediscover DOGE-native causal structure without importing SOL/ETH coordinates.
