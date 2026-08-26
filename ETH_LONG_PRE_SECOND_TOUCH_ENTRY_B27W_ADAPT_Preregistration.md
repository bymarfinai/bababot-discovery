# ETH LONG B27W-Adapt — Pre-Second-Touch Retracement Entry — Preregistration

## Purpose
Adapt the BTC B27W entry-discovery milestone to ETHUSDT using the cohort selected by ETH B27Q-Adapt.

Frozen structural cohort from the preceding milestone:
- transition: LONDON_TO_NEWYORK
- side: LONG
- K1
- OPP0

Structural DNA remains:
first distinct visit to completed previous-session High -> causal leave from that visit -> retracement entry before High Arrival #2 -> evaluate whether price returns to High before opposite Low close-break/session end.

## What is pair-specific here
Unlike the exact BTC transplant, the retracement fraction is re-discovered for ETH.

Broad first-pass grid, measured from previous-session Low=0 to High=1:
- F95, F90, F85, F80, F75, F70, F65, F60, F55, F50.

This grid is frozen before the ETH B27W-Adapt result. No level below F50 is inspected in this run.

Boundary rule: if F50 is the selected deepest passing level, it is treated as a lower-boundary hit rather than a final optimum; a separately preregistered extension must test deeper levels before locking the ETH entry fraction.

## Event chronology
- H/L are the completed London High/Low and are frozen before New York.
- The B27Q-Adapt K1 bar is the first High-visit bar.
- Consecutive High-touch bars belong to the same first-touch episode.
- A causal leave requires a completed 5m bar that is not a High touch and has not strict-close broken H or L.
- Entry eligibility starts on the next 5m bar after that leave bar completes.
- H2 is the first later 5m bar with high >= H, including a breakout-arrival.
- The H2 bar itself is never entry-eligible.
- A close < L before H2 is opposite-break failure.
- If the same terminal bar both reaches H and closes < L, classify it ambiguous; earlier entries remain valid but that terminal is not awarded as H2.
- No future terminal event may retroactively veto an entry that was valid earlier.

## Outputs
For every partition and fraction:
- K1 setup count
- clean-window count
- fills before H2
- fill rate
- H2 target-hit rate among fills
- median minutes entry->H2
- reward-to-H as fraction of prior London range
- median / P10 minimum post-entry fraction
- median adverse excursion in range units

Persist one row per window and one row per fraction candidate.

## Screen / selection
A fraction passes only if the exact same fraction has in external, development, and reference_validation:
- >=30 pre-H2 fills in each partition; and
- >=70% H2 target-hit rate among fills in each partition.

Among passing fractions, select the deepest (lowest fraction) because it offers the largest geometric reward back to H while retaining the frozen quality gate. Ties are broken by highest minimum partition hit rate, then highest total fills.

If no level passes, do not tune stops/exits to rescue it.
If the selected level is F50, run a preregistered lower-boundary extension before advancing to MAE.
Otherwise advance to the ETH adaptation of B27X (winner MAE / stop-distance audit).

No stop, TP, runner, EMA, ATR, volume, candle-shape, or regime tuning in this milestone. Research only.