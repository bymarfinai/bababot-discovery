# SOL Regime Benchmark 1D — Actual Run

Source: Binance USDS-M Futures, SOLUSDT 1H
Warm-up: 2023-09-01 UTC onward
Evaluation: 2023-12-02 00:00 UTC → 2026-09-25 11:00 UTC
Ground truth: Stage 1C frozen labels
4H alignment: detector state is usable only after the 4H candle fully closes; state is then held until the next completed 4H candle.
4H aggregation: strict 4x contiguous 1H bars.
EMA settings: fast=7, slow=20.
Swing settings: legacy SwingRegime slb=5, sa=0.5.

## Key result

All legacy detectors show little to no stable precision lift over the Stage 1C base rate. EMA Cross classifies essentially every hour as BULL or BEAR and has zero abstention. EMA Simple, Dual and Swing abstain more, but directional precision remains close to the unconditional BULL/BEAR prevalence.

### DEV 2023-2024
Ground-truth prevalence: BULL 17.51%, BEAR 14.22%.

| detector | Bull precision | Bull recall | Bear precision | Bear recall | Directional accuracy | Exact match | No-direction capture |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross | 17.24% | 52.64% | 14.42% | 47.22% | 50.22% | 15.93% | 0.00% |
| EMA Simple | 17.46% | 44.35% | 13.77% | 37.01% | 41.06% | 16.61% | 16.91% |
| Dual | 17.41% | 37.50% | 13.69% | 30.57% | 34.39% | 17.20% | 30.16% |
| Swing V1 | 17.50% | 46.94% | 14.35% | 31.24% | 39.90% | 17.02% | 21.94% |

Precision lift vs prevalence:
- EMA Cross: Bull 0.985x, Bear 1.015x
- EMA Simple: Bull 0.997x, Bear 0.968x
- Dual: Bull 0.994x, Bear 0.963x
- Swing V1: Bull 0.999x, Bear 1.010x

### VAL 2025
Ground-truth prevalence: BULL 15.97%, BEAR 15.62%.

| detector | Bull precision | Bull recall | Bear precision | Bear recall | Directional accuracy | Exact match | No-direction capture |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross | 16.04% | 45.53% | 14.47% | 50.66% | 48.07% | 15.18% | 0.00% |
| EMA Simple | 15.31% | 38.31% | 13.51% | 38.96% | 38.63% | 15.05% | 14.48% |
| Dual | 16.35% | 33.10% | 13.46% | 32.75% | 32.92% | 16.79% | 30.17% |
| Swing V1 | 16.48% | 39.53% | 14.34% | 43.20% | 41.34% | 16.61% | 15.68% |

Precision lift vs prevalence:
- EMA Cross: Bull 1.004x, Bear 0.927x
- EMA Simple: Bull 0.959x, Bear 0.865x
- Dual: Bull 1.024x, Bear 0.862x
- Swing V1: Bull 1.032x, Bear 0.919x

### OOS 2026 YTD
Ground-truth prevalence: BULL 11.04%, BEAR 11.21%.

| detector | Bull precision | Bull recall | Bear precision | Bear recall | Directional accuracy | Exact match | No-direction capture |
|---|---:|---:|---:|---:|---:|---:|---:|
| EMA Cross | 11.82% | 53.97% | 10.34% | 45.75% | 49.82% | 11.09% | 0.00% |
| EMA Simple | 11.31% | 42.35% | 11.82% | 43.79% | 43.08% | 13.71% | 17.13% |
| Dual | 12.27% | 38.10% | 11.90% | 36.12% | 37.10% | 16.56% | 32.98% |
| Swing V1 | 14.07% | 33.00% | 11.18% | 42.40% | 37.74% | 16.49% | 32.74% |

Precision lift vs prevalence:
- EMA Cross: Bull 1.071x, Bear 0.922x
- EMA Simple: Bull 1.025x, Bear 1.055x
- Dual: Bull 1.112x, Bear 1.062x
- Swing V1: Bull 1.275x, Bear 0.997x

The isolated 2026 Bull lift in Swing V1 is not stable across DEV/VAL and therefore is not treated as a validated edge.

## Transition contamination

When a detector emits BULL or BEAR, roughly half of those hours are actually Stage 1C TRANSITION:
- DEV: approximately 46-48%
- 2025: approximately 45-49%
- 2026: approximately 52-54%

This is the dominant failure mode.

## Sustained-run response audit

For ground-truth directional runs lasting at least 4 consecutive hours, if the detector is NOT already matching at the start of the run, it usually fails to switch during that same run.

Selected conditional results:

EMA Cross
- DEV BULL: miss 87.5%, median successful switch delay 9h
- DEV BEAR: miss 97.1%, median successful switch delay 10h
- 2025 BULL: miss 91.3%, median successful switch delay 7.5h
- 2025 BEAR: miss 94.2%, median successful switch delay 13h
- 2026 BULL: miss 93.1%, median successful switch delay 6.5h
- 2026 BEAR: miss 89.2%, median successful switch delay 6.5h

EMA Simple
- DEV BULL: miss 72.0%, median successful switch delay 7h
- DEV BEAR: miss 84.9%, median successful switch delay 9h
- 2025 BULL: miss 83.3%, median successful switch delay 7h
- 2025 BEAR: miss 77.6%, median successful switch delay 7h
- 2026 BULL: miss 86.1%, median successful switch delay 5h
- 2026 BEAR: miss 68.6%, median successful switch delay 3h

Dual and Swing V1 also show high miss rates, generally ~81-97% when not already matching at directional-run start.

## Conclusion

1. None of the legacy regime detectors qualifies as a reliable live classifier for the Stage 1C BULL/BEAR/SIDEWAYS/TRANSITION target.
2. EMA Cross is especially unsuitable as a permission layer because it has no abstention and behaves close to a binary coin-flip on Stage 1C directional states.
3. EMA Simple is faster than EMA Cross in some transitions but still provides no stable precision lift.
4. Dual improves abstention but sacrifices directional recall without creating stable precision.
5. Swing V1 does not validate across DEV → 2025 → 2026.
6. The main structural issue is TRANSITION contamination, not lack of SOL movement.
7. Next step should be a new causal feature universe / detector built explicitly to separate confident BULL/BEAR from TRANSITION.

This is a research benchmark, not a trading signal.
