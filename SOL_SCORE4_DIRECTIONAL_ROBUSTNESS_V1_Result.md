# SOL Score-4 Directional Character Robustness V1 — Result

- 5m coverage: **99.769767%**
- Post-cutoff data: **EXCLUDED**.
- Frozen BUY rule: **time_to_fill_min <= 15 AND directional_improvement_range_units <= 0.21471170803**
- SELL_SIDE remains auto-accepted.
- No threshold was selected or changed in this audit.

## 1. Exact pooled BUY-side rule

- Unfiltered BUY: N **29**, event rate **31.03%**, mean **-0.339R**, PF **0.526**
- Accepted BUY: N **9**, event rate **66.67%**, mean **0.507R**, PF **2.141**
- Event-rate lift: **35.63 pp**
- Check: **PASS**

## 2. Temporal consistency

| Period | Accepted BUY N | Evaluable | Event support | Mean-R support |
|---|---:|---|---|---|
| HIST_2020_2024 | 5 | YES | PASS | PASS |
| RETRO_2025 | 3 | YES | PASS | PASS |
| RETRO_2026_PRE | 1 | NO | — | — |
- Check: **PASS**

## 3. Leave-one-out

- Mean R remains positive: **100.00%** of removals
- Event rate remains >=50%: **100.00%** of removals
- Check: **PASS**

## 4. Threshold neighborhood

- Supportive variants: **5/9**
- Check: **FAIL**

| Fill <= | Improvement <= | N | Event rate | Mean R | PF | Supportive |
|---:|---:|---:|---:|---:|---:|---|
| 10 | 0.171769 | 1 | 100.00% | 2.442 | inf | NO |
| 10 | 0.214712 | 6 | 66.67% | 0.457 | 1.915 | YES |
| 10 | 0.257654 | 9 | 44.44% | -0.028 | 0.957 | NO |
| 15 | 0.171769 | 2 | 100.00% | 1.880 | inf | NO |
| 15 | 0.214712 | 9 | 66.67% | 0.507 | 2.141 | YES |
| 15 | 0.257654 | 13 | 46.15% | 0.043 | 1.071 | YES |
| 20 | 0.171769 | 2 | 100.00% | 1.880 | inf | NO |
| 20 | 0.214712 | 9 | 66.67% | 0.507 | 2.141 | YES |
| 20 | 0.257654 | 15 | 46.67% | 0.040 | 1.066 | YES |

## 5. 2025 + 2026 pre-cutoff out-of-construction check

- Unfiltered BUY: N **13**, event rate **23.08%**, mean **-0.221R**
- Accepted BUY: N **4**, event rate **50.00%**, mean **0.519R**, PF **2.037**
- Event-rate lift: **26.92 pp**
- Random same-size subset exceedance fraction: **10.21%** (73/715)
- Check: **PASS**

## 6. Bootstrap stability

- P(mean R > 0): **85.41%**
- P(event rate >= pooled unfiltered BUY): **99.15%**
- Mean-R bootstrap 5/50/95%: **-0.193/0.507/1.251R**
- Event-rate bootstrap 5/50/95%: **44.44%/66.67%/88.89%**
- Check: **PASS**

## 7. SELL-side auto-accept

- Pooled SELL: N **27**, mean **0.571R**, PF **2.542**
- Positive periods: **3/3**
- Check: **PASS**

## 8. Full architecture uplift

- Unfiltered all: N **56**, event rate **46.43%**, mean **0.100R**, PF **1.182**, cum **5.582R**
- Accepted all: N **36**, event rate **63.89%**, mean **0.555R**, PF **2.428**, cum **19.987R**
- Check: **PASS**

## Primary check audit

- PASS — exact_pooled_buy_stability
- PASS — temporal_consistency
- PASS — leave_one_out_stability
- FAIL — threshold_neighborhood_sensitivity
- PASS — out_of_construction_retrospective
- PASS — bootstrap_stability
- PASS — sell_side_auto_accept_stability
- PASS — full_architecture_uplift

**VERDICT: SCORE4_DIRECTIONAL_CHARACTER_RETROSPECTIVELY_FRAGILE**

This is retrospective robustness evidence only. It does not convert the frozen Score-4 directional character into independent validation.

POST_CUTOFF_DATA=EXCLUDED
