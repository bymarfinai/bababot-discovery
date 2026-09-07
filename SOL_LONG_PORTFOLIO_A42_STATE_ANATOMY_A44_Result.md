# SOL LONG A42 Portfolio-State Anatomy — A44 Result

A44 is forensic only. Frozen A42 `G_MAE145` and A24/A25 portfolio architecture are unchanged.

A42 recovery rows: **28**. A43-key reconciliation: **True**. 15UTC parent reconciliation: **True**.

## Recovery sample

| Partition | N | Stress WR |
|---|---:|---:|
| development | 12 | 83.3% |
| external | 9 | 77.8% |
| reference_validation | 7 | 57.1% |

## A43 week-flip diagnosis

Raw positive→non-positive weeks: **3**; raw non-positive→positive weeks: **1**.
5bps positive→non-positive weeks: **1**; 5bps non-positive→positive weeks: **2**.

| Partition | Week | N rec | Base raw | +A42 raw | Raw flip | Base 5bps | +A42 5bps | 5bps flip |
|---|---|---:|---:|---:|---|---:|---:|---|
| development | 2022-02-15 | 1 | $1.68 | $5.62 | POS_STAYS_POS | $-1.32 | $2.37 | NONPOS_TO_POS |
| development | 2024-05-28 | 1 | $-1.91 | $1.06 | NONPOS_TO_POS | $-5.16 | $-2.44 | NONPOS_STAYS_NONPOS |
| external | 2021-05-18 | 1 | $1.83 | $-16.67 | POS_TO_NONPOS | $-0.92 | $-19.67 | NONPOS_STAYS_NONPOS |
| external | 2021-06-15 | 1 | $3.70 | $-1.92 | POS_TO_NONPOS | $1.20 | $-4.67 | POS_TO_NONPOS |
| reference_validation | 2025-09-23 | 1 | $2.53 | $6.27 | POS_STAYS_POS | $-0.72 | $2.77 | NONPOS_TO_POS |
| reference_validation | 2026-07-14 | 1 | $0.13 | $-1.60 | POS_TO_NONPOS | $-4.12 | $-6.10 | NONPOS_STAYS_NONPOS |

## Replicated causal portfolio-state separators

Only pre-entry causal features are eligible here. Full final-day/week diagnostics above are outcomes only.

| Feature | Dev WIN med | Dev FAIL med | Dev gap | Effect | External gap | RefVal gap |
|---|---:|---:|---:|---:|---:|---:|
| none | - | - | - | - | - | - |

## Decision

**Status: SOL_LONG_PORTFOLIO_A42_STATE_ANATOMY_A44_INCONCLUSIVE**

No causal portfolio-state feature met the preregistered replication rule. Do not invent a week/calendar filter from the A43 failure.

Research only. Live Baba Bot remains unchanged.
