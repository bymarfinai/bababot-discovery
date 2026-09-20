# SOL Score-4 Directional Anatomy V2 — Preregistration

## Objective

Discover and freeze one causal directional-character gate for anatomy-score-4 setups.

Known retrospective problem:
- Score-4 SELL-side liquidity -> LONG has historically been much healthier.
- Score-4 BUY-side liquidity -> SHORT has historically been much weaker and dominated the 2026 pre-cutoff degradation.

This experiment does NOT assume "SHORT bad, LONG good" as the final rule.

Instead:
- all Score-4 SELL_SIDE setups remain accepted;
- BUY_SIDE Score-4 setups may be filtered only by one frozen causal pre-entry character selected from historical 2020-2024.

## Evidence status

The directional asymmetry was discovered using data through:
**2026-08-26 00:00 UTC**

Therefore:
- 2020-2024 = directional-character construction;
- 2025 = retrospective consistency only;
- 2026 entries before 2026-08-26 = retrospective consistency only;
- entries at/after 2026-08-26 = first eligible fresh holdout for the frozen directional character;
- no pre-cutoff result may be called independent validation.

## Frozen upstream stack

Detector:
- actionable structural-liquidity detector;
- anatomy score = 4 only.

Entry:
- GAP_25.

SL:
- static RECLAIM_EXTREME.

Primary economic diagnostic:
- structural-completion exit.

No TP optimization or stop modification is allowed.

## Causal features allowed for BUY_SIDE character selection

All are known no later than entry:

1. source_to_opposite_structure_range_units
2. approach_start_distance_to_level_range_units
3. reclaim_directional_body_range_units
4. reclaim_close_inside_range_units
5. time_to_fill_min
6. directional_improvement_range_units
7. initial_risk_range_units
8. structural_target_distance_range_units
9. structural_reward_r

No post-entry feature may enter the selector.

## Historical BUY_SIDE selector construction — 2020-2024 only

Population:
- score 4;
- BUY_SIDE only;
- filled GAP25 entries.

Outcome used for character quality:
- positive = STRUCTURAL_LIQUIDITY_EVENT;
- negative = reclaim failure / no-BOS outcome.

For each allowed feature, compute BUY_SIDE 2020-2024:
- q25
- q50
- q75

Create atomic conditions:
- feature <= quantile
- feature >= quantile

Candidate rules:
- exactly one atom; or
- conjunction of exactly two atoms from different features.

No side, year, session, hour, TP, MFE, MAE, or future path variable may be added.

## Historical eligibility gates

A BUY_SIDE candidate is eligible only if ALL are true:

1. selected N >= 5;
2. selected structural-event rate >= 60%;
3. structural-event lift vs unfiltered historical BUY_SIDE baseline >= +20 percentage points;
4. structural-completion mean realized R > 0;
5. structural-completion PF > 1.0.

Select exactly one eligible candidate by:

1. highest Wilson 95% lower bound of structural-event rate;
2. then highest structural-event rate;
3. then highest structural-completion mean R;
4. then larger N;
5. then fewer conditions;
6. then lexicographic rule text.

If no rule is eligible:
`NO_SCORE4_DIRECTIONAL_CHARACTER_CANDIDATE`

No threshold rescue is allowed.

## Frozen directional architecture

If a BUY_SIDE rule is selected:

- SELL_SIDE Score-4 -> ACCEPT
- BUY_SIDE Score-4 -> ACCEPT only if frozen selected rule passes
- otherwise -> REJECT

This creates one full directional-character detector.

The rule is frozen before 2025 / 2026 consistency metrics or post-cutoff data are evaluated.

## Retrospective consistency reporting

Apply the exact frozen architecture to:
- 2025;
- 2026 pre-cutoff.

For each period report:
- unfiltered Score-4 N/event rate/mean R/PF;
- accepted N/event rate/mean R/PF;
- rejected BUY_SIDE N/event rate/mean R;
- accepted BUY_SIDE N/event rate/mean R;
- SELL_SIDE N/event rate/mean R.

Retrospective consistency is considered supportive only if, in each period where accepted BUY_SIDE N >= 2:

1. accepted BUY_SIDE event rate >= unfiltered BUY_SIDE event rate;
2. accepted BUY_SIDE mean R >= unfiltered BUY_SIDE mean R.

Failure does NOT authorize rule modification.

Status after retrospective audit:
- `SCORE4_DIRECTIONAL_CHARACTER_FROZEN_RETROSPECTIVE_SUPPORT`, or
- `SCORE4_DIRECTIONAL_CHARACTER_FROZEN_RETROSPECTIVE_MIXED`.

Neither is validation.

## Fresh holdout protocol

Cutoff:
**2026-08-26 00:00 UTC**

Only entries with:
`entry_time >= cutoff`
are fresh for this exact rule.

Minimum sample:
1. total Score-4 fresh N >= 12;
2. accepted total N >= 8;
3. fresh BUY_SIDE N >= 5;
4. accepted fresh BUY_SIDE N >= 3;
5. fresh SELL_SIDE N >= 3.

Quality gates:

6. accepted total structural-event rate > unfiltered fresh Score-4 event rate;
7. accepted total structural-completion mean R > unfiltered fresh Score-4 mean R;
8. accepted BUY_SIDE structural-event rate > unfiltered fresh BUY_SIDE event rate;
9. accepted BUY_SIDE mean R > unfiltered fresh BUY_SIDE mean R;
10. accepted total mean R > 0;
11. accepted total PF >= 1.10.

If fresh sample minimums are not met:
`SCORE4_DIRECTIONAL_CHARACTER_FROZEN_AWAITING_FRESH_HOLDOUT`

If sample is sufficient and all quality gates pass:
`SCORE4_DIRECTIONAL_CHARACTER_VALIDATED_FRESH`

If sample is sufficient but any quality gate fails:
`SCORE4_DIRECTIONAL_CHARACTER_FAILED_FRESH_HOLDOUT`

No rule change is permitted after fresh data are opened.

## Interpretation

A fresh pass would mean:

> Score-4 is not intrinsically one uniform setup. SELL-side Score-4 remains broadly acceptable, while BUY-side Score-4 requires a specific pre-entry structural character before being treated as equivalent quality.

This experiment modifies only Score-4 quality classification.
Score-3 logic remains untouched.

