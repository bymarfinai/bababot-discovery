# B27AM — BTC London->NY SHORT F15 Post-H2 Breakdown Extension Atlas — Preregistration

## Purpose
Freeze the independently discovered B27AK F15 SHORT cohort and answer one narrow reward-side question before selecting any TP:

**After a valid F15 SHORT fill reaches H2 at the completed London Low, how often does price obtain completed 5m acceptance below that Low and how far does downside extension continue?**

This is a structural/path atlas only. It does not choose a TP, stop, entry confirmation, runner, or live rule.

## Frozen upstream cohort
- BTCUSDT, same repository raw 5m archive and frozen partitions.
- LONDON_TO_NEWYORK only.
- SHORT, B27Q K1, OPP0.
- H/L are the completed London-session High/Low.
- B27AK causal leave and independent retrace-zone discovery are frozen.
- F15 = `L + 0.15*(H-L)`.
- Use the exact persisted B27AK F15 filled identities; no new fill logic may replace them.
- H2 = first later raw 5m bar with `low <= L`, exactly as B27AK/B27AD.
- H2 is a milestone, not TP.
- No 4H regime gate.

Before interpreting extension results, B27AM must reproduce the frozen B27AK F15 identities exactly:
- external: 50 fills, 37 H2;
- development: 79 fills, 59 H2;
- reference_validation: 34 fills, 24 H2;
- august: 1 fill, 1 H2.

## Post-H2 event clock
For every F15 fill with H2:
- Start the post-H2 analysis on the frozen H2 raw 5m bar itself.
- End at the active New York session boundary.
- A completed breakdown acceptance exists when a raw 5m bar has strict `close < L`.
- Persist first accepted-breakdown bar start and completion timestamp.
- The H2 bar itself may be the accepted-breakdown bar if it closes strictly below L.

## Downside extension measures
Let `R = H-L`.

For every H2 path persist:
- maximum low extension = `(L - minimum_5m_low_from_H2_to_session_end) / R`;
- maximum close extension = `(L - minimum_5m_close_from_H2_to_session_end) / R`.

Freeze the same coarse atlas used by LONG B27Y:
- E05 = `L - 0.05R`
- E10 = `L - 0.10R`
- E15 = `L - 0.15R`
- E20 = `L - 0.20R`
- E25 = `L - 0.25R`
- E30 = `L - 0.30R`
- E40 = `L - 0.40R`
- E50 = `L - 0.50R`

For each level report both:
- raw-low reach rate;
- completed-close reach rate;
- each conditional on H2 and relative to all F15 fills;
- median minutes from H2 to first low reach.

Report accepted close-below-L rate given H2 and relative to all F15 fills, plus extension distribution quantiles by partition.

## Mandatory assertions
1. Raw 5m archive coverage reproduces 100%.
2. Persisted B27AK F15 fill/H2 identities reproduce exactly by partition before result interpretation.
3. Every H2 path has `fill_bar_start < h2_bar_start`.
4. Frozen H2 raw bar has `low <= L`.
5. Post-H2 slice starts exactly on H2 and never before it.
6. Accepted breakdown uses strict completed 5m `close < L` only.
7. Every extension price equals `L - e*(H-L)` exactly.
8. Low and close reach are kept separate.
9. No PnL, stop, target selection, entry confirmation, EMA, swing, regime, or runner information influences this atlas.
10. Synthetic mirrored paths verify H2-bar breakdown acceptance, low-vs-close reach, and extension geometry before real results persist.

## Interpretation
B27AM is descriptive. No extension level is promoted as TP from this result alone. The next economic experiment, if warranted, must freeze its target candidates before execution.

Research only. Live BBC unchanged.
