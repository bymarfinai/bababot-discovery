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
