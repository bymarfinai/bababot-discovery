# BNB B29-B2E — Frozen Character Economic Anatomy Result

**Status: BNB_B29_B2E_ECONOMIC_GEOMETRY_WEAK**

B2E measures post-entry path geometry for the exact frozen B1J character + E0 event-close universe. It does not select TP/SL and does not authorize trading.

## Frozen universe / integrity
- Frozen events: **451** (2022 97, 2023 82, 2024 114, 2025 93, 2026 65).
- Primary +60m raw-path coverage: **100.00%**.
- Max raw-vs-immutable endpoint difference: **0.0000000000**.
- Endpoint anchor mismatches >5e-6: **0**.
- Integrity gate: **PASS**.

## Horizon anatomy
| Horizon | N | Terminal hit | Median terminal | Median MFE | Median adverse | P(MFE>adverse) | Med t-MFE | Med t-MAE |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| +15m | 451 | 54.10% | 0.03% | 0.17% | 0.15% | 51.66% | 10m | 5m |
| +30m | 451 | 57.87% | 0.05% | 0.22% | 0.20% | 51.22% | 20m | 10m |
| +60m | 451 | 59.20% | 0.08% | 0.33% | 0.30% | 54.77% | 35m | 20m |
| +120m | 451 | 57.87% | 0.09% | 0.45% | 0.41% | 54.77% | 60m | 40m |
| +360m | 451 | 57.21% | 0.12% | 0.78% | 0.74% | 49.45% | 195m | 115m |

## +60m symmetric first-touch anatomy
| Threshold | Unamb N | Positive first | Wilson LCB | Recent 2025+26 | Era pass | Frozen gate |
|---:|---:|---:|---:|---:|---:|---:|
| 0.25% | 381 | 52.49% | 47.48% | 56.59% | 3/5 | FAIL |
| 0.50% | 267 | 46.82% | 40.92% | 45.12% | 1/5 | FAIL |
| 0.75% | 151 | 45.70% | 37.96% | 46.34% | 1/5 | FAIL |
| 1.00% | 95 | 43.16% | 33.66% | 50.00% | 0/5 | FAIL |

## Frozen geometry gates
- Primary valid N >=400: **PASS** (451).
- Median MFE60 > median adverse60: **PASS** (0.33% vs 0.30%).
- Adjacent-threshold plateau: **FAIL** (none).
- Pooled +60m directional sanity >=57%: **PASS** (59.20%).

## Endpoint WIN vs LOSS diagnostic
- LOSS: N=184; median MFE60=0.14%; median adverse60=0.61%; median t-MFE=10m; median t-MAE=50m.
- WIN: N=267; median MFE60=0.50%; median adverse60=0.16%; median t-MFE=50m; median t-MAE=10m.

## Decision
**BNB_B29_B2E_ECONOMIC_GEOMETRY_WEAK**

A PROMISING verdict only permits a separately preregistered B3 TP/SL discovery. B2S prospective shadow remains a separate unchanged checkpoint. No live orders are authorized.
