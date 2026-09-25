# SOL Regime Stage 2 — Causal Feature Discovery

Date: 2026-09-25
Status: COMPLETE
Ground truth: Stage 1C frozen labels.
Evaluation: DEV 2023-2024 -> VAL 2025 -> OOS 2026 YTD.
All features are causal: only information available at or before the current candle close is used.

Boundary safety:
- The final 24 hours before a split boundary are excluded from feature evaluation so the Stage 1C future horizon never crosses into the next split.
- Stage 1C thresholds remain frozen from the original DEV fit.

## 1H feature universe tested

Momentum:
- ret1, ret2, ret4, ret8, ret12, ret24
- accel2v8 = ret2 - ret8/4
- accel4v12 = ret4 - ret12/3

Path / trend quality:
- eff4, eff8, eff12, eff24
- signed persistence 8H / 24H

Volatility / expansion:
- ATR14 as % of price
- current TR / ATR14
- current range / 20H median range
- realized volatility 8H / 24H

Position / structure:
- 8H and 24H channel position
- distance from rolling high / low
- breakHigh24 / breakLow24
- current candle body %
- current candle close-location

Activity / order flow:
- volume z-score 24H
- trade-count z-score 24H
- taker imbalance 1H / 4H / 8H

## Stage 2 key finding #1 — Directional opportunity IS learnable

Instead of directly asking BULL vs BEAR, the cleaner first question is:

DIRECTIONAL = BULL + BEAR
NON-DIRECTIONAL = SIDEWAYS + TRANSITION

DEV base directional prevalence: 31.70%
VAL base directional prevalence: 31.67%
OOS 2026 base directional prevalence: 22.25%

Frozen DEV high-threshold gates:

| Feature | DEV Lift | VAL 2025 Lift | OOS 2026 Lift | OOS Support |
|---|---:|---:|---:|---:|
| distLow8 high (> 3.482%) | 1.215x | 1.117x | 1.573x | 8.18% |
| rv24 high (> 1.163%) | 1.201x | 1.089x | 1.934x | 3.92% |
| ATR14% high (> 1.885%) | 1.198x | 1.167x | 1.789x | 3.30% |
| rv8 high (> 1.125%) | 1.170x | 1.241x | 1.771x | 5.24% |

Interpretation:
- High realized volatility / high ATR / wide displacement from the recent low materially increases the probability that the next Stage 1C state is genuinely directional.
- The effect survives DEV -> VAL -> OOS without threshold retuning.
- 2026 support is lower because the absolute DEV volatility thresholds fire less often, but conditional directional precision becomes much higher.

Example OOS 2026:
- base probability of BULL+BEAR = 22.25%
- rv24 gate precision = 43.03% (1.93x lift)
- ATR14 gate precision = 39.81% (1.79x)
- rv8 gate precision = 39.40% (1.77x)
- distLow8 gate precision = 34.99% (1.57x)

### Verdict
KEEP as Stage 3 gate candidates:
- rv8
- rv24
- ATR14%
- distLow8

## Stage 2 key finding #2 — BULL opportunity features are stronger than BEAR

Frozen single-feature BULL lifts:

| Feature | DEV | VAL 2025 | OOS 2026 |
|---|---:|---:|---:|
| ATR14% high | 1.389x | 1.244x | 1.760x |
| rv8 high | 1.364x | 1.269x | 2.136x |
| rv24 high | 1.346x | 1.043x | 2.130x |
| distLow8 high | 1.283x | 1.163x | 1.767x |
| distHigh8 low | 1.256x | 1.149x | 1.457x |
| ret2 low | 1.238x | 1.063x | 1.210x |

This suggests many strong future BULL states occur around elevated volatility and pullback/recovery geometry rather than a simple EMA uptrend.

### Verdict
Strong BULL candidate family:
- volatility regime
- distance from rolling low/high
- short-term pullback / reversal context

## Stage 2 key finding #3 — BEAR single-feature edge is weaker

Frozen BEAR lifts:

| Feature | DEV | VAL 2025 | OOS 2026 |
|---|---:|---:|---:|
| accel4v12 high | 1.160x | 1.046x | 1.246x |
| ret4 high | 1.141x | 1.083x | 1.333x |
| distLow8 high | 1.130x | 1.070x | 1.382x |
| close-location high | 1.130x | 1.077x | 0.990x |
| channel8 high | 1.164x | 0.995x | 0.998x |
| distHigh8 high | 1.152x | 0.947x | 0.761x |

### Verdict
KEEP as weaker BEAR candidates:
- accel4v12
- ret4
- distLow8

DROP / deprioritize:
- channel8
- distHigh8 high
- close-location alone

The stable BEAR signal is consistent with a possible post-rally / acceleration reversal structure, but the lift is much weaker than the BULL volatility family.

## Stage 2 key finding #4 — SIDEWAYS and TRANSITION overlap heavily

Frozen SIDEWAYS features:
- low ATR14%: lift 1.120x / 1.115x / 1.063x
- low rv8: lift 1.145x / 1.106x / 1.027x

Frozen TRANSITION features:
- low ATR14%: lift 1.053x / 1.039x / 1.071x
- low rv8: lift 1.050x / 1.079x / 1.092x

Conclusion:
- low-volatility information helps identify the broad NON-DIRECTIONAL region,
- but single monotonic 1H features do not reliably separate SIDEWAYS from TRANSITION.
- This supports a hierarchical architecture rather than a flat four-way rule.

## Hierarchical decomposition

### Layer A — DIRECTIONAL vs NON-DIRECTIONAL
Promising and validated.
Best families: realized volatility, ATR, recent range/displacement.

### Layer B — BULL vs BEAR conditional on DIRECTIONAL
Still difficult using simple 1H features.

DEV one-vs-one BULL-vs-BEAR AUC:
- distHigh8: 0.563
- ATR14%: 0.562
- rv8: 0.553
- rv24: 0.552
- ret2: 0.547

VAL 2025:
- almost all collapse toward ~0.50
- ret24 reaches ~0.541 but does not retain a stable direction in OOS.

OOS 2026:
- ATR14% ~0.555
- rv8 ~0.557
- most price-direction features remain ~0.50-0.52.

Conclusion:
- 1H features can tell us WHEN a strong move is likely much better than they can tell us WHICH DIRECTION.

## 15m microstructure exploratory pass

To investigate the missing direction signal, fixed 30-day windows were sampled without tuning:
- DEV: Dec-2023, Apr-2024, Aug-2024
- VAL: Jan-2025, May-2025, Sep-2025
- OOS: Jan-2026, May-2026, Sep-2026

Features tested at each 1H close:
- last 15m / 30m / 1H / 2H returns
- 15m path efficiency / signed persistence
- 15m candle body and close location
- taker imbalance 15m / 1H / 2H
- taker imbalance delta
- 15m realized volatility
- intra-hour channel position
- 30m reversal / acceleration
- volume z-score

Directional BULL-vs-BEAR sample sizes were small:
- DEV 112
- VAL 136
- OOS 117
Therefore this pass is exploratory only.

Most features are not stable across all three samples.

One feature keeps the same direction in all three:
- 30-minute momentum (m15ret2)
  - DEV AUC ~0.559, higher -> BULL
  - VAL AUC ~0.605, higher -> BULL
  - OOS AUC ~0.541, higher -> BULL

Other apparently strong features fail stability:
- 15m rv8: DEV strong, weak/unstable in VAL
- 30m reversal: DEV/VAL strong, not top-ranked OOS
- taker imbalance direction changes across samples
- signed persistence changes orientation OOS

### Verdict
KEEP as exploratory Stage 3 micro feature:
- 30m momentum at 1H close

DO NOT yet promote:
- taker imbalance
- micro realized-volatility direction
- micro persistence
- reversal30 as standalone rule

## Final Stage 2 shortlist

### Tier A — validated directional-gate features
1. rv8
2. rv24
3. ATR14%
4. distLow8

### Tier B — BULL context features
5. distHigh8
6. ret2

### Tier C — weaker BEAR context features
7. accel4v12
8. ret4

### Tier D — exploratory 15m direction feature
9. m15ret2 (30-minute momentum sampled at 1H close)

### Non-directional context
10. low rv8
11. low ATR14%

## Stage 2 conclusion

Stage 2 succeeded at finding a robust answer to:
"WHEN is SOL likely to enter a genuinely directional state?"

It did NOT yet solve:
"WHEN directional, is the next state BULL or BEAR?"

Therefore Stage 3 should NOT start as a flat 4-class EMA-like detector.

Recommended Stage 3 architecture:

1. DIRECTIONAL GATE
   - combine rv8 / rv24 / ATR14% / distLow8
2. DIRECTION HEAD
   - search combinations of pullback/reversal context and 15m 30-minute momentum
   - BULL and BEAR may require asymmetric rules
3. NON-DIRECTIONAL HEAD
   - default to TRANSITION / NO-TRADE first
   - only call SIDEWAYS when additional compression/chop evidence is strong

Research only; not a live trading signal.
