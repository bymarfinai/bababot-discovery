# BTC Friday C12A — COIN-M vs USD-M Perpetual Lead/Lag Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched.**

## Objective
Test whether BTCUSD COIN-M perpetual leads BTCUSDT USD-M perpetual strongly enough to identify a robust >=80% Friday USD-M catch-up trade.

New information source: official Binance **COIN-M BTCUSD_PERP** 15m klines, not used in C0-C11.

## Universe / execution
- traded instrument: BTCUSDT USD-M perpetual
- leader instrument: BTCUSD_PERP COIN-M perpetual
- synchronized completed 15m candles on WIB Friday
- entry next BTCUSDT 15m open
- TP=SL1.30%, hold6h, modeled round-trip fee0.15%, $500 reference notional

## Frozen lead feature
For aligned completed 15m bars:
- `cm_ret15 = cm_close/cm_open-1`
- `um_ret15 = um_close/um_open-1`
- `lead_spread = cm_ret15-um_ret15`
- `lead_z7d` = current lead_spread standardized against previous7 calendar days excluding current, min192

## Frozen event
LONG USD-M iff:
1. `lead_z7d >= +2.0`
2. `cm_ret15 >0`

SHORT USD-M iff:
1. `lead_z7d <= -2.0`
2. `cm_ret15 <0`

The hypothesis is pure cross-contract catch-up. No candle/taker/OI condition is added.

## Validation / gate
First70% Friday dates discovery; last30% validation.

Promotion `BTC_FRIDAY_C12A_COINM_LEAD_80_CANDIDATE` requires:
- discovery N>=12, WR>=80%
- validation N>=10, WR>=80%
- full N>=25, WR>=80%
- validation PnL>0 and PF>1
- >=3/4 blocks with >=5 trades each, WR>50%, PnL>0
- zero timestamp/alignment integrity violations

No direction-only rescue.

## Guardrails
No sigma/lookback sweep, no COIN-M symbol substitution, no adding spot/premium/OI after result, no TP/SL/hold/fee rescue, no reversal flip, no transfer to other coins if failed.
