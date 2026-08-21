# BabaBot Research Registry — AMD/FVG H4 Track

## H4P1 — Session-anchored H4 AMD/FVG Path Map — DESCRIPTIVE COMPLETE

Frozen design:
- BTCUSDT USD-M perpetual;
- official completed Binance Futures 1H source, aggregated into session-anchored synthetic H4 bars so Asia 00UTC, London 07UTC, and New York 13UTC opens remain exact;
- accumulation = exactly three completed H4 bars before session open (12H context);
- manipulation = first H4 bar after session open only;
- exact opposite FVG = manipulation bar + next two H4 bars, same strict three-candle gap logic as the H1 AMD family;
- post-FVG-confirmation path observation = next six H4 bars / 24H;
- levels mapped: FVG NEAR edge, FVG FAR edge, manipulation extreme, opposite accumulation boundary;
- same-H4 multi-level hits remain explicitly SAME_BAR ambiguous;
- failure close through FAR and subsequent FAR retest tracked descriptively;
- no entry, TP, SL, RR, session/side selection, or parameter optimization.

Coverage: 2020-01-01 through 2026-08-19 completed source data, 58,152 official H1 rows.

Exact-H4-FVG counts:
- development: 100 / 915 manipulation events;
- reference validation: 43 / 417;
- external 2020-2021: 48 / 586;
- August diagnostic: 2 / 6.

Aggregate post-confirmation 24H path rates:
- FVG NEAR touch: development 70.00%, validation 69.77%, external 62.50%;
- FVG FAR touch: development 51.00%, validation 60.47%, external 45.83%;
- NEAR -> FAR conditional: development 72.86%, validation 86.67%, external 73.33%;
- manipulation-extreme revisit: development 25.00%, validation 27.91%, external 20.83%;
- opposite accumulation boundary reach: **development 82.00%, validation 88.37%, external 93.75%**;
- BOTH FAR + opposite boundary within 24H: development 35.00%, validation 51.16%, external 41.67%;
- failure close through FAR: development 39.00%, validation 48.84%, external 27.08%;
- failure-close -> FAR retest within next 24H: development 82.05% (32/39), validation 71.43% (15/21), external 61.54% (8/13).

Two-sided ordering among trajectories that visited BOTH FAR and opposite boundary:
- validation: OPP_FIRST 12, SAME_BAR 10, FAR_FIRST 0;
- external: OPP_FIRST 15, FAR_FIRST 3, SAME_BAR 2.
Thus when both sides are visited, the opposite accumulation boundary generally occurs before the full FVG penetration, not vice versa.

Top-path observation:
- validation most common path: `+3:OPP_BOUNDARY` (10/43 = 23.26%);
- external most common path: `+3:OPP_BOUNDARY` (15/48 = 31.25%).
This means a substantial fraction reaches the original opposite accumulation boundary in the first H4 candle after strict FVG confirmation.

Predeclared 80% transition flag result:
- FVG -> NEAR: validation69.77%, external62.50%;
- NEAR -> FAR: validation86.67%, external73.33%;
- failure close -> FAR retest: validation71.43%, external61.54%;
- `H4P1_80_TRANSITION_FOUND=NO` under the frozen preregistered transition list.

Important non-promotable but strong descriptive observation:
- opposite accumulation boundary reach is >80% in development, validation, and external (82.00% / 88.37% / 93.75%), with validation N43 and external N48.
- This transition was a required mapped output but was NOT included in the preregistered H4P1 80%-promotion list, so it must remain hypothesis-generating until an independent executable experiment is preregistered and tested.

Interpretation:
- H4 differs materially from the H1 path problem. The strict H4 AMD/FVG event is rare (~8-11% of manipulation events), but after it is confirmed the original opposite accumulation boundary is revisited/reached extremely often across time partitions.
- Full FVG penetration is much less common than opposite-boundary reach, and in trajectories that eventually visit both, the opposite boundary usually occurs first. This argues against treating the immediate post-FVG path as symmetric churn on H4.
- The next valid research question is executable geometry: whether a causal entry available after H4 FVG confirmation can capture the high-probability opposite-boundary move with net RR >=1:1 without recreating the late-entry/large-stop failure seen on H1.

Anti-rescue lock:
- do not alter H4 alignment, 3xH4 accumulation, first-H4 manipulation, exact FVG triplet, 24H horizon, or post-hoc isolate sessions/sides from H4P1;
- do not call the >80% opposite-boundary observation a tradable 80% edge until independently tested with frozen entry/SL/fee rules;
- any executable H4 strategy requires a new preregistered experiment.