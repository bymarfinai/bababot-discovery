# BTC Potential B — August 2026 True-OOS Replay Result

**Parity status: PARITY_UNRESOLVED**

Official 5m coverage: **2023-12-02 00:00:00+00:00 -> 2026-08-18 23:55:00+00:00**, rows **285408**.

## Historical parity reconstruction

Known benchmark: recent base **17/24**, recent aggressive **11/15**, full aggressive **43/67**.

| Variant | Recent base | Recent aggressive | Full aggressive | Parity score |
|---|---:|---:|---:|---:|
| `H8_TRAP_BACK_BELOW` | 42/89 | 25/57 | 96/204 | 336 |
| `H7_TRAP_BACK_BELOW` | 54/98 | 33/60 | 113/233 | 414 |
| `H8_CONFIRM2` | 62/113 | 42/76 | 152/281 | 549 |
| `H7_CONFIRM2` | 73/123 | 48/80 | 177/309 | 633 |

Selected only by historical parity: **`H8_TRAP_BACK_BELOW`**. August was not used to choose the variant.

## August 2026 — Potential B 60m directional replay

| Cohort | N | Wins | WR | Avg SELL return | Median MFE | Median MAE |
|---|---:|---:|---:|---:|---:|---:|
| Base sequence | 4 | 2 | 50.00% | 0.17% | 0.32% | 0.15% |
| Aggressive >50% | 3 | 1 | 33.33% | -0.02% | 0.19% | 0.14% |

## >1% move diagnostic — same trigger, no 1m data

TP1.0% / SL1.0%, max6h, same-bar adverse-first, fee0.15%, $500 reference notional.

| Cohort | N | Wins | WR | TP | SL | TIME | PnL |
|---|---:|---:|---:|---:|---:|---:|---:|
| Base sequence | 4 | 1 | 25.00% | 1 | 3 | 0 | $-13.00 |
| Aggressive >50% | 3 | 1 | 33.33% | 1 | 2 | 0 | $-7.25 |

## August event ledger

| UTC date | Entry WIB | HOD | Taker buy | Aggressive | 60m | 60m SELL ret | 1%/6h | 6h MFE |
|---|---|---:|---:|---|---|---:|---|---:|
| 2026-08-05 | 2026-08-05 22:30 | 64500.00 | 77.0% | YES | LOSS | -0.389% | SL_1PCT | 0.187% |
| 2026-08-08 | 2026-08-08 22:45 | 65046.10 | 59.0% | YES | LOSS | -0.002% | SL_1PCT | 0.070% |
| 2026-08-11 | 2026-08-11 20:45 | 64148.00 | 63.1% | YES | WIN | 0.333% | TP_1PCT | 1.466% |
| 2026-08-12 | 2026-08-12 21:00 | 63886.00 | 48.4% | NO | WIN | 0.723% | SL_1PCT | 0.820% |

August is true post-cutoff evidence; no rule, clock, direction, taker threshold, or TP/SL is retuned from these outcomes.
