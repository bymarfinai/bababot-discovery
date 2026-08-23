# B27BL — BTC 24H Temporal Transition Resolution Audit — Preregistration

## Purpose

Audit whether the ambiguity exposed by B27BH/B27BI/B27BJ/B27BK is better treated as a temporal `PENDING` state rather than forcing a final regime decision on the first completed 4H bar labeled SIDEWAYS.

This experiment is regime-state research only. It does **not** map regimes to LONG/SHORT, does not define an entry, stop, target, fee, WR, PF, PnL, session filter, or live trading rule.

## Frozen parent lineage

- Existing raw regime detector semantics remain exactly B27AG/B27BG: completed 4H UTC bars only; `SwingRegime(5, 0.5)`; BULL/BEAR/SIDEWAYS definitions unchanged.
- Exact B27BH directionally bracketed SIDEWAYS cohort must reproduce: **1,023 episodes = 527 same-direction RESUME + 496 opposite-direction TRANSITION; BULL-origin 532; BEAR-origin 491.**
- Reporting partitions remain `external`, `development`, and `reference_validation`; partition boundaries are reporting boundaries only and do not reset regime episodes.
- All seven calendar days remain eligible.

## Causal clock and temporal states

For every bracketed SIDEWAYS episode:

- `t0`: first completed 4H bar whose raw regime is SIDEWAYS; information becomes available only at that bar's completion time.
- At `t0`, the proposed conceptual state is **PENDING**. No outcome is inferred yet.
- `age=1` means one SIDEWAYS 4H interval has completed.
- At each subsequent completed 4H boundary, the raw detector is observed causally:
  - if raw state returns to the origin directional state, the episode resolves as `RESUME`;
  - if raw state becomes the opposite directional state, it resolves as `TRANSITION`;
  - if raw state remains SIDEWAYS, it remains `PENDING`.
- No future exit state may be used before its completed 4H bar becomes available.

## Frozen readouts

The audit will report, separately for BULL-origin and BEAR-origin and by major partition plus pooled major:

1. SIDEWAYS episode duration distribution.
2. Cumulative causal resolution by +4h, +8h, +12h, +16h, +20h, and +24h after the first SIDEWAYS bar.
3. Among episodes still PENDING after each age threshold, the eventual `TRANSITION` rate versus the unconditional transition rate at first SIDEWAYS.
4. Cause-specific resolution counts: same-direction RESUME versus opposite-direction TRANSITION at each SIDEWAYS age.
5. OOS-only (`external` + `reference_validation`) temporal readouts to ensure the finding is not development-only.

No first-bar or second-bar price/EMA feature threshold, classifier, probability cutoff, or decision tree will be selected in B27BL.

## Frozen promotion gate for the PENDING-state concept

`B27BL_TEMPORAL_PENDING_STATE_SUPPORTED` requires **all** of the following:

1. Identity/causality checks pass and the exact 1,023 B27BH cohort is reproduced.
2. In pooled OOS, at least **40%** of all episodes causally resolve by +8h, so PENDING is not merely an indefinite relabeling.
3. For **both BULL-origin and BEAR-origin**, pooled-OOS `P(TRANSITION | still PENDING after one full 4H SIDEWAYS interval)` must exceed the corresponding unconditional first-SIDEWAYS transition rate by at least **10 percentage points**.
4. The sign of that one-bar survival effect must be the same in **external** and **reference_validation** for both origins: remaining SIDEWAYS longer must not lower transition probability in either OOS partition.
5. At least **30 PENDING observations per origin** must remain in pooled OOS after one full SIDEWAYS interval, preventing a tiny-sample promotion.
6. At least **70%** of pooled-OOS episodes must be causally resolved by +12h. This bounds the practical duration of PENDING.

If any gate fails, frozen verdict is `B27BL_TEMPORAL_PENDING_STATE_NOT_SUPPORTED`.

## Interpretation boundary

A PASS supports only the **concept** that SIDEWAYS should initially be treated as a causal pending/transition state whose age carries information. It does not specify a production state machine, holding behavior, trading direction, or entry rule. A separate preregistered experiment is required to redesign/promote the actual detector.

If B27BL fails, no age threshold may be changed post hoc under this experiment ID.

Research only. Live BBC unchanged.
