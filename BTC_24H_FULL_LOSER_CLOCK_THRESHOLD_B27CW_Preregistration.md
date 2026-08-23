# B27CW — BTC 24H F05 SHORT Clock-Specific Full-Loser Threshold Calibration — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether the frozen B27CV PLUS15 full-loser classifier becomes more useful when only its BAD-probability cutoff is calibrated separately for each of the six 4H clock blocks.

This is classifier/anatomy calibration only. No feature, model, entry, TP, SL, runner, label, clock inclusion, or regime rule may change. Trading WR/PF/expectancy/PnL are N/A.

External and reference_validation are reused lineage data, not untouched OOS. Live BBC unchanged.

## Frozen parent model
Use the exact B27CV data identity, labels, causal PLUS15 feature family, preprocessing, and logistic model:
- 652 executable F05 BASE_H trades: external 183 / development 297 / reference_validation 172;
- BAD = FULL_SL_HIGH_BREAK, pooled major 78;
- GOOD = target_reached, pooled major 348;
- OTHER = 226, reported but never relabeled;
- PLUS15 checkpoint only;
- exact B27CV LogisticRegression pipeline and development fit.

The implementation must reproduce before threshold calibration:
- B27CV development PLUS15 AUC = 0.8860088365243004;
- global SAFE threshold = 0.6079191233470493, development BAD capture 28/38 = 73.6842%, GOOD sacrifice 9/159 = 5.6604%;
- global AGGRESSIVE threshold = 0.4101988544354365.

Any mismatch fails audit.

## Frozen clock-specific threshold selection
Clocks: 00-04, 04-08, 08-12, 12-16, 16-20, 20-00 UTC (07-11, 11-15, 15-19, 19-23, 23-03, 03-07 WIB).

For each clock independently and using DEVELOPMENT only:
- denominator BAD = all BAD in that clock at PLUS15, including BAD already too late before the checkpoint;
- denominator GOOD = all GOOD in that clock, including GOOD safely resolved before the checkpoint;
- only model-eligible/alive BAD+GOOD rows may be newly flagged;
- candidate thresholds are +inf plus each unique frozen B27CV PLUS15 BAD probability in descending order;
- SAFE: maximize cumulative BAD capture subject to cumulative GOOD sacrifice <=10%;
- AGGRESSIVE: maximize cumulative BAD capture subject to cumulative GOOD sacrifice <=20%;
- tie-break: lower GOOD sacrifice, then higher threshold;
- if no trade can be flagged under the cap, threshold = +inf;
- no clock may be deleted.

Apply the six frozen development thresholds unchanged to external and reference_validation.

## Required reporting
Six clocks independently first for SAFE and AGGRESSIVE:
- threshold;
- BAD total / too late / eligible / flagged / cumulative capture;
- GOOD total / resolved safe / eligible / flagged / cumulative sacrifice;
- flagged BAD precision.

Then pooled development, external, reference_validation, pooled reused ext+validation, and pooled major.

Also compare the clock-specific SAFE map directly with the frozen global B27CV PLUS15 SAFE threshold.

## Frozen support gate
Primary mode = SAFE.

`B27CW_CLOCK_THRESHOLD_REUSED_CANDIDATE` requires:
1. audit PASS;
2. development clock-map GOOD sacrifice <=10% and BAD capture >= frozen global SAFE development capture (73.6842%);
3. external clock-map BAD capture >= frozen global SAFE external capture 39.1304% and GOOD sacrifice <=15%;
4. reference_validation clock-map BAD capture >= frozen global SAFE validation capture 47.0588% and GOOD sacrifice <=15%;
5. pooled reused clock-map GOOD sacrifice <=15%;
6. all six clocks retained.

Otherwise verdict: `B27CW_CLOCK_THRESHOLD_NOT_SUPPORTED`.

Even a candidate only supports separability calibration. A separate preregistered causal economic simulation is required before using an early-abort detector.
