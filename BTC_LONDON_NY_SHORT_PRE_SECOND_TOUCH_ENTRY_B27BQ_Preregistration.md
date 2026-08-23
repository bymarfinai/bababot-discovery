# B27BQ — London -> New York SHORT Pre-Second-Touch Entry Geometry — Preregistration

## Purpose
Mirror the successful causal structure of B27W on the SHORT side without post-hoc threshold mining:

**First distinct visit to previous London Low -> price causally leaves that first visit -> find a SHORT retrace entry -> first later return/arrival to London Low (Low Arrival #2).**

This is a structural entry-quality experiment only. It does not change B27Q directional detection and does not change live BBC.

## Frozen cohort
Primary cohort only:
- BTCUSDT
- LONDON_TO_NEWYORK
- SHORT / previous London Low pressure
- B27Q K1
- OPP0 at K1 signal
- same frozen external / development / reference_validation / August partitions

The cohort must reproduce the frozen B27Q SHORT K1 OPP0 signal identities exactly.

## Frozen levels and event clock
- H = completed previous London High
- L = completed previous London Low
- R = H - L
- raw event clock = repository 5m source
- require H > L
- range fraction f maps to `L + f*R`

No EMA, ATR, order block, volume, candle-body threshold, newly formed swing, or adaptive level may replace the frozen London H/L geometry.

## First Low-touch episode
The B27Q K1 SHORT signal bar is the first 5m bar of the first distinct Low visit.

A bar belongs to the same Low-touch episode when:
- `low <= L`
- `close >= L`
- and no prior strict breakout has terminated the episode.

A confirmed target-side breakdown during K1 is a completed 5m `close < L`.
A confirmed opposite-side breakout during K1 is a completed 5m `close > H`.
Either occurring before causal leave means there is no eligible pullback-entry window.

## Causal leave
The first-touch episode ends only after a completed 5m bar that does not qualify as a Low touch while still inside the frozen London range.

Entry search becomes eligible only from the NEXT 5m bar after that leave bar completes. This prevents intrabar hindsight.

## Second Low arrival
After causal leave, `L2_ARRIVAL` is the first later raw 5m bar whose `low <= L`, regardless of whether that bar closes back above L or closes below L.

Thus Low Arrival #2 includes both:
- a normal second Low retest;
- a second arrival that immediately breaks/closes below L.

The L2 bar itself is not entry-eligible.

If a completed 5m `close > H` occurs before L2, classify `OPPOSITE_BREAK_BEFORE_L2`.
If one 5m bar both reaches `low <= L` and closes `> H`, classify `AMBIGUOUS_L2_VS_OPPOSITE_BREAK` because intrabar order is unknowable.
If neither occurs by New York session end, classify `NO_L2_BY_SESSION_END`.

## Frozen entry grid — before L2 only
Mirror B27W exactly around the London-range midpoint:
- F05 = 0.05
- F10 = 0.10
- F15 = 0.15
- F20 = 0.20
- F25 = 0.25

A SHORT limit is eligible only after causal leave and only on bars strictly before L2.
A fill occurs when an eligible 5m bar spans the frozen level.
No fill may occur on the L2 bar or after it.
A strict close > H before fill cancels the setup.

This experiment intentionally does NOT optimize stops or profit targets. It isolates whether a usable SHORT retrace entry exists before the second Low arrival.

## Required outputs
For every partition / entry level report:
- K1 setup count
- clean pullback windows
- L2-arrival probability after clean leave
- pre-L2 fills
- fill rate
- among filled entries: L2 target-hit rate before opposite close-break/session end
- median minutes from entry to L2
- median reward to L as fraction of London range
- median and 90th-percentile maximum post-entry price fraction before L2/failure
- median adverse excursion from entry in range units

Persist one-row-per-window and one-row-per-entry-candidate audit files.

## Frozen structural screen
A level is tagged `SCREEN_PASS` only if the exact same level has in EACH of external, development, and reference_validation:
- >= 30 pre-L2 fills
- >= 70% L2 target-hit rate among filled entries

This is structural discovery evidence only, not an economic backtest and not live promotion.

## Mandatory assertions
1. B27Q SHORT K1 OPP0 identities are reproduced exactly.
2. First-touch episode is contiguous and cannot itself become L2.
3. Entry eligibility begins only after a completed causal leave bar.
4. L2 is the first later `low <= L` after leave, including a breakdown-on-second-arrival bar.
5. No entry is filled on the L2 bar.
6. Every filled entry timestamp is strictly before L2 when L2 exists.
7. Entry price equals the frozen range fraction exactly.
8. No entry after strict close > H.
9. All chronology uses raw 5m data.
10. Synthetic paths for contiguous K1 bars, leave, second revisit, breakdown-on-second-arrival, opposite breakout, and no-L2 must pass before real results persist.

Research only. Live BBC unchanged.
