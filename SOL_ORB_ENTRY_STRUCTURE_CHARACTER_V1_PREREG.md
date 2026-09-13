# SOL ORB Entry Structure Characterization v1 — Preregistration

## Purpose
Characterize *where inside the already-frozen ORB sequence the executable LONG entry is strongest* without changing the detector and without optimizing TP/SL.

Population is fixed to Development-only H23 UTC sessions that already satisfy `BREAK_RETEST_ACCEPT_LONG` under `SOL_ORB_STRUCTURE_DETECTOR_V1`.

## Frozen population
- SOLUSDT 5m.
- Weekdays only.
- Development: 2022-01-01 <= timestamp < 2025-01-01.
- Habitat: 23:00-00:00 UTC.
- ORB = first three 5m bars.
- Structure = first close above ORB high -> retest -> later close above ORB high.
- No Reference Validation/OOS.

## Entry coordinates to compare
All are evaluated on the same frozen structural population.

- E1 `BREAKOUT_NEXT_OPEN`: open of the bar immediately after the first breakout close.
- E2 `RETEST_LEVEL`: theoretical limit at ORB high when the retest bar trades through/touches ORB high. This is an opportunity-price diagnostic, not yet a claim of guaranteed fill quality.
- E3 `ACCEPTANCE_CLOSE`: close of the acceptance bar.
- E4 `ACCEPTANCE_NEXT_OPEN`: open of the next 5m bar after acceptance; this is the current detector's causal executable signal.

## Structural features
Measured causally by the acceptance decision time:
- ORB range percent.
- Breakout close extension above ORB high, normalized by ORB range.
- Breakout candle body, normalized by ORB range.
- Bars from ORB completion to breakout.
- Bars breakout -> retest.
- Retest low depth relative to ORB high, normalized by ORB range.
- Retest close location inside/above ORB, normalized by ORB range.
- Bars retest -> acceptance.
- Acceptance close extension above ORB high, normalized by ORB range.
- Entry-next-open extension above ORB high, normalized by ORB range.

## Outcome diagnostics
No TP/SL search. For each entry coordinate measure fixed forward mark-to-market returns at 15m, 30m, 60m and 120m. For E4 also measure 120m MFE and MAE. All returns are raw price returns; fees are intentionally excluded at this characterization stage.

## Character discovery rule
No thresholds are promoted from a single loss or best-looking row. Character is described using population medians and quartile monotonicity. A feature is called a useful structural clue only if its ordered quartiles show a reasonably consistent relationship with 60m/120m continuation, or if the positive-vs-negative 120m groups show a material median separation.

## Boundary
This experiment may identify an entry *character* and a preferred execution coordinate. Any threshold rule or live gate derived from it requires a new preregistered experiment.
