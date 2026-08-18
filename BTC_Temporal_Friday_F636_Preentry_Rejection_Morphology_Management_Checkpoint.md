# Friday F6.36 — Pre-entry Rejection Morphology Management

**Diagnostic screen: FAIL**
**Same-sample diagnostic only; live BBC untouched; no automatic promotion.**

## Exact architecture
Start from F6.34. For the no-flow-divergence +20 branch only, the immediate pre-entry 5m candle is rejection-like when an upper wick is present and total wick length exceeds body length. Rejection-like cases join the existing +35 higher-close watcher; all other no-divergence cases keep the +20 cut. No new timing or confirmation rule is introduced.

## Routing
- no-divergence +20 branch **6** = 1 winner / 5 losers
- morphology signals **3** = 1 winner / 2 losers
- morphology +35 HOLD W/L **1 / 1**; CUT35 W/L **0 / 0**

## Economics
- frozen **+138.329** → F6.34 **+155.181** → F6.36 **+152.901**
- incremental vs frozen **+14.572**; vs F6.34 **-2.280**
- D/V incremental vs frozen **+9.936 / +4.637**; delta vs F6.34 **+2.020 / -4.300**
- WR **52.90% → 52.90%**; PF **1.827 → 2.001**; DD **24.259 → 19.622**
- acted parent winners preserved positive **3/3**; baseline positive→nonpositive **0**
- morphology winner gain vs F6.34 **+2.020**; morphology loser cost vs F6.34 **-4.300**

## No-divergence detail
- `2024-01-19` discovery: parent +0.646; body 0.474; upper-wick 0.157; total-wick 0.526; morph **True** → CONFIRM35_HOLD; ΔF6.34 +2.020
- `2024-09-20` discovery: parent -4.250; body 0.631; upper-wick 0.117; total-wick 0.369; morph **False** → CUT20; ΔF6.34 +0.000
- `2025-05-09` discovery: parent -4.250; body 0.962; upper-wick 0.037; total-wick 0.038; morph **False** → CUT20; ΔF6.34 +0.000
- `2025-08-29` validation: parent -4.250; body 0.359; upper-wick 0.038; total-wick 0.641; morph **True** → CONFIRM35_HOLD; ΔF6.34 -1.995
- `2025-09-12` validation: parent -0.464; body 0.897; upper-wick 0.000; total-wick 0.103; morph **False** → CUT20; ΔF6.34 +0.000
- `2026-03-27` validation: parent -4.250; body 0.437; upper-wick 0.001; total-wick 0.563; morph **True** → FROZEN_BEFORE35; ΔF6.34 -2.305

## Guardrail
This is a same-sample economic diagnostic built from F6.35 morphology. Even a PASS cannot promote the rule. If it fails, do not tune wick/body thresholds or +35 timing on these same cases.
