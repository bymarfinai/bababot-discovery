# B27AU — BTC London->NY SHORT F15 E20 Hybrid Loss Decomposition — Preregistration

Purpose: diagnose, not optimize, the frozen B27AT E20 full-position hybrid candidate.

Frozen cohort/rule:
- BTCUSDT London->NY SHORT BLIND_F15 all-regime cohort.
- Entry F15 = L + 0.15R.
- Pre-activation completed-close invalidation F65 = L + 0.65R.
- Activation E20_DOWN = L - 0.20R.
- After activation, 100% position remains open with the frozen 3-bar pivot-high profit-ceiling runner.
- Use only persisted B27AT E20 trades; no parameter search or alternative rule.

Required diagnostics by external/development/reference_validation and pooled-major:
1. PnL decomposition by exit bucket: PRE_ACT_CLOSE_INVALIDATION_F65, PROFIT_CEILING_HIT, PROFIT_CEILING_GAP_OPEN, TIME_EXIT_SESSION_END.
2. Activated vs non-activated: N, WR, total PnL, expectancy, mean winner, mean loser.
3. For pre-activation invalidations: normalized close overshoot above F65, median/P75/P90/max, and total loss.
4. For activated trades: median trough extension, realized exit extension, capture ratio, giveback; separately activated winners vs activated losers.
5. Loss concentration: worst 5 and worst 10 trades as share of gross losses, plus their exit-reason mix.
6. Counterfactual diagnostic only: for activated trades, compare realized E20-hybrid PnL with the mechanical PnL that would have resulted from an exact E20 exit at activation price. This is attribution only, not a proposed rule.
7. Reproduce B27AT E20 partition identities and totals before interpretation.

No new entry, stop, target, activation, regime filter, confirmation, split ratio, candle threshold, or runner parameter. Research only; live BBC unchanged.
