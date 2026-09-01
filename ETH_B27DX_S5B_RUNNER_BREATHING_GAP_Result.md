# ETH B27DX — S5B Live-Executable Runner Breathing-Gap Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen: **R300/X360 · F75 entry · F20 pre-arm invalidation · E25 arm · 0.10R ratchet step · four ETH-native clocks**. Only breathing gap varies.

## Pooled-major gap comparison

| Gap | Initial floor | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS | 5bps PF | 5bps Net | Support | BTC quality |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| G05 | E20 | 478 | 1.393 | 61.3% | 1.43 | 0.82 | 393.99 | 5 | 1.15 | 154.52 | NO | NO |
| G10 | E15 | 478 | 1.393 | 61.3% | 1.41 | 0.79 | 375.86 | 5 | 1.13 | 136.41 | NO | NO |
| G15 | E10 | 478 | 1.393 | 61.3% | 1.43 | 0.82 | 393.02 | 5 | 1.15 | 153.55 | NO | NO |
| G20 | E05 | 477 | 1.390 | 61.4% | 1.44 | 0.85 | 405.91 | 5 | 1.16 | 166.93 | NO | NO |
| G25 | E00 | 477 | 1.390 | 61.4% | 1.44 | 0.85 | 405.28 | 5 | 1.16 | 166.30 | NO | NO |

## Fixed S4 baseline

- Accepted **478**, frequency **1.393/wk**, WR **62.8%**, PF **1.42**, expectancy **+$0.81/trade**, net **+$385.75**, max LS **5**.

## Supported gap-family runs

None.

## Per-partition 0 bps

| Gap | Partition | Accepted | WR | PF | Exp | Net | Max LS |
|---:|---|---:|---:|---:|---:|---:|---:|
| G05 | external | 144 | 62.5% | 1.80 | 1.64 | 236.22 | 3 |
| G05 | development | 233 | 59.7% | 1.17 | 0.32 | 74.27 | 5 |
| G05 | reference_validation | 101 | 63.4% | 1.46 | 0.83 | 83.50 | 4 |
| G10 | external | 144 | 62.5% | 1.79 | 1.63 | 235.20 | 3 |
| G10 | development | 233 | 59.7% | 1.14 | 0.27 | 63.20 | 5 |
| G10 | reference_validation | 101 | 63.4% | 1.43 | 0.77 | 77.46 | 4 |
| G15 | external | 144 | 62.5% | 1.78 | 1.61 | 232.16 | 3 |
| G15 | development | 233 | 59.7% | 1.18 | 0.35 | 81.80 | 5 |
| G15 | reference_validation | 101 | 63.4% | 1.44 | 0.78 | 79.05 | 4 |
| G20 | external | 144 | 62.5% | 1.73 | 1.49 | 215.14 | 3 |
| G20 | development | 233 | 59.7% | 1.26 | 0.50 | 117.24 | 5 |
| G20 | reference_validation | 100 | 64.0% | 1.42 | 0.74 | 73.53 | 4 |
| G25 | external | 144 | 62.5% | 1.69 | 1.43 | 205.28 | 3 |
| G25 | development | 233 | 59.7% | 1.31 | 0.59 | 138.56 | 5 |
| G25 | reference_validation | 100 | 64.0% | 1.35 | 0.61 | 61.44 | 4 |

## Causal audit

- Early floor activations: **0**.
- All gap variants causal-audit pass: **YES**.

## Decision

**Status: ETH_S5B_NO_SUPPORTED_GAP**

- No arm, ratchet-step, structure, entry, clock, leverage, fee, or live-code tuning was performed.
