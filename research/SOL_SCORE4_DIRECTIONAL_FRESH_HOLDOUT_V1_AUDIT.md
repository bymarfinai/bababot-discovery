# SOL Score-4 Directional Character — Fresh Holdout Run V1

This run executes the already-frozen rule from:

- branch: sol-score4-directional-anatomy-v2
- prereg: research/SOL_SCORE4_DIRECTIONAL_ANATOMY_V2_PREREG.md
- frozen BUY_SIDE rule:
  - time_to_fill_min <= 15
  - directional_improvement_range_units <= 0.21471170803
- SELL_SIDE remains auto-accepted.
- fresh cutoff: 2026-08-26 00:00 UTC.

No detector, entry, SL, exit, threshold, feature, gate, or sample rule is changed.

The purpose of this branch is only to rerun the frozen evaluator against newly available post-cutoff data.

Possible outcomes are exactly those already preregistered:
- SCORE4_DIRECTIONAL_CHARACTER_FROZEN_AWAITING_FRESH_HOLDOUT
- SCORE4_DIRECTIONAL_CHARACTER_VALIDATED_FRESH
- SCORE4_DIRECTIONAL_CHARACTER_FAILED_FRESH_HOLDOUT


## Data-horizon plumbing correction before fresh data are opened

The first workflow rerun revealed that the inherited raw-data loader itself was still hardcoded to:
`END = 2026-08-26 00:00 UTC`.

Therefore the first rerun did **not** expose any post-cutoff market data and cannot constitute a fresh-holdout result.

Before opening fresh data, the observation horizon is now frozen to:
**2026-09-21 00:00 UTC**

This correction changes only raw-data availability. It does NOT change:
- fresh cutoff;
- frozen BUY_SIDE rule;
- SELL_SIDE auto-accept rule;
- detector;
- entry;
- SL;
- exit;
- fresh sample gates;
- fresh quality gates.

Only completed UTC days before 2026-09-21 00:00 are eligible for this run.
