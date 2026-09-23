# BNB B41-S4 — Frozen Direction Detector Validation

**Status: BNB_B41_S4_DIRECTION_MAP_NOT_READY**

S4 signature: `c6eb2c0ade6c4f11c3d9d6512ec06473d5d22c3e2d6c8a75a16a640782d960dc`

All price movement below is measured from the detector close, after the 15m character is fully known.

## Frozen directional classes

| Period | Wall side | Character | Direction | N | N180 | 60m | Hit60 | 180m | Hit180 | MFE | MAE | Fav dominance | Session close |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | UPPER | C1_CLEAN_REJECTION | SHORT | 88 | 79 | 0.015x | 53.0% | 0.094x | 58.2% | 0.487x | 0.392x | 58.0% | 0.037x |
| DEV | UPPER | C3_ACCEPTANCE_HOLD | LONG | 84 | 81 | 0.072x | 59.0% | -0.005x | 48.1% | 0.595x | 0.415x | 53.6% | 0.076x |
| DEV | LOWER | C1_CLEAN_REJECTION | LONG | 89 | 81 | 0.030x | 56.3% | 0.028x | 54.3% | 0.382x | 0.349x | 52.8% | 0.080x |
| DEV | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | 49 | 42 | 0.037x | 56.2% | 0.152x | 66.7% | 0.447x | 0.433x | 44.9% | 0.144x |
| REF | UPPER | C1_CLEAN_REJECTION | SHORT | 33 | 32 | 0.014x | 57.6% | 0.150x | 78.1% | 0.541x | 0.265x | 63.6% | 0.140x |
| REF | UPPER | C3_ACCEPTANCE_HOLD | LONG | 49 | 43 | 0.013x | 52.2% | -0.079x | 39.5% | 0.452x | 0.567x | 49.0% | 0.015x |
| REF | LOWER | C1_CLEAN_REJECTION | LONG | 36 | 32 | 0.037x | 60.6% | 0.011x | 50.0% | 0.592x | 0.394x | 47.2% | 0.044x |
| REF | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | 27 | 27 | 0.048x | 55.6% | 0.114x | 63.0% | 0.596x | 0.401x | 59.3% | 0.391x |
| ALL | UPPER | C1_CLEAN_REJECTION | SHORT | 121 | 111 | 0.014x | 54.3% | 0.099x | 64.0% | 0.521x | 0.380x | 59.5% | 0.075x |
| ALL | UPPER | C3_ACCEPTANCE_HOLD | LONG | 133 | 124 | 0.035x | 56.6% | -0.058x | 45.2% | 0.547x | 0.445x | 51.9% | 0.059x |
| ALL | LOWER | C1_CLEAN_REJECTION | LONG | 125 | 113 | 0.033x | 57.5% | 0.028x | 53.1% | 0.457x | 0.389x | 51.2% | 0.080x |
| ALL | LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | 76 | 69 | 0.048x | 56.0% | 0.150x | 65.2% | 0.468x | 0.431x | 50.0% | 0.179x |

## Preregistered class support

| Side | Character | Dir | DEV N180 | REF N180 | DEV 180m | REF 180m | DEV hit | REF hit | DEV fav-dom | REF fav-dom | Supported |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| UPPER | C1_CLEAN_REJECTION | SHORT | 79 | 32 | 0.094x | 0.150x | 58.2% | 78.1% | 58.0% | 63.6% | YES |
| UPPER | C3_ACCEPTANCE_HOLD | LONG | 81 | 43 | -0.005x | -0.079x | 48.1% | 39.5% | 53.6% | 49.0% | NO |
| LOWER | C1_CLEAN_REJECTION | LONG | 81 | 32 | 0.028x | 0.011x | 54.3% | 50.0% | 52.8% | 47.2% | NO |
| LOWER | C2_RECLAIM_AFTER_CLOSE | LONG | 42 | 27 | 0.152x | 0.114x | 66.7% | 63.0% | 44.9% | 59.3% | NO |

## Pooled detector

| Period | Eligible chars | Signals | Coverage | LONG | SHORT | N180 | 180m | Hit180 | MFE | MAE | Fav dominance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| DEV | 470 | 310 | 66.0% | 222 | 88 | 283 | 0.040x | 55.5% | 0.455x | 0.406x | 53.2% |
| REF | 238 | 145 | 60.9% | 112 | 33 | 134 | 0.052x | 56.0% | 0.548x | 0.411x | 53.8% |
| ALL | 708 | 455 | 64.3% | 334 | 121 | 417 | 0.044x | 55.6% | 0.481x | 0.411x | 53.4% |

## Annual pooled direction

| Year | Signals | N180 | 180m | Hit180 | Fav dominance |
|---|---:|---:|---:|---:|---:|
| 2022 | 101 | 89 | 0.056x | 55.1% | 53.5% |
| 2023 | 108 | 101 | 0.093x | 59.4% | 50.9% |
| 2024 | 101 | 93 | 0.005x | 51.6% | 55.4% |
| 2025 | 92 | 83 | 0.114x | 57.8% | 55.4% |
| 2026 | 53 | 51 | 0.010x | 52.9% | 50.9% |

## Gate
- All four directional classes supported: **NO**.
- Pooled DEV/REF support: **YES**.
- Positive annual median 180m: **5/5** years.
- Final S4 gate: **NOT READY — do not proceed to entry optimization**.

S4 remains direction-only; no entry, SL, TP, WR, PF, expectancy, or PnL was optimized.
