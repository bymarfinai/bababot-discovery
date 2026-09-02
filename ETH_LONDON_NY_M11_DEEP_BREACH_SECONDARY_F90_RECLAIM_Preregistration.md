# ETH London -> New York M11 Deep-Breach Secondary F90 Reclaim — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Test one causal hypothesis suggested by M10: after an executed **F90 EARLY_RECLAIM** entry suffers a deep completed-close breach, eventual breakout winners may differ from failures by their ability to perform a **secondary completed-close reclaim of F90**.

M11 is structural anatomy only. It installs no trading exit, stop, target, PnL, fee, slippage, runner, portfolio lock, or regime filter.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- Exact 95 M5 F90 EARLY_RECLAIM executed identities, as persisted/reproduced by M10.
- London H/L/R and M5 terminal outcome remain unchanged.
- Success remains strict completed 5m `close > H` before M5 terminal/session end.
- Deep-breach families are frozen to **F80 and F75 only**; no intermediate fractions may be added after inspection.

## Frozen event definitions
For each boundary independently:
1. `deep_breach` = first post-entry completed 5m candle with `close < boundary`, occurring before strict breakout completion.
2. `secondary_F90_reclaim` = first later completed 5m candle with `close > F90` after the deep-breach candle.
3. For eventual breakout winners, distinguish:
   - `RECLAIM_BEFORE_BO`: secondary F90 reclaim bar starts strictly before the strict-breakout bar;
   - `RECLAIM_ON_BO_BAR`: secondary F90 reclaim is first achieved on the strict-breakout bar itself;
   - `NO_RECLAIM_BEFORE_BO` otherwise.
4. For non-breakout cases, secondary reclaim is searched only until the frozen terminal/session end.
5. A reclaim cannot be known until its 5m candle completes.

## Frozen recovery checkpoints
For deep-breach cases only, evaluate **15 / 30 / 45 / 60 minutes after deep-breach candle completion**.

At each checkpoint, if the trade is still structurally alive and has not yet produced strict breakout, classify:
- `RECLAIMED_F90` if a secondary completed-close F90 reclaim has already completed;
- `NO_RECLAIM_F90` otherwise.

Report eventual strict-breakout probability from each checkpoint state.

## Required outputs
For F80 and F75, by external/development/reference_validation and pooled major:
- deep-breach N, winner N, non-winner N;
- secondary F90 reclaim rate among deep-breach winners;
- reclaim-before-breakout rate among deep-breach winners;
- reclaim-on-breakout-bar rate among deep-breach winners;
- secondary F90 reclaim rate among deep-breach non-winners;
- median/p75 breach->secondary-reclaim minutes;
- eventual breakout rate conditional on secondary reclaim vs no secondary reclaim;
- 15/30/45/60-minute recovery-state counts and eventual breakout rates.

## Frozen structural signature screen
A boundary is `SECONDARY_RECLAIM_SIGNATURE_SUPPORTED` only if:
1. pooled-major deep-breach N >= 30;
2. pooled-major deep-breach winner N >= 15 and non-winner N >= 10;
3. pooled winner secondary-reclaim rate >= 90%;
4. pooled non-winner secondary-reclaim rate <= 20%;
5. pooled separation >= 65 percentage points;
6. every major partition with >=5 deep-breach winners has winner reclaim rate >=85%;
7. every major partition with >=5 deep-breach non-winners has non-winner reclaim rate <=35%.

## Frozen recovery-deadline screen
A boundary/checkpoint pair is `NO_RECLAIM_DEADLINE_CANDIDATE` only if:
1. pooled `NO_RECLAIM_F90` checkpoint N >= 10;
2. pooled eventual-breakout rate among `NO_RECLAIM_F90` <= 30%;
3. every major partition with >=5 `NO_RECLAIM_F90` cases has eventual-breakout rate <=40%;
4. among deep-breach eventual winners, at least 80% have already reclaimed F90 by that checkpoint (winner recovery retention >=80%).

No deadline is authorized as a trading rule by M11; any candidate requires a separately preregistered economic execution test.

## Mandatory assertions
1. M10 95-row cohort and breakout outcomes reproduce exactly.
2. Deep breach must be known before any secondary reclaim.
3. `RECLAIM_BEFORE_BO` must have reclaim bar strictly before breakout bar.
4. No post-terminal/session data are used.
5. F80/F75 prices equal exact frozen London fractions.
6. Raw ETH 5m coverage >=99.5%.

Research only. Live BBC unchanged.
