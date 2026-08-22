# B27W — London -> New York Pre-Second-Touch Entry — Preregistration

## Purpose
Test the user's intended entry window literally:

**First distinct visit to previous London High -> price leaves that first visit -> find a LONG entry -> first return/arrival to London High (Touch/Arrival #2).**

B27Q liquidity levels and K1 OPP0 signal identities remain frozen. This experiment does not change the directional detector. It only constrains entry to occur before the second arrival at High.

## Cohort
Primary only:
- BTCUSDT
- LONDON_TO_NEWYORK
- LONG / previous London High pressure
- B27Q K1
- OPP0 at K1 signal
- same frozen external / development / reference_validation / August partitions

## Frozen level and event clock
- H = completed London High, frozen.
- L = completed London Low, frozen.
- Raw event clock = repository 5m source.
- Require H > L.

## First-touch episode and causal leave
The B27Q K1 bar is the first 5m bar of the first distinct High visit.

A bar belongs to the same High-touch episode when `high >= H` and `close <= H`, with no prior strict close-break.

The first-touch episode ends only after a completed 5m bar that does **not** qualify as a High touch. To avoid intrabar hindsight, entry search becomes eligible only from the NEXT 5m bar after that leave bar completes.

If the market strict-close breaks H or L before a causal leave is established, there is no eligible pullback-entry window.

## Second-arrival definition
After the causal leave has completed, `H2_ARRIVAL` is the first later 5m bar whose `high >= H`, regardless of whether its close is below/equal to H or above H.

Therefore the second arrival includes both:
- a normal second High visit/retest; and
- a second arrival that immediately breaks/closes above H.

The H2 arrival bar is the target event and is **not entry-eligible**. Any entry requiring that bar is rejected because intrabar ordering is unknowable.

If a 5m close < L occurs before H2, classify `OPPOSITE_BREAK_BEFORE_H2`.
If neither happens by New York session end, classify `NO_H2_BY_SESSION_END`.

## Entry grid — before H2 only
Freeze five simple limit levels measured from previous London Low=0 to High=1:
- F95 = 0.95
- F90 = 0.90
- F85 = 0.85
- F80 = 0.80
- F75 = 0.75

A limit is eligible only after causal leave and only on bars strictly before the H2 arrival bar.
A fill occurs when an eligible bar spans the frozen level.
A strict close < L before fill cancels the setup.
No fill may occur on or after H2 arrival.

This experiment intentionally does **not** optimize a stop. It isolates whether a usable entry price exists before the second High arrival.

## Entry-quality outputs
For every partition / limit level report:
- K1 setup count;
- clean pullback windows;
- H2-arrival probability after a clean leave;
- limit fills before H2;
- fill rate;
- among filled entries: H2 target-hit rate before opposite close-break/session end;
- median minutes from entry to H2;
- median reward to H as % of previous-session range;
- median and 10th-percentile minimum post-entry price fraction before H2/failure (MAE context);
- median adverse excursion from entry in range units.

Also persist one-row-per-window and one-row-per-entry-candidate audit files with K1, leave, entry, H2/opposite-break timestamps.

## Discovery screen
A level is only tagged `SCREEN_PASS` if the exact same level has in external, development, and reference_validation:
- >= 30 pre-H2 fills in each partition;
- >= 70% H2 target-hit rate among filled entries in each partition.

This is a structural entry-quality screen, not live promotion and not an economic backtest.

## Mandatory assertions
1. B27Q K1 OPP0 identities are reused unchanged.
2. First-touch episode is contiguous and cannot itself become H2.
3. Entry eligibility begins only after a completed leave bar.
4. H2 is first later `high >= H` after leave, including breakout-arrival.
5. No entry is filled on the H2 bar.
6. Every filled entry timestamp is strictly before H2 when H2 exists.
7. Entry price equals frozen range fraction exactly.
8. No entry after strict close < L.
9. All event timestamps come from raw 5m chronology.
10. Synthetic paths covering consecutive K1 bars, leave, second revisit, breakout-on-second-arrival, and no-H2 cases must pass before persistence.

Research only. Live BBC unchanged.
