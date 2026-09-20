# BNB B38-S17 — R Geometry Cause Audit Preregistration

## Objective
Diagnose why the frozen E2 baseline can remain near-zero/negative expectancy despite ~73.9% WR.

## Frozen baseline
- E2 signature: `d01de02f7fa7c30f740e20a015ee879d79d9f308bfe26262141690d1081d5267`
- DEV 440 = 325 WIN / 115 LOSS
- REF 272 = 201 WIN / 71 LOSS
- Baseline loss = -1R from frozen touch-low structural SL.
- Baseline target = causal TP1.

## Questions
1. Is SL distance in price terms materially wider in weak periods?
2. Is TP1 absolute distance too small?
3. Is the real issue the ratio TP1 distance / SL distance?
4. How much average winner R is required for break-even at the observed WR, versus what is actually achieved?
5. Does wider SL quartile systematically reduce expectancy in both DEV and REF?

## Measurements
For every executable E2 trade:
- SL distance % of entry
- TP1 distance % of entry
- TP1 R = TP1 distance / SL distance
- baseline outcome and realized R

Report:
- DEV/REF aggregate decomposition
- annual 2022–2026 decomposition
- SL-distance quartiles using DEV cuts applied unchanged to REF
- TP-distance quartiles using DEV cuts applied unchanged to REF
- R-ratio quartiles using DEV cuts applied unchanged to REF

## Boundary
Diagnostic only. No SL cap, TP alteration, or entry filter is promoted in S17.
