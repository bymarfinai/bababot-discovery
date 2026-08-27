# BNB F85/F15 Transfer — M1 K1 OPP0 Structural Replication — B27ED

**Status:** PREREGISTERED before result-bearing execution.

## Purpose
Test only the first transferable milestone of the frozen BTC F85 LONG / F15 SHORT mechanism on Binance USD-M BNBUSDT perpetual:

> Does one-sided first-boundary pressure (`K1 + OPP0`) create the same causal pre-second-arrival structure on BNB before any F85/F15 entry logic is introduced?

This experiment MUST stop at M1. It does not test F85, F15, entry execution, stop, target, runner, portfolio lock, leverage, or PnL.

B27ED deliberately reuses the exact state engine already used by the ETH M1 transfer lineage. No BNB-specific parameter, clock, threshold, or rule may be introduced after seeing the result.

## Market and event clock
- Instrument: Binance USD-M BNBUSDT perpetual.
- BTCUSDT is the transfer-control benchmark.
- Raw event clock: 5m.
- Data source: Binance Vision futures USD-M archives.
- Analysis span is frozen to `2020-01-01 <= ts < 2026-08-26`, matching the existing transfer M1 implementation.
- Historical partitions are frozen:
  - external: 2020-01-01 to 2022-01-01
  - development: 2022-01-01 to 2025-01-01
  - reference_validation: 2025-01-01 to 2026-07-30
  - august: 2026-08-01 through available data before 2026-08-26
- Weekday execution starts only.

## Frozen clocks transferred from BTC
No clock discovery or sweep is allowed.

LONG habitats:
- ALT_0330: reference start 03:30 UTC; reference duration 5h30; execution 09:00-15:30 UTC.
- RAW_0530: reference start 05:30 UTC; execution 11:00-17:30 UTC.
- LONDON: reference start 08:00 UTC; execution 13:30-20:00 UTC.
- RAW_2330: reference start 23:30 UTC; execution 05:00-11:30 UTC next chronology.

SHORT habitat:
- SHORT_2000: reference start 20:00 UTC; reference duration 5h30; execution 01:30-08:00 UTC next chronology.

M1 deliberately does **not** apply ALT_0330 touch-time filtering or RAW_0530/RAW_2330 range-completion filtering because those belong to later entry-quality milestones, not K1 detection.

## Frozen reference range
For each complete reference window:
- `H = max(high)`
- `L = min(low)`
- require `H > L`
- H/L become immutable when the 5h30 reference completes.

No EMA, ATR, volume, candle-body, wick, trend, regime, order-block, or other indicator is allowed.

## Exact visit definition
Before the first strict boundary breakout:
- High visit: raw 5m `high >= H` and `close <= H`.
- Low visit: raw 5m `low <= L` and `close >= L`.
- Consecutive qualifying bars at one level are one visit episode.
- A new visit requires at least one intervening non-touch bar.
- Strict BULL breakout: completed raw 5m `close > H`.
- Strict BEAR breakout: completed raw 5m `close < L`.
- A pre-breakout bar touching both H and L is `AMBIGUOUS_BOTH_LEVELS` and excluded from K1 qualification.

## M1 LONG state
For each frozen LONG clock:
1. Seek the first distinct High visit.
2. LONG K1 OPP0 is born only if that is High visit #1 while Low visits known at the signal close equal zero.
3. Consecutive High-touch bars remain one K1 episode.
4. Require a completed non-High-touch bar to establish causal leave.
5. After causal leave, classify the first terminal event before execution end:
   - `H2_ARRIVAL`: first later raw 5m `high >= H`;
   - `OPPOSITE_BREAK_BEFORE_H2`: first completed raw 5m `close < L`;
   - `NO_H2_BY_END`: neither occurs;
   - same-bar H2 plus opposite break: `AMBIGUOUS_H2_VS_OPPOSITE_BREAK`.

No F85 is calculated or consulted for eligibility.

## M1 SHORT state
For SHORT_2000:
1. Seek the first distinct Low visit.
2. SHORT K1 OPP0 is born only if that is Low visit #1 while High visits known at the signal close equal zero.
3. Consecutive Low-touch bars remain one K1 episode.
4. Require a completed non-Low-touch bar to establish causal leave.
5. After causal leave, classify the first terminal event before execution end:
   - `H2_ARRIVAL`: first later raw 5m `low <= L`;
   - `OPPOSITE_BREAK_BEFORE_H2`: first completed raw 5m `close > H`;
   - `NO_H2_BY_END`: neither occurs;
   - same-bar H2 plus opposite break: `AMBIGUOUS_H2_VS_OPPOSITE_BREAK`.

No F15 is calculated or consulted for eligibility.

## BTC control
Run the exact same M1 state engine on BTCUSDT over the same clocks and partitions solely as a transfer-control benchmark. BTC control cannot alter any BNB rule.

## Outputs
For BNB and BTC, by side/clock/partition and pooled-major partitions, persist/report:
- complete sessions;
- K1 OPP0 count and rate;
- causal-leave count and rate;
- H2 arrivals after leave;
- opposite-break-before-H2 count;
- ambiguous terminal count;
- no-H2-by-end count;
- H2 rate among clean leaves using all outcomes denominator;
- resolved H2 win rate (`H2 / (H2 + opposite break)`);
- median minutes from causal leave completion to H2.

No trading WR, PF, expectancy, or PnL may be reported because there is no entry in M1.

## Frozen interpretation gate
A specific BNB habitat is tagged `M1_STRUCTURAL_REPLICATION` only if pooled-major:
- K1 OPP0 count >= 30;
- causal-leave count >= 25;
- H2 rate among clean leaves >= 60%;
- resolved H2 win rate >= 65%;
- BNB H2 rate is no more than 10 percentage points below the exact BTC control for the same side/clock.

Overall M1 is `SUPPORTED` only when:
- at least 3 of 4 LONG habitats replicate; and
- SHORT_2000 replicates.

A PASS authorizes only discussion of M2. It does not authorize running M2 automatically.

## Mandatory audits
Execution must abort before result persistence if any fail:
1. Exact existing transfer-M1 state engine is reused; no BNB-specific strategy branch.
2. Reference windows contain exactly 66 raw 5m bars and H/L are frozen before execution.
3. Consecutive same-side touch bars remain one K1 episode.
4. K1 OPP0 uses only opposite visits known at K1 signal completion.
5. Strict breakout bars are not counted as visits.
6. Causal leave requires a completed non-touch bar.
7. H2 search begins only after causal leave completion.
8. No F85/F15/stop/target/runner/indicator is consulted.
9. Raw 5m coverage for both BNB and BTC is >=99.5% across the available analysis span.
10. Existing transfer-M1 synthetic state tests pass before real-data scoring.

**Research only. Stop after B27ED M1 result persistence.**
