# BTC Multi-Timeframe Strong Trend State B20 — Preregistration

## Purpose
Test the user's clarified hypothesis: BTC sometimes enters a persistent **STRONG trend state** visible simultaneously on small, medium, and large timeframes, and the strategy should keep trading in the trend direction while that state remains ON instead of searching for one isolated weekly setup.

This is materially different from prior single-entry EMA/MTF confirmation and fixed-opportunity regime-gating studies. B20 treats trend as a persistent causal **episode/state machine** and permits repeated non-overlapping re-entry while the same state remains ON.

Research only. Live BBC must remain untouched.

## Data and causal timing
- Instrument: Binance USD-M BTCUSDT perpetual.
- Source: official Binance Futures 15m klines with OHLC, quote volume, and taker-buy quote volume.
- Small / medium / large TF: **15m / H1 / H4**.
- The chart reference uses **MA(7), MA(25), MA(99)**, therefore B20 uses simple moving averages (SMA), not EMA.
- Every state decision is made for a 15m bar open using information fully completed before that open.
- 15m features are available only after their 15m bar closes; H1 features only after the H1 bar closes; H4 features only after the H4 bar closes. Higher-TF state is forward-filled only after its causal availability timestamp.

Frozen partitions by entry/episode timestamp:
- external: 2020-01-01 <= t < 2022-01-01
- development: 2022-01-01 <= t < 2025-01-01
- reference_validation: 2025-01-01 <= t < 2026-07-30
- August 2026: diagnostic only, 2026-08-01 <= t < 2026-08-20

## Core stack semantics
A pullback below MA7 does **not** turn the trend off by itself. This is intentional because the supplied 15m screenshot shows price slightly below MA7 while MA7 > MA25 > MA99 and price remains well above MA25.

For LONG on each of 15m, H1, and H4:
- `MA7 > MA25 > MA99`
- completed close > MA25

SHORT is the exact mirror:
- `MA7 < MA25 < MA99`
- completed close < MA25

## Frozen progressive state variants
Exactly four variants are tested. No threshold search is allowed.

### S1_STACK
Core stack holds in the same direction on **all three TFs: 15m + H1 + H4**.

### S2_STACK_SLOPE
S1 plus MA25 and MA99 slopes are aligned on all TFs:
- 15m: MA25/MA99 now versus 4 completed 15m bars earlier;
- H1: MA25/MA99 now versus 3 completed H1 bars earlier;
- H4: MA25/MA99 now versus 2 completed H4 bars earlier.
LONG requires positive slopes; SHORT requires negative slopes.

### S3_STACK_MOMENTUM
S2 plus price momentum is aligned using the same frozen lags:
- 15m close versus 4 bars earlier;
- H1 close versus 3 bars earlier;
- H4 close versus 2 bars earlier.
LONG requires positive returns; SHORT requires negative returns.

### S4_STACK_MOMENTUM_FLOW
S3 plus futures taker-flow confirmation immediately before entry:
- completed 1h taker imbalance;
- completed 3h taker imbalance;
where `imbalance = 2 * taker_buy_quote / quote_volume - 1`.
LONG requires both > 0; SHORT requires both < 0. Magnitude thresholds are prohibited.

## State episode semantics
For each variant:
- State is `LONG`, `SHORT`, or `OFF` at every tradable 15m open.
- An episode begins when state changes from OFF/opposite to LONG or SHORT.
- It ends at the first 15m open where that same directional state is no longer true.
- No grace period, hysteresis, minimum-duration filter, or later rescue is allowed.
- Episode duration and weekly state coverage are reported diagnostically.

## Continuous execution — "trade while STRONG is ON"
- Maximum one open position at a time.
- When flat and state is LONG/SHORT at a 15m open, enter at that 15m open in the state direction.
- Gross favorable barrier: +1.15% for LONG / -1.15% for SHORT.
- Gross adverse barrier: -0.85% for LONG / +0.85% for SHORT.
- Modeled round-trip fee: 0.15%, giving approximately net +1% at TP and -1% at SL.
- Same-15m TP+SL ambiguity is adverse-first.
- If TP/SL occurs intrabar and the state is still ON at that bar's completed close, the strategy may re-enter at the next 15m open.
- If the directional state turns OFF/opposite before TP/SL, close at the next 15m open and charge the same fee. A newly active opposite state may open at that same next open after the old position is closed.
- No overlapping positions and no intrabar re-entry.
- Partition-end positions are force-closed for accounting and labeled EOP.

This repeated-entry policy is the key B20 hypothesis and is not a weekly first-signal router.

## Episode directional diagnostic
Independently of repeated trading, evaluate the first entry of every state episode using the same +1.15% / -0.85% barriers until the episode ends. Record TP / SL / OFF. This measures whether the detector itself identifies a directionally useful state before evaluating repeated harvesting.

## Metrics
For every variant and partition report:
- episodes and LONG/SHORT episode counts;
- median/mean episode duration hours;
- weeks containing state / complete weeks;
- episode first-entry TP rate;
- continuous trades and LONG/SHORT trades;
- TP / SL / OFF / EOP exits;
- positive-trade rate (`net_ret > 0`);
- TP-hit rate;
- mean and total net return;
- profit factor;
- max losing streak;
- weeks with trades / complete weeks;
- positive-week rate among traded weeks.

## Development selection
A variant is eligible for PRIMARY only if development has >=100 continuous trades and >=50 episodes.
Rank eligible variants using development only:
1. higher positive-trade rate;
2. higher profit factor;
3. higher episode first-entry TP rate;
4. higher weekly trade coverage;
5. lexical rule name.
Freeze PRIMARY before external/reference-validation interpretation. All four variants must still be reported OOS.

## Gates
`B20_STRONG_STATE_USEFUL` PASS requires PRIMARY in BOTH external and reference validation:
- >=100 continuous trades;
- positive expectancy per trade;
- PF > 1.20;
- positive-trade rate >=60%;
- positive-week rate >=65% among weeks with trades;
- episode first-entry TP rate >=65%.

`B20_HIGH_PRECISION` PASS requires in BOTH external and reference validation:
- positive-trade rate >=75%;
- PF > 1.50;
- >=75 trades.

`B20_WEEKLY_100_DIAGNOSTIC` is aspirational only: every complete week has >=1 trade and every traded week has positive aggregate net return in both OOS partitions.

## Prohibited rescue
After results are visible, do not change:
- MA lengths 7/25/99;
- SMA to EMA or another MA type;
- 15m/H1/H4 timeframe set;
- close-vs-MA25 stack rule;
- slope lags 4 / 3 / 2;
- momentum lags 4 / 3 / 2;
- 1h/3h flow windows or zero thresholds;
- immediate OFF semantics;
- repeated-entry policy;
- TP/SL/fee;
- partitions.

No ADX, RSI, ATR, volume threshold, VAH, liquidity-sweep, regime-ML, session, day-of-week, or post-result threshold rescue belongs to B20 V1. Historical performance is not a guarantee of future performance.
