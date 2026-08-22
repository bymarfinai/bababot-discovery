# B27AH — BTC London -> New York SAME_BAR_REJECTION + 4H BULL Hybrid Attribution — Preregistration

**Status:** PREREGISTERED. Attribution/confirmation audit only; no live promotion.

## Question
Does the existing B27AC LONG `SAME_BAR_REJECTION` cohort become stronger when restricted to the pre-signal causal 4H `BULL` state already frozen in B27AG?

## Frozen inputs
- Trade cohort and economics: B27AC `SAME_BAR_REJECTION` only.
- Fixed exit: existing E20 baseline from B27AC.
- Hybrid exit: existing E20 profit-lock structural runner from B27AC.
- Regime label: B27AG `regime_at_signal` only.
- 4H regime semantics are unchanged: existing causal SwingRegime using confirmed 4H structure, EMA7/EMA20, swing_lb=5, swing_atr=0.5.
- No entry, F85, E20, F35, runner, fee, session, timeframe, or regime threshold changes.

## Primary comparison
Pooled major partitions (external + development + reference_validation):
1. SAME_BAR all regimes (must exactly reproduce B27AC N=68 and persisted fixed/hybrid economics).
2. SAME_BAR + pre-signal 4H BULL.
3. SAME_BAR + pre-signal 4H BEAR.
4. SAME_BAR + pre-signal 4H SIDEWAYS.

For each report N, WR, PF, expectancy/trade, and total PnL for both fixed E20 and hybrid.

## Partition transparency
Report BULL-only results separately for external, development, and reference_validation. Small cells must remain visible and cannot be pooled away.

## Audit requirements
- Every SAME_BAR trade must join one-to-one to the existing B27AG LONG signal detail using partition + signal_ts.
- `regime_available_ts <= signal_ts` for every joined trade.
- Existing B27AC pooled-major SAME_BAR values must reproduce within floating-point tolerance: N=68, fixed total about +$61.80, hybrid total about +$91.31, fixed WR about 73.5%, hybrid WR about 69.1%.
- No post-result threshold rescue or alternate regime definition.

## Interpretation guardrail
Because SAME_BAR_REJECTION was originally an adaptively observed diagnostic subset, B27AH can show whether 4H BULL attribution improves its historical concentration, but it cannot convert that subset into an independent OOS validation.

Research only. Live BBC unchanged.
