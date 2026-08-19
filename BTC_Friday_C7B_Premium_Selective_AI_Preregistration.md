# BTC Friday C7B — Premium-Augmented Selective Walk-Forward AI Preregistration

**CONDITIONAL, FROZEN BEFORE C7A RESULT. Research-only. Live BBC untouched.**

Run C7B only if C7A rejects its frozen promotion gate.

## Objective
Test whether Premium Index information can let a selective model identify at most one BTC Friday 15m trade with pseudo-OOS observed WR >=80% while keeping the exact C6 confidence standard.

## Base design
Keep C6 unchanged:
- BTCUSDT Friday-WIB 15m signals
- next-15m-open execution
- TP=SL1.30%, max hold6h, fee0.15%, $500 reference notional
- first52 unique Fridays warmup
- expanding training: each scored Friday trains only on strictly earlier Fridays
- separate LONG-success and SHORT-success models
- score every eligible 15m Friday signal
- choose at most one highest-confidence pair(direction, candle) per Friday
- TRADE only if confidence >=0.80

## Frozen model
Exactly C6:
`HistGradientBoostingClassifier(loss='log_loss', learning_rate=0.05, max_iter=100, max_depth=3, min_samples_leaf=30, l2_regularization=1.0, random_state=20260819)`.

No model hyperparameter change is allowed.

## Frozen base features
All C6 causal features:
- signal_ret
- body_ratio
- upper_ratio
- lower_ratio
- close_pos
- range_open
- prior1h_ret
- taker_imbalance
- taker_delta_vs_prior3
- rel_quote_volume_24h
- rel_range_prior12
- top_vs_global
- top_pos_chg15
- global_chg15
- taker_log
- oi_chg15
- oi_chg60

## New premium features
All computed using the completed Premium Index 15m signal candle plus only earlier premium history:
1. `premium_close`
2. `premium_z7d`: current completed premium close versus previous 7 calendar days, excluding current observation, min192
3. `premium_delta15`: current premium close minus previous completed 15m premium close
4. `premium_delta60`: current premium close minus premium close at or before 60m earlier
5. `premium_range_z7d`: current premium candle high-low versus previous-7d premium-range mean/std, excluding current, min192

No alternate premium lookback or feature is authorized after result.

## Missing data
Each training fold fills nonfinite feature values using medians calculated only from that fold's training rows, exactly as C6. A scored row must have a Premium Index signal candle at the exact signal timestamp.

## Promotion gate
`BTC_FRIDAY_C7B_PREMIUM_AI_80_CANDIDATE` requires ALL:
1. >=30 pseudo-OOS selected trades at fixed confidence >=0.80
2. observed pseudo-OOS WR >=80%
3. total pseudo-OOS PnL >0
4. expectancy/trade >0
5. PF >1.30
6. >=3/4 chronological OOS blocks each containing >=5 trades, WR >=65%, PnL >0
7. zero source-outcome mismatch, current-Friday training leakage, timestamp causality violation, or premium-alignment integrity violation

Calibration buckets are descriptive only. A favorable lower-confidence bucket may NOT lower the 0.80 threshold after result.

## Guardrails
- no threshold reduction below0.80
- no alternate model/tree/neural network rescue
- no hyperparameter tuning
- no premium z/lookback sweep
- no LONG-only or SHORT-only rescue
- no more than one selected trade per Friday
- no TP/SL/hold/fee change
- no same-Friday training rows
- no transfer to other coins unless frozen BTC gate passes
- observed historical 80% is not a guarantee of future wins
