# BTC Continuous MA Failure Survival B22F — Result

5m source rows: **698,112**; coverage: **100.0000%**

Every completed candle after entry is monitored continuously. No six-bar fakeout cutoff is used. The tables below show how long the bullish MA structure survives before first failure.

## Pullback/reclaim survival by higher-TF state

| Partition | Entry→HTF | HTF state | N | Median bars→soft fail | Soft survive 1 | 2 | 3 | 4 | 6 | 12 | 24 | 48 | Median bars→hard fail |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| august | 1h→4h | NEUTRAL | 3 | 9.0 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 33.33% | 0.00% | 0.00% | 40.0 |
| august | 1h→4h | STRONG_BULL | 3 | 9.0 | 66.67% | 66.67% | 66.67% | 66.67% | 66.67% | 33.33% | 33.33% | 0.00% | 15.5 |
| august | 5m→1h | STRONG_BEAR | 3 | 17.0 | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 100.00% | 0.00% | 0.00% | 20.0 |
| august | 5m→1h | NEUTRAL | 36 | 7.0 | 86.11% | 72.22% | 69.44% | 63.89% | 58.33% | 34.29% | 27.27% | 6.06% | 17.0 |
| august | 5m→1h | STRONG_BULL | 24 | 9.5 | 91.67% | 79.17% | 70.83% | 66.67% | 58.33% | 33.33% | 16.67% | 0.00% | 14.5 |
| development | 1h→4h | NEUTRAL | 182 | 8.0 | 92.31% | 80.22% | 72.53% | 66.48% | 56.59% | 35.71% | 14.29% | 1.65% | 16.0 |
| development | 1h→4h | STRONG_BULL | 94 | 9.5 | 91.49% | 81.91% | 74.47% | 65.96% | 57.45% | 42.55% | 23.40% | 2.13% | 28.5 |
| development | 5m→1h | STRONG_BEAR | 395 | 7.0 | 89.62% | 76.46% | 69.37% | 60.00% | 50.89% | 23.29% | 6.58% | 0.51% | 12.0 |
| development | 5m→1h | NEUTRAL | 2371 | 6.0 | 90.22% | 79.00% | 70.94% | 62.25% | 49.09% | 25.77% | 7.68% | 1.31% | 12.0 |
| development | 5m→1h | STRONG_BULL | 1239 | 6.0 | 87.97% | 78.61% | 68.68% | 60.61% | 48.91% | 26.88% | 9.28% | 1.05% | 12.0 |
| external | 1h→4h | NEUTRAL | 136 | 10.0 | 92.65% | 83.82% | 78.68% | 75.00% | 58.82% | 41.18% | 17.65% | 2.94% | 16.0 |
| external | 1h→4h | STRONG_BULL | 80 | 7.0 | 92.50% | 85.00% | 80.00% | 70.00% | 55.00% | 28.75% | 12.50% | 3.75% | 17.5 |
| external | 5m→1h | STRONG_BEAR | 294 | 7.0 | 90.14% | 81.63% | 71.77% | 64.63% | 54.42% | 29.25% | 8.84% | 0.00% | 11.0 |
| external | 5m→1h | NEUTRAL | 1652 | 7.0 | 90.13% | 80.63% | 71.67% | 65.31% | 51.39% | 29.48% | 10.59% | 2.06% | 13.0 |
| external | 5m→1h | STRONG_BULL | 1032 | 7.0 | 90.89% | 79.94% | 71.61% | 63.08% | 50.29% | 26.07% | 9.79% | 1.45% | 13.0 |
| reference_validation | 1h→4h | NEUTRAL | 90 | 6.5 | 91.11% | 77.78% | 68.89% | 64.44% | 50.00% | 31.11% | 6.67% | 4.44% | 15.0 |
| reference_validation | 1h→4h | STRONG_BULL | 61 | 7.0 | 95.08% | 80.33% | 75.41% | 67.21% | 55.74% | 34.43% | 9.84% | 3.28% | 15.0 |
| reference_validation | 5m→1h | STRONG_BEAR | 226 | 7.0 | 86.73% | 76.99% | 69.91% | 62.39% | 51.33% | 29.20% | 10.62% | 0.88% | 11.0 |
| reference_validation | 5m→1h | NEUTRAL | 1048 | 8.0 | 91.03% | 82.63% | 75.38% | 68.03% | 55.15% | 30.25% | 10.78% | 1.81% | 15.0 |
| reference_validation | 5m→1h | STRONG_BULL | 608 | 8.0 | 92.11% | 82.73% | 75.00% | 68.42% | 56.91% | 32.57% | 9.54% | 0.99% | 16.0 |

## Frozen opposing-HTF hypothesis

- 5m_to_1h: **FAIL**; >=20pp strong effect: **NO**
  - external: bear N=294, bull N=1032; median soft failure 7.0 vs 7.0 bars; bar-6 survival 54.42% vs 50.29% (Δ +4.13pp)
  - development: bear N=395, bull N=1239; median soft failure 7.0 vs 6.0 bars; bar-6 survival 50.89% vs 48.91% (Δ +1.98pp)
  - reference_validation: bear N=226, bull N=608; median soft failure 7.0 vs 8.0 bars; bar-6 survival 51.33% vs 56.91% (Δ -5.58pp)
- 1h_to_4h: **INCONCLUSIVE**; >=20pp strong effect: **NO**
  - external: MISSING_STATE
  - development: MISSING_STATE
  - reference_validation: MISSING_STATE

## Interpretation

- Failure time starts at bar 1 immediately after execution and every later candle is inspected.
- Because every trend eventually ends, eventual failure alone is not called a fakeout; earlier failure is the object of comparison.
- Higher-TF states are causally shifted to candle-close availability.
- Research only; live BBC unchanged.
