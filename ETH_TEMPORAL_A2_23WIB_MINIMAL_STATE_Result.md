# ETH Temporal A2 — 23:00 WIB Minimal-State Discovery — Result

- ETHUSDT 5m Development coverage: **100.000000%**
- Complete 23:00 WIB anchors: **1096**
- Search: 5 families × 6 lookbacks × 3 bins × 6 holds = **540 candidates**
- 2022-calibrated quantile thresholds frozen before 2023/2024 application: **YES**
- Formal pass candidates: **0**
- Formal pass families: **0**

## Unconditional 23:00 WIB LONG controls

| Hold | N | WR | Net | Exp | PF | DD | LS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 60m | 1096 | 34.95% | $-806.64 | $-0.7360 | 0.570 | $881.98 | 18 |
| 120m | 1096 | 40.05% | $-850.02 | $-0.7756 | 0.639 | $905.22 | 9 |
| 240m | 1096 | 45.16% | $-888.49 | $-0.8107 | 0.732 | $903.41 | 12 |
| 360m | 1096 | 44.80% | $-741.16 | $-0.6762 | 0.802 | $751.44 | 11 |
| 720m | 1095 | 45.75% | $-652.17 | $-0.5956 | 0.869 | $826.76 | 11 |
| 960m | 1095 | 47.49% | $-477.85 | $-0.4364 | 0.909 | $737.68 | 9 |

## Best candidate per one-dimensional state family

| Family | LB | Bin | Hold | PASS | N | WR | Net | Exp | PF | DD | LS | MinFwdExp | WR22/23/24 |
|---|---:|:---:|---:|:---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| RV | 240m | HIGH | 720m | NO | 191 | 53.40% | $100.23 | $0.5248 | 1.085 | $308.30 | 7 | $1.8359 | 50.82/62.50/56.60% |
| DRIVE | 120m | HIGH | 960m | NO | 329 | 48.94% | $140.35 | $0.4266 | 1.088 | $237.08 | 7 | $1.3353 | 51.64/49.47/45.54% |
| TREND | 360m | HIGH | 960m | NO | 324 | 49.07% | $134.69 | $0.4157 | 1.081 | $172.05 | 9 | $1.2163 | 52.46/50.59/44.44% |
| RANGE_POS | 360m | HIGH | 960m | NO | 346 | 48.55% | $31.62 | $0.0914 | 1.018 | $288.28 | 6 | $0.9962 | 50.00/49.51/46.28% |
| EFFICIENCY | 30m | MID | 960m | NO | 330 | 46.97% | $24.73 | $0.0749 | 1.016 | $274.31 | 9 | $0.9908 | 41.32/49.50/50.93% |

## Formal pass candidates

No candidate passed the frozen formal gate. Near-misses remain diagnostic only.

## Overall robustness-ranked candidate
**RV / LB240 / HIGH / H720** — formal_pass=False; N=191, WR=53.40%, net=$100.23, exp=$0.5248, PF=1.085, DD=$308.30, LS=7, min-forward-exp=$1.8359.

## Interpretation boundary
A2 is a one-dimensional state-discovery experiment at one exact clock. A PASS identifies a minimal conditional state worth advancing; it is not a production strategy. No state-family combinations were tested and OOS was not opened.
