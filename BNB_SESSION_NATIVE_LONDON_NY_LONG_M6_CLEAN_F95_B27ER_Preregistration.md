# B27ER — BNB Session-Native LONG Clean F95 Reclaim External Holdout Preregistration

## Purpose
Test whether the post-B27EQ concept of a **clean shallow F95 reclaim** is more stable than raw F95 reclaim when applied unchanged to the untouched **external** partition.

This milestone is structural only. It does not define TP, SL, fees, slippage, leverage, PnL, SHORT, H3, breakout-retest, August, or live integration.

## Data partitions
- Threshold derivation source: **development only (2022-01-01 to 2025-01-01)**.
- Holdout test: **external only (2020-01-01 to 2022-01-01)**.
- Reference-validation and August are not used to derive thresholds or tune the rule in this milestone.

## Upstream structure
Use the frozen B27EM London 08:00 local -> New York 09:30 local reference H/L/R and the existing causal K1 -> leave -> terminal state machine.

External integrity expected from B27EM:
- causal leaves = **63**
- upstream H2 = **45**
- upstream non-H2 = **18**

## Base entry rule
Raw F95 reclaim is frozen from B27EO/B27EP:
1. after causal K1 leave, a completed 5m candle has `low <= F95` and `close > F95`, where `F95 = L + 0.95R = H - 0.05R`;
2. terminal H2/opposite must not already have occurred;
3. entry is the next 5m open.

## Clean-reclaim hypothesis
Only two causal dimensions are allowed.

### Development-derived thresholds
Using **development F95 entries whose eventual outcome is H2**, calculate:
- `PATH_P75` = P75 of `pre_entry_max_depth_R`, where `pre_entry_max_depth_R = (H - minimum low from leave through reclaim signal bar) / R`.
- `RECLAIM_LOW_P75` = P75 of `signal_low_depth_R`, where `signal_low_depth_R = (H - reclaim-candle low) / R`.

No other feature may enter the clean rule.

### Frozen clean rule
A raw F95 entry is `CLEAN_F95` iff both:
- `pre_entry_max_depth_R <= PATH_P75`
- `signal_low_depth_R <= RECLAIM_LOW_P75`

The thresholds are computed mechanically from development H2 F95 entries before external results are evaluated. No threshold search, alternate percentile, or post-hoc adjustment is permitted.

## External evaluation
Report for both RAW_F95 and CLEAN_F95:
- eligible entries
- H2 count
- non-H2 count
- H2-after-entry rate
- Wilson 95% interval
- share of 45 upstream H2 captured
- median leave->entry
- median entry->H2
- median entry depth
- median and P75 post-entry MAE

Also report clean retention = CLEAN_F95 entries / RAW_F95 entries and delta H2 rate in percentage points.

## Preregistered support contract
The clean-reclaim hypothesis is **SUPPORTED** only if all are true on external:
1. CLEAN_F95 eligible N >= **8**;
2. CLEAN_F95 H2-after-entry rate improves by >= **5 percentage points** over RAW_F95;
3. CLEAN_F95 retains >= **50%** of RAW_F95 entries.

`STRONG_SUPPORT` additionally requires CLEAN_F95 H2-after-entry >= **90%** with N >= 8.

Otherwise status is `NOT_SUPPORTED` or `INCONCLUSIVE_LOW_N` if clean N < 8.

## Interpretation guardrail
H2-after-entry is a structural outcome rate, **not trading win rate**. No new entry rule is promoted solely from this milestone.

## Stop condition
Persist results and stop. Do not test F90/F85, alternate percentiles, time/body/wick filters, economics, August, SHORT, or live integration.
