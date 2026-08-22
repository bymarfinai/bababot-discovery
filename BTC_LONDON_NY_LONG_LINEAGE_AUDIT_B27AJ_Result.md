# B27AJ — BTC London->NY LONG Lineage / Regime-Gate Audit — Result

**Audit status: PASS.** Source-code lineage and persisted trade identities were checked directly.

## Finding

- The older V2 detector really did define BULL as 2 confirmed HH + 2 confirmed HL (and BEAR as 2 LH + 2 LL).
- B27Q was explicitly a new liquidity experiment **without** the prior swing/fractal engine.
- In B27Q code, `b22b` is used only for scoring partitions (`PARTS`); its regime state is not used to create signals.
- B27Q creates LONG directly when the visited frozen level is `HIGH`; B27W then selects only `LONDON_TO_NEWYORK + LONG + K1 + OPP0`.
- B27AC cohort construction contains no HH/HL or regime predicate.
- Original SAME_BAR pooled-major hybrid reproduces **N=68**, **WR=69.1%**, **total=$+91.31**.
- Those exact 68 trades later label as **BULL=37**, **BEAR=19**, **SIDEWAYS=12** under the causal B27AG 4H regime detector.

**Conclusion: the +$91.31 B27AC SAME_BAR LONG result was an all-regime liquidity cohort. It was not pre-gated by the older HH/HL BULL regime.**

The historical HH/HL regime detector existed, but it belongs to an earlier research lineage and was not inherited into B27Q/B27W/B27AC.

Research only; live BBC unchanged.
