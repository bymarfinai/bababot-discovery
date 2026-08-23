# B27BS — BTC 24H Age-2 Close-Break 5m Acceptance Anatomy — Preregistration

## Purpose

B27BR found that cumulative 4H **close-break by SIDEWAYS age 2 / 8h** was a stronger diagnostic than wick-break, although close-break was secondary-only and could not rescue B27BR.

B27BS therefore preregisters a new microstructure question before examining 5m behavior:

> Within the frozen age-2 cumulative close-break cohort, does failure to reclaim the frozen swing boundary after the first 5m close-break inside the decisive 4H bar identify eventual regime TRANSITION more strongly than an intrabar reclaim?

This is structural anatomy only. No trade entry, stop, target, fee, WR, PF, PnL, session filter, or live BBC change is allowed.

## Frozen parent lineage

Reuse unchanged:
- raw BTCUSDT 5m source identity from B21: 698,112 rows / 100% coverage;
- completed 4H `SwingRegime(5,0.5)` detector;
- B27BH bracketed SIDEWAYS episodes;
- B27BN frozen prior swing boundary;
- B27BR age-2 cumulative close-break cohort.

Mandatory age-2 close-break cohort identity across major partitions:
- BULL-origin: 95 total = external 40 + development 29 + reference_validation 26; pooled OOS 66;
- BEAR-origin: 56 total = external 19 + development 23 + reference_validation 14; pooled OOS 33.

The cohort contains episodes with `n_intervals >= 2`, boundary available, and first 4H close-break age <=2.

## Decisive 4H close-break bar

Use the first SIDEWAYS 4H interval whose completed close is beyond the frozen boundary.

For BULL-origin:
- frozen boundary = prior BULL latest confirmed swing low;
- a 5m close-break is `close < boundary`.

For BEAR-origin:
- frozen boundary = prior BEAR latest confirmed swing high;
- a 5m close-break is `close > boundary`.

The decisive 4H source interval contains exactly 48 completed 5m bars and is fully known when its 4H close confirms the close-break.

## Frozen 5m features

Inside the decisive 4H source interval:

1. `first_break_pos`: 1..48 position of the first 5m close beyond the frozen boundary.
2. `reclaim_after_break`:
   - BULL-origin: any later 5m close `>= boundary` after first break;
   - BEAR-origin: any later 5m close `<= boundary` after first break.
3. `NO_RECLAIM`: no such later reclaim before the decisive 4H bar completes.
4. `acceptance_share`: fraction of 5m closes from the first break through bar end that remain beyond the boundary.
5. `final_acceptance_streak`: number of consecutive 5m closes ending the 4H bar that remain beyond the boundary.

No threshold on acceptance share, streak length, break timing, ATR, excursion, or distance may be optimized in B27BS.

## Primary outcome

Eventual detector outcome remains retrospective only:
- RESUME = return to origin direction;
- TRANSITION = reach opposite directional state.

For external, development, reference_validation, pooled OOS, and pooled major, report separately by origin:
- cohort N;
- NO_RECLAIM N and RECLAIM N;
- P(TRANSITION | NO_RECLAIM);
- P(TRANSITION | RECLAIM);
- transition lift;
- median/P25/P75 first-break position, acceptance share, and final acceptance streak by outcome.

## Frozen support gate

Call `B27BS_5M_CLOSE_BREAK_ACCEPTANCE_SUPPORTED` only if ALL hold:

1. exact raw-data/detector/parent/cohort identity reproduces;
2. every decisive 4H source interval contains exactly 48 continuous 5m bars and at least one 5m close-break;
3. pooled-OOS NO_RECLAIM N >=10 and RECLAIM N >=10 for each origin;
4. pooled-OOS `P(TRANSITION | NO_RECLAIM) > P(TRANSITION | RECLAIM)` for both origins;
5. pooled-OOS NO_RECLAIM-minus-RECLAIM transition lift >=10pp for both origins;
6. the same lift sign is positive in external and reference_validation separately for both origins, with >=3 observations in each compared cell;
7. all 5m features use only the decisive 4H source interval and no later price action;
8. no trading/economic or live BBC rule is changed.

Otherwise call `B27BS_5M_CLOSE_BREAK_ACCEPTANCE_NOT_SUPPORTED`.

## Interpretation boundary

A supported result would validate only a causal intrabar acceptance/reclaim discriminator after an age-2 frozen-boundary close-break. It would not yet authorize a trade. Any entry geometry would require a new preregistered experiment.

Research only. Live BBC unchanged.
