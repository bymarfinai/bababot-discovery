# ETH B27DX — S8B Reference-Direction Regime — Preregistration

## Purpose
Test whether the remaining ETH B27DX quality gap is directional-regime dependent rather than volatility dependent.

S8A found no Development-promotable HIGH_VOL/LOW_VOL state under the frozen causal volatility definition. S8B therefore changes only the regime variable, not the trade architecture or quality gates.

## Frozen trade architecture
- LONG only.
- R300 reference / X360 execution.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- Entry F75.
- Target E25.
- Completed-close invalidation F20.
- Same raw 5m data, weekdays, partitions, notional, fee model, corrected B27DX event grammar, next-bar chronology, and global one-position lock as S4/S7/S8A.
- No candle filter, runner, leverage, or live-code changes.

## Causal directional regime
For each candidate's completed R300 reference window:
- `reference_open` = open of the first completed 5m reference bar.
- `reference_close` = close of the final completed 5m reference bar.
- `reference_drift = reference_close / reference_open - 1`.

State is frozen at execution start:
- `UP_REF` if `reference_close > reference_open`.
- `DOWN_REF` if `reference_close < reference_open`.
- exact equality is `FLAT_REF` and is excluded from directional selection.

This is a sign-only split. No return-magnitude threshold, moving average, lookback, or alternate timeframe is tested in S8B.

## Development selection
UP_REF and DOWN_REF are complementary predeclared states.

A state is Development-promotable for a clock only if:
- N >= 20,
- retention >= 40% of non-flat BASE fills for that clock,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

If both states pass, choose deterministically by higher retention; exact ties choose UP_REF. Do not select by PF, WR, or expectancy.

## Historical replication
Only the frozen Development-selected state is opened in External and Reference Validation. Each independently requires:
- N >= 10,
- retention >= 30%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Validation cannot change the state.

## Portfolio rescore
Only replicated clock+direction streams are combined. Rerun global chronological one-position lock separately for every major partition. Report 0 bps and 5 bps stress.

## BTC-quality diagnostic
Pooled-major 0 bps requires:
- WR >= 71.9%,
- PF >= 2.22,
- expectancy >= +$1.26/trade,
- every major partition PF > 1 and net > 0,
- pooled 5 bps PF >= 1 and net >= 0.

## Decision statuses
- `ETH_S8B_CAUSAL_AUDIT_FAILED`
- `ETH_S8B_NO_DEV_DIRECTION_REGIME`
- `ETH_S8B_DEV_REGIMES_NOT_REPLICATED`
- `ETH_S8B_DIRECTION_REGIMES_REPLICATED_BELOW_BTC`
- `ETH_S8B_DIRECTION_REGIME_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only. Do not modify live BBC.