# B27AZ — BTC London→NY SHORT Post-H2 Full-Range Entry-Zone Discovery — Preregistration

Goal: independently discover where a SHORT entry naturally occurs after valid distinct Low retest #2 and its causal leave, without assuming legacy F15 and without using PnL/stop/target/regime information.

Frozen source semantics:
- BTCUSDT 5m source and B27Q London→NY SHORT K1/OPP0 lineage.
- Reuse B27AY identification of valid Low retest #2 and causal leave #2.
- Eligible entry search starts at `eligible_start` after leave #2 completes.
- Frozen London range: R=H-L, candidate Fx=L+xR.
- Candidate grid is fixed before results: F05,F10,...,F95 (5%-point increments).
- On every bar, terminal event has precedence over a candidate fill: strict close<L = direct breakdown; strict close>H = opposite break; valid Low revisit (`low<=L` and `L<=close<=H`) = retest #3. Thus a fill must occur strictly before the next terminal event.
- After a candidate fill, continue causally until first direct breakdown, valid Low revisit, opposite break, or session end.

Primary structural diagnostics per partition and pooled-major:
1. clean post-H2 windows,
2. candidate fills and fill/clean,
3. downside-resolution after fill = first subsequent event is either valid Low revisit or strict close<L,
4. downside-resolution/fill,
5. direct-breakdown/fill,
6. opposite-break/fill,
7. session-end unresolved/fill,
8. median minutes fill→downside resolution.

Guardrails:
- No PnL, F65 stop, E20 target, hybrid runner, confirmation, EMA/swing/4H regime, or feature filter is used to select an entry zone.
- No interpolation such as F12/F17 or post-hoc finer grid.
- This is an atlas, not a promotion test. Because the post-H2 cohort is structurally smaller than B27AK, the old >=30 fills in every partition gate is not reused or weakened after seeing results.
- Report whether high-range zones (F65–F95) are actually reachable before the next Low resolution and how their conditional resolution compares with low-range zones.
- Research only; live BBC unchanged.
