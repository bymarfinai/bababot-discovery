# BabaBot V3 Entry Research — FINAL CONCLUSION

**Status:** CLOSED — OHLCV + candle-level taker flow exhausted  
**Date:** 2026-08-08  
**Scope:** 971 days, BTC/ETH/SOL/BNB, causal 15m/1H/4H data, V2/V2.5 regime context  

---

## 1. CONCLUSION

**No tested entry mechanism — including OHLCV price-action, EMA variants, breakout patterns, and candle-level taker buy/sell flow — produced a robust, out-of-sample advantage over random control within the V2/V2.5 regime framework.**

---

## 2. RESEARCH PHASES COMPLETED

### Phase 1 — EMA Reclaim Family (closed)
| Trigger | Signals | MFE/MAE | TP-b4-SL | Gross E/t |
|---|---|---|---|---|
| Baseline 15m EMA reclaim | 16,662 | 1.051 | 51.9% | +$0.26 |
| + body/location filter | 10,136 | 1.058 | 52.3% | +$0.29 |
| + ATR expansion | 5,337 | 1.077 | 51.5% | +$0.19 |
| + volume confirmation | 2,726 | 1.018 | 51.5% | +$0.21 |
| + structural breakout | 4,798 | 1.025 | 51.3% | +$0.17 |
| EMA7/EMA20 hypotheses (4 variants) | 1,743–4,713 | — | 50.9–52.6% | all net negative |

### Phase 2 — Breakout/Compression Family (closed)
| Mechanism | Signals | MFE/MAE | Lift vs baseline |
|---|---|---|---|
| Donchian breakout | 7,195 | 0.973 | -0.027 |
| Compression + retest | 8,855 | 0.965 | -0.039 |
| Range expansion | 2,813 | 0.936 | -0.068 |
| Volume breakout | 5,390 | 0.958 | -0.042 |
| Random control | 4,746 | 0.977 | -0.025 |

All breakout mechanisms performed WORSE than baseline.

### Phase 3 — 4H Regime Experiment (closed)
Eight 4H EMA configurations tested:

| Config | Active% | TP-b4-SL | vs 1H V2 (51.9%) |
|---|---|---|---|
| EMA7/20 Swing | 77% | 49.9% | -2.0pp |
| EMA21/50 Swing | 77% | 49.3% | -2.6pp |
| EMA7/20 Close>Both | 83% | 51.1% | -0.8pp |
| EMA21/50 Close>Both | 86% | 50.3% | -1.6pp |
| EMA7/20 Cross | 100% | 49.6% | -2.3pp |
| EMA21/50 Cross | 100% | 49.2% | -2.7pp |
| EMA7/20 Dual | 69% | 51.0% | -0.9pp |
| EMA21/50 Dual | 69% | 50.2% | -1.7pp |

4H regime at ANY EMA configuration does not improve entry quality over 1H V2 strict. Higher timeframe regime is too loose.

### Phase 4 — Taker-Flow Forensic (closed)

**"Binance candle-level taker buy/sell data is real and causally usable, but it does not provide a stable entry-level edge. Feature direction reverses across pairs, quantile relationships are non-monotonic, and integrated hypotheses remain net negative out-of-sample."**

Scope: 15m candle-level taker flow, 1H aggregated taker flow, completed 4H delta features, V2/V2.5 regime context, four tested pairs, causal first-touch evaluation.

| Feature | Win median | Loss median | Lift | Verdict |
|---|---|---|---|---|
| dp (delta %) | 0.597 | 0.960 | -0.363 | marginal, wrong direction |
| ds4 (4-bar sum) | -2,187 | -3,010 | +824 | reverses across pairs |
| dz (z-score) | 0.115 | 0.136 | -0.021 | noise |
| tbr (buy ratio) | 0.503 | 0.505 | -0.002 | noise |
| pdiv (price-delta div) | 1.036 | 1.025 | +0.011 | noise |
| d4h (4H delta) | -1.248 | -1.140 | -0.108 | noise |
| delta_aligned | 83.2% | 84.2% | -1.0pp | wrong direction |

Quantile analysis: zero features show monotonic Q1→Q4 WR across all 4 pairs. ds4 monotonic on ETH (positive) but BTC (negative) — opposite directions.

Integrated hypotheses:

| Hypothesis | Trades | WR | Net | WF |
|---|---|---|---|---|
| Delta aligned with direction | 3,292 | 50.5% | -$2,209 | 0/12 |
| Delta cross (strong imbalance) | 3,058 | 50.9% | -$1,916 | 0/12 |
| Strong delta z-score | 2,249 | 50.4% | -$1,537 | 1/12 |
| No price-delta divergence | 2,949 | 50.9% | -$1,828 | 0/12 |
| 4H delta aligned | 3,121 | 51.5% | -$1,710 | 1/12 |

All net negative. 0–1 out of 12 walk-forward folds positive.

---

## 3. WHAT HAS BEEN PROVEN

1. **V2 1H regime detector is valid** as a regime classifier (+12.7pp EMA hold lift, 99% HH/LL accuracy). Retain as permission layer.
2. **4H regime is too loose** at any EMA configuration (69–100% active vs V2's 15%). Does not improve entry quality.
3. **No OHLCV entry mechanism at 15m/1H/4H timescales** separates winners from losers within the V2 regime.
4. **No candle-level taker feature** provides stable directional signal across pairs and walk-forward folds.
5. **All breakout mechanisms perform worse than EMA reclaim**, which itself performs at random-control level.
6. **BNB is structurally incompatible** with all tested architectures.

---

## 4. WHAT THIS CONCLUSION DOES NOT CLAIM

- Does NOT claim all OHLCV strategies are impossible on all markets/timeframes
- Does NOT claim tick-level order flow would fail
- Does NOT claim open interest, funding rate, or liquidation data would fail
- Applies specifically to: 15m/1H/4H candle timescales, OHLCV + candle-level taker data, BTC/ETH/SOL/BNB, 971 days, within V2/V2.5 regime context on Binance Futures

---

## 5. FROZEN — DO NOT CONTINUE

- ❌ EMA reclaim tuning
- ❌ Breakout/compression variants
- ❌ 4H EMA parameter sweeps
- ❌ Candle-level taker flow filters
- ❌ TP/SL sweeps on any of the above
- ❌ Live code changes

---

## 6. NEXT HYPOTHESIS — REQUIRES EXTERNAL DATA

The candle-based research family is closed. Future V4 research requires:

**Tier 1 — data already partially available:**
- Tick-level order flow (not candle-aggregated)
- Sub-candle taker imbalance sequences

**Tier 2 — requires historical data collection:**
- Open interest change per candle (Binance API: /fapi/v1/openInterestHist)
- Funding rate history (Binance API: /fapi/v1/fundingRate)

**Tier 3 — requires third-party data:**
- Liquidation cascade data (Coinglass API)
- Order-book depth snapshots (real-time streaming, no historical)

Each hypothesis must be written with explicit causal rules before implementation. Do not begin V4 until the data is collected and validated.

---

## 7. FILES

| File | Purpose | Status |
|---|---|---|
| `continuation_detector_endpoint.py` | V2 three-layer detector | ✅ frozen |
| `v25_detector_endpoint.py` | V2.5 tiered regime | ✅ frozen |
| `v25_triggers_endpoint.py` | Entry trigger comparison | ✅ frozen |
| `v25_forensic_endpoint.py` | Forensic winner-vs-loser (OHLCV) | ✅ frozen |
| `v3_entry_quality_endpoint.py` | V3 breakout/compression | ✅ frozen |
| `v4h_regime_endpoint.py` | 4H regime experiment | ✅ frozen |
| `taker_forensic_endpoint.py` | Taker-flow forensic | ✅ frozen |
| `BabaBot_V2_V2.5_Final_Checkpoint.md` | V2/V2.5 regime checkpoint | ✅ frozen |

**Live code:** NOT modified. No strategy enabled in production.
