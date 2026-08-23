# B27CZ — BTC 24H F05 SHORT Late-Only Bullish-Impulse Refinement — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Refine the B27CX +15m state machine specifically for `PLUS15_ONLY` trades: not SAFE-BAD at +10m but SAFE-BAD at +15m. Test whether the maximum bullish 5m candle body observed from F05 fill through +15m, normalized by R4, separates late-emerging catastrophic `FULL_SL_HIGH_BREAK` trades from late-emerging GOOD clock-target trades.

This is **anatomy/classifier research only**. No entry, TP, SL, runner, model family, clock/regime exclusion, or live rule is changed. Trading WR/PF/expectancy/PnL are N/A.

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

Expected `PLUS15_ONLY` identity among BAD/GOOD trades alive at +15m:
- development: BAD 6 / GOOD 6;
- external: BAD 2 / GOOD 3;
- reference_validation: BAD 4 / GOOD 6.

## Frozen primary discriminator
For each `PLUS15_ONLY` trade:

`bull_impulse_r4 = max_bull_body_r4` at the frozen +15m B27CV feature snapshot.

The direction is frozen as **higher bullish impulse = higher BAD risk**, based on the already-reported B27CY diagnostic. No alternative direction or feature may determine the primary verdict.

### Development-only threshold selection
Within development `PLUS15_ONLY` only, choose a threshold from unique observed `bull_impulse_r4` values plus +inf.

Flag if `bull_impulse_r4 >= threshold`.

Choose the threshold that:
1. keeps `PLUS15_ONLY` GOOD sacrifice <= 33.34%;
2. maximizes `PLUS15_ONLY` BAD capture;
3. tie-break: lower GOOD sacrifice;
4. final tie-break: higher threshold.

If no trade can be flagged under the GOOD cap, threshold = +inf.

The selected threshold is frozen and applied unchanged to external and reference_validation.

## Frozen state-machine reconstruction
At +15m:
- `BOTH`: SAFE-BAD at +10m and +15m -> flag for hypothetical abort;
- `PLUS10_ONLY`: SAFE-BAD at +10m but not +15m -> do not flag;
- `PLUS15_ONLY`: not SAFE-BAD at +10m but SAFE-BAD at +15m -> flag only if `bull_impulse_r4` passes the frozen threshold;
- `NEITHER`: do not flag.

No clock- or regime-specific threshold is allowed.

## Required reporting
Show all six 4H clocks independently first for the reconstructed state machine, then pooled aggregates.

For development, external, reference_validation, pooled reused ext+val, and pooled major report:
- total BAD / GOOD;
- PLUS15_SAFE BAD capture and GOOD sacrifice;
- B27CX persistence/BOTH BAD capture and GOOD sacrifice;
- B27CZ refined-state BAD capture and GOOD sacrifice;
- flag precision among BAD+GOOD;
- `PLUS15_ONLY` BAD/GOOD totals and impulse-gate capture/sacrifice.

Also report `bull_impulse_r4` BAD/GOOD medians and directional AUC by partition, and regime splits secondarily. No clock/regime deletion.

## Frozen support gate
Verdict `B27CZ_BULL_IMPULSE_REUSED_CANDIDATE` requires audit PASS and all of:
1. development `PLUS15_ONLY` BAD capture >= 50%;
2. development `PLUS15_ONLY` GOOD sacrifice <= 33.34%;
3. external `PLUS15_ONLY` BAD capture >= 50%;
4. external `PLUS15_ONLY` GOOD sacrifice <= 33.34%;
5. validation `PLUS15_ONLY` BAD capture >= 50%;
6. validation `PLUS15_ONLY` GOOD sacrifice <= 33.34%;
7. pooled reused refined-state BAD capture retains >= 70% of PLUS15_SAFE BAD capture;
8. pooled reused refined-state GOOD sacrifice improves by >= 3 percentage points versus PLUS15_SAFE;
9. pooled major refined-state flag precision > PLUS15_SAFE precision.

Otherwise verdict: `B27CZ_BULL_IMPULSE_NOT_SUPPORTED`.

Even a candidate verdict is reused-data anatomy evidence only. A separate preregistered causal economic abort simulation is required before interpreting actual trading WR/PF/expectancy/PnL or changing live BBC.
