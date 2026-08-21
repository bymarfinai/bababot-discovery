# BTC Strong Uptrend Lifecycle B22B — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Question
Can the visual logic in the supplied strong-uptrend reference be turned into a causal BTC setup that enters during trend initiation/healthy pullback and exits only when reversal evidence appears, without a fixed take-profit?

## Data
- Binance USD-M BTCUSDT 5m public archive.
- Analysis clock: 2020-01-01 through 2026-08-21 UTC research cutoff.
- Higher timeframes are causally resampled from 5m: 15m, 1h, 4h.
- Indicators are computed only on completed candles. Any signal on candle `t` can enter/exit no earlier than the next candle open.
- No CoinDesk L2/tick data is required for B22B.

## Frozen partitions
- External: 2020-01-01 to 2022-01-01
- Development: 2022-01-01 to 2025-01-01
- Reference validation: 2025-01-01 to 2026-07-30
- August diagnostic: 2026-08-01 to 2026-08-21

Each partition is simulated independently. Positions are force-closed at the final available open of that partition so development selection cannot use validation-period prices.

## Moving averages
Use EMA20 and EMA50 on each tested timeframe.

### Strong bull state
For a completed candle `t`:
1. `EMA20 > EMA50`.
2. `EMA20[t] > EMA20[t-3]`.
3. `EMA50[t] > EMA50[t-3]`.
4. The normalized spread `(EMA20-EMA50)/close` is larger than it was 3 candles earlier.
5. `close > EMA20`.

This directly encodes the reference image's rising fast/slow averages plus a widening gap. No future state is used.

## Frozen entry archetypes
### A — CROSSOVER_INIT
Signal at candle `t` when:
- EMA20 crosses from `<= EMA50` to `> EMA50` on `t`;
- both EMA20 and EMA50 are rising versus 3 candles earlier;
- `close[t] > EMA20[t]`.
Entry: next candle open.

### B — PULLBACK_RECLAIM
Signal at candle `t` when:
- strong bull state is true on `t`;
- the immediately preceding candle `t-1` reached the MA20/MA50 pullback zone: `low[t-1] <= EMA20[t-1]` and `low[t-1] >= EMA50[t-1]`;
- `close[t-1] >= EMA50[t-1]` (pullback did not structurally break the slow average);
- current candle is bullish and reclaims/holds above EMA20: `close[t] > open[t]` and `close[t] > EMA20[t]`.
Entry: next candle open.

Only one position per timeframe may be open at once; subsequent entry signals while in a position are ignored.

## Frozen reversal exits
No fixed TP is used. Four exit definitions are compared; all exit on the next candle open after a completed-candle reversal signal.

- `E_FAST_20`: first close below EMA20.
- `E_WEAKEN_20`: close below EMA20 **and** EMA20 is lower than one candle earlier.
- `E_STRUCT_50`: first close below EMA50.
- `E_BEAR_CROSS`: EMA20 crosses from `>= EMA50` to `< EMA50`.

No stop-loss is added in B22B because the experiment is explicitly testing whether reversal-state exits can manage the lifecycle. MFE and MAE are therefore mandatory outputs; unacceptable adverse excursion is a valid reason to reject a setup.

## Timeframes
The exact same definitions are evaluated independently on:
- 5m
- 15m
- 1h
- 4h

## Metrics
For every timeframe × entry archetype × exit rule × partition:
- trade count
- win rate (`return > 0`)
- mean and median trade return
- profit factor
- median holding time
- median MFE
- median MAE
- P90 adverse excursion
- maximum losing streak

Fees/slippage are not included in B22B; therefore very small gross edges cannot be promoted.

## Development-only selection
A candidate is eligible for development selection only if:
- 5m/15m: N >= 100
- 1h: N >= 50
- 4h: N >= 25
- development PF >= 1.20
- development win rate >= 55%
- development median return > 0

Among eligible candidates, select exactly one champion by highest development profit factor; ties within 0.02 PF are broken by higher win rate, then larger N. External and reference-validation results are not used for selection.

## Validation gates
The frozen development champion is considered a **B22B_REPLICATED_CLUE** only if both external and reference-validation independently satisfy:
- N >= 20
- win rate >= 60%
- profit factor >= 1.20
- median return > 0
- median MAE > -2.0%

A **HIGH_PRECISION_CLUE** additionally requires win rate >= 80% in both external and reference validation with N >= 20 each. This is still not a live promotion.

## Interpretation rules
- A high win rate with poor MAE is not acceptable.
- A result driven by a tiny 4h sample is not a robust clue.
- August 2026 is diagnostic only.
- B21/B22A results remain unchanged.
- Live BBC remains untouched.
