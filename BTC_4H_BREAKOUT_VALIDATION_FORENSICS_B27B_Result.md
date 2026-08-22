# B27B — Why 4H Breakout Validation Is Worse

Source coverage: **100.0000%**. Frozen source trades: B27A 4H R2. No entry/exit rule changed.

## Partition comparison

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 229 | 86 | 143 | 37.55% | 1.14 | $1.46 | $335.46 | 2.61% |
| development | 483 | 184 | 299 | 38.10% | 1.07 | $0.55 | $263.35 | 1.91% |
| reference_validation | 343 | 110 | 233 | 32.07% | 0.87 | $-0.78 | $-266.62 | 1.37% |

## Validation by year

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025 | 224 | 69 | 155 | 30.80% | 0.78 | $-1.37 | $-306.45 | 1.35% |
| 2026 | 119 | 41 | 78 | 34.45% | 1.06 | $0.33 | $39.83 | 1.44% |

## Validation by quarter

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2025-Q1 | 69 | 23 | 46 | 33.33% | 0.66 | $-2.74 | $-189.23 | 1.50% |
| 2025-Q2 | 45 | 15 | 30 | 33.33% | 1.03 | $0.13 | $5.86 | 1.17% |
| 2025-Q3 | 48 | 15 | 33 | 31.25% | 1.06 | $0.27 | $13.13 | 1.09% |
| 2025-Q4 | 62 | 16 | 46 | 25.81% | 0.68 | $-2.20 | $-136.21 | 1.59% |
| 2026-Q1 | 62 | 22 | 40 | 35.48% | 1.18 | $1.05 | $65.00 | 1.48% |
| 2026-Q2 | 52 | 18 | 34 | 34.62% | 0.97 | $-0.16 | $-8.46 | 1.32% |
| 2026-Q3 | 5 | 1 | 4 | 20.00% | 0.27 | $-3.34 | $-16.72 | 0.81% |

## Validation by side

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| LONG | 162 | 53 | 109 | 32.72% | 0.85 | $-0.88 | $-142.13 | 1.36% |
| SHORT | 181 | 57 | 124 | 31.49% | 0.89 | $-0.69 | $-124.49 | 1.40% |

## Validation by stop distance

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <1% | 106 | 27 | 79 | 25.47% | 0.63 | $-1.01 | $-107.18 | 0.69% |
| 1-1.5% | 91 | 37 | 54 | 40.66% | 1.21 | $0.85 | $77.05 | 1.26% |
| 1.5-2% | 46 | 14 | 32 | 30.43% | 0.86 | $-0.90 | $-41.26 | 1.76% |
| 2-3% | 60 | 22 | 38 | 36.67% | 1.09 | $0.74 | $44.67 | 2.48% |
| >=3% | 40 | 10 | 30 | 25.00% | 0.63 | $-6.00 | $-239.89 | 3.96% |

## Validation by breakout candle body ratio

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <25% | 22 | 5 | 17 | 22.73% | 0.79 | $-0.76 | $-16.71 | 0.70% |
| 25-50% | 82 | 29 | 53 | 35.37% | 1.19 | $0.80 | $65.73 | 1.13% |
| 50-75% | 142 | 45 | 97 | 31.69% | 0.84 | $-0.98 | $-139.46 | 1.44% |
| >=75% | 97 | 31 | 66 | 31.96% | 0.78 | $-1.82 | $-176.17 | 2.01% |

## Validation by close extension beyond previous high/low

| Group | N | W | L | WR | Net PF | Net exp/trade | Total net | Median stop |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| <10% prev range | 42 | 11 | 31 | 26.19% | 0.67 | $-1.36 | $-57.32 | 0.89% |
| 10-25% | 61 | 16 | 45 | 26.23% | 0.55 | $-1.82 | $-111.05 | 0.91% |
| 25-50% | 68 | 20 | 48 | 29.41% | 0.81 | $-0.93 | $-63.22 | 1.18% |
| >=50% | 172 | 63 | 109 | 36.63% | 0.97 | $-0.20 | $-35.03 | 1.93% |

## Losing-trade path diagnostic

- Validation non-TP trades: **233**; MFE measurable: **233**.
- Fraction of losing/non-TP trades that still reached at least **+0.5R** before exit: **51.93%**.
- Fraction that reached at least **+1.0R** before exit: **29.61%**.

This is forensic only. Any apparent good subgroup is not a validated trading filter and requires a new preregistered test.

Research only; live BBC unchanged.
