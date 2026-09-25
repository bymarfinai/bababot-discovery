# SOL Regime Legacy Rebuild V2 — Corrected Implementation

Date: 2026-09-25

## What was rebuilt

This rerun intentionally removes the known implementation ambiguities from the legacy regime code:

1. Uses **native Binance USDS-M SOLUSDT 4H candles** instead of rebuilding 4H from 1H.
2. Uses a historical warm-up before each evaluation period.
3. Uses correct live timing:
   - Stage 1C ground truth is anchored at the **1H candle close**.
   - A native 4H detector state becomes available only when that 4H candle has fully closed.
4. EMA is computed recursively with sufficient pre-roll.
5. ATR for Swing V2 uses Wilder-style initialization.
6. Swing V2 uses a symmetric confirmed 5-bar pivot (2 left + pivot + 2 right).
7. Swing V2 compares the **last two confirmed highs and last two confirmed lows**, instead of accumulated stale HH/HL/LH/LL counters.
8. Mixed structural states are explicitly treated as TRANSITION/abstain.

EMA definitions:
- EMA Cross V2: EMA7 > EMA20 = BULL; EMA7 < EMA20 = BEAR.
- EMA Location V2: close > max(EMA7, EMA20) = BULL; close < min(...) = BEAR; otherwise TRANSITION.
- EMA Dual V2: EMA7 > EMA20 and close > EMA7 = BULL; inverse = BEAR; otherwise TRANSITION.

Ground truth remains frozen Stage 1C.

## Corrected Results

### DEV 2023-2024

Ground-truth base rates:
- BULL 17.51%
- BEAR 14.19%

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross V2 | 17.20% | 52.47% | 0.982x | 14.42% | 47.36% | 1.017x | 0.00% |
| EMA Location V2 | 17.46% | 44.34% | 0.997x | 13.62% | 36.65% | 0.960x | 17.33% |
| EMA Dual V2 | 17.41% | 37.47% | 0.994x | 13.46% | 30.11% | 0.949x | 30.59% |
| Swing V2 | 16.45% | 31.75% | 0.939x | 12.05% | 26.77% | 0.849x | 34.68% |

### VAL 2025

Ground-truth base rates:
- BULL 16.01%
- BEAR 15.66%

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross V2 | 16.11% | 45.46% | 1.006x | 14.33% | 50.15% | 0.915x | 0.00% |
| EMA Location V2 | 15.37% | 38.24% | 0.960x | 13.48% | 38.82% | 0.861x | 15.06% |
| EMA Dual V2 | 16.42% | 33.02% | 1.026x | 13.34% | 32.46% | 0.852x | 29.70% |
| Swing V2 | 16.17% | 34.17% | 1.009x | 16.09% | 33.11% | 1.027x | 33.92% |

### OOS 2026 YTD

Ground-truth base rates:
- BULL 11.04%
- BEAR 11.21%

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross V2 | 11.85% | 54.11% | 1.073x | 10.47% | 46.30% | 0.934x | 0.00% |
| EMA Location V2 | 11.31% | 42.35% | 1.025x | 11.90% | 44.07% | 1.061x | 17.14% |
| EMA Dual V2 | 12.18% | 37.82% | 1.104x | 11.99% | 36.40% | 1.070x | 31.71% |
| Swing V2 | 10.49% | 29.60% | 0.951x | 10.90% | 31.94% | 0.973x | 36.02% |

## Transition contamination remains dominant

Even after rebuild, when EMA variants emit directional states, around half of those predictions are Stage 1C TRANSITION:
- DEV: roughly 46-48%
- 2025: roughly 45-48%
- 2026: roughly 52-54%

## Main conclusion

The original code did contain real engineering problems (partial 4H aggregation, cold-start sensitivity, stale swing counters, and an evaluation-timing mismatch in the first 1D benchmark).

However, **fixing those problems does not materially rescue the legacy regime logic**.

EMA Cross remains approximately base-rate precision across DEV/VAL/OOS.
EMA Location and EMA Dual add abstention but do not create a stable precision edge.
Corrected Swing V2 performs no better and is often worse than the legacy Swing V1.

Therefore the principal failure is not merely a coding bug. The underlying EMA/swing rules are too weak to separate confident Stage 1C BULL/BEAR states from TRANSITION.

This benchmark is research only, not a trading signal.
