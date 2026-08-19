# BTC Friday C9A — Spot-vs-Futures Lead/Lag Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched.**

## Objective
Test whether actual Binance spot BTC order flow leads the BTCUSDT perpetual strongly enough to identify a high-probability Friday futures catch-up trade.

This is a new information set relative to C0-C8: it uses synchronized **spot-market price return and aggressive taker flow** against the perpetual futures candle. Premium Index and funding are not substitutes for actual spot order flow.

## Universe and execution
- BTCUSDT Binance Spot 15m + BTCUSDT USD-M futures 15m
- WIB calendar Friday signal candles
- signal candle must be completed
- entry = next futures 15m open
- TP=SL=1.30%
- max hold=24 x15m =6h
- modeled round-trip fee=0.15%
- reference notional=$500
- win = net PnL>0

## Frozen synchronized features
For every aligned completed 15m candle:
- `spot_ret15 = spot_close/spot_open - 1`
- `fut_ret15 = futures_close/futures_open - 1`
- `lead_spread = spot_ret15 - fut_ret15`
- `spot_taker_imbalance = 2*spot_taker_buy_quote/spot_quote_volume - 1`
- `fut_taker_imbalance = 2*fut_taker_buy_quote/fut_quote_volume - 1`
- `flow_divergence = spot_taker_imbalance - fut_taker_imbalance`

## Frozen lead anomaly
`lead_z7d` = current completed `lead_spread` standardized against the previous 7 calendar days of aligned completed 15m `lead_spread`, excluding current observation, minimum 192 prior observations.

No alternative lookback or sigma threshold is allowed after result.

## Frozen C9A event
### LONG_SPOT_LEADS
Trade LONG iff ALL:
1. `lead_z7d >= +2.0`
2. `spot_ret15 > 0`
3. `spot_taker_imbalance > 0`
4. `flow_divergence > 0`

### SHORT_SPOT_LEADS
Trade SHORT iff ALL:
1. `lead_z7d <= -2.0`
2. `spot_ret15 < 0`
3. `spot_taker_imbalance < 0`
4. `flow_divergence < 0`

Interpretation: spot has made an unusually stronger directional move than futures and aggressive spot flow points the same way; the test asks whether futures subsequently catches up.

The +/-2 sigma, zero-return, zero-imbalance and zero-divergence boundaries are frozen natural thresholds.

## Validation
Chronological split by all unique Friday dates:
- first70%=discovery
- last30%=validation

Promotion to `BTC_FRIDAY_C9A_SPOT_LEAD_80_CANDIDATE` requires ALL:
1. discovery N>=12 and WR>=80%
2. validation N>=10 and WR>=80%
3. full N>=25 and WR>=80%
4. validation PnL>0 and PF>1
5. >=3/4 chronological blocks with >=5 trades each have WR>50% and PnL>0
6. zero alignment/causality/integrity violations

LONG/SHORT are descriptive only and cannot rescue a failed combined result.

## Conditional C9B
If C9A rejects, one follow-up is authorized: add the frozen spot-futures features to the exact C6 expanding selective model, keep first52 Friday warmup, same model hyperparameters, at most one candidate/Friday and fixed p>=0.80. No threshold lowering.

## Guardrails
- no lead-z threshold sweep
- no 1d/3d/14d/30d lookback sweep
- no direction-only rescue
- no flow magnitude optimization
- no TP/SL/hold/fee rescue
- no post-result tree rule
- no transfer to other coins until BTC passes
- historical WR is not a future guarantee
