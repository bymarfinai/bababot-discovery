# SOL Adaptive SL V1 — Result

- 5m coverage: **99.769767%**
- Frozen SL construction winner: **RECLAIM_EXTREME**
- Upstream detector and adaptive-entry router are unchanged.
- No TP, PnL, hour, indicator, or regime optimization.
- 2026 is a secondary monitor, NOT an untouched SL holdout.

## Construction 2020-2024

- Filled router entries: **218**
- Positive structural entries: **130**
- Positive survival: **92.31%**
- BUY positive survival: **90.91%**
- SELL positive survival: **93.75%**
- Score-3 positive survival: **92.92%**
- Score-4 positive survival: **88.24%**
- Negative stop-hit rate: **88.64%**
- Survivor structural-event rate: **92.31%**
- Median initial risk: **1.4051 H1 range units**
- P75 initial risk: **1.7730**
- Median negative time-to-stop: **220.0 min**
- Median positive MAE/stop: **0.2637**
- Same-entry-bar stop hits: **0**

## Frozen 2025 confirmation

- Filled router entries: **60**
- Positive structural entries: **35**
- Positive survival: **97.14%**
- BUY positive survival: **100.00%**
- SELL positive survival: **95.45%**
- Score-3 positive survival: **96.43%**
- Score-4 positive survival: **100.00%**
- Negative stop-hit rate: **88.00%**
- Survivor structural-event rate: **91.89%**
- Median initial risk: **1.4195 H1 range units**
- P75 initial risk: **1.7774**
- Median negative time-to-stop: **125.0 min**
- Median positive MAE/stop: **0.1817**
- Same-entry-bar stop hits: **0**

## 2025 gate audit

- PASS — filled_n_ge_40
- PASS — positive_n_ge_25
- PASS — positive_survival_ge_85pct
- PASS — buy_positive_survival_ge_80pct
- PASS — sell_positive_survival_ge_80pct
- PASS — score3_positive_survival_ge_85pct
- PASS — score4_positive_survival_ge_65pct_if_n_ge5
- PASS — median_risk_le_1_5x_construction

## 2025 verdict

**PASS — frozen SL candidate confirmed historically.**

## 2026 YTD secondary replication monitor

- Filled router entries: **46**
- Positive structural entries: **30**
- Positive survival: **90.00%**
- BUY positive survival: **92.31%**
- SELL positive survival: **88.24%**
- Score-3 positive survival: **89.29%**
- Score-4 positive survival: **100.00%**
- Negative stop-hit rate: **68.75%**
- Survivor structural-event rate: **84.38%**
- Median initial risk: **1.6148 H1 range units**
- P75 initial risk: **2.0550**
- Median negative time-to-stop: **135.0 min**
- Median positive MAE/stop: **0.2706**
- Same-entry-bar stop hits: **0**

## 2026 monitor sample audit

- PASS — filled_n_ge_20
- PASS — positive_n_ge_10

## 2026 monitor quality audit

- PASS — positive_survival_ge_80pct
- PASS — buy_survival_ge_70pct_if_n_ge5
- PASS — sell_survival_ge_70pct_if_n_ge5
- PASS — score3_survival_ge_80pct_if_n_ge5
- PASS — score4_survival_ge_60pct_if_n_ge5
- PASS — median_risk_le_1_75x_construction

**VERDICT: ADAPTIVE_SL_CANDIDATE_REPLICATED_NOT_INDEPENDENT**

This is not labeled fully validated SL because 2026 was already observed during entry work. A genuinely new holdout is still required for that claim.

2027_PLUS=CLOSED
