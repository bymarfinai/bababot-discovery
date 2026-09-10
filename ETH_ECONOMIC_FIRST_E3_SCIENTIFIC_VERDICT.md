# ETH Economic-First E3 — Scientific Verdict

**Status: `ETH_ECONOMIC_FIRST_E3_BOUNDARY_OPEN`.**

E3 tested whether the E2 drive-response family becomes materially cleaner when trades are conditioned on **causal pre-entry drive strength**, with no H/L/reference-range/breakout/retest/EMA/Fibonacci inputs.

## Result-bearing run
- Workflow run: `34457154404`
- Artifact: `10144007918`
- Vectorized implementation was scientifically equivalent to the preregistered E3 universe and gates; only repeated computation was cached/vectorized.
- ETHUSDT raw 5m coverage: **100%**.
- Development candidates: **17,280**.
- High-quality gate passers: **5**.
- High-quality + local-stability passers: **3**.

## Development-selected character
**20:30 UTC (03:30 WIB) / REVERSAL / lookback 15m / causal strength >=0.85 / hold 720m**

- Trades: **131**
- Net WR: **56.49%**
- Net PnL: **+$346.12**
- Expectancy: **+$2.6421/trade**
- PF: **1.695**
- Max DD: **$78.67**
- Max loss streak: **7**
- Max win streak: **9**
- Positive chronological blocks: **3/4**
- Supportive local neighbors: **3/6**

The selected cell passes the preregistered high-quality economic gate and local-stability gate.

## Other eligible Development cells
1. 11:30 UTC / REVERSAL / LB360 / strength>=0.85 / hold360: N139, WR56.83%, net +$245.64, exp +$1.77, PF1.593, DD$79.62, loss streak4, neighbors4/6.
2. 00:00 UTC / REVERSAL / LB360 / strength>=0.80 / hold60: N161, WR55.28%, net +$58.17, exp +$0.36, PF1.228, DD$56.24, loss streak6, neighbors3/6.

Two additional cells passed the raw high-quality gate but failed local stability.

A notable family-level observation is that **all five high-quality E3 cells were REVERSAL**, supporting the hypothesis that unusually strong ETH pre-entry drives can contain mean-reversion information at specific clocks.

## Boundary diagnosis
The selected winner touches **two preregistered outer sentinels**:
- lookback **15m** = minimum tested lookback;
- strength threshold **0.85** = maximum tested strength threshold.

Hold **720m** is interior because 960m was included as the upper sentinel. Clock is circular and therefore has no edge.

Accordingly, historical holdouts remain closed. No second-best substitution is allowed.

The immediate next experiment is a bounded E4 refinement around the selected clock/mode/hold that extends the lookback below 15m and the causal strength threshold above 0.85. E4 must remain economic-first and must not reopen H-based structure.

Research/shadow only. No live promotion or profit guarantee.
