# B27AJ — BTC London->NY LONG Lineage / Regime-Gate Audit — Preregistration

## Question
Did the historical LONG/SAME_BAR hybrid result (+$91.31 pooled major in B27AC) already require the older HH/HL BULL regime, or was it an all-regime liquidity cohort?

## Frozen audit only
No strategy parameters, entries, exits, or regime definitions may be changed. This is provenance/source-code audit only.

Required assertions:
1. The older V2 regime document contains the causal BULL definition based on confirmed HH+HL.
2. B27Q explicitly defines a new liquidity experiment without the prior swing/fractal engine.
3. In B27Q source, `btc_strong_uptrend_lifecycle_b22b` is used only for `PARTS`; it does not gate signals.
4. B27Q LONG signal creation is caused by a HIGH visit K, with no regime predicate.
5. B27W loads B27Q `LONDON_TO_NEWYORK`, `LONG`, `K1`, `OPP0` only, with no regime predicate.
6. B27AC loads its cohorts from B27Z/B27AA and has no regime predicate in cohort construction.
7. The pooled-major B27AC SAME_BAR hybrid cohort reproduces N=68 and total +$91.31 (within floating tolerance).
8. Those same 68 trades split under the later causal B27AG 4H regime attribution into BULL/BEAR/SIDEWAYS, proving the original cohort was not hard-gated to BULL. Expected split must reproduce B27AH: BULL=37, BEAR=19, SIDEWAYS=12.

Output a single PASS/FAIL lineage conclusion. Research only; live BBC unchanged.
