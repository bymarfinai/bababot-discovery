# SOL Execution Feasibility Audit V1 — Result

- Frozen 302-trade final universe; no strategy rule changed.
- Binance regular-user commission model: maker **2.0 bps**, taker **5.0 bps** per leg.
- Score 3: taker entry + taker exit.
- Score-4 LONG: maker GAP25 entry + taker exit.
- Current SOLUSDT half-spread calibration: **0.447 bps**.
- Historical SOLUSDT funding is applied trade-by-trade.

## Actual maker/taker mix

- Maker entries: **28**
- Taker entries: **274**
- Taker exits: **302**
- Total maker legs: **28**
- Total taker legs: **576**

## Cost decomposition — ALL

- Gross mean R before execution costs: **0.127R**
- Regular fee only, no funding/slippage: **0.063R**, PF **1.155**
- BNB-discount fee only: **0.070R**, PF **1.172**
- Regular fees + historical funding, zero slippage: **0.063R**, PF **1.155**
- Funding crossed by **0/302** trades; cumulative funding cost/credit: **0.000R**.

## Slippage stress — regular fees + funding

| Slippage per taker leg | ALL mean R | PF | Cum R | Score3 mean | Score4 LONG mean |
|---:|---:|---:|---:|---:|---:|
| 0.0 bps | 0.063 | 1.155 | 19.147 | 0.023 | 0.457 |
| 0.5 bps | 0.057 | 1.139 | 17.259 | 0.017 | 0.453 |
| 1.0 bps | 0.051 | 1.123 | 15.371 | 0.010 | 0.449 |
| 2.0 bps | 0.038 | 1.091 | 11.595 | -0.003 | 0.441 |
| 3.0 bps | 0.026 | 1.061 | 7.819 | -0.016 | 0.432 |
| 5.0 bps | 0.001 | 1.002 | 0.267 | -0.042 | 0.416 |

## Primary scenario — regular fees + 0.5 bps/taker-leg slippage + funding

| Component | N | Mean net R | PF | Cum R | Win rate | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 302 | 0.057 | 1.139 | 17.259 | 56.29% | 8.695 |
| BUY_SIDE | 131 | 0.066 | 1.176 | 8.628 | 58.02% | 5.982 |
| SELL_SIDE | 171 | 0.050 | 1.114 | 8.632 | 54.97% | 7.240 |
| SCORE3_ALL | 274 | 0.017 | 1.041 | 4.576 | 55.84% | 9.441 |
| SCORE3_BUY_SIDE_SHORT | 131 | 0.066 | 1.176 | 8.628 | 58.02% | 5.982 |
| SCORE3_SELL_SIDE_LONG | 143 | -0.028 | 0.936 | -4.052 | 53.85% | 14.630 |
| SCORE4_SELL_SIDE_LONG | 28 | 0.453 | 2.078 | 12.683 | 60.71% | 2.193 |

## Break-even execution budget

| Component | Mean=0 extra slippage / taker leg | Max slippage for PF>=1.10 |
|---|---:|---:|
| ALL | 5.071 bps | 1.718 bps |
| BUY_SIDE | 5.947 bps | 2.756 bps |
| SELL_SIDE | 4.438 bps | 0.974 bps |
| SCORE3_ALL | 1.791 bps | 0.000 bps |
| SCORE3_BUY_SIDE_SHORT | 5.947 bps | 2.756 bps |
| SCORE3_SELL_SIDE_LONG | 0.000 bps | 0.000 bps |
| SCORE4_SELL_SIDE_LONG | 50.000 bps | 47.989 bps |

## Frozen gate audit

- PASS — all_mean_net_r_gt_0
- PASS — all_pf_ge_1_10
- PASS — all_cum_net_r_gt_0
- PASS — score3_mean_net_r_gt_0
- FAIL — score3_pf_ge_1_05
- PASS — score4_long_mean_net_r_gt_0
- PASS — score4_long_pf_ge_1_20
- PASS — buy_side_mean_net_r_gt_0
- PASS — sell_side_mean_net_r_gt_0
- PASS — all_breakeven_slippage_ge_1bps_per_taker_leg
- PASS — current_half_spread_below_breakeven_budget

**VERDICT: SOL_EXECUTION_NOT_FEASIBLE_UNDER_BASELINE_BINANCE_ASSUMPTIONS**

Passed **10/11** frozen execution-feasibility gates.

This is an execution-cost feasibility audit, not proof of live fills.
