# BNB B42-S2 — Causal Daily 1% Fingerprint Selector Result

**Status: BNB_B42_S2_SELECTOR_CALIBRATION_NOT_READY**

Signature: `1acd7720c44c040b9d9e33ce48973f1579ca67e0d8573cf32b5a21febb2a4664`

Selected calibration threshold: **0.50** (DESCRIPTIVE_FALLBACK_NO_PROMOTION)

## 2024 calibration threshold sweep

| Threshold | N | Trades/day | WR | Mean R | Eligible |
|---:|---:|---:|---:|---:|---|
| 0.50 | 352 | 0.962 | 45.17% | -0.030 | NO |
| 0.55 | 308 | 0.842 | 42.21% | -0.112 | NO |
| 0.60 | 124 | 0.339 | 43.55% | -0.073 | NO |
| 0.65 | 14 | 0.038 | 28.57% | -0.429 | NO |
| 0.70 | 0 | 0.000 | — | nan | NO |
| 0.75 | 0 | 0.000 | — | nan | NO |
| 0.80 | 0 | 0.000 | — | nan | NO |
| 0.85 | 0 | 0.000 | — | nan | NO |
| 0.90 | 0 | 0.000 | — | nan | NO |

## Untouched REF 2025-2026

- N: **505**
- Trades/day: **0.837**
- WIN rate: **44.16%**
- Mean realized R/trade: **-0.009R**
- Total gross R: **-4.5R**
- LONG share: **47.72%**

| Year | N | Trades/day | WR | Mean R | Total R |
|---|---:|---:|---:|---:|---:|
| 2025 | 315 | 0.863 | 47.30% | 0.040 | 12.5 |
| 2026 | 190 | 0.798 | 38.95% | -0.090 | -17.1 |

## Decision
**BNB_B42_S2_SELECTOR_CALIBRATION_NOT_READY**

The 80% / ~1 trade-per-day target is not validated under this frozen S2 selector. Do not tune REF.
