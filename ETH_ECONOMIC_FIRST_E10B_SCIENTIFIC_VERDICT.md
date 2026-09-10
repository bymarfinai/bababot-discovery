# ETH Economic-First E10B — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E10B_NO_DEV_CANDIDATE**

Research/shadow only. No live promotion or profit guarantee.

## Frozen family
- ETHUSDT Binance Futures raw 5m
- MOMENTUM
- causal drive-strength B40_60
- exact-open entry and exact-open time exit
- no TP / no SL / no H/L / no breakout / no retest / no EMA / no Fibonacci
- $500 fixed notional
- $0.75 round-trip fee

## Fine grid
- clock UTC: 12:30, 12:45, 13:00, 13:15, 13:30
- equivalent WIB: 19:30, 19:45, 20:00, 20:15, 20:30
- lookback: 15, 20, 30, 45, 60m
- hold: 240, 300, 360, 420, 480m
- 125 Development candidates

## Result-bearing run
- workflow run ID: **34475016704**
- job ID: **102863595400**
- head SHA: **16ee9f218f2c11fb85682945dda1542aed1bcfcb**
- artifact ID: **10151111566**
- targeted workflow conclusion: **success**

## E9 seed reproduction
13:00 UTC (20:00 WIB) / LB30 / hold360 reproduced:
- N167
- WR57.49%
- net +$228.25
- expectancy +$1.37/trade
- PF1.432
- max DD $64.82
- max loss streak4
- 2022 WR54.90% / exp +$1.15
- 2023 WR57.14% / exp +$1.42
- 2024 WR60.38% / exp +$1.52

## Development fine refinement
Candidate-gate passers: **2**.
Candidate + preregistered local-stability passers: **0**.

The two gate passers were the same-clock/same-lookback hold variants:
1. **13:00 UTC / LB30 / hold360** — N167 / WR57.49% / net +$228.25 / exp +$1.37 / PF1.432 / DD $64.82 / neighbors 2/6.
2. **13:00 UTC / LB30 / hold300** — N167 / WR56.29% / net +$189.51 / exp +$1.13 / PF1.382 / DD $75.81 / annual WR56.86% / 52.38% / 60.38% / neighbors 2/6.

Nearby clock and lookback perturbations degraded materially. Examples:
- 12:45 UTC / LB30 / hold360: N162 / WR50.62% / exp +$0.21 / PF1.062; 2022 and 2023 were weak/negative economically.
- 13:15 UTC / LB45 / hold360: N160 / WR51.25% / exp +$1.02 / PF1.327, but aggregate WR and annual consistency failed the gate.
- 13:00 UTC / LB60 / hold360: N136 / WR55.15% / exp +$1.15 / PF1.365, but sample and 2023 economics failed.

The region therefore behaves as a coordinate-sensitive ridge rather than a stable clock/lookback/hold character plateau under the preregistered test.

## OOS handling
No Development candidate earned OOS exposure. External and Reference Validation remained closed for E10B. No gate relaxation, second-best substitution, or post-hoc rescue is permitted.

## Scientific interpretation
E9 successfully identified cross-era-positive coordinates, but E10A and E10B independently show that the two strongest E9 regions do not survive fine perturbation of their defining coordinates. This indicates that fixed clock + fixed lookback + fixed hold is still too coordinate-specific to serve as the durable ETH character grammar.

The next discovery should remain economic-first but move one level more invariant: seek a causal market-state or path-shape variable that explains when momentum/reversal works, with clock treated as context rather than the primary coordinate. Any new family must again require multi-era Development consistency before a single frozen candidate is exposed to OOS.
