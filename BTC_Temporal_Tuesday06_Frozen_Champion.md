# BTC Tuesday 06:00 WIB — FROZEN RESEARCH CHAMPION

**Freeze date:** 2026-08-16
**Status:** FROZEN FOR OOS / LIVE-PARITY VALIDATION — DO NOT RETUNE ON THE SAME 971-DAY SAMPLE

Canonical checkpoint: `BTC_Temporal_A510_A511_RunnerRecovery_Checkpoint.md`

## Frozen strategy
- Symbol: BTCUSDT
- Temporal prior: every Tuesday 06:00 WIB SELL
- Base TP: 1.35%
- Base SL: 0.80%
- Max hold: 6h
- Management layers: A5.2 price-path protection + A5.9 EMA20 FastMR + A5.11 EMA7 Runner Recovery

## Frozen research result
- 139 trades / 971 days
- 89 wins / 50 losses
- WR 64.03%
- net PnL +$130.33 at fixed $10 margin x 50 leverage
- expectancy +$0.9376/trade
- PF 1.692
- max DD $26.64
- max loss streak 4
- 7/8 chronological blocks positive

## Live-parity requirements
1. Live entry must be a real market SELL triggered at Tuesday 06:00 WIB; record Binance actual average fill price and use it as the sole price anchor for TP, SL, MFE/progress and all management thresholds.
2. Place real exchange-side TP1.35 and SL0.80 after fill confirmation. Do not use candle-open as a phantom live entry price.
3. State logic must consume only completed 5m candles. No look-ahead/intrabar retrospective cancellation.
4. A5.9 profit lock +0.20 must be represented by a real exchange-side protective stop (or immediate real market exit if the lock price has already been lost at the decision open). Keep the original TP1.35 alive unless explicitly replaced/cancelled.
5. A5.11 may cancel the +0.20 lock only after a completed 5m EMA7 rejection signal occurs before the lock has been touched; cancellation/restoration happens at the next live decision point. If the lock was already filled, no recovery is allowed.
6. Max-hold 6h must force a real market close using the actual exchange fill for PnL accounting.
7. Reconcile exchange position and open algo orders on restart; exchange state is source of truth.
8. No duplicate position per pair; no second Tuesday entry if a BTC position is already active under the agreed one-pair-one-position rule.

This file is the canonical freeze marker. Future experiments may validate this strategy, but must not silently change its parameters and still call it the Tuesday frozen champion.
