# BTC Friday C9B — Spot/Futures Selective Walk-Forward AI Preregistration

**CONDITIONAL, FROZEN BEFORE C9A RESULT. Research-only.**

Run only if C9A rejects.

## Base
Exact C6 expanding Friday protocol and model:
- first52 Friday dates warmup
- train only strictly earlier Friday rows
- separate LONG/SHORT success models
- `HistGradientBoostingClassifier(loss='log_loss', learning_rate=.05, max_iter=100, max_depth=3, min_samples_leaf=30, l2_regularization=1.0, random_state=20260819)`
- at most one top confidence candle/direction per Friday
- TRADE iff raw model confidence >=0.80
- same next-15m-open TP=SL1.30%, hold6h, fee0.15% outcomes

## Base features
Keep all C6 features unchanged.

## Frozen new spot/futures features
Computed from synchronized completed 15m spot and futures candles using only current completed candle and earlier history:
1. `spot_ret15`
2. `spot_ret60`
3. `spot_taker_imbalance`
4. `spot_taker_delta_vs_prior3`
5. `spot_rel_quote_volume_24h`
6. `basis = futures_close/spot_close - 1`
7. `basis_delta15`
8. `basis_delta60`
9. `lead_spread = spot_ret15-futures_ret15`
10. `lead_z7d` using previous7 calendar days excluding current, min192
11. `flow_divergence = spot_taker_imbalance-futures_taker_imbalance`

No alternate spot feature/lookback is allowed after result.

## Gate
`BTC_FRIDAY_C9B_SPOT_FUTURES_AI_80_CANDIDATE` requires:
- pseudo-OOS selected N>=30 at fixed p>=0.80
- WR>=80%
- positive total PnL and expectancy
- PF>1.30
- >=3/4 OOS blocks with >=5 trades, WR>=65%, positive PnL
- zero causality/alignment/training leakage

## Guardrails
No p<0.80, model tuning, direction rescue, feature addition, lead-z/basis threshold optimization, TP/SL/hold change, or transfer to another coin if failed.
