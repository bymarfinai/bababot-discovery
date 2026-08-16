# BTC Temporal A3.7–A3.9 — Tuesday Money Optimization Checkpoint

**Date:** 2026-08-16  
**Status:** MONEY-GEOMETRY DISCOVERY COMPLETE — local optimum identified; requires walk-forward/OOS validation before deployment  
**Symbol:** BTCUSDT  
**Setup:** SELL every Tuesday at exact 06:00 WIB  
**Evaluation:** frozen 971-day window, 139 Tuesday occurrences  
**Data:** official Binance Futures BTCUSDT 5m, 279,648 / 279,648 = 100% coverage  
**Sizing:** $10 fixed margin x 50 leverage = $500 notional, no compounding  
**Fee assumption:** 0.15% round-trip of notional = $0.75/trade  
**Intrabar ambiguity:** if TP and SL touched in same 5m candle, SL is assumed first (conservative)  
**Timeout:** any trade not hitting TP/SL is closed at actual final 5m close at max-hold

## Why this experiment

The earlier symmetric 0.5%/0.5% configuration produced a ~65% first-touch headline WR but was nearly/below breakeven after the frozen 0.15% round-trip fee assumption. A3.7 therefore optimized actual net economics rather than headline WR.

Metrics ranked:
- total net PnL after fees
- expectancy per trade
- profit factor
- max drawdown
- maximum loss streak
- 8-block chronological stability
- all 139 Tuesday entries preserved

## A3.7 broad grid

Grid:
- TP: 0.4, 0.5, 0.6, 0.7, 0.8, 1.0, 1.2%
- SL: 0.4, 0.5, 0.6, 0.7, 0.8, 1.0%
- max hold: 2h, 4h, 6h
- 126 configurations

Best first-pass stable result:
- TP 1.2%
- SL 0.8%
- max hold 6h
- RR = 1.50
- 139 trades
- net WR (including timeout exits) = 56.83%
- gross PnL = +$177.515
- fees = -$104.250
- **net PnL = +$73.265**
- expectancy = +$0.5271/trade
- PF = 1.330
- max DD = $29.563
- max loss streak = 4
- positive chronological blocks = 6/8

The winner sat on the TP/hold boundary, so A3.8 extended the search rather than prematurely declaring an optimum.

## A3.8 boundary extension

Grid:
- TP 1.0–2.0%
- SL 0.6–1.2%
- holds 6h, 8h, 12h

Raw highest net result:
- TP 2.0%, SL 0.8%, hold 12h
- net +$99.551
- expectancy +$0.7162/trade
- PF 1.329
- but only **5/8 blocks positive**
- max DD $41.252

This was not selected as the stable champion.

Best stable A3.8 region concentrated around TP ~1.4%, SL 0.8%, hold 6–8h.

## A3.9 local refinement

Local grid:
- TP 1.25–1.55% in 0.05 increments
- SL 0.70–0.90% in 0.05 increments
- max hold 6h, 7h, 8h, 9h, 10h
- 175 configurations

### Highest stable net PnL

**TP 1.35% / SL 0.80% / max hold 7h**

- RR = **1.688**
- trades = **139**
- TP hits = 47
- SL hits = 43
- timeouts = 49
- net-positive trades = 74
- net-negative trades = 65
- net WR = **53.24%**
- gross PnL = **+$204.029**
- total fees = **-$104.250**
- **net PnL = +$99.779**
- expectancy = **+$0.7178/trade**
- PF = **1.440**
- max DD = **$30.105**
- max loss streak = **8**
- positive blocks = **6/8**
- block net PnL = `[-18.648, +24.688, -9.855, +18.918, +12.492, +33.865, +17.314, +21.004]`
- average actual hold = 269.35 minutes

At $500 notional:
- full TP gross = +$6.75; net after $0.75 fee ≈ **+$6.00**
- full SL gross = -$4.00; net after $0.75 fee ≈ **-$4.75**

### Preferred consistency variant

**TP 1.35% / SL 0.80% / max hold 6h**

- RR = **1.688**
- trades = **139**
- TP hits = 42
- SL hits = 39
- timeouts = 58
- net-positive trades = 79
- net-negative trades = 60
- net WR = **56.83%**
- gross PnL = **+$199.984**
- fees = **-$104.250**
- **net PnL = +$95.734**
- expectancy = **+$0.6887/trade**
- PF = **1.431**
- max DD = **$31.636**
- max loss streak = **4**
- positive blocks = **6/8**
- block net PnL = `[-20.997, +26.272, -5.751, +18.203, +19.518, +26.227, +12.179, +20.083]`
- average actual hold = 246.01 minutes

The 6h variant gives up only ~$4.05 total net PnL versus the 7h variant while halving the observed max loss streak from 8 to 4. It is therefore the preferred balanced candidate for validation.

## Comparison with symmetric 0.5% / 0.5%

At max hold 4h:
- TP/SL 0.5%/0.5%
- 139 trades
- 84 TP hits / 45 SL hits / 10 timeout
- net-positive trades = 86, net-negative = 53
- net WR = 61.87%
- gross PnL = +$96.350
- fees = -$104.250
- **net PnL = -$7.900**

At max hold 6h:
- net PnL = **-$7.548**

Therefore the old 65%-ish first-touch WR did not translate into attractive net economics under the frozen fee assumption.

## Current interpretation

The Tuesday temporal edge appears more economically useful as a **lower-WR, asymmetric-payoff setup** than as a high-WR symmetric 1:1 setup.

Current validation candidate:

`Tuesday 06:00 WIB SELL -> TP 1.35% -> SL 0.80% -> timeout 6h at market`

Why 6h rather than the raw 7h optimum:
- nearly identical total PnL (+$95.73 vs +$99.78)
- same 6/8 positive-block count
- PF nearly identical (1.431 vs 1.440)
- materially lower observed max loss streak (4 vs 8)
- shorter exposure

## Important limitation

A3.7–A3.9 are parameter discovery on the same 971-day historical sample. The local optimum is therefore **not yet deployable proof**. The next required step is parameter-robustness / walk-forward validation: freeze a small neighborhood around TP 1.35%, SL 0.80%, hold ~6h and verify that the economic edge survives chronological out-of-sample selection without re-optimizing on each test block.
