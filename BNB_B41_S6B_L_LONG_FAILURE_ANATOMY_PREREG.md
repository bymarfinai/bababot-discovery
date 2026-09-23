# BNB B41-S6B-L — LONG Failure Anatomy Preregistration

## Objective

Explain why the frozen B41 LONG setup fails after entry and identify causal precursor families that separate eventual +180m winners from losers.

This stage is **anatomy only**. It does not define or optimize a stop.

## Frozen parent

- B41-S5 signature: `5f2e2977c746c47b6c16eda35c72afc7993fe123713f5b011ad281c1317f5241`
- B41-S6 signature: `cd192358bb7b294fb3f581aa1e887aa7f4de97a4995dae7866b1a440fe3561fc`
- Setup: LOWER Q80 + TF60 C2_RECLAIM_AFTER_CLOSE -> LONG
- Entry: market at TF60 detector close
- Outcome label: frozen detector+180m aligned outcome >0 = WINNER; <=0 = LOSER.
- DEV: 2022-2024.
- REF: 2025-2026.

## Fixed causal snapshots

Measure only information known by:
- +15m
- +30m
- +45m
- +60m

after LONG entry.

No later information is used in a snapshot.

## Frozen risk-oriented features

All continuous features are oriented so **higher = more failure risk**:

1. `entry_drawdown`: (entry - current close) / wall_distance
2. `below_wall_depth`: max(0, wall - current close) / wall_distance
3. `mae_so_far`: maximum adverse excursion from entry to snapshot
4. `lack_mfe`: negative of maximum favorable excursion so far
5. `below_wall_fraction`: fraction of completed 5m closes below Q80
6. `max_consecutive_below_wall`
7. `final_consecutive_below_wall`
8. `failed_reclaim_count`: inside->below-wall transitions after a reclaim
9. `lower_low_pressure`: how far second-half low extends below first-half low, normalized
10. `down_slope_3`: negative 3-bar close slope, normalized

Binary risk features:
11. `final_below_wall`
12. `detector_extreme_touched`
13. `detector_extreme_close_breached`

No thresholds on these features are searched in S6B-L.

## DEV nomination

For each snapshot/feature:

Continuous feature is DEV_NOMINATED if:
- DEV winners >=30 and DEV losers >=20;
- failure AUC >=0.60.

Binary feature is DEV_NOMINATED if:
- DEV winners >=30 and DEV losers >=20;
- loser rate - winner rate >=15 percentage points.

AUC treats LOSER as positive class and higher feature value as more failure-risk.

## REF validation

A DEV-nominated continuous feature is REF_VALIDATED if:
- REF winners >=20 and REF losers >=15;
- failure AUC >=0.55.

A DEV-nominated binary feature is REF_VALIDATED if:
- REF winners >=20 and REF losers >=15;
- loser rate - winner rate >=10 percentage points.

No non-nominated feature may be promoted after REF is observed.

## Earliest precursor family

For reporting only, the earliest snapshot containing at least one REF_VALIDATED DEV nomination is the earliest stable precursor horizon.

This does **not** become an SL rule.

## Detector-extreme breach anatomy

Separately, for S6 `S5_DETECTOR_EXTREME_CLOSE5` breach events:
- false breach = baseline WINNER that breached;
- true failure breach = baseline LOSER that breached.

Describe:
- time-to-breach;
- pre-breach close position vs wall;
- pre-breach MAE/MFE;
- pre-breach below-wall fraction;
- prior reclaim/failure counts.

Because REF breach cohorts are small, this section is descriptive only and cannot promote a rule.

## Gate

- If at least one DEV-nominated precursor validates on REF -> `LONG_FAILURE_PRECURSOR_FOUND`.
- Otherwise -> `NO_STABLE_LONG_FAILURE_PRECURSOR`.

The next step, if supported, is S6C-L rule construction with a fresh preregistered rule; S6B-L itself does not choose an exit threshold.
