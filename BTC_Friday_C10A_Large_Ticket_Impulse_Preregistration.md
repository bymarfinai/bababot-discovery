# BTC Friday C10A — Large-Ticket Impulse Preregistration

**FROZEN BEFORE C9B RESULT. Research-only. Live BBC untouched.**

## Objective
Test whether unusually large average trade ticket size, combined with directionally consistent aggressive futures flow, identifies a robust >=80% BTC Friday continuation trade.

This adds a new information field not used in C0-C9: Binance futures kline `number_of_trades`, allowing `quote_volume / trade_count` as average quote notional per trade.

## Universe / execution
- BTCUSDT USD-M perpetual 15m
- WIB calendar Friday completed signal candles
- entry next 15m open
- continuation direction = signal candle direction
- TP=SL1.30%, max hold6h, fee0.15%, $500 reference notional
- win = net PnL>0

## Frozen features
For every completed 15m futures candle:
- `avg_ticket = quote_volume / number_of_trades`
- `ticket_z7d` = current avg_ticket standardized against previous7 calendar days excluding current; minimum192 prior observations
- `taker_imbalance = 2*taker_buy_quote/quote_volume - 1`
- `close_pos = (close-low)/(high-low)`

## Frozen event
LONG continuation iff ALL:
1. `ticket_z7d >= +2.0`
2. signal `close > open`
3. `taker_imbalance > 0`
4. `close_pos >=0.50`

SHORT continuation iff ALL:
1. `ticket_z7d >= +2.0`
2. signal `close < open`
3. `taker_imbalance < 0`
4. `close_pos <=0.50`

No negative-ticket-z reversal branch is authorized.

## Validation
First70% unique Friday dates discovery, last30% validation.

Promotion `BTC_FRIDAY_C10A_LARGE_TICKET_80_CANDIDATE` requires ALL:
- discovery N>=12, WR>=80%
- validation N>=10, WR>=80%
- full N>=25, WR>=80%
- validation PnL>0, PF>1
- >=3/4 chronological blocks with >=5 events each: WR>50% and PnL>0
- zero integrity violations

Directions descriptive only; no side rescue.

## Guardrails
No ticket-z/lookback threshold sweep, no trade-count cutoff, no direction rescue, no reversal flip, no TP/SL/hold/fee optimization, no tree/model rescue inside C10A.

If C10A fails, any follow-up must be separately preregistered before seeing its result and introduce either 1m sequence information or a different causal selection mechanism; it may not merely retune ticket thresholds.
