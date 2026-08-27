# BNB F85/F15 Transfer — M3 Frozen BTC-Rule Economics — B27EF Result

Raw BNB 5m coverage: **100.0000%**. Exact B27EE candidate identity/geometry reproduction: **PASS (176 candidates)**.

Frozen portfolio: **ALT_0330 fixed E20 + RAW_0530 B27DQ N+2 runner + SHORT_2000 fixed E20_DOWN**. $500 notional, $0.40 fee, one BNB position.

## Pooled-major portfolio

| Candidates | Accepted | Blocked | Wins | WR | PF | Expectancy | Net | Max loss streak |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 175 | 170 | 5 | 104 | 61.2% | 0.76 | $-0.54 | $-91.95 | 8 |

## Source contribution

| Source | Side | Candidates | Accepted | WR | PF | Exp | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| ALT_0330 | LONG | 56 | 55 | 61.8% | 0.65 | $-0.89 | $-49.12 | 6 |
| RAW_0530 | LONG | 55 | 51 | 52.9% | 0.55 | $-1.42 | $-72.31 | 5 |
| SHORT_2000 | SHORT | 64 | 64 | 67.2% | 1.36 | $+0.46 | $+29.47 | 4 |

## Major partitions

| Partition | N | WR | PF | Exp | Net | Max LS |
|---|---:|---:|---:|---:|---:|---:|
| external | 45 | 60.0% | 0.77 | $-0.72 | $-32.48 | 6 |
| development | 83 | 57.8% | 0.75 | $-0.51 | $-42.29 | 8 |
| reference_validation | 42 | 69.0% | 0.76 | $-0.41 | $-17.18 | 3 |

## Adverse fill sensitivity — pooled major

| Slippage/fill | N | WR | PF | Exp | Net | Max LS |
|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 170 | 61.2% | 0.76 | $-0.54 | $-91.95 | 8 |
| 2 bps | 170 | 59.4% | 0.68 | $-0.74 | $-125.90 | 8 |
| 5 bps | 170 | 56.5% | 0.58 | $-1.04 | $-176.81 | 8 |
| 10 bps | 170 | 52.4% | 0.43 | $-1.54 | $-261.64 | 8 |

## Exit reasons

| Source | Side | Exit reason | N |
|---|---|---|---:|
| ALT_0330 | LONG | CLOSE_INVALIDATION_F35 | 19 |
| ALT_0330 | LONG | TIME_EXIT_EXEC_END | 5 |
| ALT_0330 | LONG | TP_E20 | 31 |
| RAW_0530 | LONG | CLOSE_INVALIDATION_F35 | 15 |
| RAW_0530 | LONG | LIVE_FLOOR_GAP_OPEN | 10 |
| RAW_0530 | LONG | LIVE_FLOOR_TOUCH | 17 |
| RAW_0530 | LONG | LIVE_RUNNER_TIME_EXIT | 1 |
| RAW_0530 | LONG | TIME_EXIT_EXEC_END | 8 |
| SHORT_2000 | SHORT | CLOSE_INVALIDATION_F65 | 14 |
| SHORT_2000 | SHORT | TIME_EXIT_SESSION_END | 11 |
| SHORT_2000 | SHORT | TP_E20_DOWN | 39 |

**Status: B27EF_BNB_FROZEN_ECONOMICS_NOT_SUPPORTED**

B27EF stops here. No BNB-specific optimization, forward shadow, or next milestone is run automatically.
