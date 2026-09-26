# SOL Regime Stage 4 — Robustness / Forward Validation

Date: 2026-09-26
Status: **COMPLETE — FINAL DETECTOR NOT PASSED**
Branch: `sol-regime-forensic-1b`

## Purpose

Stage 4 tested whether Stage 3 could survive stricter temporal validation and whether:
1. volatility normalization could recover coverage,
2. 30-minute momentum could improve direction,
3. the BEAR head could be rebuilt,
4. apparent aggregate performance was stable across market subperiods.

No 2025/2026 results were used to change frozen candidate thresholds.

## Method improvement

Stage 4 used walk-forward development inside DEV instead of fitting all 2023-2024 at once:

- Discovery: Dec 2023-Mar 2024
- DEV validation: Apr-Jul 2024
- DEV holdout: Aug-Dec 2024
- VAL: 2025 split into Jan-Apr / May-Aug / Sep-Dec
- OOS: 2026 split into Jan-Apr / May-Aug / Sep partial

Features were causal and normalized by the trailing 30-day (720H) rolling median:
- rv8_rel
- rv24_rel
- atr_rel
- pullback distance / ATR
- rally distance / ATR
- 2H return / ATR
- 4H return / ATR
- 30-minute close-to-close momentum / ATR

The 30-minute feature is equivalent to the Stage 2 `m15ret2` momentum sampled at each completed 1H close.

## Frozen Stage 4 candidates

### V2-PRECISION BULL
Frozen after DEV:
- all three volatility ratios >= 1.5
- pullback >= 1.5 ATR
- 30m momentum >= -0.2 ATR
- 2H return <= +0.5 ATR

This candidate failed immediately in Jan-Apr 2025:
- precision 14.04%
- base BULL 17.78%
- lift 0.79x

**REJECTED.**

### V2-BALANCED BULL
Frozen after DEV:
- at least one of rv8_rel / rv24_rel / atr_rel >= 1.3
- pullback from 8H high >= 1 ATR
- 30m momentum >= 0
- 2H return <= -0.5 ATR

DEV subperiod lift:
- Dec-Mar: 1.70x
- Apr-Jul: 1.09x
- Aug-Dec: 1.54x

Thus it passed the internal DEV walk-forward gate.

### V2 BEAR
Frozen after DEV:
- at least 2 of rv8_rel / rv24_rel / atr_rel >= 1.5
- rally from 8H low >= 1.5 ATR
- 30m momentum >= +0.4 ATR
- 4H return >= 0

This is intentionally an **overextension** detector: BEAR risk appears while rally momentum is still positive, not after a bearish reversal has already happened.

DEV lift:
- discovery: 2.38x
- DEV validation: 1.85x
- DEV holdout: 1.65x

This was a major improvement versus the old BEAR search inside DEV.

## 2025 VAL — V2-BALANCED BULL

| Subperiod | Base BULL | Precision | Lift | n |
|---|---:|---:|---:|---:|
| Jan-Apr | 17.78% | 23.68% | 1.33x | 76 |
| May-Aug | 17.17% | 23.91% | 1.39x | 92 |
| Sep-Dec | 13.09% | 19.35% | 1.48x | 62 |

2025 aggregate:
- actual BULL: 1,399 / 8,736 = 16.01%
- BULL predictions: 230
- true BULL: 52
- precision: **22.61%**
- lift: **1.41x**
- recall: 3.72%
- transition contamination: 97 / 230 = 42.17%
- opposite BEAR contamination: 35 / 230 = 15.22%

**2025 PASS for BULL.**

## 2026 OOS — V2-BALANCED BULL

| Subperiod | Base BULL | Precision | Lift | n |
|---|---:|---:|---:|---:|
| Jan-Apr | 11.60% | 12.50% | 1.08x | 88 |
| May-Aug | 9.99% | 8.65% | **0.87x** | 104 |
| Sep partial | 13.65% | 14.29% | 1.05x | 14 |

2026 aggregate:
- actual BULL: 706 / 6,396 = 11.04%
- BULL predictions: 206
- true BULL: 22
- precision: **10.68%**
- lift: **0.97x**
- recall: 3.12%
- transition contamination: 95 / 206 = 46.12%
- opposite BEAR contamination: 24 / 206 = 11.65%

**OOS FAIL.**

Normalization successfully increased firing frequency, but destroyed the stable conditional BULL edge in OOS.

## V2 BEAR forward results

### 2025
- Jan-Apr: 26.79% precision, 1.45x lift, n=56
- May-Aug: 9.52% precision, **0.70x lift**, n=21
- Sep-Dec: 13.64% precision, **0.91x lift**, n=22

Aggregate 2025:
- predictions 99
- true BEAR 20
- precision 20.20%
- base 15.66%
- aggregate lift ~1.29x

Despite positive aggregate lift, it fails temporal robustness because two of three 2025 blocks are below 1x.

### 2026
- Jan-Apr: 17.65% precision, 1.24x lift, n=17
- May-Aug: 11.76% precision, 1.38x lift, n=51
- Sep partial: 0 / 6 correct, 0x lift

2026 aggregate:
- predictions 74
- true BEAR 9
- precision 12.16%
- base 11.21%
- aggregate lift ~1.08x
- transition contamination ~54.05%

**BEAR FAIL due instability and very low support.**

## Normalized SIDEWAYS head

Rule:
- rv8_rel <= 1.0
- atr_rel <= 0.9

It was not stable:
- some subperiods modestly >1x,
- 2025 May-Aug ~0.90x,
- 2026 Jan-Apr ~0.99x,
- Sep 2026 ~0.66x.

**SIDEWAYS FAIL.**

## Stage 3 V1 temporal robustness audit

Stage 4 also re-audited the original Stage 3 absolute-threshold V1 by subperiod.

### V1 BULL — 2025
- Jan-Apr: 1.36x
- May-Aug: **0.68x**
- Sep-Dec: 1.27x

So the apparently positive aggregate 2025 result hides a clear mid-year failure.

### V1 BULL — 2026
- Jan-Apr: 1.97x
- May-Aug: 1.77x
- Sep partial: no signals

V1 retains a strong 2026 BULL edge when it fires, but coverage is extremely low and it was not stable in 2025.

### V1 BEAR
2025:
- 1.19x / **0.70x** / 1.45x

2026:
- 1.07x / 1.27x / **0.77x**

Not stable.

## Final Stage 4 verdict

### What passed
- Stage 1C ground truth remains usable.
- Volatility information genuinely helps identify directional opportunity.
- 30m momentum contains useful context.
- Normalized features improve cross-regime firing frequency.
- The new overextension-style BEAR hypothesis was strong across all three DEV subperiods.

### What failed
- No complete BULL/BEAR/SIDEWAYS detector is robust across DEV -> 2025 subperiods -> 2026 subperiods.
- V2 normalization recovers coverage but removes the OOS BULL edge.
- BEAR remains non-stationary.
- SIDEWAYS remains poorly separable from TRANSITION.
- Aggregate yearly metrics can hide multi-month periods with lift below 1x.

## Decision

**DO NOT promote Stage 3 V1 or Stage 4 V2 to production regime detector.**

Keep:
- Stage 1C as frozen research ground truth.
- V1/V2 only as research baselines.
- `TRANSITION / NO-TRADE` as the safe default in future detector research.

The discovery loop should return to the direction-feature/model layer rather than proceeding to trading setup integration.

Most important next research target:
**a direction discriminator that is stable by subperiod, not merely by full-year aggregate.**
