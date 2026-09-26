# SOL Regime Stage 4B — Dedicated BEAR Discovery

Date: 2026-09-26  
Status: **COMPLETE — no new BEAR head promoted**  
Branch: `research/sol-regime-stage4b`

## Objective

Stage 4B isolates the remaining bottleneck after Stage 4:

- Bull Stage 4 is frozen and is **not retuned** here.
- Stage 1C future-informed ground truth remains frozen.
- Research target is BEAR only.
- 2023–2024 is discovery/DEV.
- 2025 is validation.
- 2026 is final OOS robustness check.

The question is whether a dedicated asymmetric BEAR feature universe can materially improve robustness over the Stage 3/V1 Bear head.

## Feature universe added

All features are causal at the completed 1H candle.

New BEAR-specific families tested:

- drawdown from recent 8H/24H peak,
- age of recent 24H peak,
- normalized 4H/8H rally and acceleration,
- downside/upside semivariance ratio,
- negative-return share,
- rolling skew,
- lower-high / lower-low counts,
- true-range expansion,
- candle body / close-location / upper-wick rejection,
- volume and trade-count z-scores,
- red-vs-green volume response,
- taker imbalance 1H/4H/8H and taker-imbalance delta.

Candidate conjunctions were selected on DEV only with internal 2023–H1 2024 / H2 2024 stability requirements and minimum support.

## Finding 1 — new micro/order-flow features overfit DEV

The strongest DEV-selected new candidate was:

- 8H return normalized by ATR >= **1.159946**
- 8H taker imbalance <= **-0.024899**

Interpretation:

> a strong preceding rally while taker flow is no longer strongly buy-dominant.

Results:

| Period | n | Precision | Lift |
|---|---:|---:|---:|
| DEV | 267 | 22.47% | **1.584x** |
| DEV H1 | 107 | 25.23% | **1.740x** |
| DEV H2 | 160 | 20.63% | **1.492x** |
| VAL 2025 | 267 | 13.48% | **0.861x** |
| OOS 2026 | 116 | 14.66% | 1.307x |

This candidate **fails formal validation** because 2025 lift falls below 1.

Other new-feature combinations using peak age, semivariance, skew, lower-high/lower-low, and taker imbalance showed the same pattern: attractive DEV lifts but unstable validation.

### Verdict

**REJECT new micro/order-flow Bear head.**

Taker imbalance is not sufficiently stationary as a standalone structural discriminator in this sample.

## Finding 2 — the old raw rally/exhaustion family remains the most portable

A broader raw precursor candidate was also audited:

- `ret4 >= 1.053869%`
- `accel4v12 >= 0.877085%`
- `distLow8 >= 3.046480%`

Interpretation:

> SOL has rallied materially away from its recent low and the latest 4H move is still accelerated — a possible rally-exhaustion precursor.

Head-only results:

| Period | n | Precision | Lift |
|---|---:|---:|---:|
| DEV | 1,109 | 18.21% | **1.284x** |
| VAL 2025 | 805 | 16.52% | **1.055x** |
| OOS 2026 | 326 | 14.72% | **1.313x** |

This is much more portable annually than the new micro candidates.

However annual stability alone is not sufficient.

## Finding 3 — combined detector exposes the hidden instability

The broad exhaustion candidate was then combined with the **frozen Stage 4 Bull head**:

Bull remains:

- rolling 720H percentile,
- at least 2 of rv8 / rv24 / ATR14% >= 85th percentile,
- distance from 8H high <= 25th percentile,
- Bull/Bear conflict -> TRANSITION.

### Combined Stage 4B candidate — Bear

| Period | Bear Precision | Bear Recall | Bear Lift | Bear n |
|---|---:|---:|---:|---:|
| DEV | 18.46% | 14.28% | **1.301x** | 1,040 |
| VAL 2025 | 16.11% | 8.85% | **1.029x** | 751 |
| OOS 2026 | 13.89% | 5.58% | **1.239x** | 288 |

Coverage is better than V1, but quarterly robustness still fails.

### Bear lift by quarter

| Quarter | Broad Stage 4B | V1 Bear |
|---|---:|---:|
| 2025 Q1 | **0.867x** | 1.129x |
| 2025 Q2 | 1.151x | **0.771x** |
| 2025 Q3 | 1.124x | **0.924x** |
| 2025 Q4 | 1.029x | 1.330x |
| 2026 Q1 | **0.980x** | 1.034x |
| 2026 Q2 | 1.599x | 1.195x |
| 2026 Q3 | **0.545x** | 1.060x |

The critical failure is **2026 Q3**. The broad candidate creates more Bear calls, but those additional calls are not robustly directional.

## V1 comparison after frozen Stage 4 Bull integration

V1 Bear inside the frozen Stage 4 combined detector:

| Period | Precision | Recall | Lift | n |
|---|---:|---:|---:|---:|
| DEV | 19.11% | 7.96% | **1.347x** | 560 |
| VAL 2025 | 16.67% | 5.85% | **1.064x** | 480 |
| OOS 2026 | 13.19% | 3.35% | **1.176x** | 182 |

V1 is weaker in recall, but its OOS quarter behavior is less catastrophic than the broader replacement.

## Stage 4B verdict

### PASSED

- Dedicated BEAR research confirmed that the useful Bear precursor remains an **asymmetric post-rally / overextension** pattern.
- `ret4`, `accel4v12`, and displacement from the recent low remain directionally portable at annual scale.
- Adding more causal microstructure information can improve DEV precision, but does not automatically improve robustness.

### FAILED

- No newly discovered BEAR head survives DEV -> 2025 -> 2026 with acceptable quarterly stability.
- Taker imbalance is not stable enough for promotion.
- Semivariance, skew, peak-age, LH/LL, and volume-response combinations did not solve the problem.
- The higher-coverage Broad Exhaustion candidate collapses in 2026 Q3 after integration.

## Decision

**Do not replace V1 Bear yet.**

Current detector research state:

- **BULL Stage 4 adaptive head: PASS / frozen research candidate**
- **BEAR V1: retain only as conservative research fallback**
- **BEAR Stage 4B replacements: REJECTED**
- **TRANSITION / abstain remains mandatory when evidence conflicts or is weak**

The full detector is still **not production-ready**.

## Implication for the next research loop

The remaining Bear information likely does not live in simple OHLCV/taker-bar transforms alone.

The next Bear-specific loop should test information that is economically different from the current feature family rather than more combinations of the same price bars, especially:

- open-interest change and price/OI divergence,
- funding-rate regime and funding acceleration,
- liquidation / forced-flow proxies if available,
- basis / premium-index behavior,
- cross-asset confirmation (BTC/ETH risk-off impulse),
- breakdown/retest sequencing rather than static single-candle thresholds.

Do not retune the frozen Stage 4 Bull head while doing this.
