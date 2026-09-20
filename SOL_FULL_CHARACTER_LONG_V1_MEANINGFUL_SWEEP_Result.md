# SOL Full-Character Long V1 — Meaningful Sweep Confirmation Result

- Data coverage: **99.769767%**
- Base V1 sweep/reclaim trades reproduced: **109**
- Exact rule: sweep depth >= **0.25x** demand-zone width AND reclaim lower wick >= **0.50** of candle range.
- Selected trades: **27** (24.77% retention).
- 2020-2024 is development confirmation because the rule was motivated by prior characterization.
- 2025+ remained CLOSED.

## Pooled economics

| Group | N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE/MAE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Base V1 | 109 | 53.21% | +0.1361% | 1.308 | $74.18 | $66.87 | 8 | 12.84% | 1.333 |
| Meaningful sweep | 27 | 62.96% | +0.0775% | 1.153 | $10.46 | $25.68 | 3 | 11.11% | 2.684 |
| Complement | 82 | 50.00% | +0.1554% | 1.369 | $63.72 | $79.93 | 9 | 13.41% | 1.242 |

## Selected yearly economics

| Year | N | WR60 | Exp60 | PF | PnL | MFE/MAE |
|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 0 | n/a | n/a | n/a | $0.00 | n/a |
| 2021 | 9 | 66.67% | -0.1543% | 0.754 | $-6.94 | 2.684 |
| 2022 | 3 | 66.67% | +0.3595% | 2.750 | $5.39 | 0.551 |
| 2023 | 5 | 100.00% | +0.9008% | inf | $22.52 | 4.663 |
| 2024 | 10 | 40.00% | -0.2102% | 0.716 | $-10.51 | 0.545 |

## Frozen gate audit

- FAIL — n_ge_100
- PASS — expectancy_positive
- PASS — pf_ge_1_15
- FAIL — positive_pnl_years_ge_4_of_5
- PASS — median_mfe_mae_ge_1_20

## Interpretation

- The exact preregistered meaningful-sweep rule improves WR and median MFE/MAE but does **not** improve pooled expectancy or PF versus the frozen V1 base.
- The complementary 82 trades retain higher expectancy and PF than the selected 27.
- The 2022 failure is not resolved into stable cross-year behavior; the selected rule instead becomes negative in 2021 and 2024.
- Therefore the characterization association should not be converted into a threshold rescue.
- Do not test nearby 0.20/0.30 sweep-depth or 0.40/0.60 wick thresholds on the same 2020-2024 sample.

OFFICIAL_VERDICT=REJECTED_AS_DEFINED
VALIDATION_STATUS=DEVELOPMENT_CONFIRMATION_ONLY
2025_PLUS=CLOSED

Authoritative run: 35484351893
Artifact: 10596622619
Artifact digest: sha256:18918453431334e41ed8b0ac223a8a1203ff27e7786f84c0e56f67b30cd9288b