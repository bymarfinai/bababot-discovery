# SOL Score-3 SELL Missing-B Temporal Character V1 — Freeze / Holdout Protocol

## Objective

Validate one frozen structural character for the unresolved SOL Score-3 SELL_SIDE Missing-B cohort.

This experiment does **not** search for a new detector, entry, stop, TP, session, indicator, or numeric price threshold.

## Frozen cohort

Only events satisfying all of the following:
- side == SELL_SIDE
- anatomy_score == 3
- cond_A == 1
- cond_B == 0
- cond_C == 1
- cond_D == 1

Interpretation: the setup passes the existing A/C/D anatomy but fails B because the approach originates farther from the liquidity level than the frozen detector threshold.

## Discovery evidence already consumed

2020-2025 has already been used for character discovery and is therefore retrospective discovery data.

The frozen character is:

**TEMPORAL_CONFIRMATION_SCORE >= 2**

where:

`TEMPORAL_CONFIRMATION_SCORE = approach_bars + reclaim_delay_h1_bars`

Both terms are available causally no later than reclaim completion, before the existing Score-3 entry route is allowed to fill.

Structural interpretation:
- a far-origin approach is not enough by itself;
- the setup must accumulate at least two H1 confirmation bars across approach formation and/or reclaim delay;
- this is intended to distinguish established/absorbed liquidity from fast continuation through a level.

No alternative score, threshold, OR-rule, feature combination, or rescue rule may be selected after 2026 is opened.

## Frozen execution stack

For both selected and baseline cohorts:
- Entry: existing Score-3 FIVE_MIN_REVERSAL_BREAK route.
- Initial SL: existing RECLAIM_EXTREME.
- Exit: existing structural-completion / outcome-known-time exit.
- No adaptive TP.
- No session/hour filter.
- No indicator filter.
- No parameter tuning.

## Discovery reference metrics (2020-2025)

These are documentation only and are not validation:
- Baseline Missing-B N: 55.
- Frozen selected N: 34.
- Selected retention: 61.82%.
- Structural-event rate: 70.59%.
- Structural-event capture: 70.59%.
- Existing gross-winner retention: 71.88%.
- Gross WR: 67.65%.
- Gross mean R: +0.229R.
- Gross PF: 1.804.
- 10 bps mean net R / PF: +0.171R / 1.562.
- 20 bps mean net R / PF: +0.113R / 1.349.
- 2025 selected N: 7.
- 2025 structural-event rate: 71.43%.
- 2025 gross mean R / PF: +0.156R / 1.546.
- 2025 20 bps mean net R / PF: +0.018R / 1.054.

## Untouched 2026 holdout

Only after this file and the executable rule are committed may 2026 be evaluated.

Observation end is frozen at 2026-09-21 00:00:00 UTC.

### Sample gates
- baseline Missing-B N >= 5
- selected N >= 5
- selected retention vs baseline >= 40%

### Structural quality gates
- selected structural-event rate >= 65%
- selected structural-event rate > baseline structural-event rate

### Trading quality gates
Using the frozen existing execution stack:
- gross WR >= 60%
- gross mean R > 0
- gross PF >= 1.15
- 10 bps mean net R > 0
- 10 bps PF >= 1.10
- 20 bps mean net R >= 0
- 20 bps PF >= 1.00

## Verdict rules

If all sample, structural, and trading quality gates pass:

**MISSING_B_TEMPORAL_CHARACTER_HOLDOUT_SUPPORTED**

Otherwise:

**MISSING_B_TEMPORAL_CHARACTER_NOT_VALIDATED**

If the sample gates fail:

**MISSING_B_TEMPORAL_CHARACTER_HOLDOUT_INSUFFICIENT_SAMPLE**

No rule rescue, threshold adjustment, entry rerouting, TP/SL modification, or 2026 subgroup mining is allowed in V1 after the holdout is opened.
