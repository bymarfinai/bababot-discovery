# B27BF — BTC 24H Adaptive Regime Router Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27BE remained frozen and supplied the complete rolling 4H block/range/regime universe. No Asia/London/New-York session label was used for entry eligibility.

**Router v1:** BULL -> LONG B27W/B27AA/B27AC lineage; BEAR -> SHORT B27AY/B27BC lineage; SIDEWAYS -> FLAT. UTC 4H boundaries refresh state/range but are not preferred trading windows.

## Router economics

| Partition | N | WR | PF | Exp/trade $ | Total $ | E20 act | Trades/week |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 197 | 49.7% | 0.853 | -0.247 | -48.616 | 43.7% | 1.89 |
| development | 269 | 50.2% | 0.969 | -0.038 | -10.169 | 47.6% | 1.72 |
| reference_validation | 114 | 51.8% | 1.025 | 0.022 | 2.535 | 52.6% | 1.39 |
| POOLED_MAJOR | 580 | 50.3% | 0.926 | -0.097 | -56.249 | 47.2% | 1.69 |

## Router components — pooled major

| Component | Regime | N | WR | PF | Exp/trade $ | Total $ | E20 act |
|---|---|---:|---:|---:|---:|---:|---:|
| LONG | BULL | 488 | 52.3% | 0.960 | -0.052 | -25.359 | 49.6% |
| SHORT | BEAR | 92 | 40.2% | 0.750 | -0.336 | -30.890 | 34.8% |

## Counterfactual playbook attribution — pooled major

| Side / actual regime | N | WR | PF | Exp/trade $ | Total $ | E20 act |
|---|---:|---:|---:|---:|---:|---:|
| LONG / BULL | 488 | 52.3% | 0.960 | -0.052 | -25.359 | 49.6% |
| LONG / BEAR | 350 | 48.6% | 0.719 | -0.369 | -129.094 | 44.9% |
| LONG / SIDEWAYS | 169 | 48.5% | 0.813 | -0.253 | -42.693 | 41.4% |
| SHORT / BULL | 105 | 37.1% | 0.391 | -0.789 | -82.864 | 34.3% |
| SHORT / BEAR | 92 | 40.2% | 0.750 | -0.336 | -30.890 | 34.8% |
| SHORT / SIDEWAYS | 57 | 47.4% | 1.349 | 0.421 | 24.010 | 45.6% |

## Structural opportunity counts — pooled major

- BULL observation blocks: **6,690**; routed LONG executions: **488**.
- BEAR observation blocks: **5,312**; routed SHORT executions: **92**.
- SIDEWAYS observation blocks: **2,407**; routed executions by design: **0**.

## Frozen verdict

**B27BF_ADAPTIVE_ROUTER_NOT_SUPPORTED.**

Support required >=30 routed trades in each major partition, nonnegative expectancy and PF>=1.0 in each, plus pooled expectancy>0, PF>=1.20, and positive total. No thresholds or router mapping were changed after seeing results.

Research only; live BBC unchanged.
