# BNB/SOL IV-HOD/LOD Forward Reaction Validation v0 — Preregistration

## Objective

Validate prospectively whether the frozen IV/range level family from `IV_LEVEL_ENGINE_V0` identifies future local HOD/LOD-like reaction zones for BNBUSDT and SOLUSDT.

This is a forward shadow validation. No entry, SL, TP, leverage, or PnL is defined.

## Parent

- Engine signature: `0579e22b9bf36a5c55f496c8ee067edf73b7e6b6a8d635c4b461850094c8f34d`
- Method: `IV_LEVEL_ENGINE_V0`
- First frozen snapshot: 2026-09-24T02:36:56.134Z

## Snapshot cadence

- One causal snapshot each hour.
- Snapshot timestamp T freezes the complete level map before observing bars after T.
- Evaluation window: completed 5m BNBUSDT / SOLUSDT futures bars with open timestamps > T and <= T+60m.
- If data for the full 60m window is unavailable, the forecast remains PENDING and is not scored.

## Frozen level families

Primary non-diagnostic levels:
- IV_DAILY_LOWER / UPPER
- IV_WEEKLY_LOWER / UPPER
- HIST_DAILY_NORMAL_LOWER / UPPER
- HIST_WEEKLY_NORMAL_LOWER / UPPER
- HIST_WEEKLY_Q75_LOWER / UPPER

Diagnostic-only:
- SURFACE_WEEKLY_LOWER / UPPER

Confluence clusters are primary only when composed entirely from non-diagnostic levels.

## Side

- Any UPPER level is a candidate HOD/resistance reaction.
- Any LOWER level is a candidate LOD/support reaction.
- Confluence inherits UPPER or LOWER only when every member is same-side.

## Touch definition

A frozen level L is touched in the next 60m when the first completed 5m bar satisfies:

`low <= L <= high`.

The first such bar is the touch bar.

No nearest-price substitution.

## Reaction metrics

All price-distance metrics are expressed in basis points of L.

For UPPER/HOD candidates after first touch:
- penetration_bps_h = max(0, max_high_through_h - L) / L × 10,000
- favorable_reaction_bps_h = max(0, L - min_low_through_h) / L × 10,000
- close_rejected_h = final completed close through h < L

For LOWER/LOD candidates:
- penetration_bps_h = max(0, L - min_low_through_h) / L × 10,000
- favorable_reaction_bps_h = max(0, max_high_through_h - L) / L × 10,000
- close_rejected_h = final completed close through h > L

Fixed horizons after first touch:
- 15m
- 30m
- through the frozen 60m forecast endpoint

## HOD/LOD capture error

For an UPPER level:
- hour_extreme = maximum high in the full forecast window
- capture_error_bps = abs(hour_extreme - L) / L × 10,000

For a LOWER level:
- hour_extreme = minimum low in the full forecast window
- capture_error_bps = abs(hour_extreme - L) / L × 10,000

## Frozen descriptive capture bands

Report, do not optimize:
- <=25 bps
- <=50 bps
- <=100 bps

## Frozen reaction labels

A touched level is:

### CLEAN_REACTION_30
if at 30m after touch:
- favorable_reaction_bps >= 25
- favorable_reaction_bps > penetration_bps
- close_rejected = TRUE

### STRONG_REACTION_30
if:
- favorable_reaction_bps >= 50
- favorable_reaction_bps >= 1.5 × penetration_bps
- close_rejected = TRUE

### BREAK_THROUGH_30
if:
- penetration_bps >= 50
- penetration_bps > favorable_reaction_bps
- close_rejected = FALSE

Otherwise: MIXED_30.

These thresholds are frozen before any forward outcomes are scored.

## Confluence comparison

Primary research question:

Do primary confluence clusters react better than primary singleton levels?

Compare:
- touch rate;
- median capture_error_bps;
- CLEAN_REACTION_30 rate;
- STRONG_REACTION_30 rate;
- BREAK_THROUGH_30 rate;
- median favorable/penetration ratio.

No significance claim until >=30 touched primary confluence forecasts and >=30 touched primary singleton forecasts overall.

## Asset-specific reporting

BNB and SOL must be reported separately and pooled.

No pair-specific threshold changes in v0.

## De-duplication

Because hourly forecasts overlap:
- raw snapshot-level observations are retained;
- for headline daily statistics, same symbol + same side + same level-family touched within rolling 60m counts only once, keeping the earliest frozen forecast.
- confluence and singleton families are de-duplicated separately.

## Promotion gate

No strategy promotion until both conditions hold:

1. sample gate:
   - >=30 de-duplicated touched primary confluence forecasts overall;
   - >=15 touched confluence forecasts in each BNB and SOL.

2. quality gate:
   - confluence median capture_error <=100 bps;
   - CLEAN_REACTION_30 >=60%;
   - BREAK_THROUGH_30 <=25%;
   - confluence CLEAN_REACTION_30 exceeds primary singleton CLEAN_REACTION_30 by >=10 percentage points.

If the sample gate is not reached: `FORWARD_VALIDATION_ACCUMULATING`.

If sample reached but quality fails: `IV_HOD_LOD_V0_NOT_SUPPORTED`.

If both pass: `IV_HOD_LOD_V0_MECHANISM_SUPPORTED`.

This is still not a trading strategy; an entry/exit protocol would require a separate preregistration.
