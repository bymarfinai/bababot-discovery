# B27DG — F85 LONG Single-Position Portfolio — Preregistration

## Purpose
Re-score the currently interesting F85 LONG clock zones under the operational rule that only one BTC position may be open at a time. If a new eligible entry occurs before the currently accepted trade has closed, the new entry is skipped. No pyramiding and no replacement of an open trade.

## Frozen source
- B27DE persisted generic F85 LONG Same-Bar trade cases.
- B27DF persisted causal treatment result for ALT_0330.
- Existing fixed-E20 economics and exit timestamps are reused exactly; B27DG does not alter entries or exits.

## Frozen cohorts
Primary candidate portfolio:
1. `ALT_0330`: reference 03:30-09:00 UTC, execution 09:00-15:30 UTC, with the B27DF `TOUCH_FIRST_HALF` treatment only (touch <= 195 minutes after execution start).
2. `LONDON`: reference 08:00-13:30 UTC, execution 13:30-20:00 UTC, unfiltered Same-Bar baseline because B27DF found no beneficial filter.

Exploratory expanded portfolio, reported separately and not promoted:
- the primary two zones plus raw B27DE zones 05:30, 09:30, and 23:30 UTC reference starts, because these were the remaining positive-economics research-watch zones in the previous review.

## Single-position lock rule
Within each scoring partition:
1. Collect all eligible trades from the frozen cohort.
2. Sort by `entry_bar_start` ascending.
3. Accept the earliest trade when flat.
4. Set `locked_until = accepted exit_ts`.
5. Any later candidate with `entry_bar_start < locked_until` is skipped as `SKIP_OPEN_POSITION`.
6. Entry exactly at `locked_until` is allowed because the prior trade is already closed at that timestamp.
7. After close, the next chronological eligible candidate may be accepted.

No hindsight priority is allowed. A later trade cannot replace an earlier accepted trade because it eventually wins or has a better zone label.

If two zones have the exact same entry timestamp, deterministic frozen tie order is: `LONDON`, `ALT_0330`, `RAW_0530`, `RAW_0930`, `RAW_2330`. This is only a deterministic implementation rule and must be reported if any tie occurs.

## Reporting
For each partition and portfolio report:
- eligible candidates before lock
- accepted trades
- skipped due open position
- accepted WR, PF, expectancy, total net
- accepted trades contributed by each zone
- per-zone candidate -> accepted retention

Also report pooled-major totals for external + development + reference_validation.

## Guardrails
- No new filter search.
- No changed exit.
- No priority selection using outcomes.
- Primary portfolio and expanded exploratory portfolio must remain separate.
- August may be sparse and is descriptive only.
- Research only; live BBC unchanged.
