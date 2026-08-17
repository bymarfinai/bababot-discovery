# Friday F6.23 — F6.22 False-Positive Winner Forensic

**Status: COMPLETE — FORENSIC ONLY; NO EXIT RULE TUNED/PROMOTED.**
**Live BBC untouched; frozen stack and F6.22 unchanged.**

## Frozen cohorts
- true low failures: **5** (D 4 / V 1)
- false-positive eventual winners: **7** (D 5 / V 2)
- excluded high givebacks: **2**

## Strong causal separators
- taker_last2_mean: strength 0.857, AUC D/V 0.200/0.000; lower_failure; median failure -0.2363 vs false-win -0.1198; LOO median 0.845
- taker_last4_mean: strength 0.800, AUC D/V 0.200/0.000; lower_failure; median failure -0.2672 vs false-win -0.1620; LOO median 0.800
- ema20_reclaims: strength 0.786, AUC D/V 0.300/0.000; lower_failure; median failure 0.0000 vs false-win 1.0000; LOO median 0.786
- frac_taker_positive: strength 0.771, AUC D/V 0.175/0.250; lower_failure; median failure 0.3846 vs false-win 0.5385; LOO median 0.750
- pre120_retr_from_high: strength 0.771, AUC D/V 0.250/0.000; lower_failure; median failure 0.3162 vs false-win 0.7292; LOO median 0.750
- pre120_entry_range_pos: strength 0.771, AUC D/V 0.750/1.000; higher_failure; median failure 0.6838 vs false-win 0.2708; LOO median 0.750
- pre120_dist_low_pct: strength 0.743, AUC D/V 0.650/1.000; higher_failure; median failure 0.0040 vs false-win 0.0017; LOO median 0.732
- pre120_ret: strength 0.743, AUC D/V 0.700/1.000; higher_failure; median failure 0.0029 vs false-win -0.0023; LOO median 0.733
- pre60_taker: strength 0.743, AUC D/V 0.650/1.000; higher_failure; median failure 0.0961 vs false-win -0.1154; LOO median 0.724
- pre120_taker: strength 0.714, AUC D/V 0.600/1.000; higher_failure; median failure 0.0557 vs false-win -0.0776; LOO median 0.700
- pre60_entry_range_pos: strength 0.714, AUC D/V 0.750/0.500; higher_failure; median failure 0.5657 vs false-win 0.3838; LOO median 0.707

## Top feature atlas
- taker_last2_mean: strength 0.857, AUC 0.143, D/V 0.200/0.000, failure -0.2363, false-win -0.1198
- taker_mean: strength 0.829, AUC 0.171, D/V 0.050/0.500, failure -0.0944, false-win -0.0245
- taker_last4_mean: strength 0.800, AUC 0.200, D/V 0.200/0.000, failure -0.2672, false-win -0.1620
- ema20_reclaims: strength 0.786, AUC 0.214, D/V 0.300/0.000, failure 0.0000, false-win 1.0000
- frac_taker_positive: strength 0.771, AUC 0.229, D/V 0.175/0.250, failure 0.3846, false-win 0.5385
- pre120_retr_from_high: strength 0.771, AUC 0.229, D/V 0.250/0.000, failure 0.3162, false-win 0.7292
- pre120_entry_range_pos: strength 0.771, AUC 0.771, D/V 0.750/1.000, failure 0.6838, false-win 0.2708
- taker_median: strength 0.771, AUC 0.229, D/V 0.200/0.500, failure -0.1126, false-win 0.0147
- pre120_dist_low_pct: strength 0.743, AUC 0.743, D/V 0.650/1.000, failure 0.0040, false-win 0.0017
- pre120_ret: strength 0.743, AUC 0.743, D/V 0.700/1.000, failure 0.0029, false-win -0.0023
- pre60_taker: strength 0.743, AUC 0.743, D/V 0.650/1.000, failure 0.0961, false-win -0.1154
- higher_low_fraction: strength 0.729, AUC 0.271, D/V 0.150/0.750, failure 0.4167, false-win 0.4167

## Guardrail
Only information known at/before the fixed F6.22 +65m decision is used as a feature. Final winner/loss outcome is label-only. Validation contains only one true low failure, so V direction is informative but not sufficient proof. Any F6.24 action rule must be predeclared from a small interpretable subset; do not threshold-sweep this 12-case cohort.
