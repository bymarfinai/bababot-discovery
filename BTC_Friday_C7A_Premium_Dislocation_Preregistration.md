# BTC Friday C7A — Premium Dislocation + OI Unwind Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched.**

## Objective
Test whether a rare futures-market dislocation event can identify an executable BTC Friday trade with observed historical win rate >=80% without post-result threshold tuning.

This is materially different from C0-C6: the key new information is Binance USD-M perpetual **Premium Index Kline** state, intended to capture intraday futures-vs-index dislocation rather than candle shape, funding level, or positioning level alone.

## Universe
- BTCUSDT USD-M perpetual
- WIB calendar Friday 15m signal candles
- Primary historical window: 2023-12-02 UTC through 2026-07-30 UTC exclusive, matching C4/C5 where futures metrics coverage is strong
- Signal candle must be completed before entry
- Entry = next 15m futures candle open

## Data
1. Standard BTCUSDT 15m futures klines.
2. Binance USD-M 15m Premium Index Klines.
3. Binance USD-M futures metrics for open-interest value.

All observations used for a trade must be known at or strictly before entry. The latest futures-metrics snapshot must be strictly before entry and no more than 15 minutes stale.

## Frozen premium anomaly
For each completed 15m signal candle:
- use the Premium Index close of that completed signal candle;
- reference distribution = the **previous 7 completed calendar days** of 15m premium closes, excluding the signal candle itself;
- require at least 192 prior premium observations;
- `premium_z = (signal_premium_close - prior7d_mean) / prior7d_std`;
- if prior std is zero/nonfinite, signal is ineligible.

No alternative lookback is allowed after result.

## Frozen OI unwind
`oi_chg15 = log(latest_pre_entry_OI / OI_at_or_before_15m_before_that_snapshot)`.

`OI_UNWIND = oi_chg15 < 0`.

No magnitude threshold is allowed.

## Frozen C7A event rules
### LONG_DISLOCATION_RECLAIM
Trade LONG only when ALL are true:
1. `premium_z <= -2.0`
2. `OI_UNWIND`
3. signal futures candle is bullish: `close > open`
4. signal candle closes in its upper half: `(close-low)/(high-low) >= 0.50`

### SHORT_DISLOCATION_REJECT
Trade SHORT only when ALL are true:
1. `premium_z >= +2.0`
2. `OI_UNWIND`
3. signal futures candle is bearish: `close < open`
4. signal candle closes in its lower half: `(close-low)/(high-low) <= 0.50`

The +/-2 sigma anomaly, OI<0 sign test, and 0.50 close-position boundary are frozen natural thresholds. They may not be changed after observing C7A.

If both directions are somehow true, mark integrity error and do not trade.

## Execution
- entry = next 15m open
- TP = 1.30%
- SL = 1.30%
- max hold = 24 x 15m = 6 hours
- first-touch bar handling identical to C4/C5 sequential simulator
- if neither TP nor SL is hit, close at final 15m close
- modeled round-trip fee = 0.15%
- reference notional = $500
- win = net PnL > 0 after modeled fee

No TP/SL/hold/fee retuning is allowed.

## Chronological validation
Split by unique Friday dates:
- first 70% = discovery
- last 30% = validation

The deterministic rule is not selected from discovery; the split is used only to test temporal survival.

## Promotion gate
`BTC_FRIDAY_C7A_PREMIUM_80_CANDIDATE` requires ALL:
1. discovery trades >= 12
2. discovery observed WR >=80%
3. validation trades >= 10
4. validation observed WR >=80%
5. full trades >= 25
6. full observed WR >=80%
7. validation total PnL >0
8. validation PF >1
9. at least 3/4 chronological full-history blocks with >=5 trades have WR >50% and positive PnL
10. zero causality/integrity violations

LONG and SHORT are reported descriptively. Neither side may rescue a failed combined C7A after result.

## Conditional C7B
If C7A rejects, one and only one follow-up is authorized: an expanding walk-forward selective classifier using premium features plus already-frozen candle/derivatives features. C7B must keep a fixed trade-confidence threshold of 0.80 and may not lower it after observing predictions.

## Guardrails
- no 1.5/1.75/2.5/3 sigma sweep
- no premium lookback sweep
- no OI magnitude threshold sweep
- no direction-only rescue
- no TP/SL/hold optimization
- no deeper tree rescue in C7A
- no reclassification of TIME exits
- no transfer to another coin unless a BTC candidate survives the frozen gate
- observed historical 80% is not a guarantee of future wins
