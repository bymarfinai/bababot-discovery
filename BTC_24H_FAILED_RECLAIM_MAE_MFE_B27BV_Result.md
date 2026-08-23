# B27BV — BTC 24H BEAR-Origin Failed-Reclaim MAE/MFE Anatomy — Result

**Audit status: PASS.** No entry/stop/target parameter was optimized. The exact B27BU next-5m-open anchor and LOCAL_LOW risk unit are used only as frozen measurement coordinates.

Frozen signal identity reproduced exactly: **34 = external 6 + development 20 + reference_validation 8; pooled OOS 14. Outcomes: pooled major 22 TRANSITION + 12 RESUME; pooled OOS 11 + 3.**

## Pooled excursion envelope

| Pool | Outcome | N | LOCAL_LOW breached | MAE median / P75 / P90 | MFE median / P75 / P90 | MAE local-R median / P75 / P90 | MFE local-R median / P75 / P90 |
|---|---|---:|---:|---|---|---|---|
| POOLED_OOS | ALL | 14 | 71.43% | 0.59% / 1.05% / 1.88% | 0.84% / 1.32% / 2.19% | 2.07R / 4.69R / 11.46R | 3.29R / 5.97R / 8.25R |
| POOLED_OOS | TRANSITION | 11 | 63.64% | 0.57% / 0.80% / 1.02% | 0.92% / 1.40% / 2.51% | 1.91R / 2.65R / 4.65R | 3.86R / 5.46R / 6.60R |
| POOLED_OOS | RESUME | 3 | 100.00% | 1.68% / 3.25% / 4.19% | 0.47% / 0.84% / 1.06% | 13.54R / 14.15R / 14.52R | 2.07R / 5.90R / 8.20R |
| POOLED_MAJOR | ALL | 34 | 76.47% | 0.73% / 1.49% / 2.18% | 0.72% / 1.33% / 2.41% | 2.15R / 4.76R / 12.12R | 2.67R / 5.53R / 9.59R |
| POOLED_MAJOR | TRANSITION | 22 | 68.18% | 0.58% / 0.81% / 1.50% | 0.84% / 1.46% / 2.97% | 2.02R / 2.81R / 4.76R | 3.47R / 6.33R / 9.23R |
| POOLED_MAJOR | RESUME | 12 | 91.67% | 1.50% / 2.13% / 2.81% | 0.57% / 1.14% / 1.21% | 5.31R / 11.51R / 13.44R | 1.72R / 3.73R / 9.18R |

## Major partition transition anatomy

| Partition | N transition | LOCAL_LOW breached | MAE median | MAE P75 | MFE median | MFE P75 | >=1R MFE | >=1.5R | >=2R |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 5 | 60.00% | 2.02R | 2.11R | 4.45R | 6.47R | 100.00% | 100.00% | 100.00% |
| development | 11 | 72.73% | 2.20R | 2.79R | 3.40R | 7.58R | 81.82% | 63.64% | 54.55% |
| reference_validation | 6 | 66.67% | 1.46R | 2.86R | 1.75R | 3.84R | 50.00% | 50.00% | 50.00% |

## Timing and detector-exit diagnostics

| Pool | Outcome | Median min to MAE | Median min to MFE | Median detector-exit return |
|---|---|---:|---:|---:|
| POOLED_OOS | TRANSITION | 75 | 160 | 0.60% |
| POOLED_OOS | RESUME | 670 | 140 | -1.21% |
| POOLED_MAJOR | TRANSITION | 120 | 210 | 0.50% |
| POOLED_MAJOR | RESUME | 408 | 125 | -1.14% |

## Frozen interpretation gate

- Exact signal/outcome identity: **PASS**.
- Non-empty continuous post-entry observation windows: **PASS**.
- Positive frozen LOCAL_R for every signal: **PASS**.
- Transition sample >=20 pooled-major and >=10 pooled-OOS: **PASS**.
- Pooled-major TRANSITION median MFE_local_R > MAE_local_R: **PASS**.
- Pooled-OOS TRANSITION median MFE_local_R > MAE_local_R: **PASS**.
- Pooled-major TRANSITION P75 MAE_local_R > 1.0: **PASS**.
- No geometry selected or changed from this audit: **PASS**.

**Frozen verdict: `B27BV_FAILED_RECLAIM_EXCURSION_INFORMATIVE`.**

An informative result is not a trade approval. It only permits a separately preregistered geometry experiment using this frozen excursion envelope.

Research only. Live BBC unchanged.
