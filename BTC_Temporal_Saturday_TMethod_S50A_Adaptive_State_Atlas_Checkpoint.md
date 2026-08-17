# BTC Temporal Saturday T-Method S5.0A — Adaptive State Atlas (Parity-Corrected)

**Status:** COMPLETE — STRONG SATURDAY-NATIVE STATE STRUCTURE FOUND; NO NEW TRADE RULE PROMOTED
**Parent:** Saturday 18:00 WIB BUY / TP2.6 / SL1.2 / max18h
**Sample:** 139; discovery83 / validation56
**Frozen benchmarks preserved:** A7.19 full-coverage and A7.26 selective.

## Reproduction/parity gates
- Parent: 139 / 65W / 74L / WR 46.76% / $+87.200
- A7.19 reproduced: $+103.383
- A7.26 exact state: 16 signals (8 discovery / 8 validation); frozen A7.19+skip economics $+109.587
- A7.13 +60m failure: 30 live-position signals / 23 eventual losses = 76.67%

## 1. Pre-entry state
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| NORMAL | 69 | 44.93% | $+9.737 | 38 / 47.37% / $+10.256 | 31 / 41.94% / $-0.519 |
| PULLBACK | 54 | 55.56% | $+91.313 | 37 / 56.76% / $+55.829 | 17 / 52.94% / $+35.483 |
| STRETCHED | 16 | 25.00% | $-13.851 | 8 / 12.50% / $-13.419 | 8 / 37.50% / $-0.432 |

### Stretch score
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| 0 | 42 | 57.14% | $+72.775 | 29 / 58.62% / $+44.294 | 13 / 53.85% / $+28.481 |
| 4 | 29 | 41.38% | $-1.888 | 16 / 37.50% / $-5.184 | 13 / 46.15% / $+3.296 |
| 2 | 23 | 52.17% | $+22.780 | 12 / 58.33% / $+25.273 | 11 / 45.45% / $-2.493 |
| 3 | 17 | 41.18% | $-11.155 | 10 / 50.00% / $-9.834 | 7 / 28.57% / $-1.321 |
| 5 | 16 | 25.00% | $-13.851 | 8 / 12.50% / $-13.419 | 8 / 37.50% / $-0.432 |
| 1 | 12 | 50.00% | $+18.538 | 8 / 50.00% / $+11.535 | 4 / 50.00% / $+7.003 |

## 2. +60m thesis health
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| MIXED | 80 | 51.25% | $+74.101 | 49 / 55.10% / $+56.982 | 31 / 45.16% / $+17.119 |
| FAILURE_CANDIDATE | 30 | 23.33% | $-28.406 | 17 / 23.53% / $-24.757 | 13 / 23.08% / $-3.649 |
| HEALTHY | 28 | 60.71% | $+48.254 | 16 / 56.25% / $+27.192 | 12 / 66.67% / $+21.062 |
| NOT_ALIVE | 1 | 0.00% | $-6.750 | 1 / 0.00% / $-6.750 | 0 / NA / $+0.000 |

## 3. Runner maturity
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| DEEP_RUNNER | 61 | 85.25% | $+285.259 | 38 / 86.84% / $+178.698 | 23 / 82.61% / $+106.561 |
| NO_0.5_IMPULSE | 50 | 4.00% | $-162.439 | 29 / 3.45% / $-107.127 | 21 / 4.76% / $-55.312 |
| SHALLOW_RUNNER | 28 | 39.29% | $-35.621 | 16 / 37.50% / $-18.904 | 12 / 41.67% / $-16.716 |

## 4. Post-0.5 path
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| NO_HINGE | 50 | 4.00% | $-162.439 | 29 / 3.45% / $-107.127 | 21 / 4.76% / $-55.312 |
| NORMAL_PULLBACK | 37 | 78.38% | $+127.096 | 25 / 76.00% / $+90.525 | 12 / 83.33% / $+36.571 |
| FAST_GIVEBACK | 30 | 50.00% | $+26.989 | 20 / 60.00% / $+40.482 | 10 / 30.00% / $-13.493 |
| CONTINUATION_FIRST | 22 | 86.36% | $+95.553 | 9 / 88.89% / $+28.787 | 13 / 84.62% / $+66.766 |

## 5. +240m A7.19 state (classification only)
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| PRESERVE | 124 | 49.19% | $+126.144 | 71 / 52.11% / $+95.609 | 53 / 45.28% / $+30.534 |
| SHALLOW_FAILURE | 8 | 37.50% | $-10.694 | 7 / 42.86% / $-9.193 | 1 / 0.00% / $-1.501 |
| NOT_ALIVE | 7 | 14.29% | $-28.250 | 5 / 0.00% / $-33.750 | 2 / 50.00% / $+5.500 |

## 6. +18h timeout health (descriptive only)
| State | N | WR | PnL | Discovery | Validation |
|---|---:|---:|---:|---:|---:|
| MIXED | 51 | 45.10% | $+19.603 | 31 / 48.39% / $+20.060 | 20 / 40.00% / $-0.457 |
| NOT_TIMEOUT | 36 | 38.89% | $+22.058 | 25 / 36.00% / $+1.388 | 11 / 45.45% / $+20.670 |
| DEAD | 26 | 38.46% | $-7.721 | 13 / 46.15% / $+0.643 | 13 / 30.77% / $-8.363 |
| STILL_ALIVE | 26 | 69.23% | $+53.259 | 14 / 71.43% / $+30.577 | 12 / 66.67% / $+22.683 |

### Next 6h after frozen timeout
- DEAD: N26; next6h mean -0.01%; median MFE 0.25%; median MAE 0.29%
- MIXED: N51; next6h mean -0.02%; median MFE 0.29%; median MAE 0.37%
- STILL_ALIVE: N26; next6h mean 0.05%; median MFE 0.34%; median MAE 0.30%

## 7. Fixed % vs volatility-normalized information (+60m, live positions only)
- full: progress 0.652 vs RV 0.653; MFE 0.621 vs RV 0.619; MAE-for-loss 0.598 vs RV 0.605
- discovery: progress 0.660 vs RV 0.663; MFE 0.562 vs RV 0.552; MAE-for-loss 0.557 vs RV 0.555
- validation: progress 0.632 vs RV 0.631; MFE 0.706 vs RV 0.702; MAE-for-loss 0.676 vs RV 0.688

## 8. Most common routes (N>=4, descriptive only)
- N15 / WR 0.0% / $-51.913 / D8 V7: `NORMAL>MIXED>NO_0.5_IMPULSE>NO_HINGE>PRESERVE`
- N9 / WR 11.1% / $-20.797 / D4 V5: `NORMAL>FAILURE_CANDIDATE>NO_0.5_IMPULSE>NO_HINGE>PRESERVE`
- N8 / WR 87.5% / $+52.235 / D5 V3: `PULLBACK>MIXED>DEEP_RUNNER>NORMAL_PULLBACK>PRESERVE`
- N7 / WR 85.7% / $+26.599 / D4 V3: `NORMAL>MIXED>DEEP_RUNNER>CONTINUATION_FIRST>PRESERVE`
- N7 / WR 85.7% / $+32.327 / D6 V1: `NORMAL>MIXED>DEEP_RUNNER>NORMAL_PULLBACK>PRESERVE`
- N6 / WR 16.7% / $-18.856 / D5 V1: `PULLBACK>MIXED>NO_0.5_IMPULSE>NO_HINGE>PRESERVE`
- N5 / WR 100.0% / $+40.951 / D5 V0: `PULLBACK>MIXED>DEEP_RUNNER>FAST_GIVEBACK>PRESERVE`
- N4 / WR 100.0% / $+28.470 / D1 V3: `NORMAL>HEALTHY>DEEP_RUNNER>CONTINUATION_FIRST>PRESERVE`
- N4 / WR 75.0% / $+8.402 / D2 V2: `NORMAL>MIXED>DEEP_RUNNER>FAST_GIVEBACK>PRESERVE`
- N4 / WR 0.0% / $-8.869 / D3 V1: `STRETCHED>MIXED>NO_0.5_IMPULSE>NO_HINGE>PRESERVE`

## Guardrail
S5.0A maps causal states only. It does not authorize a new skip, cut, lock, flip, or hold-extension rule. S5.1 should test actions against this fixed state map while always benchmarking against preserved A7.19/A7.26.
