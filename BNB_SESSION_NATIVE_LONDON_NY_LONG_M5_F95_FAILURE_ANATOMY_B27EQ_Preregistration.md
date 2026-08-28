# B27EQ — BNB Session-Native LONG F95 Failure Anatomy Preregistration

## Purpose
Diagnose the causal pre-entry anatomy of the already-observed frozen F95-reclaim cohort after B27EO/B27EP. This is **post-validation diagnosis**, not a new validation or promotion milestone.

## Cohort
Use only F95-reclaim entries already implied by the frozen B27EO rule in:
- development: 2022-01-01 -> 2025-01-01
- reference_validation: 2025-01-01 -> 2026-07-30

Expected integrity from prior milestones:
- development: 21 eligible F95 entries, 20 H2 / 1 non-H2
- reference_validation: 7 eligible F95 entries, 6 H2 / 1 non-H2
- combined: 28 entries, 26 H2 / 2 non-H2

August remains excluded. External is not added. No new holdout is opened.

## Frozen entry rule
F95 = L + 0.95R. After K1 causal leave, first completed 5m bar with low <= F95 and close > F95 is the reclaim signal; entry timestamp is the next 5m bar open, provided no H2/opposite terminal has already occurred and fill lies inside (L,H).

## Causal feature set
Only information fully known by the entry timestamp may be measured:
1. minutes_leave_to_signal / minutes_leave_to_entry
2. reclaim candle open_depth_R, low_depth_R, close_depth_R
3. reclaim candle range_R and body_R
4. reclaim candle body_ratio and close_position
5. reclaim_overshoot_R = (close-F95)/R
6. wick_below_F95_R = max(0,(F95-low)/R)
7. pre_entry_max_depth_R from H using all bars from leave_ts through reclaim candle
8. pre_entry_min_close_depth_R / max_close_depth_R over same causal window
9. pre_entry_bar_count
10. entry_depth_R

## Reporting contract
- Report H2 winner distribution (median, P25, P75, min, max) for every feature.
- Print the two failure rows exactly for the same features.
- For each failure/feature, flag whether it lies below winner min, above winner max, below winner P25, above winner P75, or inside winner IQR.
- Report features where **both failures are outside the winner IQR in the same direction** as descriptive leads only.
- Report features where a failure is outside the full winner min-max range as stronger descriptive anomalies, still not rules.

## Prohibitions
No threshold optimization, no new entry filter, no F90/F85 comparison, no TP/SL, no PnL/fees/slippage, no H3/breakout-retest, no SHORT, no August, no live integration, and no claim of trading WR.

## Stop
B27EQ ends after descriptive causal failure anatomy. Any candidate discriminator must be separately preregistered and tested later; B27EQ itself cannot promote one.
