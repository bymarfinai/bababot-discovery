# Friday F6.39 — Exact F6.38 Balance-Gate Robustness Audit

**Robustness screen: PASS**
**FORENSIC ONLY — no promotion; live BBC untouched.**

## Frozen exact gate
`upper_wick_ratio > body_expansion_vs_median_prior_3_completed_5m_bars`

No threshold, alternate lookback, timing, EMA, or economic action was tested.

## Branch-matched control (8 future winners vs 6 true-dead)
- gate winner/dead: **7/8 (87.5%) vs 0/6 (0.0%)**
- winner-minus-dead gap **+87.5pp**; balance-margin AUC **0.938**; one-sided enrichment p **0.0023**

## Broad control (13 future winners vs 9 true-dead)
- gate winner/dead: **10/13 (76.9%) vs 1/9 (11.1%)**
- winner-minus-dead gap **+65.8pp**; balance-margin AUC **0.786**; one-sided enrichment p **0.0038**

## D/V branch robustness
- D: gate **4/5 W vs 0/2 dead**; gap **+80.0pp**; margin AUC **0.900**
- V: gate **3/3 W vs 0/4 dead**; gap **+100.0pp**; margin AUC **1.000**

## Leave-one-calendar-year-out branch sensitivity
- omit 2024: 4/4 W vs 0/5 dead; gap **+100.0pp**; AUC **1.000**
- omit 2025: 6/7 W vs 0/4 dead; gap **+85.7pp**; AUC **0.893**
- omit 2026: 4/5 W vs 0/3 dead; gap **+80.0pp**; AUC **0.933**

## Guardrail
This is robustness evidence on already-inspected history, not untouched OOS. Even a PASS does not freeze or promote F6.38.
