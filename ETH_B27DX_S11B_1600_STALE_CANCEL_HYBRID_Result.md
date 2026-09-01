# ETH B27DX — S11B 16:00 Stale-Cancel Hybrid — Result

ETH raw 5m coverage: **100.0000%**.

Frozen map: **05:00 fixed E25 · 09:00 fixed E25 · 10:00 S10 E10 profit-lock runner · 16:00 fixed E25 with immediate-fill-only entry**.

- S10 candidate/parity/causal audit: **PASS**.
- Freshness causal audit: **PASS**.

## Portfolio comparison

| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | S10 | 0 bps | 144 | 1.379 | 63.9% | 1.62 | 1.24 | 178.00 | 3 |
| external | S10 | 5 bps | 144 | 1.379 | 58.3% | 1.37 | 0.82 | 117.46 | 4 |
| external | S11B | 0 bps | 119 | 1.140 | 66.4% | 1.63 | 1.27 | 151.72 | 2 |
| external | S11B | 5 bps | 119 | 1.140 | 61.3% | 1.39 | 0.86 | 102.18 | 3 |
| development | S10 | 0 bps | 233 | 1.488 | 63.9% | 1.38 | 0.66 | 154.09 | 5 |
| development | S10 | 5 bps | 233 | 1.488 | 60.1% | 1.12 | 0.24 | 55.31 | 5 |
| development | S11B | 0 bps | 205 | 1.309 | 65.4% | 1.51 | 0.80 | 163.90 | 5 |
| development | S11B | 5 bps | 205 | 1.309 | 61.0% | 1.21 | 0.37 | 76.08 | 5 |
| reference_validation | S10 | 0 bps | 101 | 1.230 | 66.3% | 1.38 | 0.64 | 64.63 | 4 |
| reference_validation | S10 | 5 bps | 101 | 1.230 | 61.4% | 1.11 | 0.21 | 20.87 | 5 |
| reference_validation | S11B | 0 bps | 86 | 1.047 | 70.9% | 1.68 | 0.94 | 80.91 | 3 |
| reference_validation | S11B | 5 bps | 86 | 1.047 | 65.1% | 1.33 | 0.51 | 43.87 | 4 |
| POOLED_MAJOR | S10 | 0 bps | 478 | 1.393 | 64.4% | 1.46 | 0.83 | 396.72 | 5 |
| POOLED_MAJOR | S10 | 5 bps | 478 | 1.393 | 59.8% | 1.20 | 0.41 | 193.65 | 5 |
| POOLED_MAJOR | S11B | 0 bps | 410 | 1.195 | 66.8% | 1.58 | 0.97 | 396.52 | 5 |
| POOLED_MAJOR | S11B | 5 bps | 410 | 1.195 | 62.0% | 1.29 | 0.54 | 222.13 | 5 |

## Portfolio impact

- Accepted retention vs S10: **85.8%**.
- Baseline accepted removed after 16:00 freshness rule/re-lock: **68**.
- Newly freed accepted trades after re-lock: **0**.
- WR: **64.4% → 66.8%**.
- PF: **1.46 → 1.58**.
- Expectancy: **0.83 → 0.97**.
- Net: **396.72 → 396.52**.
- Frequency: **1.393 → 1.195 trades/week**.

## Frozen gates

- Audit pass: **PASS**.
- All major partitions PF>1 and net>0: **PASS**.
- Pooled 5 bps PF>1 and net>0: **PASS**.
- Accepted retention >=80%: **PASS**.
- Frequency >=1.10/wk: **PASS**.
- WR/PF/expectancy/net all improve vs S10: **FAIL**.
- BTC-class diagnostic: **FAIL**.

## Decision

**Status: ETH_S11B_1600_STALE_CANCEL_HYBRID_NOT_SUPPORTED**

- Exploratory/engineering validation: S11A informed the 16:00 freshness hypothesis; this is not pristine unseen OOS confirmation.
- No alternate freshness cutoff, geometry, target, stop, runner, leverage, fee, or live-code change was made.
