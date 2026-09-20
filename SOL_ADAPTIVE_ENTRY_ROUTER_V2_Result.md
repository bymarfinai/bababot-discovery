# SOL Adaptive Entry Router V2 — Result

- 5m coverage: **99.769767%**
- Frozen router: **score 3 -> FIVE_MIN_REVERSAL_BREAK; score 4 -> GAP_25**.
- Actionable detector remains SCORE>=3 with same-reclaim-bar resolved outcomes excluded.
- No SL, TP, PnL, hour, indicator, or regime optimization.

## Construction 2020-2024

- Signals: **288**
- Filled: **218** (75.69%)
- Positive structural events: **153**
- Positive-event capture: **84.97%**
- Filled structural-event rate: **59.63%** vs detector baseline **53.12%**
- Negative-event fill rate: **65.19%**
- BUY positive capture: **80.49%**
- SELL positive capture: **90.14%**
- Score-3 positive capture: **88.98%**
- Score-4 positive capture: **65.38%**
- Score-4 median positive improvement: **0.2200 H1 range units**
- Median time-to-fill: **20.0 min**
- Median positive adverse excursion: **0.4583 H1 range units**

## Frozen 2025 confirmation

- Signals: **80**
- Filled: **60** (75.00%)
- Positive structural events: **44**
- Positive-event capture: **79.55%**
- Filled structural-event rate: **58.33%** vs detector baseline **55.00%**
- Negative-event fill rate: **69.44%**
- BUY positive capture: **72.22%**
- SELL positive capture: **84.62%**
- Score-3 positive capture: **90.32%**
- Score-4 positive capture: **53.85%**
- Score-4 median positive improvement: **0.2110 H1 range units**
- Median time-to-fill: **15.0 min**
- Median positive adverse excursion: **0.3166 H1 range units**

## 2025 gate audit

- PASS — signal_n_ge_50
- PASS — filled_n_ge_35
- PASS — positive_n_ge_25
- PASS — positive_capture_ge_75pct
- PASS — filled_event_rate_ge_detector_baseline
- PASS — buy_positive_capture_ge_65pct
- PASS — sell_positive_capture_ge_65pct
- PASS — score3_positive_capture_ge_75pct
- PASS — score4_positive_capture_ge_50pct_if_n_ge5
- PASS — score4_positive_improvement_gt_0

## 2025 verdict

**PASS — frozen router confirmed. 2026 YTD was opened only after this pass.**

## Untouched 2026 YTD

- Signals: **61**
- Filled: **46** (75.41%)
- Positive structural events: **33**
- Positive-event capture: **90.91%**
- Filled structural-event rate: **65.22%** vs detector baseline **54.10%**
- Negative-event fill rate: **57.14%**
- BUY positive capture: **86.67%**
- SELL positive capture: **94.44%**
- Score-3 positive capture: **96.55%**
- Score-4 positive capture: **50.00%**
- Score-4 median positive improvement: **0.2116 H1 range units**
- Median time-to-fill: **25.0 min**
- Median positive adverse excursion: **0.5447 H1 range units**

## 2026 sample audit

- PASS — signal_n_ge_30
- PASS — filled_n_ge_20
- PASS — positive_n_ge_10

## 2026 quality audit

- PASS — positive_capture_ge_70pct
- PASS — filled_event_rate_not_below_baseline_minus_3pp
- PASS — buy_positive_capture_ge_55pct_if_n_ge5
- PASS — sell_positive_capture_ge_55pct_if_n_ge5
- PASS — score3_positive_capture_ge_65pct_if_n_ge5
- PASS — score4_positive_capture_ge_45pct_if_n_ge5
- PASS — score4_positive_improvement_gt_0_if_5_filled

**VERDICT: VALIDATED_ADAPTIVE_ENTRY_ROUTER**

This verdict concerns adaptive entry routing only. SL and TP remain separate.

2027_PLUS=CLOSED
