# B27CU — BTC 24H SHORT Clock × Regime EMA Filter Anatomy — Preregistration

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test whether a causal 1H EMA trend filter improves the existing F05 SHORT setup differently across each of the six 4H clock zones and each pre-existing 4H regime state (BULL / BEAR / SIDEWAYS).

B27CU is **anatomy/filter research only**. It does not optimize SL, runner, entry price, target depth, regime definitions, or clock inclusion. Trading WR/PF/expectancy/PnL are N/A.

External and reference_validation have already been inspected in this research lineage, so they are reused-data confirmation only, not untouched OOS. No live/production BBC change is authorized.

## Frozen source / identity
Use `BTC_24H_CLOCK_TP_DEPTH_B27CR_Detail.csv` and the exact B27CR clock-target map:
- 00-04 UTC / 07-11 WIB -> T5
- 04-08 / 11-15 -> T15
- 08-12 / 15-19 -> T15
- 12-16 / 19-23 -> T10
- 16-20 / 23-03 -> T10
- 20-00 / 03-07 -> T15

Select exactly one B27CR row per source event using that clock's frozen target. Expected source identity: external 202 / development 333 / reference_validation 194 / pooled major 729. Expected F05 fills: external 183 / development 297 / reference_validation 173 / pooled major 653.

Raw 5m data identity must be exactly 698,112 rows with 100% coverage.

## Frozen causal EMA construction
Build 1H candles from raw 5m BTCUSDT data using UTC hour boundaries. A 1H candle is usable only after all twelve constituent 5m candles have completed.

On completed 1H closes compute:
- EMA20 with span 20, adjust=False;
- EMA50 with span 50, adjust=False;
- EMA50 slope reference = EMA50 three completed 1H bars earlier.

For each event at `reclaim_complete_ts`, use only the most recent 1H candle whose completion timestamp is <= `reclaim_complete_ts`.

The observed reclaim price is the completed 5m close immediately preceding `reclaim_complete_ts`; assert that this bar exists and has completed by the decision time.

No current/incomplete 1H candle may enter EMA calculation or gate state.

## Frozen EMA gates
Only these candidates are allowed:
1. `BASE`: no EMA filter.
2. `EMA50_DOWN`: reclaim close < EMA50 AND EMA50 < EMA50 three completed 1H bars earlier.
3. `EMA20_50_DOWN`: all `EMA50_DOWN` conditions AND EMA20 < EMA50.

No other EMA length, slope lookback, price relation, OR/AND combination, or threshold may be introduced after results are seen.

## Frozen outcome
Entry and target outcomes are inherited exactly from B27CR selected-target anatomy. For every gate/cell report:
- source events;
- gate-pass events and pass rate;
- F05 fills;
- retained fills vs BASE;
- target reached N / target-per-fill;
- target yield/source;
- High failure N / High-failure-per-fill;
- unresolved N / unresolved-per-fill.

These are structural target statistics, **not trading WR**.

## Required grouping
Report all 18 clock × regime cells independently first:
- six clocks: 00-04, 04-08, 08-12, 12-16, 16-20, 20-00 UTC;
- three regimes: BULL, BEAR, SIDEWAYS.

Also report regime-only, clock-only, and pooled aggregates secondarily.

No clock or regime cell may be deleted because its result is poor.

## Development-only cell selection
For each clock × regime cell, BASE is always eligible. A non-BASE EMA gate may be selected only if all are true in development:
1. BASE filled N >= 10;
2. gate filled N >= 8;
3. retained fills >= 50% of BASE fills;
4. target/fill >= BASE target/fill + 5.0 percentage points;
5. High-failure/fill <= BASE High-failure/fill.

Among eligible EMA gates select highest development target/fill. Tie-break: lower High-failure/fill, then higher retained fills, then simpler `EMA50_DOWN` before `EMA20_50_DOWN`.

If the cell lacks sufficient data or no EMA gate qualifies, select BASE. No cell is dropped.

## Reused-data confirmation
Apply the frozen development-selected cell map unchanged to external and reference_validation.

A selected non-BASE cell is `REUSED_CONFIRMED` only if both external and reference_validation have >=5 selected-gate fills and in both partitions:
- target/fill >= that cell's BASE target/fill;
- High-failure/fill <= BASE;
- retained fills >=40% of BASE.

Small-cell confirmation is explicitly weak evidence and cannot authorize production.

## Overall interpretation gate
`B27CU_CLOCK_REGIME_EMA_REUSED_CANDIDATE` requires:
1. audit PASS;
2. at least 4 of 18 cells select a non-BASE EMA gate;
3. at least half of selected non-BASE cells are reused-confirmed;
4. development selected-map pooled target/fill >= universal BASE +5pp;
5. pooled-major selected-map target/fill > BASE;
6. pooled-major retained fills >=60% of BASE fills;
7. pooled-major High-failure/fill <= BASE;
8. no cell exclusion.

Otherwise verdict: `B27CU_CLOCK_REGIME_EMA_NOT_SUPPORTED`.

Even a candidate PASS remains reused-data anatomy evidence only. A separate preregistered economic experiment would be required before interpreting WR/PF/PnL.

Research only. Live BBC unchanged.
