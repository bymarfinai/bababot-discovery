# ETH B27DX — S10 Hybrid Profit-Lock — Result

ETH raw 5m coverage: **100.0000%**.

Frozen hybrid map: **05:00 fixed E25 · 09:00 fixed E25 · 10:00 B27DQ-style E10 profit-lock runner · 16:00 fixed E25**.

- Candidate/parity/causal audit: **PASS**.
- Runner selection is exploratory because 10:00 was identified from previously inspected S5A history.

## Portfolio comparison

| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | S4 fixed | 0 bps | 144 | 1.379 | 63.9% | 1.67 | 1.38 | 198.25 | 3 |
| external | S4 fixed | 5 bps | 144 | 1.379 | 58.3% | 1.44 | 0.99 | 143.26 | 4 |
| external | S10 hybrid | 0 bps | 144 | 1.379 | 63.9% | 1.62 | 1.24 | 178.00 | 3 |
| external | S10 hybrid | 5 bps | 144 | 1.379 | 58.3% | 1.37 | 0.82 | 117.46 | 4 |
| development | S4 fixed | 0 bps | 233 | 1.488 | 61.4% | 1.21 | 0.40 | 93.40 | 5 |
| development | S4 fixed | 5 bps | 233 | 1.488 | 59.7% | 1.02 | 0.03 | 7.52 | 5 |
| development | S10 hybrid | 0 bps | 233 | 1.488 | 63.9% | 1.38 | 0.66 | 154.09 | 5 |
| development | S10 hybrid | 5 bps | 233 | 1.488 | 60.1% | 1.12 | 0.24 | 55.31 | 5 |
| reference_validation | S4 fixed | 0 bps | 101 | 1.230 | 64.4% | 1.52 | 0.93 | 94.10 | 4 |
| reference_validation | S4 fixed | 5 bps | 101 | 1.230 | 63.4% | 1.28 | 0.56 | 56.12 | 4 |
| reference_validation | S10 hybrid | 0 bps | 101 | 1.230 | 66.3% | 1.38 | 0.64 | 64.63 | 4 |
| reference_validation | S10 hybrid | 5 bps | 101 | 1.230 | 61.4% | 1.11 | 0.21 | 20.87 | 5 |
| POOLED_MAJOR | S4 fixed | 0 bps | 478 | 1.393 | 62.8% | 1.42 | 0.81 | 385.75 | 5 |
| POOLED_MAJOR | S4 fixed | 5 bps | 478 | 1.393 | 60.0% | 1.21 | 0.43 | 206.90 | 5 |
| POOLED_MAJOR | S10 hybrid | 0 bps | 478 | 1.393 | 64.4% | 1.46 | 0.83 | 396.72 | 5 |
| POOLED_MAJOR | S10 hybrid | 5 bps | 478 | 1.393 | 59.8% | 1.20 | 0.41 | 193.65 | 5 |

## Pooled-major source-clock comparison (0 bps)

| Clock | S4 N | S4 WR | S4 PF | S4 Exp | S4 Net | S10 N | S10 WR | S10 PF | S10 Exp | S10 Net |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 05:00 | 101 | 62.4% | 1.71 | 1.00 | 101.35 | 101 | 62.4% | 1.71 | 1.00 | 101.35 |
| 09:00 | 90 | 62.2% | 1.30 | 0.67 | 60.14 | 90 | 62.2% | 1.30 | 0.67 | 60.14 |
| 10:00 | 164 | 66.5% | 1.58 | 0.98 | 161.04 | 164 | 71.3% | 1.78 | 1.05 | 172.01 |
| 16:00 | 123 | 58.5% | 1.21 | 0.51 | 63.22 | 123 | 58.5% | 1.21 | 0.51 | 63.22 |

## Runner anatomy — accepted 10:00 trades

- Accepted runner-managed 10:00 trades: **164**.
- Armed after E10 touch: **114**.
- Live floor exits: **111**.
- Scheduled floor updates: **197**; activations: **187**; ratchet updates: **83**.

## Pooled impact vs S4

- WR: **62.8% → 64.4%**.
- PF: **1.42 → 1.46**.
- Expectancy: **0.81 → 0.83**.
- Net: **385.75 → 396.72**.
- Frequency: **1.393 → 1.393 trades/week**.
- Accepted N: **478 → 478**.

## Frozen gates

- All major partitions PF>1 and net>0: **PASS**.
- Pooled 5 bps PF>1 and net>0: **PASS**.
- Accepted N >=95% S4: **PASS**.
- WR/PF/expectancy/net all improve vs S4: **PASS**.
- BTC-class diagnostic: **FAIL**.

## Decision

**Status: ETH_S10_HYBRID_PROFIT_LOCK_SUPPORTED**

- No S9A freshness cancellation, S9B scratch, alternate runner clock, arm/gap/step sweep, geometry, leverage, fee, or live-code change was made.
- Evidence remains exploratory/engineering validation because the runner habitat was selected from previously inspected history.
