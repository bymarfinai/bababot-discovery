# Friday F6.24 — CONTEXT_REPAIR_FAILURE_65 Management

**Status: COMPLETE — single predeclared causal action test. Live BBC untouched.**

## Frozen rule
- first causal +0.5R milestone
- evaluate exactly +65m later
- F6.22 bearish persistence: final 4 completed 5m closes below EMA7 + final-2 taker mean < 0
- strictly pre-entry 2h entry position > 50% of local range
- zero EMA20 reclaims from first +0.5R hit to decision
- exit at actual decision open
- no timing / taker / range-position / EMA-distance sweep

## Baseline
Frozen four-layer: **+123.232**, WR **51.45%**, PF **1.680**, DD **28.699**.

## Funnel
- F6.22 raw signals **18**
- upper-half context **8**
- zero EMA20 reclaim **12**
- both context+repair conditions **6**
- active after chronology **6**

## Result
- actions **6** (D 3 / V 3)
- low givebacks caught **3**; high givebacks caught **2**; eventual winners acted **1**
- loss→positive **2**; winner→nonpositive **0**
- incremental **+15.097**; D/V **+7.611 / +7.486**
- managed PnL **+138.329**, WR **52.90%**, PF **1.827**, DD **24.259**
- screen **PASS**

## Guardrail
F6.24 is same-sample provisional because the state was motivated by F6.23 on the same history. Do not retune the 50% half-range split, EMA20-reclaim definition, flow window, or +65m timing on this sample. A PASS still requires independent OOS trigger evidence.
