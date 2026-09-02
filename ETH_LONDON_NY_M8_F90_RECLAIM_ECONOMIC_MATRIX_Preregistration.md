# ETH London -> New York M8 F90 Early-Reclaim Economic Matrix — Preregistration

**Status: PREREGISTERED before result-bearing execution.**

## Purpose
Convert the structurally supported ETH London->New York setup into an actual trade-level economic test using only coordinates independently supported before this run.

Frozen setup:
`LONG K1 OPP0 -> causal leave -> touch F90 -> earliest causal 5m reclaim close > F90 -> enter next raw 5m open`.

Risk-side candidates come only from M6: **F55, F50** completed-close invalidation boundaries.
Reward-side candidates come only from M7: **E05, E10, E15** breakout extensions.

M8 tests exactly **6 cells**. No additional entry, stop, target, confirmation, runner, timing, regime, or indicator parameter may be added after seeing results.

## Frozen cohort
- ETHUSDT perpetual, raw 5m.
- Exact persisted M5 `EARLY_RECLAIM` rows with `executed=True`.
- Actual M5 next-bar-open `entry_bar_start` and `entry_px` are reused unchanged.
- London H/L and range R remain frozen from the originating setup.
- Historical partitions unchanged: external, development, reference_validation, August telemetry.

## Frozen targets
- E05 = H + 0.05R
- E10 = H + 0.10R
- E15 = H + 0.15R

These are limit take-profit prices. The limit is active from the actual M5 entry-bar open onward.

## Frozen close-invalidation boundaries
- F55 = L + 0.55R
- F50 = L + 0.50R

Invalidation is **completed-close only**: a raw 5m candle must close strictly below the frozen boundary. Wick-only penetration does not exit.

Close invalidation exits at that candle's actual close so overshoot/gap loss is not hidden.

## Chronological execution
For each executed M5 EARLY_RECLAIM entry and each of the six target/boundary cells:
1. Position becomes active at the M5 actual entry-bar open and exact M5 `entry_px`.
2. On every active raw 5m bar, including the entry bar, if `high >= target_px`, the limit TP executes at exact target price.
3. If target was not reached on that bar, completed-close invalidation is evaluated at bar completion. If `close < boundary`, exit at the actual close.
4. Therefore if the same bar reaches target intrabar and later closes below the boundary, TP has already executed and wins chronological precedence.
5. H2 and strict breakout are telemetry only and do not themselves exit the trade.
6. If neither target nor invalidation occurs by 20:00 UTC, exit at the first available 5m open at/after 20:00 UTC.
7. No post-session event is used.

## Economics
- Illustrative notional: **$500**.
- Round-trip fee: **$0.40**.
- Trading win: net PnL > 0.
- Base case: no additional execution stress.
- 5bps stress mirrors prior ETH M3 semantics:
  - entry execution worsened by +5 bps;
  - target limit remains exact target price;
  - non-target exits are worsened by -5 bps;
  - same $0.40 round-trip fee retained.

Net PnL = notional * (exit_exec / entry_exec - 1) - fee.

## Required outputs
For each partition and each of the six exact cells report:
- N;
- TP count/rate;
- close-invalidation count/rate;
- time-exit count/rate;
- actual trading WR;
- PF;
- mean net expectancy/trade;
- total net PnL;
- median winner and loser PnL;
- max loss streak;
- median hold minutes;
- median realized entry fraction;
- median nominal reward/risk using actual entry price and frozen boundary/target;
- same metrics under 5bps stress.

Persist one row per trade/cell with full entry/exit chronology.

## Frozen economic screen
A cell is `SCREEN_PASS` only if the **same exact target/boundary pair** satisfies all of the following:
1. at least 15 trades in each major partition;
2. base-case WR >=70% in each major partition;
3. base-case PF >=1.20 in each major partition;
4. base-case expectancy >0 and total net >0 in each major partition;
5. POOLED_MAJOR base-case WR >=70%, PF >=1.20, expectancy >0, net >0;
6. POOLED_MAJOR 5bps PF >1.00 and net >0.

August remains telemetry only and cannot rescue a failed cell.

If multiple cells pass, rank **WR first**, then PF, expectancy, 5bps PF. Do not select a non-passing high-WR cell.

## Mandatory assertions
1. Exact M5 EARLY_RECLAIM executed identities, timestamps, and entry prices reproduce unchanged.
2. F55/F50 and E05/E10/E15 geometry is exact.
3. Wick-only stop penetration never exits.
4. Every close-invalidation exit has raw 5m `close < boundary` and exits at that exact close.
5. Every target exit has raw 5m `high >= target` and exits at exact target.
6. Target wins same-bar precedence over later close invalidation.
7. No event after 20:00 UTC changes a result.
8. Raw ETH 5m coverage >=99.5%.
9. Full grid contains exactly cohort_N * 6 base-case trade rows (with paired 5bps metrics).

Research only. Live BBC unchanged. Portfolio one-position lock, leverage, and management remain out of scope until an individual-trade economic cell is supported.
