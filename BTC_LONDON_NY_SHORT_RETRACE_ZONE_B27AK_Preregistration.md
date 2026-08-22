# B27AK — BTC London->NY SHORT Pre-H2 Retrace Zone Discovery — Preregistration

## Purpose
Find the SHORT retrace zone independently instead of assuming the exact LONG mirror F15.

## Frozen source cohort
- BTCUSDT, same 5m archive and partitions used by B27AD/B27W.
- Transition: `LONDON_TO_NEWYORK`.
- Side: `SHORT`.
- K = 1.
- `opp_visits_at_signal == 0` (OPP0).
- Frozen London High/Low from the completed London session.
- Reuse B27AD causal K1-low-touch / leave / H2 chronology exactly.
- No 4H regime gate.

## Sequence
`Low Touch #1 (K1) -> causal completed leave -> candidate retrace fill before H2 -> H2 Low arrival`.

H2 is a structural milestone only, not TP.

## Candidate retrace zones
`f` is measured from London Low=0 to London High=1:
- F05 = 0.05
- F10 = 0.10
- F15 = 0.15
- F20 = 0.20
- F25 = 0.25

These five values are frozen before execution. No additional fraction may be added after results are seen.

## Entry-opportunity semantics
- Candidate becomes eligible only after the causal leave bar has completed, exactly as B27AD.
- A fill is counted only on a raw 5m bar strictly before the H2/opposite-break terminal bar.
- Candidate price = `L + f*(H-L)`.
- Fill requires the eligible bar range to include candidate price.
- H2 is the first later raw 5m bar with `low <= L`, even if that bar also closes below L.
- Opposite invalidation for the structural window is first completed raw 5m `close > H`.
- Ambiguous H2/opposite-break terminal bars are never candidate fill bars.

## Frozen structural screen
A candidate passes only if, in EACH major partition (`external`, `development`, `reference_validation`):
- at least 30 pre-H2 fills; and
- H2 hit rate among fills >= 70%.

This is the same screen philosophy used to identify LONG F85 in B27W.

## Required assertions
1. B27AD K1 SHORT cohort identities reproduce.
2. F15 results reproduce the already-audited B27AD BLIND_F15 structural counts before interpreting other fractions.
3. Every candidate fill is strictly after causal leave and strictly before terminal/H2 bar.
4. Candidate formula is exact.
5. No regime, EMA, swing, economics, target, stop, or exit condition influences selection.
6. Full 5m archive coverage must reproduce.

## Interpretation
This is structural zone discovery only. Do not select on PnL, WR economics, PF, or later exit behavior. If multiple candidates pass, report all passing candidates; do not choose a single winner post hoc unless a separate preregistered tie-break study is run.

Research only; live BBC unchanged.
