# SOL Full-Character Long V3 — Breakout-Level Retest Result

- Data coverage: **99.769767%**
- Qualifying impulsive H1 breakout contexts: **1028**
- Contexts reaching a first 5m retest within 24H: **878**
- Valid first-retest sweep/reclaim entries: **433**
- Character: **H1 impulse -> new high -> first retest of broken H1 swing-high -> 5m sweep/reclaim -> LONG**.
- 2020-2024 evaluation; 2025+ remained CLOSED.

## Pooled economics

| N | WR60 | Exp60 | PF | PnL | Max DD | Max LS | Clean impulse | MFE | MAE | MFE/MAE | Retest delay | Pos yrs | Verdict |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 433 | 46.53% | -0.0717% | 0.860 | $-154.77 | $252.03 | 7 | 13.19% | 0.734% | -0.680% | 1.077 | 50.0m | 1/5 | **REJECTED_AS_DEFINED** |

## Yearly economics

| Year | N | WR60 | Exp60 | PF | PnL | MFE/MAE | Retest delay |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2020 | 35 | 51.43% | -0.0047% | 0.992 | $-0.83 | 0.988 | 60.0m |
| 2021 | 118 | 50.00% | +0.1334% | 1.244 | $78.70 | 1.213 | 35.0m |
| 2022 | 77 | 44.16% | -0.2925% | 0.479 | $-112.61 | 0.989 | 95.0m |
| 2023 | 94 | 41.49% | -0.1600% | 0.695 | $-75.19 | 1.059 | 85.0m |
| 2024 | 108 | 47.22% | -0.0830% | 0.796 | $-44.83 | 1.135 | 45.0m |

## Frozen gate audit

- PASS — n_ge_100
- FAIL — expectancy_positive
- FAIL — pf_ge_1_15
- FAIL — positive_pnl_years_ge_4_of_5
- FAIL — median_mfe_mae_ge_1_20

## Interpretation

- First retest of a broken H1 swing-high is not sufficient as a SOL LONG character in this frozen definition.
- The failure is well-sampled rather than sample-limited.
- Do not rescue with second-retest logic, alternative 24H windows, extra confirmation, hours, indicators, TP or SL on 2020-2024.
- Full-Character Long V1 remains the stronger candidate observed so far.

OFFICIAL_VERDICT=REJECTED_AS_DEFINED
2025_PLUS=CLOSED

Authoritative run: 35485362958
Artifact: 10596533799
Artifact digest: sha256:da4c709efe03ebfcab17b6554de175de90738a16e0fcbdaca2363207db7569c5