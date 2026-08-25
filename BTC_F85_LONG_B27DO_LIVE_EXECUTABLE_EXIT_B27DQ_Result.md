# B27DQ — B27DO Live-Executable TP/Runner Rescore — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Prerequisite parity: PASS.** Fixed-E20 baseline and saved B27DO hybrid metrics reproduced before corrected execution interpretation.

**Execution correction:** a floor learned from completed bar N is deliberately not scored until bar N+2, giving one full 5m placement/acknowledgement buffer.

ALT_0330 remains fixed E20. RAW_0530, LONDON and RAW_2330 use the same E10/step-10 structural runner with the corrected activation timing.

## Exact portfolio comparison after global one-position re-lock

| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | FIXED_E20 | 81 | 74 | 7 | 77.0% | 2.91 | $+1.89 | $+139.72 | 3 |
| external | LIVE_EXEC_NPLUS2_E10_HYBRID | 81 | 74 | 7 | 74.3% | 2.77 | $+1.81 | $+134.07 | 3 |
| development | FIXED_E20 | 113 | 107 | 6 | 72.0% | 1.52 | $+0.60 | $+63.83 | 3 |
| development | LIVE_EXEC_NPLUS2_E10_HYBRID | 113 | 106 | 7 | 67.0% | 1.75 | $+0.88 | $+93.48 | 3 |
| reference_validation | FIXED_E20 | 48 | 47 | 1 | 80.9% | 2.26 | $+0.84 | $+39.30 | 2 |
| reference_validation | LIVE_EXEC_NPLUS2_E10_HYBRID | 48 | 47 | 1 | 80.9% | 2.99 | $+1.32 | $+62.21 | 2 |
| august | FIXED_E20 | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| august | LIVE_EXEC_NPLUS2_E10_HYBRID | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| POOLED_MAJOR | FIXED_E20 | 242 | 228 | 14 | 75.4% | 2.07 | $+1.07 | $+242.84 | 3 |
| POOLED_MAJOR | LIVE_EXEC_NPLUS2_E10_HYBRID | 242 | 227 | 15 | 72.2% | 2.25 | $+1.28 | $+289.76 | 3 |

## Pooled-major contribution by zone

| Zone | Exit | N | WR | PF | Exp | Net |
|---|---|---:|---:|---:|---:|---:|
| ALT_0330 | FIXED_E20 | 61 | 77.0% | 2.44 | $+1.35 | $+82.44 |
| RAW_0530 | LIVE_EXEC_NPLUS2_E10 | 54 | 70.4% | 2.08 | $+1.07 | $+58.01 |
| LONDON | LIVE_EXEC_NPLUS2_E10 | 67 | 70.1% | 1.80 | $+1.04 | $+69.93 |
| RAW_2330 | LIVE_EXEC_NPLUS2_E10 | 45 | 71.1% | 3.45 | $+1.76 | $+79.38 |

## Live-execution anatomy

- Accepted pooled-major runner-zone trades: **166**; armed: **114**.
- Scheduled floor updates: **193**; actual activations before exit: **190**.
- Resting-floor touch exits: **70**; gap-open exits: **41**.
- Initial placement-buffer F35 close exits: **0**.
- No floor is credited on N+1 after being learned at N close; first eligible scoring bar is N+2.

## Stop-market slippage sensitivity

| Adverse stop slippage | N | WR | PF | Exp | Net | Max loss streak |
|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 227 | 72.2% | 2.25 | $+1.28 | $+289.76 | 3 |
| 2 bps | 227 | 71.8% | 2.20 | $+1.23 | $+278.58 | 3 |
| 5 bps | 227 | 69.2% | 2.12 | $+1.15 | $+261.82 | 6 |
| 10 bps | 227 | 65.6% | 1.98 | $+1.03 | $+233.88 | 6 |

## Direct scorecard

- Fixed E20 baseline: **N 228 / WR 75.4% / PF 2.07 / Exp $+1.07 / Net $+242.84**.
- Original B27DO research hybrid: **N 227 / WR 72.2% / PF 2.31 / Exp $+1.32 / Net $+299.89**.
- Corrected B27DQ live-executable hybrid: **N 227 / WR 72.2% / PF 2.25 / Exp $+1.28 / Net $+289.76**.
- Delta B27DQ vs original B27DO: **$-10.13** net; WR **+0.0 pp**.
- Delta B27DQ vs fixed E20: **$+46.92** net; WR **-3.2 pp**.

## Decision

**Status: B27DQ_LIVE_EXECUTABLE_SUPPORTED**

**Evidence status: exploratory/engineering validation, not pristine unseen OOS.**

Research only; live BBC code/configuration unchanged.
