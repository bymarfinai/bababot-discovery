# B27DO — 4-Zone Hybrid Exit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Fixed-E20 B27DK parity reproduced before hybrid interpretation.

**Evidence status: exploratory.** The zone-specific exit assignment was selected after inspecting prior per-zone B27DN results.

Hybrid: ALT_0330 uses fixed E20; RAW_0530, LONDON and RAW_2330 use the frozen B27DN E20-touch -> E10 breathing step-10 runner.

## Exact portfolio comparison after global one-position re-lock

| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | FIXED_E20 | 81 | 74 | 7 | 77.0% | 2.91 | $+1.89 | $+139.72 | 3 |
| external | HYBRID_0330_FIXED_OTHERS_E10 | 81 | 74 | 7 | 73.0% | 2.75 | $+1.78 | $+131.79 | 3 |
| development | FIXED_E20 | 113 | 107 | 6 | 72.0% | 1.52 | $+0.60 | $+63.83 | 3 |
| development | HYBRID_0330_FIXED_OTHERS_E10 | 113 | 106 | 7 | 67.9% | 1.83 | $+0.97 | $+102.69 | 3 |
| reference_validation | FIXED_E20 | 48 | 47 | 1 | 80.9% | 2.26 | $+0.84 | $+39.30 | 2 |
| reference_validation | HYBRID_0330_FIXED_OTHERS_E10 | 48 | 47 | 1 | 80.9% | 3.10 | $+1.39 | $+65.41 | 2 |
| august | FIXED_E20 | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| august | HYBRID_0330_FIXED_OTHERS_E10 | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| POOLED_MAJOR | FIXED_E20 | 242 | 228 | 14 | 75.4% | 2.07 | $+1.07 | $+242.84 | 3 |
| POOLED_MAJOR | HYBRID_0330_FIXED_OTHERS_E10 | 242 | 227 | 15 | 72.2% | 2.31 | $+1.32 | $+299.89 | 3 |

## Pooled-major hybrid contribution by zone

| Zone | Exit | N | WR | PF | Exp | Net |
|---|---|---:|---:|---:|---:|---:|
| ALT_0330 | FIXED_E20 | 61 | 77.0% | 2.44 | $+1.35 | $+82.44 |
| RAW_0530 | E10_BREATHING | 54 | 70.4% | 2.11 | $+1.09 | $+59.07 |
| LONDON | E10_BREATHING | 67 | 70.1% | 1.87 | $+1.14 | $+76.18 |
| RAW_2330 | E10_BREATHING | 45 | 71.1% | 3.62 | $+1.83 | $+82.20 |

## Direct scorecard

- Fixed E20: **N 228 / WR 75.4% / PF 2.07 / Exp $+1.07 / Net $+242.84**.
- Universal B27DN E10 breathing: **N 227 / WR 70.5% / PF 2.16 / Exp $+1.19 / Net $+271.07**.
- B27DO hybrid: **N 227 / WR 72.2% / PF 2.31 / Exp $+1.32 / Net $+299.89**.
- Hybrid delta vs fixed: **$+57.05**; WR delta **-3.2 pp**.
- Hybrid delta vs universal B27DN: **$+28.82**; WR delta **+1.8 pp**.

## Decision

**Status: B27DO_HYBRID_PROMISING_EXPLORATORY**

Research/operating exit experiment only; live BBC unchanged.
