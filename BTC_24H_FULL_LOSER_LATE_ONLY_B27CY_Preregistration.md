# B27CY — BTC 24H F05 SHORT Late-Only BAD Refinement — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Refine the B27CX state machine specifically for trades that are **not SAFE-BAD at +10m but become SAFE-BAD at +15m** (`PLUS15_ONLY`). Test whether the increase in the already-frozen B27CV BAD probability can separate late-emerging catastrophic `FULL_SL_HIGH_BREAK` trades from late-emerging GOOD target-reaching trades.

This is **classifier/anatomy research only**. No entry, TP, SL, runner, model family, feature family, clock/regime exclusion, or live rule is changed. Trading WR/PF/expectancy/PnL from a hypothetical abort are N/A.

External and reference_validation are reused lineage data, not untouched OOS.

## Frozen parent identity
Reproduce B27CV/B27CX exactly:
- executable F05 trades: 652 pooled major;
- BAD `FULL_SL_HIGH_BREAK`: 78;
- GOOD frozen clock-target reached: 348;
- OTHER: 226;
- +10m SAFE threshold = 0.5898635948838399;
- +15m SAFE threshold = 0.6079191233470493;
- +10m development AUC = 0.8452298452298452;
- +15m development AUC = 0.8860088365243004.

Probability comparisons are inclusive with numerical tolerance 1e-12.

Expected B27CX transition identity among BAD/GOOD trades alive at +15m:
- development PLUS15_ONLY: BAD 6 / GOOD 6;
- external PLUS15_ONLY: BAD 2 / GOOD 3;
- reference_validation PLUS15_ONLY: BAD 4 / GOOD 6.

## Frozen primary discriminator
For every PLUS15_ONLY trade:

`delta_bad_prob = bad_prob_plus15 - bad_prob_plus10`

No other feature may determine the primary PASS verdict.

### Development-only threshold selection
Within development PLUS15_ONLY only, choose a threshold on `delta_bad_prob` from unique observed development values plus +inf.

Flag if `delta_bad_prob >= threshold`.

Choose the threshold that:
1. keeps PLUS15_ONLY GOOD sacrifice <= 33.34%;
2. maximizes PLUS15_ONLY BAD capture;
3. tie-break: lower GOOD sacrifice;
4. final tie-break: higher threshold.

If no trade can be flagged under the GOOD cap, threshold = +inf.

The selected threshold is frozen and applied unchanged to external and reference_validation.

## Frozen state-machine reconstruction
At the +15m decision point:
- `BOTH`: SAFE-BAD at +10m and +15m -> flag for hypothetical abort;
- `PLUS10_ONLY`: SAFE-BAD at +10m but not +15m -> do not flag;
- `PLUS15_ONLY`: not SAFE-BAD at +10m but SAFE-BAD at +15m -> flag only if `delta_bad_prob` passes the frozen development threshold;
- `NEITHER`: do not flag.

No clock- or regime-specific threshold is allowed.

## Secondary diagnostics only
On the PLUS15_ONLY subset, report but do not optimize or gate on:
- `max_bull_body_r4` at +15m;
- `higher_close_streak` at +15m;
- `net_close_from_entry_r4` at +15m.

For each feature, report BAD vs GOOD medians and univariate AUC by partition. Direction is fixed from development only; these diagnostics cannot replace `delta_bad_prob` post hoc.

## Required reporting
Show six 4H clocks independently first for the frozen combined state machine, then pooled aggregates.

For each partition and pooled reused/major report:
- total BAD / GOOD;
- PLUS15_SAFE BAD capture and GOOD sacrifice;
- B27CX BOTH/persistence BAD capture and GOOD sacrifice;
- B27CY refined state-machine BAD capture and GOOD sacrifice;
- flag precision among BAD+GOOD;
- PLUS15_ONLY BAD/GOOD counts and primary late-only capture/sacrifice.

Also report regime splits secondarily. No clock/regime deletion.

## Frozen support gate
Verdict `B27CY_LATE_ONLY_REFINEMENT_REUSED_CANDIDATE` requires audit PASS and all of:
1. development PLUS15_ONLY BAD capture >= 50%;
2. development PLUS15_ONLY GOOD sacrifice <= 33.34%;
3. external PLUS15_ONLY BAD capture >= 50%;
4. external PLUS15_ONLY GOOD sacrifice <= 33.34%;
5. validation PLUS15_ONLY BAD capture >= 50%;
6. validation PLUS15_ONLY GOOD sacrifice <= 33.34%;
7. pooled reused refined-state BAD capture retains >= 70% of PLUS15_SAFE BAD capture;
8. pooled reused refined-state GOOD sacrifice improves by >= 3 percentage points versus PLUS15_SAFE;
9. pooled major refined-state flag precision > PLUS15_SAFE precision.

Otherwise verdict: `B27CY_LATE_ONLY_REFINEMENT_NOT_SUPPORTED`.

Even a candidate verdict is reused-data anatomy evidence only. A separate preregistered causal economic abort simulation is required before interpreting actual trading WR/PF/expectancy/PnL or changing live BBC.
