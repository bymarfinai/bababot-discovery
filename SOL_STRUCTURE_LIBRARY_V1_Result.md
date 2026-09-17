# SOL Structural Detector Library V1 — Result

- Data coverage: **99.769767%**
- Total detected structure-events: **32302**
- Evaluation: **2020-2024**; 2025+ remained **CLOSED**.
- Entry: next 5m open after causal structure signal.
- Diagnostic exit: fixed +60m close, **0.15%** round-trip cost, $500 notional.

## Pooled detector scorecard

| Structure | N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | Median MFE | Median MAE | MFE/MAE | Positive years | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| SWEEP_RECLAIM | 13,599 | 43.02% | -0.1216% | 0.751 | -$8,271.57 | $8,308.62 | 15 | 9.96% | +0.575% | -0.595% | 0.957 | 0/5 | **REJECTED_AS_DEFINED** |
| HL_CONTINUATION | 11,428 | 40.14% | -0.1351% | 0.738 | -$7,719.58 | $8,341.12 | 17 | 12.73% | +0.582% | -0.582% | 0.989 | 0/5 | **REJECTED_AS_DEFINED** |
| BREAKOUT_FIRST_PULLBACK | 2,025 | 39.95% | -0.1218% | 0.750 | -$1,233.10 | $1,234.08 | 20 | 11.41% | +0.564% | -0.576% | 0.939 | 0/5 | **REJECTED_AS_DEFINED** |
| LL_REVERSAL_BREAK | 5,250 | 40.99% | -0.1366% | 0.735 | -$3,585.57 | $3,603.64 | 18 | 12.32% | +0.574% | -0.597% | 0.980 | 0/5 | **REJECTED_AS_DEFINED** |

## Per-year economics

### SWEEP_RECLAIM
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 927 | 44.55% | -0.1671% | 0.736 | -$774.36 | 10.46% | 0.889 |
| 2021 | 3,137 | 46.00% | -0.0743% | 0.882 | -$1,165.49 | 10.52% | 0.951 |
| 2022 | 3,135 | 41.50% | -0.1861% | 0.649 | -$2,917.34 | 9.54% | 0.920 |
| 2023 | 3,230 | 41.86% | -0.1045% | 0.717 | -$1,687.31 | 9.04% | 1.012 |
| 2024 | 3,170 | 42.30% | -0.1090% | 0.716 | -$1,727.06 | 10.60% | 0.957 |

### HL_CONTINUATION
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 728 | 45.47% | -0.0638% | 0.892 | -$232.22 | 11.95% | 1.109 |
| 2021 | 2,741 | 44.73% | -0.0955% | 0.860 | -$1,308.46 | 13.35% | 1.011 |
| 2022 | 2,552 | 37.85% | -0.2315% | 0.568 | -$2,953.49 | 12.15% | 0.895 |
| 2023 | 2,648 | 37.95% | -0.0872% | 0.783 | -$1,153.94 | 13.26% | 1.019 |
| 2024 | 2,759 | 38.38% | -0.1502% | 0.641 | -$2,071.47 | 12.36% | 0.971 |

### BREAKOUT_FIRST_PULLBACK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 139 | 46.76% | -0.2409% | 0.597 | -$167.45 | 5.76% | 1.029 |
| 2021 | 507 | 41.62% | -0.1826% | 0.715 | -$462.98 | 9.86% | 0.854 |
| 2022 | 423 | 40.19% | -0.1253% | 0.730 | -$265.00 | 11.58% | 1.000 |
| 2023 | 463 | 37.80% | -0.0227% | 0.945 | -$52.57 | 14.69% | 0.870 |
| 2024 | 493 | 38.13% | -0.1157% | 0.704 | -$285.09 | 11.36% | 0.975 |

### LL_REVERSAL_BREAK
| Year | N | WR60 | Exp60 | PF | PnL | Clean impulse | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 348 | 47.70% | -0.1493% | 0.769 | -$259.73 | 12.93% | 0.932 |
| 2021 | 1,188 | 46.46% | -0.0786% | 0.879 | -$466.82 | 12.04% | 1.054 |
| 2022 | 1,139 | 39.86% | -0.1914% | 0.660 | -$1,090.11 | 13.35% | 1.006 |
| 2023 | 1,255 | 35.22% | -0.1279% | 0.691 | -$802.75 | 12.27% | 0.888 |
| 2024 | 1,320 | 40.76% | -0.1464% | 0.645 | -$966.17 | 11.59% | 1.028 |

## Frozen gate audit
All four detectors PASS only the sample-size gate and FAIL expectancy, PF, 4/5 positive years, and median MFE/MAE >= 1.20.

# STATUS: PASSING_STRUCTURES=NONE

Interpretation: these exact bare structural events are common but are **not standalone entries**. Do not rescue these definitions on 2020-2024 by tuning pivot order, adding penetration thresholds, hour filters, indicators, regime filters, TP, or SL. The next library iteration must test **different market-logic structures**, not retuned versions of these four.

Authoritative workflow run: `35208494536`
Artifact: `10491381472`
Artifact digest: `sha256:04d2a4502fdc2bfc3bbbc31056d123a34c0c7e4815831ccd821db18c1135a609`
