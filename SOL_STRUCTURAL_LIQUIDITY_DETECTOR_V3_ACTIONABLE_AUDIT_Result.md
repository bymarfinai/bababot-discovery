# SOL Structural Liquidity Detector V3 — Actionability Audit

- 5m coverage: **99.769767%**
- Detector frozen unchanged at **SCORE >= 3**.
- Exclusion only: rows already structurally resolved on the reclaim H1 candle.
- No entry, TP, SL, PnL, hour, indicator, or regime changes.

## Construction 2020-2024

- Raw physical events: **5,450**
- Actionable physical events: **5,400**
- Actionable baseline rate: **24.11%**
- SCORE>=3 actionable: N=**288**, rate=**53.12%**
- Lift: **29.01 pp**

## Frozen 2025 audit

- Raw events: **1,264**
- Actionable events: **1,247**
- Actionable baseline: **24.62%**
- SCORE>=3 actionable: N=**80**, rate=**55.00%**
- Lift: **30.38 pp**
- Wilson 95% CI: **44.12% – 65.42%**
- BUY_SIDE: selected **48.65%** vs baseline **24.52%**
- SELL_SIDE: selected **60.47%** vs baseline **24.72%**

## Gate audit

- PASS — selected_2025_n_ge_50
- PASS — selected_2025_rate_ge_45pct
- PASS — lift_ge_15pp
- PASS — wilson_lower_ge_35pct
- PASS — buy_side_above_baseline
- PASS — sell_side_above_baseline

**VERDICT: VALIDATED_ACTIONABLE_STRUCTURAL_LIQUIDITY_DETECTOR**

A passing verdict means the frozen detector still enriches future structural consequences when every signal is genuinely actionable only after the reclaim close.

2026_PLUS=CLOSED
