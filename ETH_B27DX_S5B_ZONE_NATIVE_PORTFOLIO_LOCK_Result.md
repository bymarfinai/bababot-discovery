# ETH B27DX — S5B Zone-Native Fixed-Exit Portfolio Lock — Result

ETH raw 5m coverage: **100.0000%**.

**Candidate-stream parity: PASS.** Every frozen zone/partition reproduced the exact pre-lock `score_config` metrics before the global one-position rule was applied.

Frozen zone rules: 05:00 F80/E30; 09:00 F80/E25; 10:00 F75/E25; 16:00 F90/E25. All use R300/X360 and completed-close F35 invalidation.

## Global one-position portfolio

| Partition | Candidates | Accepted | Blocked | Retention | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 190 | 166 | 24 | 87.4% | 1.590 | 59.0% | 1.58 | $+1.20 | $+199.92 | 4 |
| development | 312 | 256 | 56 | 82.1% | 1.635 | 60.5% | 1.33 | $+0.50 | $+128.24 | 4 |
| reference_validation | 143 | 122 | 21 | 85.3% | 1.485 | 57.4% | 1.15 | $+0.28 | $+34.74 | 3 |
| POOLED_MAJOR | 645 | 544 | 101 | 84.3% | 1.585 | 59.4% | 1.38 | $+0.67 | $+362.91 | 4 |

## Pooled-major contribution by zone

| Zone | Candidates | Accepted | Blocked | Retention | WR | PF | Exp | Net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETH_0500 | 122 | 121 | 1 | 99.2% | 57.9% | 1.63 | $+0.92 | $+111.25 |
| ETH_0900 | 187 | 166 | 21 | 88.8% | 63.3% | 1.26 | $+0.49 | $+81.71 |
| ETH_1000 | 176 | 97 | 79 | 55.1% | 56.7% | 1.39 | $+0.68 | $+66.16 |
| ETH_1600 | 160 | 160 | 0 | 100.0% | 58.1% | 1.34 | $+0.65 | $+103.79 |

## Execution stress

| Stress | N | WR | PF | Exp | Net | Max LS | Trades/wk |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 544 | 59.4% | 1.38 | $+0.67 | $+362.91 | 4 | 1.585 |
| 2 bps | 544 | 58.5% | 1.28 | $+0.52 | $+280.85 | 7 | 1.585 |
| 5 bps | 544 | 57.5% | 1.15 | $+0.29 | $+157.83 | 7 | 1.585 |
| 10 bps | 544 | 55.5% | 0.96 | $-0.09 | $-47.05 | 7 | 1.585 |

## BTC benchmark gates

- BTC-quality 0-bps gate (WR>=71.9%, PF>=2.22, Exp>=$+1.26, maxLS<=3): **FAIL**.
- ETH >=2.00 accepted trades/week gate: **FAIL**.
- 5-bps diagnostic vs BTC published WR 68.9% / PF 2.09: **FAIL** (stress models are not identical).
- Exact same-entry-timestamp candidate ties before lock: **51**.

## Decision

**Status: ETH_S5B_BOTH_TARGETS_SHORT**

- No zone dropping, parameter search, runner selection, leverage tuning, or live-code changes were performed in S5B.
