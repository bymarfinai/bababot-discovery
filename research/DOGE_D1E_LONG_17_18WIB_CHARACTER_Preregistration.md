# DOGE D1E — 17:00–18:00 WIB LONG Character Discovery Preregistration

## Purpose
Continue the DOGE pair-native 24-hour LONG character sweep for exactly one new clock habitat: **17:00–18:00 WIB**.

D1A–D1D results are comparison context only. They MUST NOT seed D1E rule, lookback, hold, ranking, or gate selection.

## Frozen scope
- Pair: `DOGEUSDT`
- Direction: **LONG only**
- Development only; **OOS remains closed**
- Habitat anchors: **10:00, 10:15, 10:30, 10:45 UTC** = **17:00, 17:15, 17:30, 17:45 WIB**
- Same frozen pair-agnostic causal character grammar used by D1A–D1D
- Character rules: **90**
- Lookbacks: **15, 30, 60, 120, 240, 360 minutes**
- Payoff-horizon probes: **60, 120, 240, 360, 720, 960 minutes**
- Total candidates: **90 × 6 × 6 = 3,240**
- No TP/SL tuning
- No SHORT search
- No sequential execution selector
- No post-result rescue or gate relaxation

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
For each Development era 2022/2023/2024:
- trades >= 40
- WR >= 52%
- net > 0
- expectancy > 0
- PF >= 1.05

Additionally at least two eras must have WR >= 55%.

### Formal candidate gate
`candidate_gate = anchor_gate AND pooled_gate AND era_gate`

No metric may override a failed formal gate.

## Data integrity
Raw DOGEUSDT 5m coverage must be >= 99.5%. All features and percentile states remain causal/no-look-ahead. The hold is a payoff-horizon probe only, not a live exit prescription.

## Stopping rule
Persist the formal result exactly as generated. If no full candidate passes, report the strongest deterministic near-miss descriptively only and proceed to D1F without repairing D1E.
