# ETH B27DX — S8A Causal Volatility-Regime Calibration — Preregistration

## Purpose
Test whether the remaining ETH quality gap is regime-dependent rather than solvable by more event/candle filtering.

S7F ended the current candle-filter family. S8A therefore changes layer: it conditions the frozen B27DX event on a causal, pair-native reference-range volatility regime.

## Frozen trade architecture
- LONG only.
- R300 / X360.
- Execution clocks: 05:00, 09:00, 10:00, 16:00 UTC.
- F75 entry, E25 target, F20 completed-close invalidation.
- Same raw 5m data, partitions, weekdays, notional, fees, corrected B27DX grammar, next-bar chronology and one-position lock as S4/S7A-S7F.
- No candle filter, runner, leverage or live-code change.

## Causal regime feature
For every valid weekday reference window at each frozen clock, independently of whether a trade later occurs:

`range_pct = (H - L) / ((H + L) / 2)`.

At execution start, compute the median `range_pct` of the **20 immediately prior valid weekday reference windows for that same execution clock**. The current reference window is not included in the trailing median.

A regime label is then frozen before execution:
- `HIGH_VOL`: current `range_pct >= trailing_20_median`.
- `LOW_VOL`: current `range_pct < trailing_20_median`.

The first 20 valid windows without sufficient prior history are unclassified and excluded from regime scoring. The 20-window lookback is fixed as approximately one trading month; no alternate lookback is tested.

## Development selection
HIGH_VOL and LOW_VOL are complementary states of one predeclared regime family.

A state is Development-promotable for a clock only if:
- N >= 20,
- retention >= 40% of classified BASE fills for that clock,
- WR >= 75%,
- PF >= 1.50,
- expectancy >= +$0.80/trade,
- net > 0.

If both states pass, choose deterministically by higher retention; exact ties choose HIGH_VOL. Do not select by PF or expectancy.

## Historical replication
Only the frozen Development-selected state is opened in External and Reference Validation. Each independently requires:
- N >= 10,
- retention >= 30%,
- WR >= 70%,
- PF >= 1.20,
- expectancy > 0,
- net > 0.

Validation cannot change state or lookback.

## Portfolio rescore
Only replicated clock+regime streams are combined. Rerun the global chronological one-position lock separately for every major partition. Report 0 bps and 5 bps stress.

## BTC-quality diagnostic
Pooled-major primary requires WR >=71.9%, PF >=2.22, expectancy >=+$1.26/trade, all major partitions PF>1/net>0, and pooled 5bps PF>=1/net>=0.

## Statuses
- `ETH_S8A_CAUSAL_AUDIT_FAILED`
- `ETH_S8A_NO_DEV_VOL_REGIME`
- `ETH_S8A_DEV_REGIMES_NOT_REPLICATED`
- `ETH_S8A_VOL_REGIMES_REPLICATED_BELOW_BTC`
- `ETH_S8A_VOL_REGIME_PORTFOLIO_BTC_QUALITY_SUPPORTED`

Research only.