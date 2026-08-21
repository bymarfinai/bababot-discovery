# BTC Dynamic Trend-State Exit B22H — Result

5m source rows: **698,112**; coverage: **100.0000%**

Every completed entry-timeframe candle is reclassified dynamically. HOLD while STRONG_CONTINUATION or HEALTHY_CONTINUATION; EXIT at next open after first REVERSAL. No fixed TP and no fixed candle horizon.

| Partition | Entry→HTF | HTF state @ entry | N | WR | PF | Mean ret | Median ret | Median MFE | Median MAE | Median bars | Strong frac | Healthy frac | Max L streak |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| august | 1h→4h | NEUTRAL | 2 | 0.00% | 0.00 | -0.17% | -0.17% | 0.54% | -0.45% | 14.5 | 71.94% | 20.00% | 2 |
| august | 1h→4h | STRONG_BULL | 3 | 0.00% | 0.00 | -0.26% | -0.18% | 0.34% | -0.35% | 9.0 | 21.37% | 40.31% | 3 |
| august | 5m→1h | STRONG_BEAR | 2 | 100.00% | inf | 0.07% | 0.07% | 0.22% | -0.03% | 18.0 | 63.93% | 30.50% | 0 |
| august | 5m→1h | NEUTRAL | 29 | 34.48% | 4.96 | 0.21% | -0.04% | 0.09% | -0.06% | 7.0 | 46.57% | 22.47% | 5 |
| august | 5m→1h | STRONG_BULL | 20 | 30.00% | 3.34 | 0.28% | -0.10% | 0.16% | -0.18% | 9.5 | 51.80% | 23.72% | 8 |
| development | 1h→4h | NEUTRAL | 139 | 32.37% | 1.31 | 0.16% | -0.37% | 0.95% | -0.73% | 8.0 | 59.10% | 17.43% | 13 |
| development | 1h→4h | STRONG_BULL | 73 | 36.99% | 2.46 | 0.67% | -0.21% | 0.93% | -0.54% | 9.0 | 48.65% | 28.26% | 10 |
| development | 5m→1h | STRONG_BEAR | 304 | 25.33% | 0.99 | -0.00% | -0.10% | 0.15% | -0.14% | 6.0 | 56.46% | 15.87% | 20 |
| development | 5m→1h | NEUTRAL | 1789 | 24.48% | 0.98 | -0.00% | -0.09% | 0.14% | -0.14% | 6.0 | 54.18% | 18.58% | 24 |
| development | 5m→1h | STRONG_BULL | 919 | 24.37% | 0.95 | -0.01% | -0.11% | 0.18% | -0.17% | 6.0 | 52.19% | 19.59% | 18 |
| external | 1h→4h | NEUTRAL | 101 | 33.66% | 1.59 | 0.44% | -0.50% | 1.14% | -0.88% | 10.0 | 60.38% | 20.00% | 9 |
| external | 1h→4h | STRONG_BULL | 64 | 21.88% | 1.01 | 0.01% | -0.67% | 0.91% | -1.19% | 7.5 | 56.38% | 21.86% | 13 |
| external | 5m→1h | STRONG_BEAR | 213 | 25.35% | 0.66 | -0.07% | -0.11% | 0.27% | -0.21% | 7.0 | 57.09% | 16.57% | 14 |
| external | 5m→1h | NEUTRAL | 1180 | 26.27% | 0.94 | -0.01% | -0.13% | 0.24% | -0.22% | 7.0 | 54.70% | 19.07% | 17 |
| external | 5m→1h | STRONG_BULL | 739 | 25.98% | 1.13 | 0.03% | -0.14% | 0.29% | -0.22% | 7.0 | 53.15% | 21.66% | 15 |
| reference_validation | 1h→4h | NEUTRAL | 68 | 26.47% | 0.94 | -0.03% | -0.28% | 0.57% | -0.54% | 7.0 | 58.63% | 16.21% | 8 |
| reference_validation | 1h→4h | STRONG_BULL | 45 | 26.67% | 1.15 | 0.08% | -0.45% | 0.89% | -0.67% | 8.0 | 61.57% | 21.02% | 8 |
| reference_validation | 5m→1h | STRONG_BEAR | 178 | 25.28% | 0.78 | -0.03% | -0.08% | 0.14% | -0.14% | 6.0 | 53.54% | 16.77% | 11 |
| reference_validation | 5m→1h | NEUTRAL | 797 | 29.86% | 1.16 | 0.02% | -0.07% | 0.15% | -0.12% | 8.0 | 57.42% | 18.32% | 15 |
| reference_validation | 5m→1h | STRONG_BULL | 454 | 29.74% | 0.98 | -0.00% | -0.08% | 0.20% | -0.14% | 8.0 | 55.59% | 20.85% | 19 |

State transitions are evaluated at every completed candle; normal healthy pullbacks are allowed without forcing an exit.

Research only; live BBC unchanged.
