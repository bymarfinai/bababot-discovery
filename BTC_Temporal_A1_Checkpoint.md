# BTC Temporal A1 — 971-Day Weekday × Hour Discovery Checkpoint

**Date:** 2026-08-16  
**Status:** A1 COMPLETE — discovery candidates identified, not production strategy  
**Symbol:** BTCUSDT  
**Timezone:** WIB / UTC+7  
**Data:** 15m Binance Futures candles from Railway historical DB  
**Window:** 2023-12-02 00:00 UTC → 2026-07-30 00:00 UTC (exclusive)  
**Rows:** 93,216 / 93,216 expected = **100.0% coverage**  
**Slots:** all **7 × 24 = 168** weekday/hour combinations  
**Horizons:** 15m, 30m, 60m, 120m, 240m  
**Stability split:** 8 chronological blocks  

## Intent

Find the strongest repeatable BTC temporal edge. This phase is discovery and ranking, not an attempt to invalidate a previously observed slot. Winners are deepened in A2.

## Frozen A1 definition

- Entry = open of the exact local clock-hour 15m candle.
- For every weekday/hour × horizon, direction is BUY if positive forward returns are at least as frequent as negative returns; otherwise SELL.
- Directional WR is separated from executable first-touch geometry.
- MFE/MAE is measured within the selected horizon.
- No EMA, regime, HOD/LOD, London/session, price-action, volume, or other filter is applied.
- No live-trading code is changed.

## Strongest A1 discoveries

| Candidate | Direction | Horizon | N | Directional WR | Positive blocks >50 | Blocks ≥60 | Blocks ≥65 | Median MFE/MAE | Median block WR |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Tuesday 06:00** | SELL | **30m** | 139 | **64.75%** | 7/8 | 5/8 | 4/8 | 1.4725 | 65.85% |
| **Friday 15:00** | BUY | **30m** | 138 | **64.49%** | 7/8 | **6/8** | 4/8 | **1.6751** | 65.85% |
| **Tuesday 06:00** | SELL | **240m** | 139 | **64.03%** | 7/8 | 5/8 | 4/8 | **1.7933** | **68.47%** |
| **Saturday 18:00** | BUY | **240m** | 139 | **64.03%** | 7/8 | 4/8 | 4/8 | 1.5087 | 61.12% |
| **Friday 16:00** | BUY | **120m** | 138 | **64.49%** | 7/8 | 5/8 | 4/8 | 1.4192 | 65.69% |
| **Sunday 01:00** | BUY | **240m** | 139 | **62.59%** | 6/8 | 5/8 | 4/8 | 1.3718 | 65.85% |
| Friday 04:00 | BUY | 15m | 138 | 62.32% | 6/8 | 5/8 | 3/8 | **1.7582** | 62.91% |
| Wednesday 01:00 | BUY | 15m | 139 | 61.15% | 7/8 | **6/8** | 2/8 | 1.6665 | 64.71% |
| Thursday 10:00 | SELL | 60m | 138 | 60.14% | **8/8** | 2/8 | 1/8 | 1.2107 | 58.82% |

## Execution-geometry highlights

### Tuesday 06:00 SELL — 240m

- Directional WR: **64.03%** (139 observations)
- Median signed forward return: **+0.1988%** in SELL direction
- Median MFE: **0.7194%**
- Median MAE: **0.4012%**
- Median MFE/MAE: **1.7933**
- Symmetric first-touch 0.5%: **84 favorable / 45 adverse = 65.12% decisive WR**
- Symmetric first-touch 0.8%: **54 / 34 = 61.36%**
- Symmetric first-touch 1.0%: **44 / 27 = 61.97%**

This is currently the strongest long-horizon temporal candidate because both direction and excursion geometry remain favorable.

### Friday 15:00 BUY — 30m

- Directional WR: **64.49%** (138 observations)
- Median signed forward return: **+0.0848%**
- Median MFE: **0.2255%**
- Median MAE: **0.1346%**
- Median MFE/MAE: **1.6751**
- Positive blocks: **7/8**
- Blocks ≥60%: **6/8**
- Symmetric first-touch 0.3%: **47 favorable / 30 adverse = 61.04% decisive WR**
- Symmetric first-touch 0.5%: **19 / 11 = 63.33%** (many events do not reach ±0.5% inside 30m)

This is currently the strongest short-horizon stability candidate.

### Saturday 18:00 BUY — 240m

- Directional WR: **64.03%**
- Positive blocks: **7/8**
- Minimum block WR: **47.06%**
- Median MFE/MAE: **1.5087**
- Symmetric first-touch 0.5%: **49 / 27 = 64.47%**
- Symmetric first-touch 1.0%: **15 / 9 = 62.50%**

### Thursday 10:00 SELL — 60m

- Directional WR: **60.14%**
- Positive blocks >50%: **8/8**
- Minimum block WR: **52.94%**

Lower headline WR, but uniquely consistent across all eight blocks. Retain as a robustness candidate for A2.

## Important temporal clusters

A1 did not only produce isolated buckets. Two neighborhoods deserve deeper study:

1. **Friday 15:00–17:00 WIB BUY cluster**
   - Friday 15:00 BUY: 64.49% at 30m and 64.49% at 240m.
   - Friday 16:00 BUY: 64.49% at 120m and 60.14% at 240m.
   - Friday 17:00 BUY: 62.32% at 120m and 60.14% at 60m.

2. **Tuesday 06:00–08:00 WIB SELL cluster**
   - Tuesday 06:00 SELL is strongest: 64.75% at 30m and 64.03% at 240m.
   - Tuesday 07:00 SELL retains positive long-horizon geometry.
   - Tuesday 08:00 SELL retains positive MFE/MAE although weaker directional WR.

The presence of neighboring-hour structure makes these clusters higher-priority than a single isolated high-WR bucket.

## Previously observed candidates — full-history update

### Sunday 23:00 SELL

The earlier recent-window result (~80% over 35 observations) does **not** remain the leading full-history candidate.

Full 971d results:
- 15m: BUY 50.36%
- 30m: SELL 53.24%
- 60m: SELL **56.52%**
- 120m: BUY 54.68%
- 240m: BUY 53.24%

At 60m, median MFE/MAE = 1.1658 and symmetric 0.5% first-touch decisive WR = 43.90%.

Interpretation: the earlier 80% observation was a strong recent/local regime behavior, but A1 found better repeatable temporal candidates elsewhere. This slot remains useful for later regime-comparison work, not as the current temporal champion.

### Sunday 01:00 BUY

This candidate **does retain a meaningful full-history edge**, especially at longer horizon:
- 30m: 58.99%
- 60m: 57.55%
- 120m: 61.15%
- 240m: **62.59%**

It remains an A2 candidate.

### Tuesday 20:00 SELL

- Best A1 horizon: **60m SELL = 61.15%**
- Median MFE/MAE = 1.3947
- Positive blocks = 6/8

Also retained, but below Tuesday 06:00.

## A1 conclusion

The full 971-day scan shows that **BTC does contain repeatable weekday × hour structure worth deepening**, but the strongest full-history candidates are different from the strongest recent-window anomaly.

Current priority ranking for A2:

1. **Tuesday 06:00 WIB SELL** — strongest headline WR + strong long-horizon geometry.
2. **Friday 15:00 WIB BUY** — strongest short-horizon stability and part of a Friday 15–17 BUY cluster.
3. **Friday 16:00 WIB BUY** — continuation of the same Friday cluster.
4. **Saturday 18:00 WIB BUY** — strong 240m candidate with good excursion geometry.
5. **Sunday 01:00 WIB BUY** — prior candidate that survives full history.
6. **Thursday 10:00 WIB SELL** — lower WR but 8/8 positive blocks; robustness benchmark.

## Next phase — A2

For the leading candidates, do not add a large indicator stack. Deepen the temporal edge causally:

1. Entry timing around the slot: -60m to +60m in 15m increments.
2. Horizon surface rather than only one selected horizon.
3. Previous 1h / 4h price direction and extension.
4. Location versus daily open, HOD/LOD-so-far, PDH/PDL and Asia range using levels known at entry.
5. Session mapping (especially the Friday 15–17 and Tuesday 06–08 clusters).
6. Keep directional probability separate from executable TP/SL first-touch performance.

Goal: convert a temporal prior into a deterministic causal trigger with higher WR and executable RR, while retaining enough sample size.
