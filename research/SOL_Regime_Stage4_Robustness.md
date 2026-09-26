# SOL Regime Stage 4 — Audited Robustness / Refinement

Date: 2026-09-26
Status: COMPLETE — BULL refinement PASS; BEAR robustness FAIL; full detector not production-ready
Ground truth: Stage 1C frozen
Selection: DEV 2023-2024 only; 2025/2026 evaluation-only
Audit source cutoff: Binance USDS-M Futures SOLUSDT through 2026-09-25 11:00 UTC

## Objective

Stage 4 re-tests the frozen Stage 3 V1 baseline and asks:

1. Can adaptive volatility normalization recover 2026 coverage without destroying BULL lift?
2. Can the BEAR head be improved using the existing Stage 2 causal feature family?
3. Does 30-minute momentum add stable directional information?
4. Are results robust by quarter, not just annual aggregates?

All detector features are causal. Rolling percentiles use the previous 720 completed 1H candles and exclude the current candle.

The last 24 hours before DEV->VAL and VAL->OOS year boundaries are excluded from detector evaluation so the Stage 1C 24H future-informed research label does not cross the split.

---

## 1. Reproduction gate — Stage 3 V1 verified exactly

The Stage 3 detector was recomputed directly from Binance candles before any refinement.

| Split | Bull Precision | Bull Lift | Bull n | Bear Precision | Bear Lift | Bear n | Directional Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| DEV 2023-24 | 31.38% | 1.792x | 631 | 18.76% | 1.322x | 565 | 12.62% |
| VAL 2025 | 22.02% | 1.375x | 386 | 16.87% | 1.077x | 498 | 10.12% |
| OOS 2026 | 18.75% | 1.699x | 64 | 12.89% | 1.150x | 194 | 4.03% |

The predicted counts and metrics match the frozen Stage 3 report exactly. This verifies the Stage 1C labels, split boundaries, feature timing, ATR/RV calculations, and V1 implementation.

---

## 2. Pure percentile V2 — reproduced and rejected

V2 uses causal rolling-720H empirical percentiles.

Directional gate: at least one of:
- rv8 percentile >= 70%
- rv24 percentile >= 70%
- ATR14% percentile >= 70%
- distLow8 percentile >= 80%

BULL:
- directional gate
- distHigh8 percentile <= 25%
- ret2 percentile <= 20%

BEAR:
- directional gate
- accel4v12 percentile >= 80%
- ret4 percentile >= 80%
- close-location percentile >= 80%

SIDEWAYS:
- rv8 percentile <= 30%
- ATR14% percentile <= 30%

| Split | Bull Precision | Bull Lift | Bull Recall | Bear Precision | Bear Lift | Bear Recall | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| DEV | 25.79% | 1.473x | 12.77% | 18.77% | 1.323x | 4.98% | 12.44% |
| VAL | 19.17% | 1.197x | 10.94% | 17.88% | 1.142x | 3.95% | 12.59% |
| OOS | 14.19% | 1.285x | 11.90% | 11.34% | 1.012x | 3.77% | 12.98% |

V2 fixes the mechanical coverage collapse, but loses too much BULL selectivity and does not solve BEAR.

### Boundary audit correction

The earlier Q4-2025 table included Dec-31 observations whose 24H research label crosses into 2026.

Full Q4 produced Bull lift 1.231x, Bear lift 1.417x, coverage 12.64%.

Using the same boundary-safe rule as the annual VAL evaluation, the correct Q4 row is:
- Bull lift 1.217x
- Bear lift 1.401x
- coverage 12.77%

Annual V2 figures above were already boundary-safe and are unchanged.

---

## 3. 30-minute momentum veto — FAIL on fuller data

Frozen veto thresholds:
- BULL keep only if m30 >= -0.1823%
- BEAR keep only if m30 <= +1.5109%

The audit re-ran the same fixed windows using complete Binance 15m history rather than the earlier sparse microstructure snapshot.

### DEV fixed windows

| Side | Raw | After veto |
|---|---:|---:|
| BULL | 28.25% (n=223) | 30.56% (n=72) |
| BEAR | 27.40% (n=73) | 31.37% (n=51) |

The veto looks helpful in DEV.

### VAL fixed windows

| Side | Raw | After veto |
|---|---:|---:|
| BULL | 18.40% (n=212) | 16.92% (n=65) |
| BEAR | 16.67% (n=78) | 11.86% (n=59) |

### OOS fixed windows

| Side | Raw | After veto |
|---|---:|---:|
| BULL | 9.55% (n=199) | 8.70% (n=92) |
| BEAR | 6.76% (n=74) | 5.71% (n=70) |

Verdict: DROP the standalone 30m momentum veto. It improves DEV but degrades both sides outside DEV.

---

## 4. DEV-only adaptive refinement

A limited search was performed only on the Stage 2 feature families already justified before OOS inspection.

BULL family:
- rv8 / rv24 / ATR14% rolling-percentile volatility votes
- distance from 8H high percentile
- optional ret2 percentile filter

BEAR family:
- accel4v12 percentile
- ret4 percentile
- distLow8 percentile
- optional close-location percentile
- optional volatility vote gate

2025 and 2026 were not used to rank or select candidates.

### Selected BULL candidate: V1.5-ADAPTIVE-BULL

BULL if:
- at least 2 of 3 are >= their own rolling 85th percentile:
  - rv8
  - rv24
  - ATR14%
- and distHigh8 <= its rolling 25th percentile.

No ret2 veto is used.

Head-only result before conflict resolution with the frozen V1 BEAR head:

| Split | Bull n | Precision | Lift |
|---|---:|---:|---:|
| DEV | 712 | 28.09% | 1.604x |
| VAL | 714 | 21.71% | 1.356x |
| OOS | 500 | 19.40% | 1.758x |

This recovers BULL support without reproducing pure V2's loss of OOS selectivity.

### BEAR refinement search

No BEAR candidate in the tested Stage 2 feature family achieved a sufficient DEV precision/support improvement while staying positive across DEV subperiods.

No new BEAR rule is promoted.

---

## 5. Final combined research candidate — V1.5

Architecture:
- BULL = V1.5 adaptive Bull head
- BEAR = frozen Stage 3 V1 Bear head
- SIDEWAYS = frozen Stage 3 V1 low-volatility head
- conflict / insufficient evidence = TRANSITION

### DEV 2023-2024

- Bull precision 28.24%
- Bull recall 11.57%
- Bull lift 1.612x
- Bull n 680
- Bull transition contamination 46.32%
- Bear precision 19.11%
- Bear lift 1.347x
- Bear n 560
- directional coverage 13.08%

### VAL 2025

- Bull precision 21.71%
- Bull recall 10.51%
- Bull lift 1.356x
- Bull n 677
- Bull transition contamination 44.76%
- Bear precision 16.67%
- Bear lift 1.064x
- Bear n 480
- directional coverage 13.24%

### OOS 2026

- Bull precision 19.05%
- Bull recall 13.03%
- Bull lift 1.726x
- Bull n 483
- Bull transition contamination 43.27%
- Bear precision 13.19%
- Bear lift 1.176x
- Bear n 182
- directional coverage 10.40%

### OOS improvement vs Stage 3 V1

| Metric | V1 | V1.5 |
|---|---:|---:|
| Bull precision | 18.75% | 19.05% |
| Bull lift | 1.699x | 1.726x |
| Bull recall | 1.70% | 13.03% |
| Bull predicted n | 64 | 483 |
| Directional coverage | 4.03% | 10.40% |

The BULL side therefore recovers most of the lost 2026 usability without sacrificing OOS precision/lift.

---

## 6. Quarterly robustness

### BULL lift

| Period | Lift |
|---|---:|
| 2025 Q1 | 1.421x |
| 2025 Q2 | 1.319x |
| 2025 Q3 | 1.132x |
| 2025 Q4 | 1.569x |
| 2026 Q1 | 1.367x |
| 2026 Q2 | 1.338x |
| 2026 Q3 YTD | 2.949x |

BULL lift remains >1 in every 2025-2026 quarter.

### BEAR lift

| Period | Lift |
|---|---:|
| 2025 Q1 | 1.129x |
| 2025 Q2 | 0.771x |
| 2025 Q3 | 0.924x |
| 2025 Q4 | 1.330x |
| 2026 Q1 | 1.034x |
| 2026 Q2 | 1.195x |
| 2026 Q3 YTD | 1.060x |

BEAR remains non-robust because it drops below base rate in 2025 Q2 and Q3.

---

## 7. Stage 4 verdict

### PASS
1. Stage 3 V1 reproduction is exact.
2. Pure percentile V2 is reproducible.
3. A better adaptive BULL rule was selected using DEV only.
4. V1.5 fixes most of the 2026 BULL coverage collapse while preserving OOS lift.
5. V1.5 BULL lift stays >1 in every 2025-2026 quarter.
6. 30m standalone veto is rejected on fuller data.

### FAIL / unresolved
1. BEAR is still the main bottleneck.
2. BEAR quarterly robustness is not acceptable.
3. SIDEWAYS remains weak.
4. The complete four-state detector is not production-ready.

## Research decision

Promote V1.5-ADAPTIVE-BULL as the new BULL research baseline.

Do not promote a new BEAR head.
Do not integrate the detector directly into live entry logic yet.
TRANSITION / abstain remains the default when directional evidence is insufficient.

## Canonical Stage 4 implementation

research/sol_regime_detector_stage4_v15.py

The older research/sol_regime_stage4_v2_rejected.py remains only as a legacy rejected prototype.

## Next formal step

Stage 5 should be an asymmetric BEAR rebuild, not trading integration yet.

Dedicated downside feature universe:
- drawdown from recent peak
- failed recovery / rejection structure
- downside range expansion
- lower-high / lower-low age and strength
- downside realized volatility / semivariance
- rolling skew
- red-vs-green volume response
- sequence/chop entropy

Selection remains DEV-only. 2025 validation and 2026 OOS stay untouched until the candidate is frozen.
