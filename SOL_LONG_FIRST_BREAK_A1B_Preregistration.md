# SOL LONG First-Break Visit Audit — A1B Preregistration

**Status:** PREREGISTERED after A1 failure and before A1B output generation.

## Trigger
A1 selected H2 in Development using conditional conversion (`break at Hj / sessions surviving to Hj`), but the frozen Development habitat itself contained many more first-break events at H1 than H2, while both opened OOS partitions reported H1 as the dominant visit.

This exposes a denominator problem: conditional hazard answers "if H1 did not break, how likely is H2 to break?" It does not directly answer the user's question "where does the first breakout actually happen most often?"

A1B is a **semantic / denominator audit**, not a new parameter search.

## Frozen inputs
A1B may use only the already-generated A1 selected event cohort:
- central: R240 / 18:00 UTC;
- clock support: R240 / 17:00 UTC;
- reference support: R180 / 18:00 UTC;
- partitions: Development, External, Reference Validation;
- exact A1 H1-H5 distinct-visit and completed-close breakout semantics.

No new reference, clock, H-number, threshold, entry, stop, TP, PnL, or filter may be searched.

## Primary statistic
For each role × partition:

`first_break_share_j = sessions whose first completed-close breakout occurs at Hj / sessions whose first completed-close breakout occurs at any H1..H5`

Also report:
- session incidence = first-break Hj count / sessions reaching H1;
- conditional conversion from A1 for context;
- median post-break extension;
- survivor funnel H1 -> H2 -> H3 -> H4 -> H5.

The **modal first-break visit** is the visit with the largest `first_break_share_j`, tie broken by lower visit number.

## Audit support rule
A1B supports a visit-order statement only if the same modal first-break visit appears in all nine frozen role × partition combinations (3 topology roles × 3 partitions).

If not, report instability. No substitution is allowed.

## Interpretation
A1B can answer only: **where does the first upside breakout most often occur in the frozen A1 topology?**

It cannot determine an entry. Entry research remains blocked until this denominator audit is resolved.

## Required outputs
- `SOL_LONG_FIRST_BREAK_A1B_Result.md`
- `SOL_LONG_FIRST_BREAK_A1B_SUMMARY.csv`
- `SOL_LONG_FIRST_BREAK_A1B_Status.txt`
