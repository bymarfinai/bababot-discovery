# BTC Fresh 4H Strong Bull → First Pullback B22D — Preregistration

Status: **PREREGISTERED**  
Date: 2026-08-21

## Question
Test the image-like lifecycle more faithfully than B22B/B22C: a **fresh** 4h strong-uptrend activation is allowed to produce **only the first healthy lower-timeframe pullback/reclaim entry**, then the position is held until an objective reversal state. Separately, identify pre-entry characteristics that distinguish genuine continuation from fakeout.

B22D does not change B22B/B22C results and does not touch live BBC.

## Data / partitions
Binance BTCUSDT USD-M 5m klines, 2020-01-01 through 2026-08-20 inclusive, with OHLC, quote volume, and taker-buy quote volume. Same frozen partitions:
- external: 2020-01-01 to 2021-12-31
- development: 2022-01-01 to 2024-12-31
- reference_validation: 2025-01-01 to 2026-07-29
- August 2026: diagnostic only

All higher-timeframe data are causally resampled. A 1h/4h value becomes available only after that candle closes.

## Strong-uptrend state
EMA20 / EMA50 definition is frozen exactly as B22B/B22C:
- EMA20 > EMA50
- EMA20 rising versus 3 bars ago
- EMA50 rising versus 3 bars ago
- normalized EMA20-EMA50 spread widening versus 3 bars ago
- close > EMA20

A `FRESH_4H_ACTIVATION` occurs only on a completed 4h candle where STRONG(4h) changes False → True.

## First-pullback rule
For every fresh 4h activation, search forward at most **48 hours** and only while the causally available 4h STRONG state remains ON.

Lower-timeframe pullback/reclaim is frozen from B22B:
- preceding lower-TF candle low reaches the EMA20/EMA50 zone;
- that preceding candle does not close below EMA50;
- current lower-TF candle is bullish;
- lower-TF STRONG is ON;
- current close is above EMA20.

Only the **first** qualifying signal after the fresh 4h activation is admitted. Execute at the next lower-TF open. Later pullbacks belonging to the same 4h activation are ignored.

Frozen variants:
- entry TF: `5m`, `15m`
- regime at entry: `R4_FRESH` (4h strong only), `R1H4_FRESH` (1h strong AND 4h strong)
- reversal exit: `X_1H_WEAK`, `X_4H_WEAK`

Reversal definitions:
- X_1H_WEAK = completed 1h close < EMA20 and EMA20 < previous EMA20.
- X_4H_WEAK = completed 4h close < EMA20 and EMA20 < previous EMA20.

Execution is always next entry-TF open after the reversal state becomes available. No fixed TP and no stop are introduced in B22D.

## Strategy evaluation / selection
Development eligibility:
- N >= 30
- WR >= 55%
- PF >= 1.20
- median return > 0
- median MAE > -2.0%

Select at most one champion by PF; ties within 0.02 use higher WR then larger N.

Frozen OOS replication gate in BOTH external and reference_validation:
- N >= 15
- WR >= 60%
- PF >= 1.20
- median return > 0

High-precision clue additionally requires WR >= 80% with N >= 15 in each OOS partition.

## Primary fakeout label
Fakeout analysis is event-level and independent of the selected strategy champion.

At each admitted first-pullback entry, freeze the latest causally available 1h ATR14 (absolute price units).
- `FOLLOWTHROUGH`: price reaches entry + 1.0 × ATR14(1h) before 1h weakness occurs, within 24h.
- `FAKEOUT`: causally available X_1H_WEAK occurs first, before the +1.0 × ATR14(1h) target, within 24h.
- Same-time / same-5m-bucket ambiguity is conservatively classified FAKEOUT.
- If neither happens within 24h, label `AMBIGUOUS` and exclude it from discriminator fitting.

This label is for mechanism forensics, not a trading TP.

### Frozen forensic cohort
To avoid duplicate copies of the same 4h activation across multiple entry/regime variants, the **primary discriminator fitting cohort is `5m / R4_FRESH` only**. The 15m and R1H4 variants are still reported as secondary label-rate diagnostics, but they are not pooled into the SMD screen or decision-tree fit.

## Frozen pre-entry forensic features
Only information available by the signal close may be used.

### Fresh-regime geometry
- hours since fresh 4h activation
- number of completed 4h bars since activation
- 4h EMA20-EMA50 spread / close
- 4h spread change versus 3 bars ago
- 4h EMA20 3-bar slope / close
- 4h EMA50 3-bar slope / close
- 4h close extension above EMA20
- 4h ATR14 / close

### 1h support
- 1h STRONG boolean
- 1h EMA20-EMA50 spread / close
- 1h EMA20 3-bar slope / close
- 1h EMA50 3-bar slope / close
- 1h close extension above EMA20
- 1h 3-bar return
- 1h ATR14 / close

### Pullback / reclaim quality
- prior lower-TF low position inside EMA20↔EMA50 band (0 = EMA50, 1 = EMA20)
- prior lower-TF close extension versus EMA20
- reclaim candle body / range
- reclaim candle close-location value `(close-low)/(high-low)`
- reclaim close extension versus EMA20
- reclaim candle range / close
- lower-TF EMA spread / close
- lower-TF EMA20 3-bar slope / close

### Aggregate flow / participation
Using only completed Binance futures 5m klines before/through the signal close:
- signed taker quote-flow ratio over trailing 15m
- signed taker quote-flow ratio over trailing 30m
- signed taker quote-flow ratio over trailing 60m
- trailing 60m quote-volume divided by its causal prior-24h median
- trailing 60m price return

No L2/order-book claim is permitted from these aggregate fields.

## Frozen fakeout-forensic procedure
1. Development only: compare FOLLOWTHROUGH vs FAKEOUT feature medians and standardized mean differences (SMD).
2. A numeric/boolean feature is a `STABLE_DISCRIMINATOR` only if:
   - |SMD| >= 0.50 in development;
   - same SMD sign in external and reference_validation;
   - |SMD| >= 0.15 in each OOS partition;
   - each class has N >= 10 in every tested partition.
3. Fit exactly one shallow development-only `DecisionTreeClassifier(max_depth=2, min_samples_leaf=15, class_weight='balanced', random_state=20260821)` using the frozen feature list.
4. Select the development leaf with highest FOLLOWTHROUGH rate, requiring N >= 15.
5. Report its FOLLOWTHROUGH rate, baseline rate, lift, and N in external and reference_validation. This tree is forensic only and is not promoted to live trading in B22D.

## Interpretation rule
A failed strategy gate does not invalidate the descriptive claim that a feature distinguishes fakeouts. Conversely, a fakeout discriminator does not become a trading filter unless it replicates OOS and is preregistered in a later experiment.
