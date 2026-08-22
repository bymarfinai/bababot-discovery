# B27X — London -> New York F85 Winner MAE / Stop-Distance Audit — Preregistration

## Purpose
Freeze the B27W entry discovery result and answer one narrow question before choosing any stop:

**After K1 High pressure, a causal leave from Touch #1, and a valid F85 LONG fill strictly before H2, how far do trades that eventually reach H2 actually move against the F85 entry?**

This is a diagnostic path audit, not a stop optimization or live-promotion test.

## Frozen upstream logic
Unchanged from B27Q/B27W:
- BTCUSDT, repository raw 5m event clock.
- LONDON_TO_NEWYORK only.
- LONG, B27Q K1, OPP0.
- H = completed previous London High; L = completed previous London Low; H > L.
- K1 first-touch episode, causal leave, and H2 arrival semantics are exactly B27W.
- F85 = `L + 0.85*(H-L)`.
- F85 may fill only after the completed causal leave and strictly before the first later H2 arrival bar.
- H2 = first later 5m bar with `high >= H`, including a breakout-on-arrival bar.
- No fill on the H2 bar.

B27X must reproduce B27W F85 fill identity and H2/non-H2 classification exactly.

## Winner definition
An `F85_H2_WINNER` is a frozen B27W F85 fill whose terminal window outcome is `H2_ARRIVAL`.

No future information is used to create the fill. Winner status is used only for this after-the-fact diagnostic of adverse path depth.

## Adverse-excursion measurements
Range fraction uses previous London Low=0 and High=1. F85 entry is 0.85.

For every filled F85 candidate persist:
1. `pre_h2_min_low` / `pre_h2_min_frac`:
   - minimum 5m low from the fill bar through the last bar strictly before H2;
   - includes the fill bar conservatively;
   - excludes the H2 target bar.
2. `to_h2_conservative_min_low` / `to_h2_conservative_min_frac` for H2 winners:
   - minimum low from the fill bar THROUGH the H2 target bar;
   - this is the conservative stop-survival measure because if one 5m H2 bar touches both target and stop, intrabar ordering is unknown and a stop must be treated as hit.
3. `next_bar_pre_h2_min_frac`:
   - contextual lower-bound MAE excluding the fill bar, because limit-vs-low ordering inside the fill bar is unknowable.

Required stop distance in previous-session range units is:
`max(0, 0.85 - minimum_fraction)`.

Report winner required-distance distribution by partition:
- N;
- P50, P75, P90, P95, maximum;
- both pre-H2 and conservative-through-H2 versions.

## Diagnostic stop-survival curve
Without choosing or promoting a stop, report a frozen coarse survival curve for distances below F85:
D05, D10, D15, ..., D85 in 0.05 range increments.

For distance D:
- stop fraction = `0.85 - D`;
- a winner survives conservatively only if the minimum low from fill through H2 target bar is strictly ABOVE the stop price;
- equality counts as a stop touch and therefore does not survive.

Persist for each partition and D:
- H2 winner N;
- conservative winner survival N / rate;
- pre-H2 winner survival rate for context.

This curve is descriptive only. B27X does not select a best D and does not compute a promoted strategy.

## Failure comparison
For filled F85 candidates that do not reach H2, persist their minimum low until terminal/session end and required adverse distance. Report only summary quantiles so later stop work can test whether a distance separates winners from failures rather than merely preserving everything.

## Mandatory assertions
1. B27Q K1 OPP0 signal identity unchanged.
2. B27W first-touch episode, leave, H2, and F85 pre-H2 fill chronology reproduced from raw 5m.
3. No F85 fill on/after H2.
4. F85 fill price equals exact 0.85 range fraction.
5. Every H2 winner has H2 strictly after entry.
6. Pre-H2 MAE excludes H2 bar; conservative MAE includes it.
7. Fill-bar low is included in conservative MAE.
8. Stop survival uses strict `min_low > stop_px`; equality = stop touched.
9. All timestamps and lows come from raw 5m chronology.
10. Synthetic path tests verify fill-bar ambiguity, H2-bar ambiguity, and MAE interval boundaries before any result persistence.

Research only. Live BBC unchanged.
