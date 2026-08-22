# B27Y — London -> New York F85 Post-H2 Breakout Extension Atlas — Preregistration

## Correction
H2 is **not** the final take-profit. It is the second arrival at the frozen previous London High and therefore the end of the entry window / start of the breakout phase.

The intended sequence is:

**Touch High #1 -> causal leave -> F85 entry before H2 -> H2 arrival -> potential breakout/extension above High.**

B27Y is descriptive target research only. It does not select or promote a TP or stop.

## Frozen entry cohort
Reuse B27W exactly:
- BTCUSDT
- LONDON_TO_NEWYORK LONG
- B27Q K1 OPP0
- first High-touch episode causally ends
- F85 = 0.85 of frozen previous London Low-to-High range
- fill is allowed only after causal leave and strictly before H2
- B27W F85 fill identity/timestamp must reproduce exactly

H = previous London High, L = previous London Low, R = H-L.

## H2 milestone
H2 is the first later raw-5m bar, after the causal leave, whose high reaches H.
H2 is a milestone, not an exit.

For every F85 fill:
- if H2 never occurs before the opposite structural terminal/session end, the path is `NO_H2`;
- if H2 occurs, B27Y studies the path from the H2 bar through New York session end.

## Breakout and extension definitions
After H2, measure both wick-based tradable extension and close-based acceptance.

### Strict breakout acceptance
`FIRST_CLOSE_BREAK` = first completed raw 5m bar at/after H2 with `close > H`.

Report the probability of a strict close-break:
- conditional on H2;
- unconditional across all frozen F85 fills.

### Maximum extension
For each H2 path through session end:
- `max_high_extension = (max(high) - H) / R`;
- `max_close_extension = (max(close) - H) / R`.

Negative close extension is allowed if no close accepts above H.

### Frozen extension atlas
Without selecting a winner, report reach rates at exactly:
- E05 = H + 0.05R
- E10 = H + 0.10R
- E15 = H + 0.15R
- E20 = H + 0.20R
- E25 = H + 0.25R
- E30 = H + 0.30R
- E40 = H + 0.40R
- E50 = H + 0.50R

For each level report:
- wick/high reach rate among H2 paths;
- wick/high reach rate among all frozen F85 fills;
- close reach/acceptance rate among H2 paths;
- close reach/acceptance rate among all frozen F85 fills;
- median minutes from H2 bar start to first wick reach when reached.

This atlas is descriptive. No extension is called the final TP inside B27Y.

## Distribution outputs
By partition report:
- F85 fills;
- H2 count/rate;
- strict close-break count/rate conditional on H2 and unconditional;
- max-high extension P25/P50/P75/P90;
- max-close extension P25/P50/P75/P90;
- extension-level atlas E05-E50.

Persist one row per F85 fill with H2 timestamp, first strict close-break timestamp, max high/close extension, and first-reach timestamps for each E level.

## Mandatory assertions
1. B27W F85 fill identity and entry timestamps reproduce exactly.
2. Every H2 timestamp used by B27Y equals the frozen B27W H2 bar start for that F85 path.
3. Every H2 path starts strictly after the F85 entry bar.
4. No post-H2 statistic uses bars after New York session end.
5. `FIRST_CLOSE_BREAK` requires raw 5m close > H, never wick-only.
6. Extension price equals H + E*R exactly.
7. First-reach timestamps are chronological and at/after H2.
8. Synthetic cases for H2-without-close-break, close-break-on-H2, later close-break, wick extension without close acceptance, and large extension must pass before persistence.

Research only. Live BBC unchanged.
