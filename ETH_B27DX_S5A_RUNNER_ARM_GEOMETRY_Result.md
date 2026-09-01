# ETH B27DX — S5A Live-Executable Runner Arm Geometry — Result

ETH raw 5m coverage: **100.0000%**.

Frozen signal layer: **R300/X360 · F75 entry · F20 pre-arm invalidation · clocks 05:00,09:00,10:00,16:00 UTC**. Only runner arm milestone varies. Breathing gap and ratchet step are fixed at 0.10R with B27DQ-style N+2 activation.

## Pooled-major arm comparison

| Arm | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS | Armed | Floor exits | 5bps PF | 5bps Net | Support | BTC quality |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| E10 | 487 | 1.419 | 65.9% | 1.38 | 0.64 | 309.89 | 5 | 294 | 283 | 1.07 | 66.00 | NO | NO |
| E15 | 484 | 1.410 | 63.8% | 1.34 | 0.62 | 299.91 | 5 | 267 | 255 | 1.06 | 57.54 | NO | NO |
| E20 | 479 | 1.396 | 63.0% | 1.42 | 0.79 | 376.80 | 5 | 256 | 244 | 1.14 | 136.85 | NO | NO |
| E25 | 478 | 1.393 | 61.3% | 1.41 | 0.79 | 375.86 | 5 | 240 | 230 | 1.13 | 136.41 | NO | NO |
| E30 | 476 | 1.387 | 60.3% | 1.46 | 0.90 | 426.40 | 5 | 226 | 214 | 1.18 | 187.91 | NO | NO |
| E35 | 476 | 1.387 | 59.5% | 1.48 | 0.97 | 461.18 | 5 | 213 | 200 | 1.21 | 222.65 | NO | NO |
| E40 | 476 | 1.387 | 58.6% | 1.49 | 0.99 | 469.12 | 5 | 196 | 185 | 1.22 | 230.58 | NO | NO |

## Fixed S4 baseline

- Accepted **478**, frequency **1.393/wk**, WR **62.8%**, PF **1.42**, expectancy **+$0.81/trade**, net **+$385.75**, max LS **5**.

## Supported arm-family runs

None.

## Per-partition 0 bps

| Arm | Partition | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| E10 | external | 147 | 1.408 | 68.0% | 1.86 | 1.48 | 218.22 | 3 |
| E10 | development | 238 | 1.520 | 63.9% | 1.16 | 0.27 | 63.14 | 5 |
| E10 | reference_validation | 102 | 1.242 | 67.6% | 1.18 | 0.28 | 28.53 | 4 |
| E15 | external | 146 | 1.398 | 64.4% | 1.73 | 1.45 | 211.44 | 3 |
| E15 | development | 236 | 1.507 | 63.1% | 1.12 | 0.21 | 49.31 | 5 |
| E15 | reference_validation | 102 | 1.242 | 64.7% | 1.22 | 0.38 | 39.16 | 4 |
| E20 | external | 144 | 1.379 | 63.9% | 1.89 | 1.79 | 257.61 | 3 |
| E20 | development | 234 | 1.495 | 62.4% | 1.16 | 0.28 | 66.37 | 5 |
| E20 | reference_validation | 101 | 1.230 | 63.4% | 1.29 | 0.52 | 52.81 | 4 |
| E25 | external | 144 | 1.379 | 62.5% | 1.79 | 1.63 | 235.20 | 3 |
| E25 | development | 233 | 1.488 | 59.7% | 1.14 | 0.27 | 63.20 | 5 |
| E25 | reference_validation | 101 | 1.230 | 63.4% | 1.43 | 0.77 | 77.46 | 4 |
| E30 | external | 144 | 1.379 | 61.8% | 1.83 | 1.71 | 246.53 | 3 |
| E30 | development | 232 | 1.482 | 58.6% | 1.25 | 0.49 | 113.61 | 5 |
| E30 | reference_validation | 100 | 1.217 | 62.0% | 1.36 | 0.66 | 66.27 | 4 |
| E35 | external | 144 | 1.379 | 60.4% | 1.85 | 1.79 | 257.81 | 3 |
| E35 | development | 232 | 1.482 | 58.2% | 1.34 | 0.68 | 157.15 | 5 |
| E35 | reference_validation | 100 | 1.217 | 61.0% | 1.24 | 0.46 | 46.22 | 4 |
| E40 | external | 144 | 1.379 | 61.1% | 1.87 | 1.83 | 262.98 | 3 |
| E40 | development | 232 | 1.482 | 57.3% | 1.33 | 0.65 | 149.74 | 5 |
| E40 | reference_validation | 100 | 1.217 | 58.0% | 1.28 | 0.56 | 56.40 | 4 |

## Causal execution audit

- Early floor activations: **0**.
- All arm variants causal-audit pass: **YES**.

## BTC benchmark

- BTC B27DX LONG: **WR 71.9%, PF 2.22, expectancy +$1.26/trade, max loss streak 3**.
- BTC-quality labels above require those pooled-major thresholds plus positive major partitions and 5 bps stress survival.

## Decision

**Status: ETH_S5A_NO_SUPPORTED_ARM**

- No breathing-gap, ratchet-step, geometry, clock, leverage, fee, or live-code tuning was performed.
