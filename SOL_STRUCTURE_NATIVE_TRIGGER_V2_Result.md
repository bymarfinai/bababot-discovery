# SOL Structure-Specific Native Trigger V2 — Result

- Data coverage: **99.769767%**
- Structural setup records: **50748**
- Native-triggered trade records: **20147**
- Evaluation: 2020-2024; 2025+ remained CLOSED.
- Structure is frozen context only. Entry occurs only after the preregistered V2 native trigger.
- Entry = next 5m open after trigger; fixed +60m diagnostic; 0.15% RT cost.

## Native trigger V2 scorecard

| Structure | Native trigger | Setup N | Trigger N | Rate | WR60 | Exp60 | PF | PnL | Max DD | Clean impulse | MFE/MAE | Delay | Pos yrs | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SWEEP_RECLAIM | RECLAIM_CANDLE_HIGH_BREAK | 13601 | 6322 | 46.48% | 41.19% | -0.1257% | 0.743 | $-3973.85 | $4077.08 | 10.55% | 0.926 | 10.0m | 0/5 | **REJECTED_AS_DEFINED** |
| HL_SETUP | FIRST_POST_HL_SWING_HIGH_BREAK | 26411 | 7592 | 28.75% | 40.09% | -0.1472% | 0.721 | $-5586.30 | $5921.14 | 13.24% | 0.933 | 35.0m | 0/5 | **REJECTED_AS_DEFINED** |
| BREAKOUT_PULLBACK_SETUP | PULLBACK_PIVOT_HIGH_BREAK | 2025 | 1405 | 69.38% | 42.21% | -0.1151% | 0.772 | $-808.89 | $810.03 | 13.38% | 0.964 | 5.0m | 1/5 | **REJECTED_AS_DEFINED** |
| FAILED_BREAKDOWN_RECLAIM | RECLAIM_CANDLE_HIGH_BREAK | 8711 | 4828 | 55.42% | 42.79% | -0.1237% | 0.744 | $-2987.06 | $2992.39 | 11.12% | 1.000 | 5.0m | 0/5 | **REJECTED_AS_DEFINED** |

## Yearly economics

### SWEEP_RECLAIM -> RECLAIM_CANDLE_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 429 | 48.25% | -0.0230% | 0.955 | $-49.32 | 9.09% | 0.916 | 10.0m |
| 2021 | 1391 | 45.94% | -0.0667% | 0.896 | $-464.11 | 11.50% | 1.044 | 10.0m |
| 2022 | 1499 | 36.36% | -0.2195% | 0.603 | $-1644.79 | 9.81% | 0.783 | 10.0m |
| 2023 | 1529 | 39.11% | -0.1272% | 0.673 | $-972.82 | 10.40% | 0.934 | 5.0m |
| 2024 | 1474 | 41.72% | -0.1144% | 0.701 | $-842.82 | 10.99% | 0.994 | 5.0m |

### HL_SETUP -> FIRST_POST_HL_SWING_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 482 | 48.13% | -0.0659% | 0.896 | $-158.89 | 14.32% | 1.042 | 35.0m |
| 2021 | 1759 | 44.12% | -0.1264% | 0.819 | $-1111.98 | 13.53% | 0.955 | 35.0m |
| 2022 | 1702 | 37.13% | -0.2230% | 0.577 | $-1897.46 | 11.75% | 0.859 | 35.0m |
| 2023 | 1790 | 36.98% | -0.1119% | 0.743 | $-1001.10 | 13.97% | 0.947 | 35.0m |
| 2024 | 1859 | 39.91% | -0.1524% | 0.645 | $-1416.87 | 13.34% | 0.956 | 35.0m |

### BREAKOUT_PULLBACK_SETUP -> PULLBACK_PIVOT_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 107 | 46.73% | -0.2824% | 0.579 | $-151.11 | 7.48% | 1.015 | 5.0m |
| 2021 | 352 | 44.89% | -0.1214% | 0.818 | $-213.61 | 11.08% | 0.819 | 5.0m |
| 2022 | 296 | 42.91% | -0.1529% | 0.681 | $-226.27 | 13.51% | 0.964 | 5.0m |
| 2023 | 301 | 40.86% | 0.0291% | 1.081 | $43.77 | 17.28% | 1.072 | 5.0m |
| 2024 | 349 | 38.68% | -0.1500% | 0.657 | $-261.67 | 14.04% | 0.936 | 5.0m |

### FAILED_BREAKDOWN_RECLAIM -> RECLAIM_CANDLE_HIGH_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE | Delay |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 262 | 48.47% | -0.1498% | 0.777 | $-196.27 | 12.60% | 0.834 | 5.0m |
| 2021 | 1085 | 44.33% | -0.0746% | 0.881 | $-404.69 | 11.61% | 1.012 | 5.0m |
| 2022 | 1048 | 44.56% | -0.1158% | 0.770 | $-606.80 | 11.55% | 1.000 | 5.0m |
| 2023 | 1196 | 39.38% | -0.1421% | 0.632 | $-849.85 | 10.20% | 0.988 | 5.0m |
| 2024 | 1237 | 42.04% | -0.1503% | 0.619 | $-929.45 | 10.91% | 1.008 | 5.0m |

## Frozen gate audit
All four detectors PASS sample-size N>=100 and FAIL the other four promotion gates: pooled positive expectancy, PF>=1.15, positive PnL in >=4/5 years, and median MFE/|MAE|>=1.20.

## Authoritative run
- Workflow run: **35213069335**
- Artifact: **10493856343**
- Artifact SHA256: **566c26ad165dfb3c96a23556fec81502e256710f9ce4060555e39bfa45f972a5**

PASSING_NATIVE_DETECTORS=NONE
