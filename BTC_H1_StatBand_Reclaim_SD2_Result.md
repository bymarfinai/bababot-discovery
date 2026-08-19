# BTC H1 Statistical Band Reclaim SD2 — Result

Fixed clocks: **11:00 / 15:00 / 01:00 / 02:00 WIB**. Band = prior24 completed 1H closes mean ± k×population-std. Event must also sweep/reclaim the causal prior3H range.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58128**. Reference chronological cut: **2025-03-15 16:48:00+00:00**.

## Directional matrix

| Candidate | Dev N/+3H | Validation N/+3H | External N/+3H | August N/+3H | Dir supported | 80% |
|---|---:|---:|---:|---:|---|---|
| `LONG_K1.0` | 109/59.63% | 35/51.43% | 76/51.32% | 2/0.00% | FAIL | FAIL |
| `SHORT_K1.0` | 104/46.15% | 49/55.10% | 73/50.68% | 0/- | FAIL | FAIL |
| `LONG_K1.5` | 113/63.72% | 35/60.00% | 68/57.35% | 1/100.00% | FAIL | FAIL |
| `SHORT_K1.5` | 100/50.00% | 48/43.75% | 78/51.28% | 1/100.00% | FAIL | FAIL |
| `LONG_K2.0` | 103/67.96% | 35/60.00% | 64/57.81% | 3/66.67% | FAIL | FAIL |
| `SHORT_K2.0` | 77/59.74% | 50/42.00% | 64/45.31% | 1/0.00% | FAIL | FAIL |
| `LONG_K2.5` | 86/69.77% | 38/63.16% | 68/61.76% | 2/50.00% | FAIL | FAIL |
| `SHORT_K2.5` | 69/44.93% | 23/47.83% | 40/55.00% | 1/0.00% | FAIL | FAIL |

## Executable net RR 1:1 matrix

Next1H open; structural SL at event extreme; target raw distance = risk +0.30%; fee0.15%; max6H; adverse-first same-hour ambiguity.

| Candidate | Validation N/WR/PnL | External N/WR/PnL | August N/WR/PnL | Exec supported |
|---|---:|---:|---:|---|
| `LONG_K1.0` | 35/20.00%/$-64.86 | 76/23.68%/$-239.77 | 2/0.00%/$-3.57 | FAIL |
| `SHORT_K1.0` | 49/28.57%/$-64.41 | 73/32.88%/$-117.77 | 0/-/$0.00 | FAIL |
| `LONG_K1.5` | 35/14.29%/$-63.34 | 68/20.59%/$-282.09 | 1/0.00%/$-1.63 | FAIL |
| `SHORT_K1.5` | 48/25.00%/$-70.30 | 78/32.05%/$-112.66 | 1/100.00%/$2.49 | FAIL |
| `LONG_K2.0` | 35/31.43%/$-40.00 | 64/28.12%/$-205.63 | 3/33.33%/$-3.02 | FAIL |
| `SHORT_K2.0` | 50/20.00%/$-82.28 | 64/39.06%/$-59.21 | 1/0.00%/$-2.24 | FAIL |
| `LONG_K2.5` | 38/28.95%/$-70.19 | 68/23.53%/$-288.78 | 2/0.00%/$-5.79 | FAIL |
| `SHORT_K2.5` | 23/30.43%/$-22.40 | 40/37.50%/$-34.81 | 1/0.00%/$-2.24 | FAIL |

Directional/execution gate passes: **0 candidate(s)**.

## External chronological blocks

### LONG_K1.0

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 19 | 57.89% | 0.49% |
| B2 | 19 | 57.89% | 0.26% |
| B3 | 19 | 47.37% | -0.15% |
| B4 | 19 | 42.11% | -0.16% |

### SHORT_K1.0

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 18 | 50.00% | 0.23% |
| B2 | 18 | 55.56% | -0.22% |
| B3 | 18 | 55.56% | 0.20% |
| B4 | 19 | 42.11% | -0.24% |

### LONG_K1.5

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 17 | 52.94% | -0.11% |
| B2 | 17 | 64.71% | 0.33% |
| B3 | 17 | 70.59% | -0.04% |
| B4 | 17 | 41.18% | 0.37% |

### SHORT_K1.5

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 19 | 47.37% | -0.25% |
| B2 | 20 | 45.00% | -0.44% |
| B3 | 19 | 63.16% | 0.41% |
| B4 | 20 | 50.00% | -0.08% |

### LONG_K2.0

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 16 | 62.50% | 0.08% |
| B2 | 16 | 62.50% | 0.44% |
| B3 | 16 | 62.50% | 0.04% |
| B4 | 16 | 43.75% | 0.26% |

### SHORT_K2.0

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 16 | 50.00% | -0.13% |
| B2 | 16 | 43.75% | -0.58% |
| B3 | 16 | 50.00% | 0.08% |
| B4 | 16 | 37.50% | -0.11% |

### LONG_K2.5

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 17 | 52.94% | -0.09% |
| B2 | 17 | 58.82% | -0.02% |
| B3 | 17 | 58.82% | 0.19% |
| B4 | 17 | 76.47% | 0.56% |

### SHORT_K2.5

| Block | N | +3H | Avg3H |
|---|---:|---:|---:|
| B1 | 10 | 40.00% | -0.25% |
| B2 | 10 | 50.00% | -0.60% |
| B3 | 10 | 80.00% | 0.36% |
| B4 | 10 | 50.00% | -0.10% |

No k/side is reselected from validation, external, or August. No post-result rescue.
