# ETH B27DX — S9B Early Structural Failure Exit — Result

ETH raw 5m coverage: **100.0000%**.

Frozen rule: before any post-entry H revisit, a completed bar closing below the frozen leave-bar close exits as `EARLY_STRUCTURAL_FAILURE`; target and F20 precedence remain frozen.

- S4 candidate-detail parity: **PASS**.
- Leave / execution causal audit: **PASS**.

## Portfolio comparison

| Partition | Variant | Stress | Accepted | Trades/wk | WR | PF | Exp | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | S4 | 0 bps | 144 | 1.379 | 63.9% | 1.67 | 1.38 | 198.25 | 3 |
| external | S4 | 5 bps | 144 | 1.379 | 58.3% | 1.44 | 0.99 | 143.26 | 4 |
| external | S9B | 0 bps | 151 | 1.446 | 31.8% | 0.81 | -0.18 | -27.26 | 10 |
| external | S9B | 5 bps | 151 | 1.446 | 20.5% | 0.50 | -0.66 | -99.47 | 11 |
| development | S4 | 0 bps | 233 | 1.488 | 61.4% | 1.21 | 0.40 | 93.40 | 5 |
| development | S4 | 5 bps | 233 | 1.488 | 59.7% | 1.02 | 0.03 | 7.52 | 5 |
| development | S9B | 0 bps | 244 | 1.558 | 27.5% | 0.49 | -0.48 | -117.17 | 11 |
| development | S9B | 5 bps | 244 | 1.558 | 17.2% | 0.28 | -0.95 | -232.04 | 25 |
| reference_validation | S4 | 0 bps | 101 | 1.230 | 64.4% | 1.52 | 0.93 | 94.10 | 4 |
| reference_validation | S4 | 5 bps | 101 | 1.230 | 63.4% | 1.28 | 0.56 | 56.12 | 4 |
| reference_validation | S9B | 0 bps | 102 | 1.242 | 31.4% | 0.79 | -0.15 | -15.63 | 9 |
| reference_validation | S9B | 5 bps | 102 | 1.242 | 20.6% | 0.45 | -0.62 | -62.86 | 12 |
| POOLED_MAJOR | S4 | 0 bps | 478 | 1.393 | 62.8% | 1.42 | 0.81 | 385.75 | 5 |
| POOLED_MAJOR | S4 | 5 bps | 478 | 1.393 | 60.0% | 1.21 | 0.43 | 206.90 | 5 |
| POOLED_MAJOR | S9B | 0 bps | 497 | 1.448 | 29.6% | 0.64 | -0.32 | -160.06 | 11 |
| POOLED_MAJOR | S9B | 5 bps | 497 | 1.448 | 18.9% | 0.38 | -0.79 | -394.37 | 25 |

## Loss impact

- S4 losing accepted trades: **178**.
- Exact baseline losses exited earlier under S9B candidate path: **166 (93.3%)**.
- Exact baseline losses converted to non-loss on the same candidate path: **31 (17.4%)**.
- Mean PnL improvement across exact baseline losses: **3.97**.
- Mean absolute losing PnL, executable portfolio: **5.14 → 1.27**.
- Median losing PnL: **-4.06 → -0.79**.
- Accepted S9B `EARLY_STRUCTURAL_FAILURE` exits: **417**.
- Newly freed accepted trades after shorter holding periods: **19**.

## Frozen gates

- All major partitions PF>1 and net>0: **FAIL**.
- Pooled 5 bps positive: **FAIL**.
- Pooled PF + expectancy + net all improve: **FAIL**.
- Mean absolute loss decreases: **PASS**.
- BTC-class diagnostic: **FAIL**.

## Decision

**Status: ETH_S9B_EARLY_STRUCTURAL_FAILURE_EXIT_NOT_SUPPORTED**

- No S9A freshness rule, alternate scratch threshold, geometry, runner, leverage, fee, or live-code change was made.
