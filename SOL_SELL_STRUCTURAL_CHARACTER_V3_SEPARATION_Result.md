# SOL SELL Structural Character V3 — Winner/Failure Separation Result

- Data coverage: **99.769767%**
- Rule selection: **2020-2022 only**.
- Frozen confirmation: **2023-2024 only**.
- 2025+ remained CLOSED.
- No entry, TP, SL, hour, indicator, or regime filter was used.

## Selected structural rule

**bos_extension_range_units <= 0.204433550854 AND bos_to_return_min <= 886.25**

## Derivation

- Baseline: N=174, continuation=33.91%
- Selected: N=36, continuation=69.44%
- Lift: **35.54 pp**
- Wilson 95% lower bound: **53.14%**

## Frozen confirmation

- Baseline: N=161, continuation=31.68%
- Selected: N=38, continuation=39.47%
- Lift: **7.80 pp**

| Year | Baseline N | Baseline continuation | Selected N | Selected continuation | Lift |
|---:|---:|---:|---:|---:|---:|
| 2023 | 72 | 33.33% | 15 | 40.00% | 6.67 pp |
| 2024 | 89 | 30.34% | 23 | 39.13% | 8.79 pp |

## Frozen gate audit

- PASS — confirmation_n_ge_30
- FAIL — confirmation_rate_ge_45pct
- FAIL — confirmation_lift_ge_8pp
- PASS — year_2023_above_baseline
- PASS — year_2024_above_baseline

**VERDICT: REJECTED_AS_DEFINED**

## Interpretation

This rule describes a structural subtype inside the broader bearish family. It is not an entry rule and it does not specify stop-loss or take-profit placement.
If promoted, the next phase may study adaptive activation/entry only inside this frozen structural cohort. SL and TP remain separate later phases.

2025_PLUS=CLOSED
