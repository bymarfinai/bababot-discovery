# B27BS — BTC 24H Age-2 Close-Break 5m Acceptance Anatomy — Result

**Audit status: PASS.** Structural microstructure only; no trading/economic rule or live change was used.

Frozen cohort identity reproduced exactly: **BULL 95 (OOS 66); BEAR 56 (OOS 33)** age-2 cumulative close-break episodes.

## Primary OOS readout

| Origin | Cohort N | NO_RECLAIM N | P(T | NO_RECLAIM) | RECLAIM N | P(T | RECLAIM) | Lift |
|---|---:|---:|---:|---:|---:|---:|
| BULL | 66 | 37 | 56.8% | 29 | 75.9% | -19.1pp |
| BEAR | 33 | 19 | 68.4% | 14 | 78.6% | -10.2pp |

## OOS partition stability

| Partition | Origin | NO_RECLAIM N | P(T|NR) | RECLAIM N | P(T|R) | Lift |
|---|---|---:|---:|---:|---:|---:|
| external | BULL | 26 | 50.0% | 14 | 71.4% | -21.4pp |
| external | BEAR | 12 | 58.3% | 7 | 85.7% | -27.4pp |
| reference_validation | BULL | 11 | 72.7% | 15 | 80.0% | -7.3pp |
| reference_validation | BEAR | 7 | 85.7% | 7 | 71.4% | +14.3pp |

## 5m anatomy by eventual outcome — pooled OOS

| Origin | Outcome | N | First break pos median [P25,P75] | Acceptance share median [P25,P75] | Final streak median [P25,P75] |
|---|---|---:|---|---|---|
| BULL | RESUME | 23 | 19.0 [7.5,33.5] | 100.0% [94.2%,100.0%] | 21.0 [10.5,39.0] |
| BULL | TRANSITION | 43 | 22.0 [13.5,34.0] | 97.8% [79.3%,100.0%] | 12.0 [6.0,29.0] |
| BEAR | RESUME | 9 | 9.0 [7.0,29.0] | 100.0% [87.2%,100.0%] | 20.0 [10.0,40.0] |
| BEAR | TRANSITION | 24 | 14.5 [5.5,27.2] | 100.0% [81.2%,100.0%] | 21.5 [7.0,36.2] |

## Frozen support gate

- Exact raw/detector/parent/cohort identity: **PASS**.
- Every decisive 4H bar = 48 continuous 5m bars with a 5m close-break: **PASS**.
- Pooled-OOS NO_RECLAIM and RECLAIM N >=10/origin: **PASS**.
- Pooled-OOS P(T|NO_RECLAIM) > P(T|RECLAIM), both origins: **FAIL**.
- Pooled-OOS transition lift >=10pp, both origins: **FAIL**.
- Positive sign external + validation with >=3/cell, both origins: **FAIL**.
- Causal intrabar-only features / no live change: **PASS**.

**Frozen verdict: `B27BS_5M_CLOSE_BREAK_ACCEPTANCE_NOT_SUPPORTED`.**

A supported result validates only intrabar acceptance/reclaim information after the age-2 close-break. It does not authorize a trade.

Research only. Live BBC unchanged.
