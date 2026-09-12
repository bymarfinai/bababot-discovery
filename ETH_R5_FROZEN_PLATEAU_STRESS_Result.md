# ETH R5 — Frozen Plateau Stress Audit

**NO RESELECTION. H04 R4 PLATEAU FROZEN. 2026 CLOSED.**

Frozen character: **H04 DRIVE_DOWN__STR_B80_100**; cells: **5**.
Raw 5m coverage: **100.0000%**; R5 data hard-capped before **2026-01-01 UTC**.
R4 2025 baseline reproduction: **FAIL** (26/35 checks).
Primary stress: **1.5x fee + 5m execution delay**.
Primary annual plateau survival: **1/4 years**; 2025 survival: **NO**.
Primary-stress 2025 jackknife survival: **0/5 omissions**.
Verdict: **R5_FROZEN_PLATEAU_STRESS_FAIL**.

## Primary stress by year

| Year | Viable cells | Median WR | Median Exp | Median PF | Max cell DD | Plateau |
|---:|---:|---:|---:|---:|---:|:---:|
| 2022 | 0/5 | 50.00% | $+0.13 | 1.026 | $378.86 | FAIL |
| 2023 | 3/5 | 53.33% | $+0.42 | 1.246 | $105.30 | PASS |
| 2024 | 0/5 | 55.08% | $+0.38 | 1.140 | $241.47 | FAIL |
| 2025 | 0/5 | 55.67% | $+0.27 | 1.081 | $236.15 | FAIL |

## 2025 frozen cells — baseline vs primary stress

| Cell | Base Exp/PF | Base viable | Primary Exp/PF | Primary viable |
|---|---|:---:|---|:---:|
| LB120/H240 | $+0.10 / 1.031 | N | $-0.59 / 0.848 | N |
| LB180/H240 | $+1.23 / 1.450 | N | $+0.27 / 1.081 | N |
| LB240/H240 | $+0.27 / 1.087 | N | $-0.23 / 0.933 | N |
| LB180/H360 | $+2.15 / 1.621 | N | $+1.51 / 1.409 | N |
| LB240/H360 | $+1.32 / 1.387 | N | $+0.99 / 1.272 | N |

## Full implementation-stress grid — component view

| Fee | Delay | Years survived | 2025 viable | 2025 med Exp | 2025 med PF | 2025 plateau |
|---:|---:|---:|---:|---:|---:|:---:|
| 1.0x | 0m | 1/4 | 0/5 | $+1.23 | 1.387 | FAIL |
| 1.0x | 5m | 1/4 | 0/5 | $+0.65 | 1.202 | FAIL |
| 1.0x | 10m | 1/4 | 0/5 | $+0.57 | 1.174 | FAIL |
| 1.0x | 15m | 1/4 | 0/5 | $+0.52 | 1.156 | FAIL |
| 1.5x | 0m | 1/4 | 0/5 | $+0.86 | 1.267 | FAIL |
| 1.5x | 5m | 1/4 | 0/5 | $+0.27 | 1.081 | FAIL |
| 1.5x | 10m | 1/4 | 0/5 | $+0.19 | 1.056 | FAIL |
| 1.5x | 15m | 1/4 | 0/5 | $+0.15 | 1.042 | FAIL |
| 2.0x | 0m | 0/4 | 0/5 | $+0.48 | 1.155 | FAIL |
| 2.0x | 5m | 0/4 | 0/5 | $-0.10 | 0.971 | FAIL |
| 2.0x | 10m | 0/4 | 0/5 | $-0.18 | 0.948 | FAIL |
| 2.0x | 15m | 0/4 | 0/5 | $-0.23 | 0.937 | FAIL |

## 2025 primary-stress leave-one-cell-out jackknife

| Omitted | Remaining viable | Median Exp | Median PF | Survives |
|---|---:|---:|---:|:---:|
| LB120/H240 | 0/4 | $+0.63 | 1.176 | NO |
| LB180/H240 | 0/4 | $+0.38 | 1.102 | NO |
| LB180/H360 | 0/4 | $+0.02 | 1.007 | NO |
| LB240/H240 | 0/4 | $+0.63 | 1.176 | NO |
| LB240/H360 | 0/4 | $+0.02 | 1.007 | NO |

Interpretation is plateau-level only. No coordinate is promoted or replaced from these results.
Execution delay preserves the frozen signal classification and hold duration; only execution prices shift.
Loss streak is reported in the cell CSV as a diagnostic and is not a hard R5 gate.
2026 is not used anywhere in this experiment.
