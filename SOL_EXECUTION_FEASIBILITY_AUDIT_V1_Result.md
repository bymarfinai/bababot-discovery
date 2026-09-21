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
- Regular fees + historical funding, zero slippage: **0.063R**, PF **1.153**
- Funding crossed by **138/302** trades; cumulative funding cost/credit: **0.233R**.

## Slippage stress — regular fees + funding

| Slippage per taker leg | ALL mean R | PF | Cum R | Score3 mean | Score4 LONG mean |
|---:|---:|---:|---:|---:|---:|
| 0.0 bps | 0.063 | 1.153 | 18.914 | 0.022 | 0.459 |
| 0.5 bps | 0.056 | 1.137 | 17.026 | 0.016 | 0.455 |
| 1.0 bps | 0.050 | 1.121 | 15.138 | 0.009 | 0.451 |
| 2.0 bps | 0.038 | 1.089 | 11.362 | -0.004 | 0.442 |
| 3.0 bps | 0.025 | 1.059 | 7.586 | -0.017 | 0.434 |
| 5.0 bps | 0.000 | 1.000 | 0.034 | -0.043 | 0.418 |

## Primary scenario — regular fees + 0.5 bps/taker-leg slippage + funding

| Component | N | Mean net R | PF | Cum R | Win rate | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| ALL | 302 | 0.056 | 1.137 | 17.026 | 56.29% | 8.677 |
| BUY_SIDE | 131 | 0.068 | 1.181 | 8.861 | 58.02% | 5.966 |
| SELL_SIDE | 171 | 0.048 | 1.108 | 8.165 | 54.97% | 7.334 |
| SCORE3_ALL | 274 | 0.016 | 1.038 | 4.291 | 55.84% | 9.444 |
| SCORE3_BUY_SIDE_SHORT | 131 | 0.068 | 1.181 | 8.861 | 58.02% | 5.966 |
| SCORE3_SELL_SIDE_LONG | 143 | -0.032 | 0.929 | -4.570 | 53.85% | 14.979 |
| SCORE4_SELL_SIDE_LONG | 28 | 0.455 | 2.087 | 12.735 | 60.71% | 2.166 |

## Break-even execution budget

| Component | Mean=0 extra slippage / taker leg | Max slippage for PF>=1.10 |
|---|---:|---:|
| ALL | 5.009 bps | 1.652 bps |
| BUY_SIDE | 6.095 bps | 2.902 bps |
| SELL_SIDE | 4.225 bps | 0.756 bps |
| SCORE3_ALL | 1.711 bps | 0.000 bps |
| SCORE3_BUY_SIDE_SHORT | 6.095 bps | 2.902 bps |
| SCORE3_SELL_SIDE_LONG | 0.000 bps | 0.000 bps |
| SCORE4_SELL_SIDE_LONG | 50.000 bps | 48.215 bps |

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
