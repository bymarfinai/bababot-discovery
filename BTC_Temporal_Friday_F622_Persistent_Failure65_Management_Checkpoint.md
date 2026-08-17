# Friday F6.22 — PERSISTENT_FAILURE_65 Management

**Status: COMPLETE — single predeclared causal action test. Live BBC untouched.**

## Frozen rule
- first causal +0.5R milestone
- evaluate exactly +65m later
- final four completed 5m closes are all below EMA7
- final two completed 5m taker imbalance mean < 0
- exit at actual decision-time open
- no EMA20/Fib/new timing sweep

## Baseline
Frozen four-layer: **+123.232**, WR **51.45%**, PF **1.680**, DD **28.699**.

## Result
- actions **14** (D 9 / V 5)
- low givebacks caught **5**; high givebacks caught **2**; eventual winners acted **7**
- loss→positive **2**; winner→nonpositive **5**
- incremental **-5.089**; D/V **-5.890 / +0.801**
- managed PnL **+118.142**, WR **49.28%**, PF **1.699**, DD **27.143**
- screen **FAIL**

## Guardrail
F6.22 is motivated by same-sample trajectory forensic. A PASS remains provisional until independent OOS trigger evidence accumulates. Do not retune 4 bars, 2-bar flow, or 65m timing on this sample.
