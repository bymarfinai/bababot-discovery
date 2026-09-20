# SOL Score-3 Profit-Path Anatomy V1 — Result

- 5m coverage: **99.769767%**
- Scope: anatomy score 3 only.
- Entry and RECLAIM_EXTREME SL frozen.
- No TP active.
- 2025 is retrospective consistency only; 2026+ CLOSED.

## Core positive-event anatomy

- 2020-2024 positive N: **113**
- 2020-2024 median MFE: **0.979R**
- 2020-2024 median terminal R: **0.751R**
- 2020-2024 median giveback: **0.183R**
- 2020-2024 reached +0.50R: **74.34%**
- 2020-2024 median time-to-MFE: **110.0 min**
- 2025 positive N: **28**
- 2025 median MFE: **0.810R**
- 2025 median terminal R: **0.596R**
- 2025 median giveback: **0.214R**

## Positive profit-path cohorts

| Phase | Cohort | N | Share | Median MFE | Median terminal | Median giveback |
|---|---|---:|---:|---:|---:|---:|
| DISCOVERY_2020_2024 | LARGE_GIVEBACK | 15 | 13.27% | 1.874 | 0.790 | 0.807 |
| DISCOVERY_2020_2024 | MODERATE_GIVEBACK | 20 | 17.70% | 1.183 | 0.898 | 0.325 |
| DISCOVERY_2020_2024 | NEVER_REACHED_050R | 29 | 25.66% | 0.265 | 0.100 | 0.156 |
| DISCOVERY_2020_2024 | RETAINED | 49 | 43.36% | 1.077 | 0.957 | 0.109 |
| RETROSPECTIVE_2025 | LARGE_GIVEBACK | 4 | 14.29% | 1.835 | 1.025 | 0.764 |
| RETROSPECTIVE_2025 | MODERATE_GIVEBACK | 4 | 14.29% | 0.996 | 0.699 | 0.395 |
| RETROSPECTIVE_2025 | NEVER_REACHED_050R | 10 | 35.71% | 0.263 | 0.098 | 0.204 |
| RETROSPECTIVE_2025 | RETAINED | 10 | 35.71% | 1.117 | 0.973 | 0.107 |

## Causal giveback signature audit

| Phase | Signature | Eligible +0.5R | Trigger N | Trigger rate | Median exit-at-trigger R | Median final R | Median saved R | Recovery rate | Status |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| DISCOVERY_2020_2024 | ABS_DD_025R | 84 | 62 | 73.81% | 0.381 | 0.964 | -0.550 | 72.58% | NO |
| DISCOVERY_2020_2024 | ABS_DD_050R | 84 | 38 | 45.24% | 0.269 | 1.040 | -0.762 | 78.95% | NO |
| DISCOVERY_2020_2024 | FRAC_DD_25PCT | 84 | 65 | 77.38% | 0.390 | 0.942 | -0.509 | 76.92% | NO |
| DISCOVERY_2020_2024 | FRAC_DD_50PCT | 84 | 47 | 55.95% | 0.260 | 0.962 | -0.750 | 76.60% | NO |
| DISCOVERY_2020_2024 | TWO_OPPOSITE_CLOSES | 84 | 53 | 63.10% | 0.348 | 0.967 | -0.553 | 79.25% | NO |
| DISCOVERY_2020_2024 | MICRO_BREAK_3BAR | 84 | 45 | 53.57% | 0.306 | 0.967 | -0.600 | 73.33% | NO |
| RETROSPECTIVE_2025 | ABS_DD_025R | 18 | 16 | 88.89% | 0.490 | 0.899 | -0.377 | 56.25% | NO |
| RETROSPECTIVE_2025 | ABS_DD_050R | 18 | 11 | 61.11% | 0.491 | 1.016 | -0.783 | 63.64% | NO |
| RETROSPECTIVE_2025 | FRAC_DD_25PCT | 18 | 16 | 88.89% | 0.477 | 0.899 | -0.428 | 75.00% | NO |
| RETROSPECTIVE_2025 | FRAC_DD_50PCT | 18 | 12 | 66.67% | 0.316 | 0.899 | -0.628 | 58.33% | NO |
| RETROSPECTIVE_2025 | TWO_OPPOSITE_CLOSES | 18 | 15 | 83.33% | 0.491 | 0.930 | -0.457 | 53.33% | NO |
| RETROSPECTIVE_2025 | MICRO_BREAK_3BAR | 18 | 11 | 61.11% | 0.324 | 1.016 | -0.650 | 63.64% | NO |

## Candidate status

- No development signature passed all preregistered candidate gates.

**VERDICT: NO_PROFIT_GIVEBACK_SIGNATURE_CANDIDATE**

This is anatomy discovery only. No TP or adaptive exit has been validated.

2026_PLUS=CLOSED
