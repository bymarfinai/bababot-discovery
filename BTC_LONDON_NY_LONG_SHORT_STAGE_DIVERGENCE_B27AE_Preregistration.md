# B27AE — BTC London -> New York LONG vs SHORT Stage-Divergence Audit — Preregistration

**Status:** PREREGISTERED. This is a diagnostic audit only. No threshold, entry depth, stop, target, pivot width, timeframe, or session definition may be changed after seeing the result.

## Question
At which earliest causal stage do the existing exact-mirror LONG and SHORT pipelines begin to diverge?

This audit does not search for a better SHORT rule. It only compares the already-frozen mirrors:

- LONG: B27Q LONDON_TO_NEWYORK LONG K1 OPP0 -> B27W blind F85.
- SHORT: B27Q LONDON_TO_NEWYORK SHORT K1 OPP0 -> B27AD blind F15.

The geometry is exact mirror around the London-range midpoint:
- LONG entry fraction = F85 = 0.85.
- SHORT entry fraction = F15 = 0.15.
- LONG E20 = H + 0.20R.
- SHORT E20_DOWN = L - 0.20R.

where R = H - L.

## Frozen nested stages
The comparison is reported separately for external, development, reference_validation, and pooled major partitions.

### Stage 0 — K1 pressure structural outcome
`P(TARGET_BREAK | LONDON_TO_NEWYORK, K1, OPP0)` from the persisted B27Q signal census.

This stage is not conditional on an entry fill and is reported as the earliest directional structural reference.

### Stage 1 — causal leave / clean entry window
Among K1 OPP0 opportunities, proportion with a completed causal leave that creates a non-null `eligible_start`.

### Stage 2 — mirrored pre-H2 entry fill
Conditional on Stage 1:
- LONG: F85 fill before H2/opposite-break terminal.
- SHORT: F15 fill before H2/opposite-break terminal.

### Stage 3 — second-touch arrival
Conditional on Stage 2:
- LONG: later arrival to London High (H2).
- SHORT: later arrival to London Low (H2).

The H2 bar is a milestone only.

### Stage 4 — post-H2 strict breakout acceptance
Conditional on Stage 3, from the H2 bar through NY session end:
- LONG acceptance: first completed raw 5m close > H.
- SHORT acceptance: first completed raw 5m close < L.

The H2 bar itself may be the acceptance bar if its completed close qualifies.

### Stage 5 — E20 extension reach
Conditional on Stage 3, from the H2 bar through NY session end:
- LONG: any raw 5m high >= H + 0.20R.
- SHORT: any raw 5m low <= L - 0.20R.

E20 reach is structural/price-path evidence here, not an exit decision.

## Timing diagnostics
For H2 fills, also report:
- median fill -> H2 minutes;
- median H2 -> acceptance minutes among accepted paths;
- median H2 -> E20 minutes among E20-reach paths.

## Interpretation rule
No arbitrary pass threshold is introduced. The audit will identify:
1. whether Stage 1 and Stage 2 geometry are approximately mirrored;
2. the earliest stage where LONG and SHORT show a clear persistent gap in pooled results and the partition rows reveal where it comes from;
3. whether later economic weakness is already explained by that earlier path divergence.

No causal claim beyond the observed stage ordering is allowed.

## Audit requirements
- Raw 5m coverage must remain 100%.
- B27Q K1 OPP0 opportunity identities must reproduce B27W LONG and B27AD SHORT window counts.
- LONG F85 and SHORT F15 entry prices must reproduce the exact mirrored range fractions.
- Every filled entry must occur strictly before its H2 terminal when H2 exists.
- Stage 4/5 scanning starts no earlier than the frozen H2 bar.
- E20 formulas are exact and no alternative extension is tested.

Research only. Live BBC unchanged.
