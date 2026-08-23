# B27BT — BTC 24H Age-2 Causal Failed-Reclaim Anatomy — Preregistration

## Purpose

B27BS found that, inside the selected age-2 cumulative close-break cohort, intrabar reclaim cases had higher eventual TRANSITION rates than no-reclaim cases. However, B27BS conditioned on a 4H bar that ultimately closed beyond the frozen swing boundary, so using an intrabar re-break before that 4H close as an entry trigger would be lookahead-biased.

B27BT removes that conditioning completely.

Primary question:

> Among all bracketed SIDEWAYS episodes that are still alive through age 2 / 8h, does a fully causal 5m `break -> reclaim -> re-break` sequence around the frozen prior swing boundary identify eventual regime TRANSITION with stable OOS separation?

Structural anatomy only. No trade entry, stop, target, fee, WR, PF, PnL, leverage, session filter, or live BBC change is allowed.

## Frozen lineage

Reuse unchanged:
- BTCUSDT raw 5m loader from B21: exact identity 698,112 rows / 100% coverage;
- completed 4H `SwingRegime(5,0.5)` detector;
- B27BH bracketed SIDEWAYS episodes: 1,023 = 527 RESUME + 496 TRANSITION; BULL-origin 532; BEAR-origin 491;
- B27BN frozen prior swing boundary known at the immediately preceding completed directional state.

Primary cohort is NOT the B27BS close-break-selected cohort.

Primary cohort is every major-partition episode with:
- `boundary_available = True`;
- `n_intervals >= 2`, meaning SIDEWAYS survives through the second 4H SIDEWAYS interval.

## Age-2 raw 5m window

For each eligible episode, inspect only the raw 5m source interval that produces the second completed SIDEWAYS 4H state:
- start = `first_sideways_ts`;
- end = `first_sideways_ts + 4h`;
- exactly 48 continuous completed 5m bars.

No later 4H close, later 5m bar, or eventual outcome may be used to classify the intrabar path.

## Frozen boundary logic

BULL-origin:
- boundary = frozen latest confirmed swing low from the prior completed BULL state;
- `beyond` = completed 5m close `< boundary`;
- `safe/reclaim` = completed 5m close `>= boundary`.

BEAR-origin:
- boundary = frozen latest confirmed swing high from the prior completed BEAR state;
- `beyond` = completed 5m close `> boundary`;
- `safe/reclaim` = completed 5m close `<= boundary`.

## Frozen 5m path classes

Within the age-2 4H source interval, classify each episode into exactly one of:

1. `NO_BREAK`: no completed 5m close beyond the boundary.
2. `BREAK_NO_RECLAIM`: first completed close beyond boundary occurs, with no later completed reclaim close.
3. `BREAK_RECLAIM_NO_REBREAK`: break occurs, later completed reclaim occurs, but no later completed close beyond boundary.
4. `FAILED_RECLAIM`: break occurs, later completed reclaim occurs, then a later completed close beyond boundary occurs again.

For `FAILED_RECLAIM`:
- confirmation is the completion of the first re-break 5m bar after the first reclaim;
- `eligible_open_ts` is the next 5m bar open immediately after that confirmation;
- classification MUST NOT depend on how the containing 4H bar ultimately closes.

The eventual 4H close beyond/inside boundary may be reported only as a retrospective diagnostic and may not affect the frozen gate.

## Retrospective outcomes and timing

Eventual detector outcome remains:
- RESUME = return to origin direction;
- TRANSITION = reach opposite directional state.

For each FAILED_RECLAIM case report:
- first break position;
- first reclaim position;
- first re-break position;
- minutes break -> reclaim;
- minutes reclaim -> re-break;
- confirmation timestamp;
- next eligible 5m open timestamp;
- hours confirmation -> directional regime exit;
- whether the containing age-2 4H bar eventually closed beyond boundary, diagnostic only.

## Required summaries

For external, development, reference_validation, pooled OOS, and pooled major, separately for BULL-origin and BEAR-origin:
- age-2 eligible cohort N;
- N and eventual TRANSITION rate for all four path classes;
- baseline TRANSITION rate for the full eligible cohort;
- FAILED_RECLAIM N;
- P(TRANSITION | FAILED_RECLAIM);
- P(TRANSITION | non-FAILED_RECLAIM);
- FAILED_RECLAIM transition lift;
- causal timing medians/P25/P75.

## Frozen support gate

Call `B27BT_CAUSAL_FAILED_RECLAIM_SUPPORTED` only if ALL hold:

1. exact raw-data, detector, and parent identity reproduces;
2. every age-2 source interval has exactly 48 continuous 5m bars and every episode maps to exactly one path class;
3. pooled-OOS FAILED_RECLAIM N >=10 for each origin;
4. pooled-OOS `P(TRANSITION | FAILED_RECLAIM) >= 65%` for each origin;
5. pooled-OOS FAILED_RECLAIM-minus-non-FAILED_RECLAIM transition lift >=10pp for each origin;
6. external and reference_validation separately both have FAILED_RECLAIM N >=3/origin and positive FAILED_RECLAIM transition lift for both origins;
7. every FAILED_RECLAIM confirmation is strictly causal, and its next 5m eligible open occurs before the episode's eventual directional regime exit;
8. containing-4H final-close status is not used in path classification or gate logic;
9. no trading/economic/live BBC rule is changed.

Otherwise call `B27BT_CAUSAL_FAILED_RECLAIM_NOT_SUPPORTED`.

## Interpretation boundary

A supported result validates only a causal regime-transition discriminator and the existence of a post-confirmation observation window. It does not authorize a trade. Any actual entry price, invalidation, target, or economics requires a new preregistered experiment.

Research only. Live BBC unchanged.
