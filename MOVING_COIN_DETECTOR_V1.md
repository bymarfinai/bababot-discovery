# Moving Coin Detector V1

## Purpose

This is an upstream **market-wide movement scanner** for BabaBot. It answers:

> Which liquid Binance USDT perpetual pairs are beginning a directional move right now, and is the cleaner direction LONG or SHORT?

It does **not** place trades and does not replace the existing regime/entry engine.

## Why this layer exists

A top-gainer list is late by construction. V1 instead scans the most liquid USDT perpetuals and looks for early changes in:

1. 5m / 15m / 1h price acceleration
2. 5m quote-volume expansion versus the prior 20 closed candles
3. true-range expansion
4. proximity to / break of the previous 20-candle high or low
5. aggressive taker buy/sell imbalance
6. 30m change in open interest
7. EMA20/EMA50 alignment
8. spread quality and chase-risk penalties

Universe selection is **liquidity-only**, not momentum-based, so the detector does not pre-select coins only after they have already pumped.

## Direction scores

LONG and SHORT are scored independently on a 0–100 scale.

- Momentum: 30
- Activity (volume + range): 20
- Breakout / breakdown structure: 20
- Taker flow: 15
- Open-interest confirmation: 10
- Trend alignment: 5
- Penalties: extended 24h/1h move, wide spread, OI contraction during the move

Defaults:

- actionable threshold: `68`
- ignition threshold: `60`
- minimum LONG-vs-SHORT edge: `10`

## Stages

- `IGNITION`: pressure is building, volume is expanding, but the 20-bar level is not decisively broken yet.
- `EXPANSION`: directional score is strong and the 20-bar high/low is already broken.
- `MOVING`: directional movement exists but is below the actionable threshold.
- `EXHAUSTION`: the move is extended and confirmation is weakening; avoid chasing.
- `NO_TRADE`: no sufficiently asymmetric edge.

## Causality rule

Only **closed 5m candles** are used. The current in-progress Binance candle is discarded before feature calculation.

## Run

```bash
python -m moving_coin_detector --top 15
```

Machine-readable output:

```bash
python -m moving_coin_detector --json > moving_coin_scan.json
```

More selective universe:

```bash
python -m moving_coin_detector --universe 30 --min-volume 10000000 --threshold 72 --edge 12
```

## V1 validation gate

These thresholds are **engineering priors, not proven trading edge**. Before BabaBot is allowed to trade from this detector, backtest the detector snapshot every 5 minutes and measure forward excursions at 15m / 30m / 1h.

Suggested labels:

- LONG success: `MFE >= +1.0%` before `MAE <= -1.0%`
- SHORT success: `MFE >= +1.0%` before `MAE <= -1.0%`
- report base rate, precision, recall, score deciles, symbol stability, year stability, and fee/slippage sensitivity

The important test is not "did a coin move?" but:

> Did high LONG_SCORE or SHORT_SCORE materially improve the probability of the corresponding forward move versus the liquid-universe base rate?

Only after that gate should the detector feed an automated entry engine.
