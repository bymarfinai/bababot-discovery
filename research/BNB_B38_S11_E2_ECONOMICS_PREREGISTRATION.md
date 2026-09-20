# BNB B38-S11 — E2 Structural Economics Matrix

**Scientific identity:** `BNB_B38_S11_E2_ECONOMICS_V1`

## Purpose

Keep the B38-S10 E2 entry character fully frozen:

`demand touch -> reclaim -> one completed proximal hold -> break above max(reclaim_high, hold_high) -> entry`

Only the structural SL reference and structural target realization are varied in a small preregistered matrix.

No detector change, no session filter, no threshold scan, no trade-selection filter.

## Population

Exact E2 entries from B38-S10:
- DEV = 2022-2024
- REF = 2025 through final available 2026 bar

Every E2 entry remains in the candidate population unless its candidate target is unavailable.

## Frozen SL geometries

### SLa TOUCH_TO_ENTRY_LOW
Lowest 15m low from first touch through E2 entry.

This is the B38-S10 SL reference.

### SLb RECLAIM_TO_ENTRY_LOW
Lowest 15m low from reclaim candle through E2 entry.

This asks whether pre-reclaim sweep history should stop defining risk once reclaim+hold+break has completed.

No percentage buffers are used.

## Frozen invalidation mechanics

### TOUCH
Loss when exact 5m low first touches the selected SL reference.

### CLOSE15
Loss when a completed 15m candle first closes strictly below the selected SL reference.

For CLOSE15:
- target may be touched intrabar on completed 5m bars before the invalidating 15m close;
- realized loss R uses the invalidating 15m close price, not a synthetic -1R.

## Frozen target geometries

### T1 STRUCTURAL_TP1
Nearest already-known overhead structural objective at E2 entry using the exact B38-S3 objective ladder.

### T2 CAPPED_AT_1ZW
`min(structural TP1, demand_high + 1*demand_width)`, but only if this target remains above entry.

If +1ZW is already below/equal entry, retain structural TP1 rather than creating an invalid below-entry target.

This candidate is based on the already-observed S8 target-path mismatch finding. It is not a new threshold search.

## Preregistered candidate matrix

1. `A_TOUCH_LOW__TOUCH__TP1`
2. `B_TOUCH_LOW__TOUCH__CAP1ZW`
3. `C_TOUCH_LOW__CLOSE15__TP1`
4. `D_TOUCH_LOW__CLOSE15__CAP1ZW`
5. `E_RECLAIM_LOW__TOUCH__TP1`
6. `F_RECLAIM_LOW__TOUCH__CAP1ZW`
7. `G_RECLAIM_LOW__CLOSE15__TP1`
8. `H_RECLAIM_LOW__CLOSE15__CAP1ZW`

## Evaluation

For each period and candidate report:
- plans / resolved / ambiguous / unresolved;
- W/L;
- WR;
- median winning R;
- expectancy R;
- total R;
- profit factor;
- max loss streak;
- max cumulative-R drawdown;
- baseline E2 WIN retention;
- baseline E2 WIN -> LOSS conversions;
- baseline E2 LOSS -> WIN conversions.

Also report year splits:
- 2022
- 2023
- 2024
- 2025
- 2026*

## Interpretation gate

S11 is development/reference characterization only.

A candidate is structurally interesting if it can simultaneously:
- maintain approximately >=70% WR in DEV and REF;
- keep positive expectancy in DEV and REF;
- keep PF >1 in DEV and REF;
- avoid large baseline-WIN destruction.

No candidate is called validated.

## Stop rule

Do not:
- add filters;
- optimize numeric thresholds;
- alter E2 entry;
- alter demand detector;
- choose mode subsets;
- add sessions/indicators/derivatives;
- hide adverse close-invalidation losses.
