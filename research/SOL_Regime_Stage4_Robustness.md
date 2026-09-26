# SOL Regime Stage 4 — Robustness / Forward Validation

Date: 2026-09-26
Status: COMPLETE — final production detector NOT YET PASSED
Ground truth: Stage 1C frozen.
No OOS retuning.

## Goal

Stress-test Stage 3 V1 and test refinements without tuning on 2025/2026:

1. volatility-normalized thresholds,
2. Bear-head robustness,
3. 30m momentum as a causal direction veto,
4. subperiod / quarterly stability.

---

## A. Stage 3 V1 recap

V1-BALANCED used absolute DEV thresholds.

### BULL lift
- DEV: 1.792x
- 2025: 1.375x
- 2026 OOS: 1.699x

### BEAR lift
- DEV: 1.322x
- 2025: 1.077x
- 2026 OOS: 1.150x

Main issue:
- directional coverage fell from 12.62% DEV to 4.03% OOS.
- OOS BULL recall only 1.70%.

Interpretation:
the Bull edge transferred, but absolute volatility thresholds became too restrictive as the volatility regime changed.

---

## B. Volatility-normalized V2 experiment

Instead of absolute thresholds, each feature is expressed as a rolling 720-hour (~30 day) empirical percentile using only historical values before the current candle.

DEV-only candidate frozen:

Directional gate:
- at least 1 of:
  - rv8 percentile >= 70%
  - rv24 percentile >= 70%
  - ATR14% percentile >= 70%
  - distLow8 percentile >= 80%

Bull head:
- distHigh8 percentile <= 25%
- ret2 percentile <= 20%

Bear head:
- accel4v12 percentile >= 80%
- ret4 percentile >= 80%
- close-location percentile >= 80%

Sideways:
- rv8 percentile <= 30%
- ATR14% percentile <= 30%

### DEV
- Bull precision 25.79%
- Bull lift 1.473x
- Bull recall 12.77%
- Bear precision 18.77%
- Bear lift 1.323x
- Bear recall 4.98%
- directional coverage 12.44%

### VAL 2025
- Bull precision 19.17%
- Bull lift 1.197x
- Bull recall 10.94%
- Bear precision 17.88%
- Bear lift 1.142x
- Bear recall 3.95%
- directional coverage 12.59%

### OOS 2026
- Bull precision 14.19%
- Bull lift 1.285x
- Bull recall 11.90%
- Bear precision 11.34%
- Bear lift 1.012x
- Bear recall 3.77%
- directional coverage 12.98%

### Result
Normalized thresholds successfully fix the coverage collapse:
- V1 OOS directional coverage: 4.03%
- normalized V2 OOS directional coverage: 12.98%

But the trade-off is lower selectivity:
- Bull OOS lift falls from 1.699x to 1.285x.
- Bear OOS lift falls to ~1.01x.

Therefore normalized V2 is NOT automatically superior to V1.

---

## C. Quarterly robustness of normalized V2

| Period | Bull Lift | Bear Lift | Coverage |
|---|---:|---:|---:|
| 2025 Q1 | 1.459x | 1.246x | 12.27% |
| 2025 Q2 | 1.079x | 0.917x | 12.36% |
| 2025 Q3 | 1.069x | 0.989x | 12.95% |
| 2025 Q4 | 1.231x | 1.417x | 12.64% |
| 2026 Q1 | 1.282x | 1.083x | 14.40% |
| 2026 Q2 | 0.970x | 1.035x | 14.19% |
| 2026 Q3 YTD | 1.700x | 0.494x | 10.19% |

### Result
- Bull is directionally useful in most subperiods but fails 2026 Q2 (~0.97x).
- Bear is clearly non-robust, including 2026 Q3 collapse to ~0.49x.
- The exact normalized V2 rule is therefore not robust enough to be promoted to final detector.

---

## D. 30m momentum veto test

Stage 2 found 30-minute momentum as the only micro feature with the same Bull orientation in DEV / VAL / OOS exploratory samples.

Stage 4 tested it as a veto on normalized V2 directional calls.

DEV selected thresholds:
- Bull keep only if 30m momentum >= -0.1823%
- Bear keep only if 30m momentum <= +1.5109%

These thresholds improved the small DEV sample modestly.

### Fixed VAL sample
Raw:
- Bull precision 17.44%
- Bear precision 14.93%

After momentum veto:
- Bull precision 16.13%
- Bear precision 7.84%

### Fixed OOS sample
Raw:
- Bull precision 8.57%
- Bear precision 8.20%

After momentum veto:
- Bull precision 7.32%
- Bear precision 7.02%

### Result
FAIL.
30m momentum as a standalone veto degrades both Bull and Bear outside DEV.

It is removed from the candidate detector.

---

## E. Stage 4 final verdict

### What PASSED
1. Stage 1C ground truth remains valid.
2. The Stage 3 BULL feature family is real enough to survive DEV -> VAL -> OOS.
3. Volatility normalization successfully solves the coverage problem mechanically.
4. Heavy abstention remains preferable to forcing every hour into BULL/BEAR.

### What FAILED
1. No Bear head is robust enough across subperiods.
2. Normalized V2 sacrifices too much Bull precision for recovered coverage.
3. 30m momentum veto does not validate.
4. SIDEWAYS identification remains weak.
5. No current detector passes a strong enough robustness bar for production trading.

## Production decision

DO NOT replace the current trading engine with Stage 3/4 regime output yet.

Current research status:
- BULL detector = validated research edge, not production-ready.
- BEAR detector = failed robustness.
- SIDEWAYS = weak.
- TRANSITION / abstain = still the safest default state.

## Required next research loop

Before Stage 5 trading integration, loop back into a focused Stage 2B / 3B only for missing information:

1. Build a dedicated BEAR feature universe rather than mirror Bull logic.
2. Add higher-order causal features:
   - drawdown from recent peak,
   - recovery / failed-recovery structure,
   - downside range expansion,
   - lower-high / lower-low age and strength,
   - asymmetric downside realized volatility,
   - downside/upside semivariance,
   - candle-sequence entropy,
   - rolling skew,
   - volume response to red vs green candles.
3. For Bull, test adaptive normalization that preserves the V1 absolute-edge selectivity while avoiding OOS coverage collapse.
4. Keep 2026 untouched for selection decisions; use it only as final check.

Stage 4 is complete, but the full detector has NOT passed the final robustness gate.
