# B27AF — BTC London -> New York F85/F15 Post-Fill Path Anatomy — Preregistration

**Status:** PREREGISTERED. Diagnostic only; no parameter tuning or promotion.

## Question
Why does the exact mirrored SHORT F15 cohort lose more paths before H2 than the LONG F85 cohort, despite similar K1->clean-window and clean-window->fill geometry?

Frozen cohorts:
- LONG: B27W `F85`, filled before H2/terminal.
- SHORT: B27AD `BLIND_F15`, filled before H2/terminal.
- Transition: London -> New York, K1 OPP0, raw 5m.

No entry, target, stop, session, timeframe, or detector parameter changes are allowed.

## Causal path window
For each fill:
- `entry_bar_start` is the raw 5m bar in which the resting F85/F15 limit filled.
- The completed **fill-bar close** is valid post-fill information because the limit touch occurs intrabar before that bar completes.
- High/low of the fill bar are NOT used for post-fill MAE/MFE because part of that range may precede the fill.
- Full OHLC path diagnostics begin on the next raw 5m bar.
- The pre-terminal path ends strictly before the H2 bar, opposite-break terminal bar, or NY session-end open.
- H2 remains a milestone only.

## Direction-normalized coordinate
Let `R = H-L` and `s = +1` for LONG, `-1` for SHORT.

For a close `C`, directional progress from entry is:
`z_close = s * (C-entry)/R`.

Positive = intended direction; negative = adverse direction for both sides.

## Frozen diagnostics per filled trade
1. H2 success/failure and terminal type.
2. Fill-bar close progress in R.
3. Whether fill-bar close is already on the wrong side of entry (`z_close < 0`).
4. Pre-terminal wrong-side close rate, including fill-bar close and every later completed close strictly before terminal.
5. Maximum consecutive wrong-side completed closes.
6. Number of wrong-side close episodes (contiguous runs count once).
7. Maximum adverse **close** excursion in R.
8. Maximum favorable close excursion in R.
9. Maximum adverse **wick** excursion from bars strictly after the fill bar and before terminal.
10. Fraction of the mirrored 0.50R entry-to-invalidation distance consumed by adverse wick excursion. LONG F85->F35 and SHORT F15->F65 are both exactly 0.50R.
11. Minutes from fill-bar start to H2/terminal.
12. Whether the path ever completed a close on the wrong side before terminal.

## Reporting
Report each major partition and pooled-major for LONG and SHORT, split into:
- ALL fills,
- H2_SUCCESS,
- H2_FAIL.

The goal is to identify the first post-fill behavioral asymmetry, not to derive a filter.

## Audit requirements
- Raw 5m coverage = 100%.
- LONG cohort count must reproduce B27W F85 fills.
- SHORT cohort count must reproduce B27AD BLIND_F15 fills.
- Exact entry geometry must be F85/F15.
- H2 success labels must reproduce persisted results.
- No bar at or after the terminal/H2 bar may enter pre-terminal diagnostics.
- Fill-bar high/low are excluded from MAE/MFE.
- No thresholds are mined from the result.

Research only. Live BBC unchanged.
