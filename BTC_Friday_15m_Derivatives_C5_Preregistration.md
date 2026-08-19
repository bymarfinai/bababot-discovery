# BTC Friday C5 — 15m Candle + Derivatives-State Identifier

**FROZEN BEFORE C4 RESULT. Execute only if C4 does not earn its 80% gate. Research-only; live BBC untouched.**

## Objective
Test a materially new information set closer to a futures-market robot: completed BTC Friday 15m candle plus causally available open-interest and trader-positioning metrics. The goal remains one human-readable shallow rule with executable observed WR >=80% that survives Friday-level chronological validation.

## Data / timing
- BTCUSDT USD-M perpetual
- official Binance Data Vision 15m klines plus official daily `metrics` archives
- sample: `2023-12-02T00:00:00Z` through `2026-07-30T00:00:00Z` exclusive, matching the established historical research cutoff
- signal candle open timestamp converted to Asia/Jakarta must be Friday
- entry = immediately following 15m open
- derivatives metrics at a signal use the latest metrics row with timestamp **strictly earlier than entry time**; never nearest-forward alignment
- metric row must be no more than 15 minutes stale
- split by unique Friday date: first 70% discovery / final 30% validation

## Frozen execution
Two modes independently:
1. CONTINUATION: green signal -> LONG, red -> SHORT
2. REVERSAL: green -> SHORT, red -> LONG

Both: TP 1.30%, SL 1.30%, max hold 6h (24 x 15m), adverse-first dual touch, 0.15% round-trip cost, $500 reference notional, win = net PnL > 0.

## Frozen causal features
### Candle / price
1. `signal_ret`
2. `body_ratio`
3. `upper_ratio`
4. `lower_ratio`
5. `close_pos`
6. `range_open`
7. `prior1h_ret`

### Derivatives metrics
Using the latest valid metrics row before entry and completed prior metric rows:
8. `top_vs_global = log(top_trader_position_long_short_ratio) - log(global_account_long_short_ratio)`
9. `top_pos_chg15 = 15m log change in top-trader position ratio`
10. `global_chg15 = 15m log change in global-account ratio`
11. `taker_log = log(taker long/short volume ratio)`
12. `oi_chg15 = 15m log change in open-interest value`
13. `oi_chg60 = 60m log change in open-interest value`

No funding, liquidation, EMA, support/resistance, hour filter, learned embeddings, or post-entry variables.

Discovery-only medians impute nonfinite feature values; same frozen medians apply to validation.

## Frozen models
Two `DecisionTreeClassifier`s, one per execution mode:
- criterion gini
- max_depth 2
- min_samples_leaf 80
- random_state 20260819
- no class weighting
- no hyperparameter sweep

## Candidate / promotion
A positive discovery leaf is eligible only at N>=80, WR>=80%, PnL>0, PF>1. Choose exactly one across both models by WR, N, PF, mode lexical, leaf id. Only that leaf sees promotion validation.

`BTC_FRIDAY_C5_DERIVATIVES_80_CANDIDATE` requires:
- discovery N>=80, WR>=80%
- validation N>=30, WR>=80%
- combined N>=120, WR>=80%
- validation expectancy>0 and PF>1
- validation WR > same-mode unconditional validation WR
- at least 3/4 chronological blocks with >=15 selected trades have positive PnL
- zero causality/integrity violations

Otherwise `REJECT_C5_DERIVATIVES_IDENTIFIER`.

## Guardrail
No feature/threshold/tree/metric-staleness/TP-SL/hour changes and no runner-up rescue after C5. A failed C5 closes this exact derivatives-state identifier.