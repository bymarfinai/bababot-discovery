# ETH F85 LONG Exact-Transplant E1 — Preregistration

## Purpose
Test whether the frozen BTC B27 causal F85 LONG structural continuation architecture transfers to ETHUSDT without pair-specific tuning.

## Data
- Binance USD-M Futures ETHUSDT 5m klines from Binance public archive.
- Frozen research horizon and partitions are identical to the BTC B27 research:
  - external: 2020-01-01 to 2022-01-01 UTC
  - development: 2022-01-01 to 2025-01-01 UTC
  - reference_validation: 2025-01-01 to 2026-07-30 UTC
  - august: 2026-08-01 to 2026-08-21 UTC
- Reference data may begin earlier only for archive continuity; signals are partition-local.

## Frozen LONG signal geometry
Use the causal raw-5m adapter semantics already implemented in `bbc_f85_f15_signals.LongF85Session`.

For every frozen zone:
1. Build a 330-minute reference range H/L.
2. Use the following frozen reference clocks:
   - ALT_0330 = 03:30 UTC
   - RAW_0530 = 05:30 UTC
   - LONDON = 08:00 UTC
   - RAW_2330 = 23:30 UTC
3. Execution window begins after the 330-minute reference and lasts 390 minutes.
4. First High pressure visit only: K1 with OPP0.
5. Require causal leave from the first High-touch episode.
6. First eligible F85 touch only, where F85 = L + 0.85*(H-L).
7. Same-bar rejection confirmation: touch bar close must finish above F85.
8. Entry only at the next 5m bar open.
9. Entry geometry must satisfy F35 < entry < H, where F35 = L + 0.35*(H-L).
10. H2/opposite-break on a completed bar owns that bar before any F85 touch. No future terminal event may retroactively veto a previously valid causal entry.

## Frozen zone filters
- LONDON: no additional filter.
- ALT_0330: F85 touch must occur at or before minute 195 of execution.
- RAW_0530 and RAW_2330: the final reference range must have completed at or after minute 165 of the 330-minute reference window.
- No EMA, ATR, volume, wick, candle-body, volatility, regime, or pair-specific filter may be introduced.

## Frozen exit management
- Notional: USD 500 per trade.
- Fee: USD 0.40 per completed trade, matching BTC B27 accounting.
- ALT_0330: fixed E20 target / completed-close F35 invalidation / execution-end time exit.
- RAW_0530, LONDON, RAW_2330: exact B27DQ live-executable E10 structural runner semantics:
  - E20 touch arms the runner.
  - initial/ratcheted protective floor learned from completed bar N is not scoreable until N+2.
  - runner floor starts at E10 = H + 0.10R and ratchets in 0.10R structural steps using completed closes.
  - completed-close F35 invalidation remains active before the first runner floor becomes exchange-active.
  - floor gap-open and floor-touch exits follow B27DQ ordering.
- Global one-ETH-position lock: earliest causal entry wins; later entries while a trade is open are skipped.
- Same frozen zone tie-order as BTC: LONDON, ALT_0330, RAW_0530, RAW_2330.

## Stress test
Re-score pooled-major economics with runner-stop slippage of 0, 2, 5, and 10 bps. Slippage applies only to B27DQ runner floor exits, matching the BTC implementation.

## Decision labels
No parameter may be changed after results are observed.

### BTC-grade cross-pair replication
Supported only if pooled-major exact-transplant result satisfies all:
- accepted N >= 150
- WR >= 70%
- PF >= 2.00
- expectancy > 0
- total net > USD 250
- max loss streak <= 4
- at 5 bps runner-stop slippage: PF > 1.80 and total net > USD 200
- every major historical partition has positive net expectancy

### Transferable edge, below BTC grade
If BTC-grade fails, label `ETH_E1_TRANSFERABLE_EDGE_BELOW_BTC_GRADE` only if:
- pooled-major accepted N >= 100
- WR >= 65%
- PF >= 1.30
- total net > 0
- every major partition has PF > 1.00 and total net > 0
- 5 bps runner-stop slippage remains PF > 1.20 and total net > 0

Otherwise label `ETH_E1_EXACT_TRANSPLANT_NOT_SUPPORTED`.

## Integrity rule
This experiment is a pair-transfer test, not an ETH optimization study. If it fails, the result is retained as evidence. Any ETH-specific clock, level, filter, or exit modification must be a separately preregistered follow-up experiment.