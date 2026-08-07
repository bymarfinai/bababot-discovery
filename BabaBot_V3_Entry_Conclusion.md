# BabaBot V3 Entry Research — FINAL CONCLUSION

**Status:** CLOSED — OHLCV entry mechanisms exhausted at 15m timescale  
**Date:** 2026-08-08  
**Scope:** 971 days, BTC/ETH/SOL/BNB, causal 15m data, V2/V2.5 regime context, OHLCV-based entry mechanisms only  

---

## 1. CONCLUSION

**No tested entry mechanism produced a robust, out-of-sample advantage over random control within the V2/V2.5 regime framework. EMA reclaim had the highest aggregate MFE/MAE ratio by a very small margin, but random control had higher FavFirst% than EMA reclaim. Therefore EMA reclaim should not be considered a proven edge.**

**OHLCV-only entry mechanisms tested at the 15m timescale did not provide enough directional precision after fees.**

---

## 2. ENTRY MECHANISMS TESTED

### V2 EMA Reclaim Family (closed)
| Trigger | Signals | t/d/p | MFE/MAE | TP-b4-SL | Gross E/t |
|---|---|---|---|---|---|
| Baseline 15m EMA reclaim | 16,662 | 4.29 | 1.051 | 51.9% | +$0.26 |
| + break previous high/low | 10,988 | 2.83 | 1.040 | 51.7% | +$0.23 |
| + close-location + body-strength | 10,136 | 2.61 | 1.058 | 52.3% | +$0.29 |
| + ATR/range expansion | 5,337 | 1.37 | 1.077 | 51.5% | +$0.19 |
| + volume confirmation | 2,726 | 0.70 | 1.018 | 51.5% | +$0.21 |
| + structural breakout | 4,798 | 1.24 | 1.025 | 51.3% | +$0.17 |

### EMA7/EMA20 Hypotheses (closed)
| Hypothesis | Trades | t/d/p | WR | Net | WF pos |
|---|---|---|---|---|---|
| EMA7 above/below EMA20 | 4,713 | 1.21 | 51.3% | -$2,722 | 0/12 |
| Fresh EMA cross | 1,743 | 0.45 | 52.6% | -$703 | 1/12 |
| Spread widening | 2,388 | 0.61 | 50.9% | -$1,466 | 1/12 |
| Aligned + wide spread | 4,409 | 1.14 | 51.1% | -$2,650 | 0/12 |

### V3 Breakout/Compression Family (closed)
| Mechanism | Signals | t/d/p | MFE/MAE h8 | Ret h8 | FavFirst% | Lift vs baseline |
|---|---|---|---|---|---|---|
| **EMA reclaim (baseline)** | **16,657** | **4.29** | **1.012** | **-0.057%** | **43.2%** | — |
| Donchian breakout | 7,195 | 1.85 | 0.973 | -0.113% | 39.6% | **-0.027** |
| Compression → breakout | 9 | 0.00 | 0.447 | -0.314% | 25.0% | -0.185 |
| Compression + retest | 8,855 | 2.28 | 0.965 | -0.093% | 41.3% | **-0.039** |
| Range expansion + strong close | 2,813 | 0.72 | 0.936 | -0.098% | 35.6% | **-0.068** |
| Breakout + volume expansion | 5,390 | 1.39 | 0.958 | -0.122% | 38.8% | **-0.042** |
| **Random control** | **4,746** | **1.22** | **0.977** | **-0.030%** | **44.6%** | -0.025 |

---

## 3. MFE/MAE RATIO ACROSS HORIZONS (aggregate 4 pairs)

| Mechanism | h1 | h2 | h4 | h8 | h16 |
|---|---|---|---|---|---|
| EMA reclaim | 0.953 | 0.950 | 0.977 | 1.012 | 1.010 |
| Donchian BO | 0.950 | 0.951 | 0.966 | 0.974 | 0.981 |
| Comp+Retest | 0.939 | 0.923 | 0.948 | 0.964 | 0.965 |
| Range Exp | 0.866 | 0.895 | 0.923 | 0.936 | 0.957 |
| Vol Breakout | 0.957 | 0.945 | 0.976 | 0.957 | 0.975 |
| Random Ctrl | 0.990 | 0.975 | 0.969 | 0.977 | 1.029 |

No mechanism achieves MFE/MAE > 1.1 at any horizon. Random control matches or exceeds all breakout mechanisms.

---

## 4. PER-PAIR RESULTS (h=8)

### EMA Reclaim (baseline)
| Pair | N | MFE | MAE | Ratio | RetMed | FavFirst | F1ret | F2ret | F3ret |
|---|---|---|---|---|---|---|---|---|---|
| SOL | 4,168 | 0.728% | 0.696% | 1.046 | -0.065% | 43.0% | -0.052 | -0.098 | -0.061 |
| ETH | 4,255 | 0.560% | 0.507% | 1.105 | -0.045% | 44.5% | -0.045 | -0.062 | -0.036 |
| BTC | 4,310 | 0.371% | 0.372% | 0.997 | -0.038% | 43.5% | -0.035 | -0.042 | -0.038 |
| BNB | 3,924 | 0.393% | 0.454% | 0.866 | -0.081% | 42.0% | -0.088 | -0.087 | -0.067 |

### Donchian Breakout
| Pair | N | MFE | MAE | Ratio | RetMed | FavFirst | F1ret | F2ret | F3ret |
|---|---|---|---|---|---|---|---|---|---|
| SOL | 1,856 | 0.800% | 0.874% | 0.915 | -0.159% | 37.4% | -0.157 | -0.138 | -0.168 |
| ETH | 1,585 | 0.718% | 0.660% | 1.088 | -0.111% | 40.3% | -0.119 | -0.126 | -0.090 |
| BTC | 1,850 | 0.474% | 0.492% | 0.963 | -0.101% | 39.5% | -0.128 | -0.105 | -0.050 |
| BNB | 1,904 | 0.490% | 0.521% | 0.940 | -0.080% | 41.4% | -0.099 | -0.068 | -0.073 |

### Volume Breakout
| Pair | N | MFE | MAE | Ratio | RetMed | FavFirst | F1ret | F2ret | F3ret |
|---|---|---|---|---|---|---|---|---|---|
| SOL | 1,339 | 0.796% | 0.889% | 0.895 | -0.202% | 35.8% | -0.203 | -0.197 | -0.200 |
| ETH | 1,286 | 0.716% | 0.668% | 1.072 | -0.105% | 40.0% | -0.127 | -0.126 | -0.065 |
| BTC | 1,414 | 0.504% | 0.504% | 1.000 | -0.085% | 39.5% | -0.126 | -0.102 | -0.030 |
| BNB | 1,351 | 0.514% | 0.584% | 0.880 | -0.098% | 39.8% | -0.090 | -0.114 | -0.099 |

---

## 5. ROLLING THIRDS AND WALK-FORWARD

Forward returns (h=8 median) are negative in ALL thirds for ALL mechanisms across ALL pairs. No mechanism shows positive returns in any walk-forward fold. This is not a matter of fold selection — the result is uniformly negative.

---

## 6. KEY FINDINGS

1. **All breakout mechanisms perform WORSE than baseline EMA reclaim.** Breakouts overshoot then mean-revert (MFE/MAE < 1.0). This is the classic "buy the breakout, get the pullback" effect.

2. **Random control matches or exceeds all structured mechanisms** on FavFirst% (44.6% vs 35–43%). This means structured entries are not selecting better moments than random entries within the same regime.

3. **ETH is the only pair showing MFE/MAE consistently > 1.0** across mechanisms. All other pairs are at or below 1.0.

4. **BNB remains structurally adverse** (MFE/MAE 0.87–0.94) across all mechanisms.

5. **No feature measured at entry time separates winners from losers** (forensic analysis: 0/20 features discriminative).

---

## 7. WHAT THIS CONCLUSION DOES NOT CLAIM

- Does NOT claim that OHLCV can never produce a profitable strategy
- Does NOT claim the V2 regime detector is useless — it is valid
- Does NOT claim other timeframes or markets would show the same result
- Applies specifically to: 15m timescale, OHLCV data only, BTC/ETH/SOL/BNB, 971 days, within V2/V2.5 regime context

---

## 8. FROZEN — DO NOT CONTINUE

- ❌ EMA reclaim tuning
- ❌ EMA7/EMA20 alignment experiments
- ❌ Breakout/compression filter variants
- ❌ Further TP/SL sweeps on any of the above
- ❌ Live code changes
- ❌ Production deployment of any tested configuration

---

## 9. FUTURE RESEARCH — SEPARATE HYPOTHESIS REQUIRED

Further work requires a fundamentally different data source or market model:

- **Order-flow / taker imbalance:** directional pressure from aggressive buyers/sellers
- **Open interest + funding rate:** positioning data indicating crowded trades or liquidation risk
- **Liquidation cascade data:** forced selling/buying creating predictable short-term direction
- **Materially different timeframe:** 1m/5m tick-level microstructure, or daily/weekly macro
- **Cross-asset signals:** BTC dominance, ETH/BTC ratio, or macro correlation triggers
- **Fundamentally different market model:** mean-reversion instead of momentum, or regime-conditioned volatility trading

Each future hypothesis must be written explicitly with causal rules before implementation begins. The V2/V2.5 regime gate should be retained as a permission layer if the new entry mechanism operates on the same pairs and timeframes.

---

## 10. FILES

| File | Purpose | Status |
|---|---|---|
| `v3_entry_quality_endpoint.py` | V3 entry quality comparison | ✅ frozen |
| `v25_forensic_endpoint.py` | Forensic winner-vs-loser | ✅ frozen |
| `v25_triggers_endpoint.py` | Phase 3 entry trigger audit | ✅ frozen |
| `BabaBot_V2_V2.5_Final_Checkpoint.md` | V2/V2.5 regime + EMA entry conclusion | ✅ frozen |

**Live code:** NOT modified. No strategy enabled in production.
