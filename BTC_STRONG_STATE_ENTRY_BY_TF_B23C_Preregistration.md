# BTC Strong-State Entry by Timeframe B23C — Preregistration

## Purpose
Determine how a chart-native STRONG uptrend should be entered on 5m, 15m, 1h, and 4h without restricting the universe to pullback/reclaim setups.

The core hypothesis is precision-first: once a genuine STRONG state has formed, a long entered near the beginning of that state should rarely require a hard stop because the position is cut dynamically when STRONG structure first breaks. Losses, when they occur, should therefore be relatively small.

This experiment is research-only. Live BBC remains untouched.

## Data and partitions
Use the same causal BTCUSDT 5m source and chronological partitions as B23A/B23B:
- external: 2020-01-01 to 2021-12-31
- development: 2022-01-01 to 2024-12-31
- reference_validation: 2025-01-01 to 2026-07-29
- august: 2026-08-01 to 2026-08-20 diagnostic only

All 15m/1h/4h bars are causally resampled from the 5m source.

## Frozen STRONG definition
Reuse B22B/B23A exactly:
- EMA20 > EMA50
- EMA20 rising over 3 completed bars
- EMA50 rising over 3 completed bars
- EMA20-EMA50 normalized spread wider than 3 bars earlier
- close > EMA20

No future data may be used to classify STRONG.

## Fresh episode
A fresh STRONG episode begins on a completed candle where STRONG=True and the previous completed candle was not STRONG.

Overlapping trades are not allowed within the same entry variant/timeframe. A new trade may only begin after the prior trade has exited.

## Frozen entry variants
For every timeframe, test only these three variants:

1. `E0_ONSET`
   - Signal on the first completed STRONG candle of a fresh episode.
   - Execute LONG at the next candle open.

2. `E1_CONFIRM1`
   - Fresh STRONG onset followed by one additional completed candle that is also STRONG.
   - Execute LONG at the next candle open.

3. `E2_CONFIRM2`
   - Fresh STRONG onset followed by two additional consecutive completed STRONG candles.
   - Execute LONG at the next candle open.

If the required confirmation candle is not STRONG, that episode produces no entry for that variant. There is no pullback requirement.

## Frozen dynamic exit
`EXIT_FIRST_NON_STRONG`
- After execution, inspect every completed candle on the entry timeframe.
- HOLD while STRONG=True.
- On the first completed candle with STRONG=False, exit at the next candle open.
- No fixed TP.
- No fixed holding horizon.
- No hard stop is applied in this experiment; adverse excursion is measured explicitly instead.

This exit intentionally asks whether a correct STRONG detector can keep losses small by cutting as soon as the chart no longer satisfies the strong-uptrend shape.

## $10 / 50x model
For reporting only:
- margin = $10
- leverage = 50x
- notional = $500
- gross trade PnL = unlevered price return × $500

Also report an **illustrative fee sensitivity** using a frozen 0.08% round-trip fee on notional (0.04% each side):
- fee sensitivity cost = $0.40 per round trip
- net-sensitive PnL = gross PnL - $0.40

This is not a claim about the user's actual exchange/account fee. Funding and slippage are excluded and must be stated.

## Metrics
For each partition × timeframe × entry variant:
- N trades
- gross WR (`return > 0`)
- gross PF
- mean / median unlevered return
- median winner return
- median loser return
- p10 loser return (10th percentile among losing trades)
- median MFE / MAE
- p10 MAE
- median bars held
- maximum losing streak
- $10/50x gross mean PnL/trade
- $10/50x gross median PnL/trade
- fee-sensitive WR
- fee-sensitive PF
- fee-sensitive mean PnL/trade
- percent of trades with MAE <= -0.50%, -1.00%, -1.50%

## Precision-first development selection per timeframe
Choose one development candidate separately for each timeframe using:
1. minimum sample: 5m >= 500; 15m >= 200; 1h >= 50; 4h >= 20;
2. highest gross WR;
3. if WR difference <= 1 percentage point, prefer smaller absolute median loser return;
4. then higher gross PF;
5. then larger N.

Do not use external/reference_validation/August to select.

## Replication interpretation
A timeframe candidate is a `REPLICATED_PRECISION_CLUE` only if in both external and reference_validation:
- N >= 30 for 5m/15m, >= 20 for 1h, >= 10 for 4h;
- gross WR >= 70%;
- gross PF >= 1.20;
- median loser return > -0.50%;
- p10 MAE > -1.50%.

A `HIGH_PRECISION_CLUE` additionally requires gross WR >= 85% in both external and reference_validation.

Failing these gates does not invalidate STRONG-state persistence; it only means this specific entry/exit rule is not a sufficiently precise trade rule.

## Anti-overfit rules
- No threshold changes after results are observed.
- No additional confirmation variants in B23C.
- No higher-TF filters in B23C.
- No silent TP/SL insertion.
- No promotion to live BBC from this experiment alone.
