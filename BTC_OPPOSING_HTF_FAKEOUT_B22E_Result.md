# BTC Opposing Higher-TF Fakeout B22E — Result

5m source rows: **698,112**; coverage: **100.0000%**

Primary fakeout = within first 6 entry-TF bars after execution: close < EMA20, EMA20 turns down, and bullish EMA spread narrows. This is an immediate MA-structure failure, not a failed higher-high label.

## Pullback/reclaim primary comparison

| Partition | Entry→Higher TF | Higher state | N | Fakeout MA6 | Hard reversal 12 | Median ret6 | Median MFE6 | Median MAE6 | Strong-shape persistence |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| august | 1h→4h | NEUTRAL | 3 | 0.00% | 33.33% | -0.06% | 0.25% | -0.50% | 72.22% |
| august | 1h→4h | STRONG_BULL | 3 | 33.33% | 33.33% | -0.34% | 0.21% | -0.46% | 44.44% |
| august | 5m→1h | STRONG_BEAR | 3 | 0.00% | 0.00% | 0.11% | 0.13% | -0.05% | 83.33% |
| august | 5m→1h | NEUTRAL | 36 | 41.67% | 36.11% | 0.06% | 0.11% | -0.07% | 68.52% |
| august | 5m→1h | STRONG_BULL | 24 | 41.67% | 45.83% | 0.00% | 0.11% | -0.18% | 65.28% |
| development | 1h→4h | NEUTRAL | 182 | 43.41% | 43.41% | -0.05% | 0.68% | -0.62% | 70.33% |
| development | 1h→4h | STRONG_BULL | 94 | 42.55% | 30.85% | 0.07% | 0.81% | -0.53% | 67.73% |
| development | 5m→1h | STRONG_BEAR | 395 | 49.11% | 51.90% | -0.02% | 0.14% | -0.16% | 68.06% |
| development | 5m→1h | NEUTRAL | 2371 | 50.91% | 50.19% | -0.03% | 0.14% | -0.15% | 67.16% |
| development | 5m→1h | STRONG_BULL | 1239 | 51.09% | 50.44% | -0.03% | 0.18% | -0.19% | 65.60% |
| external | 1h→4h | NEUTRAL | 136 | 41.18% | 42.65% | -0.11% | 0.77% | -0.69% | 72.06% |
| external | 1h→4h | STRONG_BULL | 80 | 45.00% | 38.75% | -0.35% | 0.76% | -1.13% | 66.46% |
| external | 5m→1h | STRONG_BEAR | 294 | 45.58% | 52.04% | -0.01% | 0.25% | -0.23% | 70.92% |
| external | 5m→1h | NEUTRAL | 1652 | 48.61% | 48.97% | -0.02% | 0.23% | -0.22% | 68.23% |
| external | 5m→1h | STRONG_BULL | 1032 | 49.71% | 47.48% | -0.04% | 0.25% | -0.24% | 66.13% |
| reference_validation | 1h→4h | NEUTRAL | 90 | 50.00% | 44.44% | -0.04% | 0.55% | -0.54% | 70.37% |
| reference_validation | 1h→4h | STRONG_BULL | 61 | 44.26% | 40.98% | -0.20% | 0.71% | -0.75% | 72.95% |
| reference_validation | 5m→1h | STRONG_BEAR | 226 | 48.67% | 53.54% | 0.00% | 0.13% | -0.14% | 68.81% |
| reference_validation | 5m→1h | NEUTRAL | 1048 | 44.85% | 45.32% | -0.01% | 0.12% | -0.13% | 70.93% |
| reference_validation | 5m→1h | STRONG_BULL | 608 | 43.09% | 41.94% | 0.00% | 0.15% | -0.15% | 70.37% |

## Frozen hypothesis gates

- 5m_to_1h: **FAIL**; strong >=20pp effect: **NO**
  - external: bear N=294, bull N=1032, fakeout 45.58% vs 49.71% (Δ -4.13pp)
  - development: bear N=395, bull N=1239, fakeout 49.11% vs 51.09% (Δ -1.98pp)
  - reference_validation: bear N=226, bull N=608, fakeout 48.67% vs 43.09% (Δ +5.58pp)
- 1h_to_4h: **INCONCLUSIVE**; strong >=20pp effect: **NO**
  - external: MISSING_STATE
  - development: MISSING_STATE
  - reference_validation: MISSING_STATE

## Secondary crossover diagnostic

CROSSOVER_INIT groups are included in the CSV/events for diagnosis but do not determine the preregistered gate.

All higher-TF states are shifted to candle-close availability. Research only; live BBC unchanged.
