# SOL RCD v2 Candidate #1 — 2026 Anatomy A1 Result

Raw SOLUSDT 5m coverage: **99.7698%**.
Frozen candidate: **DRIVE_UP__STR_B0_20 + RAW_RANGE_LB_HIGH / LB30 / Hold960m**.
Diagnostic only: no filter, threshold, hold, entry, exit, or candidate was optimized in this experiment.

## Preregistered verdict: **BROADER_VOLATILITY_CONTEXT_DOMINANT**

## 2026 broader-context discriminator ranking

| Feature | Family | PSI | 2026 band | Share | Dev band Exp | Best other Dev Exp | Separation | 2025 same-band share | 2025 band Exp | Primary? |
|---|---|---:|---|---:|---:|---:|---:|---:|---:|---|
| `range_72h` | volatility | 0.797 | LOW | 74.5% | $+1.24 | $+3.39 | $+2.15 | 47.1% | $+4.33 | YES |
| `range_24h` | volatility | 0.697 | LOW | 70.6% | $+2.48 | $+5.23 | $+2.75 | 51.8% | $+0.64 | YES |
| `range_7d` | volatility | 0.601 | LOW | 70.6% | $-0.06 | $+3.59 | $+3.64 | 48.8% | $+0.91 | YES |
| `ret_7d` | direction_location | 0.739 | MID | 51.0% | $-0.12 | $+4.10 | $+4.23 | 42.4% | $+2.26 | no |
| `ret_72h` | direction_location | 0.575 | LOW | 51.0% | $+2.86 | $+3.37 | $+0.51 | 42.9% | $+8.00 | no |
| `ret_24h` | direction_location | 0.194 | MID | 49.0% | $+3.76 | $+2.28 | $-1.49 | 38.8% | $-0.35 | no |
| `loc_72h` | direction_location | 0.192 | LOW | 54.9% | $+2.08 | $+3.17 | $+1.09 | 48.8% | $+8.60 | no |
| `loc_7d` | direction_location | 0.133 | LOW | 49.0% | $+2.87 | $+3.22 | $+0.35 | 48.2% | $+9.46 | no |
| `loc_24h` | direction_location | 0.086 | LOW | 45.1% | $+2.19 | $+2.43 | $+0.25 | 40.6% | $+8.04 | no |
| `range_ratio_24_72` | volatility | 0.021 | HIGH | 39.2% | $+2.39 | $+2.60 | $+0.21 | 35.9% | $+10.08 | no |

## Frozen candidate path by year

| Year | N | WR | Net | Exp | PF | DD | LS | Med MFE | Med MAE | Med giveback |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 111 | 61.26% | $+479.60 | $+4.32 | 1.565 | $209.18 | 6 | 5.24% | -3.30% | 4.06% |
| 2021 | 840 | 49.29% | $+3276.46 | $+3.90 | 1.335 | $1489.73 | 12 | 4.26% | -4.18% | 4.38% |
| 2022 | 392 | 51.28% | $+611.65 | $+1.56 | 1.163 | $533.00 | 8 | 3.54% | -3.37% | 3.43% |
| 2023 | 224 | 47.32% | $+741.29 | $+3.31 | 1.406 | $454.80 | 10 | 2.88% | -3.17% | 3.21% |
| 2024 | 249 | 51.41% | $+658.77 | $+2.65 | 1.354 | $289.29 | 8 | 2.70% | -3.01% | 2.54% |
| 2025 | 170 | 61.76% | $+750.59 | $+4.42 | 1.746 | $190.51 | 5 | 2.96% | -2.55% | 1.83% |
| 2026 | 51 | 45.10% | $-104.80 | $-2.05 | 0.745 | $218.75 | 10 | 1.87% | -2.03% | 2.21% |

## Stop-rule note

Any primary discriminator found here is **diagnostic evidence only**. It is not a promoted trading filter. A future RCD-v3 must be separately preregistered and may not optimize a threshold on exposed 2026 data.
