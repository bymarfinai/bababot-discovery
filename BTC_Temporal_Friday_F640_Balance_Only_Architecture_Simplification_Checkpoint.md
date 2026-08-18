# Friday F6.40 — Balance-Only Architecture Simplification

**Simplification screen: FAIL**
**Same-history diagnostic only; live BBC untouched; no automatic promotion.**

## Exact replacement architecture
Ignore F6.31 for routing. Every exact F6.29 +20 candidate is admitted to the existing +35 watcher iff the exact F6.38 balance gate passes; otherwise it is cut at +20. No other rule changes.

## Economics
- frozen **+138.329** → F6.34 **+155.181** → F6.38 OR-stack **+157.201** → F6.40 balance-only **+152.785**
- Δ vs F6.38 **-4.417**; D/V **-4.417 / +0.000**
- WR **52.17%**; PF **2.005**; DD **17.627**
- acted winners preserved **2/3**; baseline positive→nonpositive **1**

## Balance gate on the 12 F6.29 actions
- PASS **4** = 2W / 2L
- FAIL **8** = 1W / 7L

## F6.31 × balance overlap
- flow False / balance False: **5** = 0W/5L; 2024-09-20, 2025-05-09, 2025-08-29, 2025-09-12, 2026-03-27
- flow False / balance True: **1** = 1W/0L; 2024-01-19
- flow True / balance False: **3** = 1W/2L; 2024-11-22, 2025-02-14, 2025-05-16
- flow True / balance True: **3** = 1W/2L; 2024-03-08, 2025-07-04, 2025-07-18

## Changed vs F6.38
- `2024-11-22` discovery: parent -4.250; flow True; balance False margin -0.0956; F6.38 CUT35 -1.131 → F6.40 CUT20 -2.190; Δ -1.059
- `2025-02-14` discovery: parent -1.520; flow True; balance False margin -0.1375; F6.38 CUT35 -0.885 → F6.40 CUT20 -1.218; Δ -0.333
- `2025-05-16` discovery: parent +0.732; flow True; balance False margin -0.5334; F6.38 CONFIRM35_HOLD +0.732 → F6.40 CUT20 -2.292; Δ -3.024

## Guardrail
Same-history simplification diagnostic only. No freeze/promotion without genuinely new evidence.
