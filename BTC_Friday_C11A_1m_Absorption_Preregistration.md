# BTC Friday C11A — 1-Minute Absorption Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched.**

## Objective
Test whether intrabar absorption in the final 5 minutes of a completed 15m Friday candle identifies a high-probability reversal that cannot be observed from 15m OHLC alone.

New information set: official Binance USD-M BTCUSDT **1m** klines and 1m taker-buy quote volume inside the signal candle.

## Universe / execution
- BTCUSDT USD-M perpetual
- every completed 15m signal candle during WIB calendar Friday
- entry = next 15m open
- TP=SL1.30%
- max hold6h
- modeled round-trip fee0.15%
- $500 reference notional
- win = net PnL>0

## Frozen microstructure measurements
For the final 5 completed 1m bars inside each 15m signal candle:
- `ret5 = final_1m_close / first_of_final5_open - 1`
- `flow5 = 2*sum(taker_buy_quote)/sum(quote_volume)-1`
- `qv5 = sum(quote_volume)`

From non-overlapping completed 5m blocks in the previous 24h, strictly before the 15m signal start:
- `median_qv5_prior24`
- `median_abs_flow5_prior24`

Require at least 144 prior completed 5m blocks.

Derived:
- `vol_rel = qv5 / median_qv5_prior24`
- `flow_strength_rel = abs(flow5) / median_abs_flow5_prior24`
- signal 15m `close_pos=(close-low)/(high-low)`

## Frozen absorption events
### SELLER_ABSORPTION_LONG
LONG iff ALL:
1. `flow5 < 0` (aggressive sellers dominate)
2. `ret5 >= 0` (price fails to move down despite selling)
3. `vol_rel > 1`
4. `flow_strength_rel >= 1`
5. signal `close_pos >=0.50`

### BUYER_ABSORPTION_SHORT
SHORT iff ALL:
1. `flow5 > 0`
2. `ret5 <= 0`
3. `vol_rel > 1`
4. `flow_strength_rel >=1`
5. signal `close_pos <=0.50`

The zero signs, relative-to-median thresholds, 5m window and 24h baseline are frozen natural definitions. No magnitude optimization.

## Validation
Chronological split by all unique Friday dates: first70% discovery / last30% validation.

Promotion `BTC_FRIDAY_C11A_1M_ABSORPTION_80_CANDIDATE` requires ALL:
- discovery N>=12 and WR>=80%
- validation N>=10 and WR>=80%
- full N>=25 and WR>=80%
- validation PnL>0 and PF>1
- >=3/4 chronological blocks with >=5 events each have WR>50% and PnL>0
- zero data completeness, same-bar, or alignment integrity violations

Sides descriptive only; no side rescue.

## Guardrails
No 3m/10m final window, no flow threshold sweep, no volume percentile sweep, no 12h/48h baseline, no close-position tuning, no direction flip, no TP/SL/hold/fee rescue after result.
