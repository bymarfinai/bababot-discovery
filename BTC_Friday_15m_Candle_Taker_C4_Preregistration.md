# BTC Friday C4 — 15m Candle + Taker-Flow Identifier

**FROZEN BEFORE RESULT. Research-only; live BBC untouched.**

## Objective
After pure candle morphology failed on 5m/15m/1h and a fixed 15m two-candle sequence failed, test one materially new information set: whether the completed 15m candle plus causal participation/taker flow identifies an executable BTC Friday trade with observed WR >=80% that survives chronological holdout.

## Data / calendar
- BTCUSDT USD-M perpetual
- official Binance Data Vision 15m klines, including quote volume and taker-buy quote volume
- `2023-12-02T00:00:00Z` to `2026-08-19T00:00:00Z` exclusive
- signal candle open timestamp converted to Asia/Jakarta must be Friday
- exact doji excluded
- entry = immediately following 15m open
- split by unique Friday date: first 70% discovery, final 30% validation; no Friday appears in both.

## Frozen execution
Two modes are modeled independently:
1. CONTINUATION: green signal -> LONG, red signal -> SHORT
2. REVERSAL: green signal -> SHORT, red signal -> LONG

For both:
- TP 1.30%
- SL 1.30%
- max hold 6h = 24 future 15m bars
- adverse-first on same-15m dual TP/SL touch
- round-trip modeled cost 0.15%
- $500 reference notional
- win = net PnL > 0

## Strictly causal frozen features
All features use the completed signal candle or bars completed before it:
1. `signal_ret` = close/open - 1
2. `body_ratio`
3. `upper_ratio`
4. `lower_ratio`
5. `close_pos`
6. `range_open`
7. `prior1h_ret` = signal open relative to close four 15m bars earlier
8. `taker_imbalance` = 2*taker_buy_quote/quote_volume - 1 for signal candle
9. `taker_delta_vs_prior3` = current taker imbalance - median prior 3 completed 15m imbalances
10. `rel_quote_volume_24h` = signal quote volume / median quote volume of prior 96 completed 15m bars
11. `rel_range_prior12` = signal range/open / median range/open of prior 12 completed 15m bars

No EMA, funding, OI, long/short ratio, liquidation, support/resistance, hour filter, or post-entry feature.

Nonfinite values are imputed with discovery-only feature medians; validation uses the frozen discovery medians.

## Frozen models
Fit exactly two `DecisionTreeClassifier`s on discovery only: one for CONTINUATION outcome and one for REVERSAL outcome.
- criterion = gini
- max_depth = 2
- min_samples_leaf = 100
- random_state = 20260819
- no class weights
- no hyperparameter sweep

## Candidate leaf selection
For each tree, positive-prediction discovery leaf is eligible only if:
- discovery N >=100
- discovery observed WR >=80%
- discovery PnL >0
- discovery PF >1

Across both trees choose exactly one eligible leaf by highest discovery WR, then N, PF, mode lexical order, leaf id. Only this selected leaf may be evaluated for promotion on validation. No runner-up rescue.

## Promotion gate
`BTC_FRIDAY_C4_TAKER_80_CANDIDATE` only if selected leaf has:
1. discovery N>=100 and WR>=80%;
2. validation N>=40 and WR>=80%;
3. combined N>=150 and WR>=80%;
4. validation expectancy>0 and PF>1;
5. validation WR exceeds same-mode unconditional validation WR;
6. at least 3/4 chronological full-history blocks containing >=20 selected trades have positive PnL.

Otherwise `REJECT_C4_TAKER_IDENTIFIER`.

## Guardrail
No tree depth/min-leaf/feature/threshold/TP-SL/time filter changes after C4. A failed C4 closes this exact candle+taker identifier; do not inspect a runner-up leaf on validation to rescue it.