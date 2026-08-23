# B27BK — BTC 24H BEAR False-Pause Anatomy Audit — Preregistration

## Purpose

Diagnose why the frozen B27BJ BEAR-origin magnitude-aware model often classifies genuine `BEAR -> SIDEWAYS -> BULL` transitions as one-bar inherited BEAR pauses. This is a detector-anatomy experiment only.

No trading direction, entry, stop, target, fee, WR, PF, PnL, session optimization, or live BBC change is permitted.

## Frozen parent lineage

B27BK inherits B27BJ exactly and may not refit, retune, or reinterpret it:

- B27BJ BEAR-origin logistic model was fit on `development` only.
- B27BJ threshold remains frozen at `P(RESUME) >= 0.50`.
- External and reference_validation remain out-of-sample.
- B27BJ result/verdict remains historical and unchanged.

The implementation must reproduce the exact BEAR pooled-OOS confusion counts before any new readout is accepted:

- `TRUE_PAUSE`: actual RESUME, predicted RESUME = **79**.
- `FALSE_TRANSITION`: actual RESUME, predicted TRANSITION = **32**.
- `FALSE_PAUSE`: actual TRANSITION, predicted RESUME = **74**.
- `TRUE_TRANSITION`: actual TRANSITION, predicted TRANSITION = **57**.
- total BEAR pooled OOS = **242**.

Primary ambiguity cohort = only rows on which B27BJ chose inherited BEAR (`pred_resume=True`):

- `TRUE_PAUSE` versus `FALSE_PAUSE`.

This directly asks why 74 genuine transitions looked enough like continuation to B27BJ to be inherited as BEAR.

## Causality / clock

All features must be available no later than the first completed 4H bar labeled raw SIDEWAYS (`first_sideways_ts`).

Allowed information:

- that first completed SIDEWAYS 4H bar;
- the immediately preceding completed 4H bar;
- detector counters/EMA/ATR values already available at those completed bars;
- the frozen B27BJ probability as a diagnostic only.

Forbidden:

- second SIDEWAYS bar or any later bar;
- eventual exit-state information in any feature;
- future return/path information;
- any 5m information after `first_sideways_ts`;
- any trading outcome.

## Preregistered causal features

### Existing B27BJ features

1. `dir_ema_spread_atr`
2. `dir_close_ema20_atr`
3. `dir_ema7_slope_atr`
4. `dir_ema20_slope_atr`
5. `dir_body_atr`
6. `bar_range_atr`

### New anatomy features frozen before results

For BEAR origin, directional normalization is defined so **higher values mean more aligned with the prior BEAR direction** where applicable (`sgn=-1`).

7. `dir_close_ema7_atr` = `sgn*(close-EMA7)/ATR`.
8. `dir_close_change_atr` = `sgn*(close-prev_close)/ATR`.
9. `dir_high_change_atr` = `sgn*(high-prev_high)/ATR`.
10. `dir_low_change_atr` = `sgn*(low-prev_low)/ATR`.
11. `dir_spread_change_atr` = change in direction-normalized `(EMA7-EMA20)` spread divided by current ATR.
12. `aligned_close_location` = close location inside current 4H range, normalized so 1.0 is at the prior-regime direction edge and 0.0 at the opposite edge. For BEAR this is `(high-close)/(high-low)`.
13. `counter_rejection_wick_fraction` = wick on the counter-direction edge divided by range. For BEAR this is upper wick/range.
14. `aligned_extension_wick_fraction` = wick on the prior-regime direction edge divided by range. For BEAR this is lower wick/range.
15. `range_ratio_prev` = current 4H range / prior 4H range.
16. `atr_ratio_prev` = current ATR14 / prior ATR14.
17. `aligned_structure_margin` = `min(LH,LL) - max(HH,HL)` on the first SIDEWAYS bar.
18. `aligned_structure_delta` = `min(LH,LL)` current minus prior.
19. `opposite_structure_delta` = `min(HH,HL)` current minus prior.
20. `prior_directional_age` = completed 4H intervals spent in the immediately prior BEAR episode (already recorded by B27BI; included for completeness).

`p_resume` from B27BJ is reported only as a model-confidence diagnostic. It is **not eligible** to satisfy the new-feature evidence gate because using it to select a new threshold after B27BJ would be post-hoc threshold tuning.

## Frozen comparisons

For every eligible feature, report medians, means, and rank AUC where positive class = `TRUE_PAUSE` and negative class = `FALSE_PAUSE` for:

- external;
- reference_validation;
- pooled OOS.

Also report the same feature table across all four B27BJ confusion buckets as a control anatomy table.

No threshold search, decision tree, feature selection, logistic refit, or multivariate model is allowed in B27BK.

## Frozen primary evidence rule

A preregistered **new anatomy feature** (features 7–20, excluding `p_resume`) is called a robust causal discriminator only if:

1. both `TRUE_PAUSE` and `FALSE_PAUSE` have at least 20 observations in external and at least 20 in reference_validation;
2. its AUC direction is the same in external and reference_validation (both >0.50 or both <0.50);
3. discrimination is at least `|AUC-0.50| >= 0.10` in **both** external and reference_validation;
4. pooled-OOS discrimination is at least `|AUC-0.50| >= 0.15`.

Frozen verdict:

- `B27BK_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR_FOUND` if at least one new feature passes all four conditions;
- otherwise `B27BK_NO_ROBUST_BEAR_FALSE_PAUSE_DISCRIMINATOR`.

Passing B27BK does **not** authorize a detector redesign. It only identifies preregistered causal evidence that may be used in a new experiment ID.

## Persistence

Persist:

- result Markdown;
- exact OOS cohort with confusion labels and feature values;
- feature summary;
- status file;
- master research registry entry.

Research only. Live BBC unchanged.
