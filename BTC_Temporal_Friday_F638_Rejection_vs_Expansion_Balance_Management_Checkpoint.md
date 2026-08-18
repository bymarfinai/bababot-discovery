# Friday F6.38 — Rejection-vs-Expansion Balance Management

**Diagnostic screen: PASS**
**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**

## Exact architecture
Start from F6.34. In the no-flow-divergence +20 branch, admit to the existing +35 watcher iff the immediate pre-entry upper-wick ratio is greater than body-ratio expansion versus the median of the prior 3 completed 5m bars. Otherwise keep the actual +20m cut. +35 confirmation is unchanged.

## Routing
- no-divergence branch **6** = 1 winner / 5 losers
- balance signals **1** = 1 winner / 0 losers; non-signals cut20 **5**
- balance +35 HOLD W/L **1 / 0**; CUT35 W/L **0 / 0**; frozen before35 **0**

## Economics
- frozen **+138.329** → F6.34 **+155.181** → F6.38 **+157.201**
- incremental vs frozen **+18.872**; vs F6.34 **+2.020**
- D/V incremental vs frozen **+9.936 / +8.937**; delta vs F6.34 **+2.020 / +0.000**
- WR **52.90% → 52.90%**; PF **1.827 → 2.059**; DD **24.259 → 17.627**
- acted parent winners preserved positive **3/3**; baseline positive→nonpositive **0**
- balance winner gain vs F6.34 **+2.020**; balance loser cost vs F6.34 **+0.000**

## No-divergence detail
- `2024-01-19` discovery: parent +0.646; upper 0.1571; body-exp +0.1128; margin +0.0443; gate **True** → CONFIRM35_HOLD; ΔF6.34 +2.020
- `2024-09-20` discovery: parent -4.250; upper 0.1171; body-exp +0.2356; margin -0.1185; gate **False** → CUT20; ΔF6.34 +0.000
- `2025-05-09` discovery: parent -4.250; upper 0.0367; body-exp +0.5686; margin -0.5320; gate **False** → CUT20; ΔF6.34 +0.000
- `2025-08-29` validation: parent -4.250; upper 0.0380; body-exp +0.2059; margin -0.1678; gate **False** → CUT20; ΔF6.34 +0.000
- `2025-09-12` validation: parent -0.464; upper 0.0000; body-exp +0.6542; margin -0.6542; gate **False** → CUT20; ΔF6.34 +0.000
- `2026-03-27` validation: parent -4.250; upper 0.0007; body-exp +0.2601; margin -0.2595; gate **False** → CUT20; ΔF6.34 +0.000

## Guardrail
Same-sample diagnostic selected from F6.37. Even a PASS cannot validate or freeze this rule. No numeric threshold, alternate lookback, or timing tuning is allowed from these same cases.
