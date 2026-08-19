# BTC AOH1 — Asia Open HIGH Failed-Acceptance Confirmation Result

Frozen sequence: previous-day HIGH sweep/reclaim during first 90m Asia Open -> immediate next 15m bearish close below reclaim low -> SHORT next 15m open -> SL reclaim high -> TP sized for **net RR 1:1 after 0.15% fee**.

Coverage: **2021-12-01 00:00:00+00:00 -> 2026-08-18 23:55:00+00:00**, 5m rows **495,936**, 15m complete rows **165,312**.

## Partition results

| Partition | Reclaim candidates | Confirmed trades | Confirm rate | TP | SL | TIME | Decisive WR | Net+ rate | PnL | Median risk | Avg raw TP distance |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| External 2022-2023 | 45 | 14 | 31.11% | 5 | 9 | 0 | 35.71% | 35.71% | $-27.33 | 0.83% | 1.35% |
| Reference 2023-2026 | 68 | 25 | 36.76% | 5 | 20 | 0 | 20.00% | 20.00% | $-44.27 | 0.55% | 0.88% |
| August 2026 | 0 | 0 | - | 0 | 0 | 0 | - | - | $0.00 | - | - |

## External 2022-2023 chronological blocks

| Block | N | TP | SL | TIME | Decisive WR | PnL | Median risk |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 | 3 | 2 | 1 | 0 | 66.67% | $8.34 | 1.33% |
| B2 | 4 | 2 | 2 | 0 | 50.00% | $-15.06 | 0.96% |
| B3 | 3 | 0 | 3 | 0 | 0.00% | $-10.52 | 0.56% |
| B4 | 4 | 1 | 3 | 0 | 25.00% | $-10.10 | 0.96% |

## Directional diagnostics

| Partition | Avg 60m SHORT ret | Avg 120m | Avg 240m |
|---|---:|---:|---:|
| External 2022-2023 | 0.23% | 0.35% | 0.42% |
| Reference 2023-2026 | -0.12% | -0.23% | -0.20% |
| August 2026 | - | - | - |

## August event ledger

| Date | Entry WIB | PDH | Reclaim high | Risk | Raw TP dist | Outcome | Net ret | PnL | 60m | 240m |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| - | - | - | - | - | - | - | - | - | - | - |

**AOH1_EXTERNAL_SUPPORT: FAIL**
**AOH1_80_CANDIDATE: FAIL**

Acceptance is determined by the external 2022-2023 partition, not the reference sample. No post-result retuning is allowed.
