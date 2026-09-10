# ETH Discovery 2 Reset — G2 Boundary Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Parent evidence
G1 supported a new ETH-native structural geometry at:
- side: LONG;
- reference start: 01:30 UTC;
- reference duration: 180m;
- execution horizon: 480m.

However, G1 selected the minimum tested reference duration (180m) and maximum tested execution horizon (480m). Therefore G1 established the clock/side family but did not fully localize the duration coordinates.

G2 is a boundary-refinement experiment only. It does not test entries, retests, TP, SL, leverage, fees, PnL, or any old Z5 L06 rule.

## Scientific question
> With the G1-supported LONG side and 01:30 UTC reference-start clock frozen, where do ETH's reference duration and execution horizon localize when both previously-open boundaries are surrounded by finer interior and sentinel coordinates?

The purpose is to determine whether R180/E480 was merely a coarse-grid edge or part of a stable pair-native duration region.

## Data and historical partitions
Identical to G1:
- ETHUSDT Binance Futures raw 5m.
- Coverage gate >=99.5%.
- External: 2020-01-01 to 2022-01-01.
- Development: 2022-01-01 to 2025-01-01.
- Reference Validation: 2025-01-01 to 2026-07-30.
- August 2026 is not used for selection or replication.
- Full reference + execution window must lie inside one partition and contain every expected 5m bar.
- Weekend exclusion follows the frozen G1 execution-start weekday rule.

## Frozen coordinates
Fixed from G1:
- direction = LONG only;
- reference start = 01:30 UTC (08:30 WIB).

### Reference-duration grid
- 60m
- 90m
- 120m
- 150m
- 180m
- 210m
- 240m
- 270m
- 300m

Step = 30m. R60 and R300 are explicit outer sentinels; they are not privileged or excluded from ranking.

### Execution-horizon grid
- 300m
- 360m
- 420m
- 480m
- 540m
- 600m
- 660m
- 720m
- 780m

Step = 60m. E300 and E780 are explicit outer sentinels; they are not privileged or excluded from ranking.

Total Development candidates = 9 × 9 = **81**.
The G1 coordinate R180/E480 is included as an ordinary comparator.

## Frozen structural event grammar
Exactly the G1 pressure-event grammar is reused without modification:
- H = maximum reference high; L = minimum reference low; R = H-L.
- strict closes outside H/L are evaluated before touch counting;
- a touch requires intrabar reach while completed close remains inside/on the reference range;
- a bar touching both boundaries while closing inside is ambiguous;
- LONG signal is the first HIGH-side visit with zero prior LOW-side visit and no prior strict breakout;
- after signal, terminal state is first strict close above H (same-side continuation), first strict close below L (opposite invalidation), ambiguous terminal, or NO_BREAK at execution end.

This remains a structural diagnostic, not a trade-entry rule.

## Metrics
For every candidate report the same G1 metrics:
- complete sessions;
- signal count/rate;
- same-side, opposite, ambiguous, and no-break counts;
- continuation rate;
- resolved same-side rate;
- Wilson 95% lower bound of continuation rate;
- median minutes signal→same-side continuation;
- four chronological Development blocks.

## Development gate
Unchanged from G1. A candidate must satisfy ALL:
- >=80 Development signals;
- continuation rate >=75%;
- resolved same-side rate >=80%;
- Wilson 95% lower bound >=65%;
- >=3 of 4 chronological Development blocks each have >=15 signals, continuation >=68%, and resolved same-side >=75%.

## Local duration stability
Only duration coordinates vary in G2. For each candidate, one-step orthogonal neighbors are:
- reference duration ±30m where present, same execution horizon;
- execution horizon ±60m where present, same reference duration.

A neighbor is supportive under the unchanged G1 soft-support gate:
- >=60 Development signals;
- continuation >=70%;
- resolved same-side >=77%.

Local-stability requirement:
- at least 60% of available orthogonal neighbors supportive;
- and at least 2 supportive neighbors.

This means an isolated duration maximum cannot be selected.

## Development-only selection
Among candidates passing both Development and local-stability gates, rank lexicographically using the same substantive priorities as G1:
1. highest Wilson 95% lower bound;
2. highest minimum qualified Development-block continuation rate;
3. highest overall continuation rate;
4. highest resolved same-side rate;
5. highest signal count;
6. shortest median time to continuation;
7. lower total span (reference + execution);
8. shorter reference duration;
9. shorter execution horizon.

External and Reference Validation remain unopened during selection.

## Boundary-localization rule
The Development-selected winner is considered **localized** only if it is not on any outer sentinel boundary:
- reference duration must be strictly between 60m and 300m; and
- execution horizon must be strictly between 300m and 780m.

If the top eligible Development candidate lies on R60, R300, E300, or E780, status is `ETH_DISCOVERY2_RESET_G2_BOUNDARY_STILL_OPEN`. Holdouts are not used to rescue or override this result. A further separately preregistered boundary extension would then be required.

This rule prevents declaring an optimum merely because the search window ended.

## Historical replication
Only if the Development winner is localized, freeze it unchanged and open both historical holdouts.

SUPPORTED requires BOTH External and Reference Validation independently to satisfy the unchanged G1 replication gate:
- >=40 signals;
- continuation >=70%;
- resolved same-side >=78%;
- same-side count > opposite count;
- Wilson 95% lower bound >=58%.

No holdout may select a different duration or rescue a failed candidate.

## Status rules
- no Development/local-stability candidate: `ETH_DISCOVERY2_RESET_G2_NO_DEV_CANDIDATE`;
- top Development candidate on an outer sentinel: `ETH_DISCOVERY2_RESET_G2_BOUNDARY_STILL_OPEN`;
- localized Development candidate but either holdout fails: `ETH_DISCOVERY2_RESET_G2_CANDIDATE_NOT_REPLICATED`;
- localized candidate and both holdouts pass: `ETH_DISCOVERY2_RESET_G2_SUPPORTED`.

Only a SUPPORTED G2 result freezes the duration geometry for downstream ETH structure discovery.

Research/shadow only. No live promotion.