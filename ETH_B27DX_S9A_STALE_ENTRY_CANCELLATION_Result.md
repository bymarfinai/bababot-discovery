# ETH B27DX — S9A Stale Entry Cancellation — Result

ETH raw 5m coverage: **100.0000%**.

Frozen rule: **F75 fill must occur on the first eligible raw 5m bar after completed leave; later fills are cancelled.**

- Candidate-detail parity: **PASS**.
- Eligible-bar causal audit: **PASS**.
- Raw candidates: **575**; immediate **259**; stale **316**.

## Original S4 accepted-trade freshness anatomy

| Freshness | N | Losses | Loss rate | WR | PF | Exp | Net |
|---|---:|---:|---:|---:|---:|---:|---:|
| Immediate | 218 | 66 | 30.3% | 69.7% | 1.82 | 1.24 | 271.40 |
| Stale | 260 | 112 | 43.1% | 56.9% | 1.20 | 0.44 | 114.35 |

## Re-locked portfolio comparison

| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | S4 | 0 bps | 144 | 1.379 | 63.9% | 1.67 | 1.38 | 198.25 | 3 |
| external | S4 | 5 bps | 144 | 1.379 | 58.3% | 1.44 | 0.99 | 143.26 | 4 |
| external | First-only | 0 bps | 73 | 0.699 | 68.5% | 1.90 | 1.61 | 117.62 | 2 |
| external | First-only | 5 bps | 73 | 0.699 | 61.6% | 1.63 | 1.25 | 91.12 | 2 |
| development | S4 | 0 bps | 233 | 1.488 | 61.4% | 1.21 | 0.40 | 93.40 | 5 |
| development | S4 | 5 bps | 233 | 1.488 | 59.7% | 1.02 | 0.03 | 7.52 | 5 |
| development | First-only | 0 bps | 107 | 0.683 | 67.3% | 1.43 | 0.69 | 73.72 | 4 |
| development | First-only | 5 bps | 107 | 0.683 | 65.4% | 1.19 | 0.34 | 36.50 | 4 |
| reference_validation | S4 | 0 bps | 101 | 1.230 | 64.4% | 1.52 | 0.93 | 94.10 | 4 |
| reference_validation | S4 | 5 bps | 101 | 1.230 | 63.4% | 1.28 | 0.56 | 56.12 | 4 |
| reference_validation | First-only | 0 bps | 42 | 0.511 | 76.2% | 2.61 | 1.67 | 70.16 | 3 |
| reference_validation | First-only | 5 bps | 42 | 0.511 | 73.8% | 2.13 | 1.32 | 55.38 | 3 |
| POOLED_MAJOR | S4 | 0 bps | 478 | 1.393 | 62.8% | 1.42 | 0.81 | 385.75 | 5 |
| POOLED_MAJOR | S4 | 5 bps | 478 | 1.393 | 60.0% | 1.21 | 0.43 | 206.90 | 5 |
| POOLED_MAJOR | First-only | 0 bps | 222 | 0.647 | 69.4% | 1.75 | 1.18 | 261.50 | 4 |
| POOLED_MAJOR | First-only | 5 bps | 222 | 0.647 | 65.8% | 1.48 | 0.82 | 183.00 | 4 |

## Portfolio impact

- Accepted-trade retention vs S4: **46.4%**.
- Baseline accepted removed by freshness rule/re-lock: **260**.
- Newly freed accepted trades after re-lock: **4**.
- Pooled 0 bps WR change: **62.8% → 69.4%**.
- Pooled 0 bps PF change: **1.42 → 1.75**.
- Pooled 0 bps expectancy change: **0.81 → 1.18**.
- Pooled frequency: **1.393 → 0.647 trades/week**.

## Frozen gates

- All three major partitions positive at 0 bps: **PASS**.
- 5 bps pooled stress positive: **PASS**.
- Retention >= 50%: **FAIL**.
- WR + PF + expectancy all improve vs S4: **PASS**.
- BTC-class diagnostic (WR/PF/expectancy): **FAIL**.

## Decision

**Status: ETH_S9A_STALE_ENTRY_CANCELLATION_NOT_SUPPORTED**

- No alternate freshness cutoff, geometry, runner, leverage, fee, or live-code change was made.
