# B27BD — BTC NY -> Post-NY Off-Session SHORT Audit — Preregistration

## Question
Does the current leading SHORT architecture behave better in the previously untested post-New-York/off-session block than in the London->New York open-session lineage?

## Frozen time geometry
- BTC trades 24/7; `market closed` here is operationally defined as the unassigned post-NY block in the current UTC session map.
- Source session: New York 13:30-20:00 UTC, weekdays only.
- Source High/Low freeze only after 20:00 UTC.
- Observation/trading block: 20:00-24:00 UTC of the same UTC weekday.
- Complete source and observation windows only.
- Partitions remain the existing B22B partitions; partition boundaries are not state resets.

## Frozen SHORT structure
Using the frozen NY High H, Low L, and R=H-L:
1. Find first distinct valid Low retest episode in 20:00-24:00: `low <= L` and `close >= L`.
2. Before Low retest #1, any prior High visit (`high >= H`, `close <= H`) disqualifies OPP0 purity. A strict close outside the range before Low #1 terminates the day.
3. Consecutive Low-touching bars are one episode.
4. Require a causal leave after Low retest #1.
5. Require a second distinct valid Low retest #2. A strict completed close `< L` is breakdown, not retest #2.
6. Consecutive bars belonging to retest #2 are one episode.
7. Require causal leave after retest #2; F15 becomes eligible from the next raw 5m bar.
8. Entry is a resting SHORT at `F15 = L + 0.15R`, only if filled strictly before the next Low revisit or a strict completed close `> H`.
9. No retest #3 is required after entry; direct breakdown is allowed.

## Frozen economics
- Entry: F15.
- Hard resting stop: D30 from entry = `entry + 0.30R`.
- Stop active intrabar from fill bar.
- If hard stop and E20 occur in the same 5m bar, stop wins conservatively.
- E20_DOWN = `L - 0.20R`.
- Fill bar cannot activate E20; activation begins from a later raw 5m bar.
- E20 is not TP. On E20 activation, 100% of position remains open.
- From activation, E20 becomes the resting profit ceiling from the next causal logic state; gap/open at or above ceiling exits at actual open, otherwise high touching ceiling exits at ceiling.
- Strict 3-bar pivot highs below the current ceiling may ratchet the ceiling down; ratchet is causal and never rises.
- No lower fixed TP.
- Time exit: exact 00:00 UTC open.
- Notional $500; fee $0.40, identical to B27BC.

## Raw off-session diagnostic
For every complete weekday source+observation pair, independently report:
- 20:00 open -> 23:55 close return sign and mean/median bp;
- whether completed 5m close breaks above frozen NY H;
- whether completed 5m close breaks below frozen NY L;
- first strict boundary close-break side, with NO_BREAK if neither.
This diagnostic does not select or modify the SHORT setup.

## Frozen support gate
The time-shift hypothesis is `ROBUST_SUPPORTED` only if the F15/D30 cohort has:
1. pooled-major expectancy > 0;
2. pooled-major PF >= 1.20;
3. external, development, and reference_validation each have N >= 5;
4. each major partition expectancy >= 0 and PF >= 1.00.
Otherwise status is `NOT_ROBUST` even if pooled PnL is positive.

## Prohibitions
- No regime/EMA/swing filter.
- No F05/F10/F20 or other entry-zone search.
- No D25/D35 or other stop search.
- No activation threshold search.
- No candle-pattern/confirmation rule.
- No weekends in this audit; weekend-closed-market behavior is a separate experiment if needed.
- No live BBC changes.

## Required audit assertions
- 5m source rows = 698,112 and coverage = 100%.
- NY source session has 78 raw 5m bars; post-NY block has 48 bars for every included day.
- H > L for all included days.
- F15 and D30 geometry exact.
- Retest episodes are distinct and consecutive touch bars collapse into one visit.
- Touch #2 must precede post-touch2 leave; leave must precede F15 fill.
- F15 fill must be strictly before next Low revisit/opposite break.
- No future event is used to establish entry eligibility.

Research only. Live BBC unchanged.
