# SOL Full-Character Long V1 — Characterization Preregistration

## Objective
Characterize the exact frozen V1 LONG candidate without changing its structure, trigger, entry, exit, or sample.

Frozen trade definition:
**H1 bullish impulse -> H1 new high -> impulse-origin demand -> first fresh H1 pullback to demand -> 5m demand-low sweep/reclaim -> next 5m open LONG.**

This stage is descriptive only. It does not promote, reject, filter, rescore, or retune trades.

## Frozen sample
- Rebuild the exact V1 structure using `sol_full_character_long_v1.py` unchanged.
- Keep only exact trigger `DEMAND_SWEEP_RECLAIM`.
- Expected authoritative sample from V1: N=109 over 2020-2024.
- 2025+ remains CLOSED.
- Fixed +60m diagnostic and 0.15% round-trip cost remain unchanged.
- No trade may be added or removed based on characterization values.

## Character dimensions to measure
### H1 impulse / structure
- impulse_bars
- impulse_displacement_pct
- impulse_displacement_range_units
- impulse_efficiency
- return_delay_h
- demand_zone_width_pct
- return_touch_depth_in_zone_units
- return_close_position_in_zone_units

### 5m sweep/reclaim trigger
- minutes_after_structure
- sweep_depth_pct_below_demand_low
- sweep_depth_in_zone_units
- reclaim_close_above_demand_low_in_zone_units
- reclaim_body_pct
- reclaim_range_pct
- reclaim_close_location
- reclaim_lower_wick_fraction
- entry_gap_from_trigger_close_pct
- entry_position_in_zone_units

### Realized post-entry path
- net60_pct
- mfe60_pct
- mae60_pct
- mfe_mae_ratio
- time_to_mfe_min
- time_to_mae_min
- clean_up_impulse

## Frozen descriptive comparisons
1. Winner vs loser, where winner means the already-frozen `net60_pct > 0` definition.
2. Per-year profiles for 2020, 2021, 2022, 2023, 2024.
3. Explicit 2022 profile versus combined 2021+2023+2024 profile because V1 already established 2022 as the material failure year; 2020 is excluded from that comparison only because V1 had N=3 there.
4. Spearman association of each pre-entry character feature with realized `net60_pct`.
5. For each pre-entry feature, report winner median, loser median, pooled IQR, and descriptive median separation normalized by pooled IQR.

## Interpretation rule
- This run may identify descriptive candidate dimensions for a future separately preregistered hypothesis.
- It may **not** create a threshold or filter from the same 109 trades.
- No feature, year, quantile, or combination discovered here may be called ready-to-trade.
- Any follow-up detector must be a new preregistered experiment with a frozen rule before its result is observed.

## Outputs
- enriched exact-trade dataset
- winner/loser profile
- yearly profile
- 2022-vs-positive-years profile
- feature association table
- result markdown
- status text

Official status for this stage is descriptive: `CHARACTERIZATION_COMPLETE_NO_FILTER_SELECTED` if execution succeeds.