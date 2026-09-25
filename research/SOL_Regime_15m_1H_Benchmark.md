# SOL Regime Detector — 15m vs 1H Benchmark

Date: 2026-09-25
Ground truth: frozen Stage 1C labels.
Source: Binance USDS-M Futures SOLUSDT 15m; strict 15m -> 1H aggregation for ground truth.
Timing: state sampled only after its candle closes. No look-ahead.
Warm-up: 14 days before each evaluation chunk.

Detector families:
- EMA Cross
- EMA Location
- EMA Dual
- Swing V2 (symmetric confirmed pivot, last-two highs/lows)
- Time-equivalent EMA variants:
  - 1H EMA28/80 ~= 4H EMA7/20 time span
  - 15m EMA112/320 ~= 4H EMA7/20 time span

## DEV 2023-2024

Ground-truth base rate: BULL 17.50%, BEAR 14.22%.

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain | Directional Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15m EMA7/20 Cross | 17.38% | 51.53% | 0.993x | 12.55% | 42.49% | 0.883x | 0.0% | 47.48% |
| 15m EMA7/20 Location | 16.90% | 41.07% | 0.966x | 12.87% | 35.90% | 0.905x | 17.83% | 38.75% |
| 15m EMA7/20 Dual | 16.53% | 33.37% | 0.945x | 11.98% | 27.31% | 0.843x | 32.28% | 30.66% |
| 15m Swing V2 | 17.37% | 35.36% | 0.993x | 12.10% | 25.98% | 0.851x | 33.85% | 31.15% |
| 15m EMA112/320 Cross | 17.11% | 52.56% | 0.978x | 14.40% | 46.85% | 1.013x | 0.0% | 50.00% |
| 15m EMA112/320 Dual | 17.04% | 35.54% | 0.974x | 13.79% | 29.46% | 0.970x | 33.13% | 32.81% |
| 1H EMA7/20 Cross | 17.43% | 52.13% | 0.996x | 13.58% | 45.52% | 0.955x | 0.0% | 49.17% |
| 1H EMA7/20 Location | 17.65% | 43.30% | 1.009x | 12.59% | 35.09% | 0.885x | 17.46% | 39.62% |
| 1H EMA7/20 Dual | 17.42% | 36.32% | 0.996x | 12.34% | 28.35% | 0.868x | 30.87% | 32.75% |
| 1H Swing V2 | 17.07% | 33.43% | 0.975x | 13.67% | 30.42% | 0.962x | 34.08% | 32.08% |
| 1H EMA28/80 Cross | 17.08% | 52.56% | 0.976x | 14.32% | 46.48% | 1.007x | 0.0% | 49.83% |
| 1H EMA28/80 Dual | 17.30% | 36.38% | 0.989x | 13.76% | 29.61% | 0.968x | 32.61% | 33.34% |

## VAL 2025

Ground-truth base rate: BULL 15.97%, BEAR 15.62%.

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain | Directional Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15m EMA7/20 Cross | 15.91% | 50.25% | 0.996x | 15.78% | 50.07% | 1.010x | 0.0% | 50.16% |
| 15m EMA7/20 Location | 15.46% | 41.32% | 0.968x | 15.50% | 40.64% | 0.993x | 16.38% | 40.98% |
| 15m EMA7/20 Dual | 15.42% | 34.45% | 0.965x | 15.52% | 33.92% | 0.994x | 30.19% | 34.19% |
| 15m Swing V2 | 15.78% | 33.74% | 0.988x | 15.11% | 31.36% | 0.968x | 33.44% | 32.56% |
| 15m EMA112/320 Cross | 15.71% | 44.60% | 0.984x | 14.47% | 50.66% | 0.927x | 0.0% | 47.60% |
| 15m EMA112/320 Dual | 16.91% | 32.38% | 1.059x | 13.80% | 32.31% | 0.884x | 32.85% | 32.35% |
| 1H EMA7/20 Cross | 15.71% | 48.32% | 0.984x | 14.47% | 47.15% | 0.927x | 0.0% | 47.74% |
| 1H EMA7/20 Location | 15.82% | 41.03% | 0.991x | 15.25% | 40.64% | 0.977x | 16.97% | 40.84% |
| 1H EMA7/20 Dual | 15.56% | 33.60% | 0.974x | 14.70% | 33.04% | 0.942x | 30.42% | 33.32% |
| 1H Swing V2 | 15.03% | 32.24% | 0.941x | 13.98% | 28.44% | 0.895x | 34.00% | 30.36% |
| 1H EMA28/80 Cross | 15.77% | 44.75% | 0.988x | 14.36% | 50.29% | 0.920x | 0.0% | 47.49% |
| 1H EMA28/80 Dual | 16.76% | 32.45% | 1.049x | 13.79% | 32.60% | 0.883x | 32.15% | 32.53% |

## OOS 2026 YTD

Ground-truth base rate at run time: BULL 11.07%, BEAR 11.21%.

| Detector | Bull Precision | Bull Recall | Bull Lift | Bear Precision | Bear Recall | Bear Lift | Abstain | Directional Accuracy |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 15m EMA7/20 Cross | 11.88% | 53.67% | 1.074x | 11.28% | 50.35% | 1.007x | 0.0% | 52.00% |
| 15m EMA7/20 Location | 11.51% | 43.50% | 1.040x | 10.91% | 40.17% | 0.974x | 16.91% | 41.82% |
| 15m EMA7/20 Dual | 11.79% | 37.29% | 1.066x | 11.19% | 34.59% | 0.998x | 30.35% | 35.93% |
| 15m Swing V2 | 11.20% | 31.92% | 1.012x | 12.05% | 33.61% | 1.075x | 37.20% | 32.77% |
| 15m EMA112/320 Cross | 12.06% | 54.38% | 1.090x | 10.45% | 46.72% | 0.933x | 0.0% | 50.53% |
| 15m EMA112/320 Dual | 12.50% | 37.01% | 1.130x | 11.75% | 34.73% | 1.048x | 34.10% | 35.86% |
| 1H EMA7/20 Cross | 11.39% | 51.41% | 1.029x | 12.27% | 54.81% | 1.095x | 0.0% | 53.12% |
| 1H EMA7/20 Location | 12.19% | 45.48% | 1.102x | 11.29% | 42.12% | 1.008x | 16.93% | 43.79% |
| 1H EMA7/20 Dual | 12.09% | 38.14% | 1.092x | 11.81% | 36.96% | 1.054x | 30.03% | 37.54% |
| 1H Swing V2 | 13.45% | 39.27% | 1.215x | 12.23% | 34.17% | 1.091x | 36.39% | 36.70% |
| 1H EMA28/80 Cross | 11.94% | 53.95% | 1.079x | 10.53% | 47.00% | 0.940x | 0.0% | 50.46% |
| 1H EMA28/80 Dual | 12.31% | 37.01% | 1.112x | 11.70% | 34.87% | 1.044x | 33.32% | 35.93% |

## Transition contamination

Across the shorter-timeframe EMA families, roughly 45-54% of directional predictions are still Stage 1C TRANSITION. Shorter timeframe updates did not solve the dominant classification problem.

## Conclusion

1. Moving from 4H to 15m or 1H removes some timing lag but does **not** create a stable regime-classification edge.
2. 15m EMA7/20 Cross is the most balanced short-timeframe binary variant in 2025/OOS, but its DEV precision lift is ~1x and therefore not a validated edge.
3. 1H EMA7/20 Cross improves OOS directional accuracy to ~53%, but DEV/VAL remain ~49%/~48%; the OOS improvement is not stable enough to trust.
4. 1H Swing V2 has an attractive 2026 Bull lift (~1.22x), but DEV and 2025 are below 1x. This is non-stationary / not validated.
5. Time-equivalent EMA periods (1H 28/80; 15m 112/320) behave similarly to 4H EMA7/20 and do not fix the problem.
6. The persistent failure mode remains TRANSITION contamination rather than raw timeframe lag.

Research benchmark only. Not a trading signal.
