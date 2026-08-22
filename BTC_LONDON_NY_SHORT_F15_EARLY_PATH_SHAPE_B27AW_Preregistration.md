# B27AW — BTC London→NY SHORT F15 Early Path-Shape Atlas — Preregistration

## Purpose
Diagnose whether the early causal price path after a frozen B27AK F15 fill separates trades that later reach H2 before the actual B27AT E20-hybrid exit from PRE_H2_FAILURE trades.

This is a diagnostic atlas only. B27AW will not select an entry filter, exit threshold, stop, target, regime, confirmation rule, candle rule, or live-BBC change.

## Frozen lineage
- Entry cohort: exact B27AK/B27AT BLIND_F15 fills.
- Economic reference: exact B27AT E20 full-position hybrid result.
- Stage labels/timestamps: exact B27AV identities and causal H2-before-exit classification.
- Major partitions: external, development, reference_validation. August remains descriptive only.
- Required reproduction before interpretation: pooled major N=163, E20 activated=92, PRE_H2_FAILURE=48, H2-before-exit=115, realized B27AT E20-hybrid total=-15.05841591698896 USD.

## Causal observation clock
The 5m fill bar high/low is excluded from all path-shape features because its intrabar ordering relative to the F15 fill is unknown.

Observation starts at the next 5m bar after `entry_start`.
Frozen horizons are 1, 2, 3, 4, 6, 8, and 12 completed 5m bars after the fill bar, i.e. 5, 10, 15, 20, 30, 40, and 60 minutes.

For a horizon to be eligible, the trade must still be unresolved at the end of that horizon:
- H2 has not occurred on or before any bar included in the horizon; and
- the actual B27AT exit timestamp is strictly after the horizon end.

Thus every feature used at a given horizon was observable before either the H2 milestone or strategy exit became known.

## Frozen outcome labels
Primary future label among horizon-eligible trades:
- `LATER_H2`: the frozen B27AV trade later reaches H2 before actual exit.
- `PRE_H2_FAILURE`: the frozen B27AV trade exits before H2.

Secondary descriptive label: eventual B27AT E20 activation. It will not replace the primary H2-vs-failure comparison.

## Frozen path-shape features
All price distances are normalized by frozen London range R=H-L. Entry is frozen F15=L+0.15R.

For the N completed post-fill bars in each horizon:
1. `adverse_wick_r = max(0, max(high)-entry)/R`.
2. `favorable_wick_r = max(0, entry-min(low))/R`.
3. `adverse_close_r = max(0, max(close)-entry)/R`.
4. `favorable_close_r = max(0, entry-min(close))/R`.
5. `net_close_progress_r = (entry-last_close)/R`; positive is favorable for SHORT.
6. `wrong_side_close_fraction = mean(close > entry)`.
7. `lower_low_step_fraction = mean(low_i < low_{i-1})` inside the post-fill window; undefined for N=1.
8. `higher_high_step_fraction = mean(high_i > high_{i-1})`; undefined for N=1.
9. `close_path_efficiency = (first_close-last_close) / sum(abs(diff(close)))`; positive means efficient downward travel, bounded [-1,1] when denominator >0; 0 when no close travel.
10. `adverse_favorable_ratio = adverse_wick_r / max(favorable_wick_r, 1e-12)`; descriptive only, with finite cap not used for selection.

No EMA, ATR, swing/fractal, volume, regime, day-of-week, time-of-day subfilter, or new price threshold is introduced.

## Frozen diagnostics
For every horizon and major partition, report N for LATER_H2 and PRE_H2_FAILURE plus median feature values. Also report pooled-major medians and the signed median gap `(failure - H2)`.

Direction checks are predetermined:
- Failure-expected-higher: adverse_wick_r, adverse_close_r, wrong_side_close_fraction, higher_high_step_fraction, adverse_favorable_ratio.
- H2-expected-higher: favorable_wick_r, favorable_close_r, net_close_progress_r, lower_low_step_fraction, close_path_efficiency.

For each feature/horizon, report whether the expected separation direction is present independently in external, development, and reference_validation. No threshold is optimized and no feature is promoted to a trading rule in B27AW.

## Guardrails
- Synthetic causal-window assertions run before real-data output.
- Exact one-to-one frozen identity checks precede interpretation.
- No use of future H2/E20 information in feature construction; future outcome is used only as the diagnostic label.
- No intermediate horizon, feature, threshold, combination, classifier, or regime slice may be added after seeing results.
- Research only; live BBC unchanged.
