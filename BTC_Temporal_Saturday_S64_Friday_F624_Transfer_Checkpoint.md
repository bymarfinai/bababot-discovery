# Saturday S6.4 — Exact Friday F6.24 Transfer

**Integrated transfer:** PASS
**Static-parent transfer:** PASS
**Research only; live BBC untouched. No Saturday retuning.**

## Exact transferred mechanism
- +0.5R milestone; Saturday frozen R=1.2%, therefore +0.5R=+0.6%
- decision +65m using Friday implementation timing
- final 4 completed 5m closes below EMA7
- final-2 taker mean < 0
- pre-entry 2h entry position >50%
- zero EMA20 reclaims from milestone to decision
- exit actual decision open

## Frozen Saturday parity
- parent **+87.200**, WR **46.76%**
- S5.7G champion **+111.240**
- S6.3 FIB5 + S5.7G **+119.738**, WR **54.68%**, PF **1.571**, DD **28.125**

## Transfer result on integrated baseline
- raw signals **1**, active after chronology **1**, preempted **0**
- actions D/V **0 / 1**
- parent winners/losses acted **0 / 1**
- loss→positive **0**, baseline positive→nonpositive **0**
- PnL **+119.738 -> +119.766**, incremental **+0.028**
- D/V incremental **+0.000 / +0.028**
- WR **54.68% -> 54.68%**, PF **1.571 -> 1.571**, DD **28.125 -> 28.125**
- action jackknife min remaining incremental **+0.000**

## Cross-context interpretation guardrail
This is a genuine transfer test because Friday F6.24 is ported without Saturday threshold/timing tuning. +0.5R is normalized to the frozen Saturday risk unit rather than copied as Friday absolute price distance. Do not retune based on this Saturday run.
