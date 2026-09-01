# ETH B27DX — S4 Global One-Position Portfolio Lock — Result

ETH raw 5m coverage: **100.0000%**.

Frozen representative: **R300/X360 · F75 entry · E25 target · F20 completed-close invalidation** across **05:00, 09:00, 10:00, 16:00 UTC**.

- Candidate-detail parity: **PASS**.
- Exact same-entry-bar clock ties: **68**.

## Portfolio summary

| Partition | Stress | Candidates | Accepted | Blocked | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 0 bps | 167 | 144 | 23 | 1.379 | 63.9% | 1.67 | 1.38 | 198.25 | 3 |
| external | 5 bps | 167 | 144 | 23 | 1.379 | 58.3% | 1.44 | 0.99 | 143.26 | 4 |
| development | 0 bps | 288 | 233 | 55 | 1.488 | 61.4% | 1.21 | 0.40 | 93.40 | 5 |
| development | 5 bps | 288 | 233 | 55 | 1.488 | 59.7% | 1.02 | 0.03 | 7.52 | 5 |
| reference_validation | 0 bps | 120 | 101 | 19 | 1.230 | 64.4% | 1.52 | 0.93 | 94.10 | 4 |
| reference_validation | 5 bps | 120 | 101 | 19 | 1.230 | 63.4% | 1.28 | 0.56 | 56.12 | 4 |
| POOLED_MAJOR | 0 bps | 575 | 478 | 97 | 1.393 | 62.8% | 1.42 | 0.81 | 385.75 | 5 |
| POOLED_MAJOR | 5 bps | 575 | 478 | 97 | 1.393 | 60.0% | 1.21 | 0.43 | 206.90 | 5 |

## Pooled-major source-clock contribution (0 bps)

| Clock | Candidates | Accepted | Blocked | WR | PF | Exp | Net |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 05:00 | 105 | 101 | 4 | 62.4% | 1.71 | 1.00 | 101.35 |
| 09:00 | 171 | 90 | 81 | 62.2% | 1.30 | 0.67 | 60.14 |
| 10:00 | 176 | 164 | 12 | 66.5% | 1.58 | 0.98 | 161.04 |
| 16:00 | 123 | 123 | 0 | 58.5% | 1.21 | 0.51 | 63.22 |

## BTC benchmark gate

- BTC B27DX LONG benchmark: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.
- ETH pooled-major 0 bps: **WR 62.8%, PF 1.42, expectancy 0.81, net 385.75, max LS 5**.
- ETH pooled-major frequency: **1.393 accepted trades/week**.
- BTC-quality gate: **FAIL**.
- 5 bps stress gate: **PASS**.

## Decision

**Status: ETH_S4_PORTFOLIO_POSITIVE_BELOW_BTC_QUALITY**

- No geometry, clock, runner, leverage, fee, or live-code tuning was performed.
