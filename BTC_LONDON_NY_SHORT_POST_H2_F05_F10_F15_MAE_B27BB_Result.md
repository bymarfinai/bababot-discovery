# B27BB — BTC London->NY SHORT Post-Retest#2 F05/F10/F15 Winner MAE / Natural Stop-Distance Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27AZ/B27BA clean windows and F05/F10/F15 fill identities reproduced before stop-independent MAE was interpreted.

Old F65 invalidation was NOT applied. B27BB selects no stop.

## Pooled-major winner MAE

| Zone | N | E20 raw | E20 rate | Pre-E20 D P50 | P75 | P90 | P95 | Max | Through-E20 D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F05 | 28 | 17 | 60.7% | 0.146 | 0.232 | 0.312 | 0.418 | 0.667 | 0.146 | 0.232 | 0.312 | 0.418 | 0.667 |
| F10 | 37 | 22 | 59.5% | 0.173 | 0.281 | 0.326 | 0.602 | 0.621 | 0.173 | 0.281 | 0.326 | 0.602 | 0.621 |
| F15 | 42 | 24 | 57.1% | 0.203 | 0.273 | 0.399 | 0.544 | 0.571 | 0.203 | 0.273 | 0.399 | 0.544 | 0.571 |

## Pooled-major non-E20 adverse distance

| Zone | Fail N | D P50 | P75 | P90 | P95 | Max |
|---|---:|---:|---:|---:|---:|---:|
| F05 | 11 | 0.505 | 0.864 | 1.099 | 1.130 | 1.160 |
| F10 | 15 | 0.529 | 0.903 | 1.010 | 1.068 | 1.110 |
| F15 | 18 | 0.442 | 0.856 | 1.017 | 1.059 | 1.060 |

## Major partitions — conservative winner D

| Zone | Partition | Winners | P50 | P75 | P90 | P95 | Max |
|---|---|---:|---:|---:|---:|---:|---:|
| F05 | external | 4 | 0.120 | 0.163 | 0.216 | 0.233 | 0.251 |
| F05 | development | 12 | 0.161 | 0.245 | 0.349 | 0.496 | 0.667 |
| F05 | reference_validation | 1 | 0.188 | 0.188 | 0.188 | 0.188 | 0.188 |
| F10 | external | 4 | 0.083 | 0.113 | 0.166 | 0.183 | 0.201 |
| F10 | development | 16 | 0.193 | 0.295 | 0.461 | 0.618 | 0.621 |
| F10 | reference_validation | 2 | 0.234 | 0.281 | 0.310 | 0.319 | 0.329 |
| F15 | external | 3 | 0.032 | 0.039 | 0.043 | 0.045 | 0.046 |
| F15 | development | 18 | 0.220 | 0.268 | 0.422 | 0.567 | 0.571 |
| F15 | reference_validation | 3 | 0.279 | 0.347 | 0.388 | 0.402 | 0.415 |

## Pooled-major descriptive winner survival

| Zone | D | Stop fraction | Winners | Pre-E20 survive | Conservative survive |
|---|---:|---:|---:|---:|---:|
| F05 | 0.10 | 0.15 | 17 | 11.8% | 11.8% |
| F05 | 0.20 | 0.25 | 17 | 64.7% | 64.7% |
| F05 | 0.30 | 0.35 | 17 | 88.2% | 88.2% |
| F05 | 0.40 | 0.45 | 17 | 94.1% | 94.1% |
| F05 | 0.50 | 0.55 | 17 | 94.1% | 94.1% |
| F05 | 0.60 | 0.65 | 17 | 94.1% | 94.1% |
| F10 | 0.10 | 0.20 | 22 | 31.8% | 31.8% |
| F10 | 0.20 | 0.30 | 22 | 54.5% | 54.5% |
| F10 | 0.30 | 0.40 | 22 | 81.8% | 81.8% |
| F10 | 0.40 | 0.50 | 22 | 90.9% | 90.9% |
| F10 | 0.50 | 0.60 | 22 | 90.9% | 90.9% |
| F10 | 0.60 | 0.70 | 22 | 90.9% | 90.9% |
| F15 | 0.10 | 0.25 | 24 | 33.3% | 33.3% |
| F15 | 0.20 | 0.35 | 24 | 50.0% | 50.0% |
| F15 | 0.30 | 0.45 | 24 | 79.2% | 79.2% |
| F15 | 0.40 | 0.55 | 24 | 87.5% | 87.5% |
| F15 | 0.50 | 0.65 | 24 | 91.7% | 91.7% |
| F15 | 0.60 | 0.75 | 24 | 100.0% | 100.0% |

Distance D is measured upward from each zone’s own entry fraction. Equality with a hypothetical stop counts as stopped.
No PnL or stop was selected. Research only; live BBC unchanged.
