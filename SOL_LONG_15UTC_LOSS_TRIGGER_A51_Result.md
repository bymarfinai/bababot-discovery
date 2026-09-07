# SOL LONG 15:00 UTC Universal Loss Trigger Anatomy — A51 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A51 audits the frozen R360/15UTC `E0_RESTING_H -> E40` state machine. It does not modify trading rules.

## Reconciliation

Trades: **1219**; raw losses: **710**; errors: **0**.

## Core trigger finding

- `M0_REFERENCE_INVALIDATION`: **76** losses.
- `M0F_REFERENCE_INVALIDATION_FINAL_BAR`: **0** losses.
- `M1_TIME_NO_STRUCTURAL_FAIL`: **95** losses.
- `M2_FAILED_BREAK`: **539** losses.

For M2, the terminal event is the same across L2/L3/L4/L5: **first completed 5m close `<= H` after a completed close `> H` confirmed breakout**. The legacy classes are latency buckets, not different trigger mechanisms.

For M0, the terminal event is **first completed close `< L` before breakout confirmation**. L1 is a time-expiry bucket unless the frozen final-bar edge places a structural invalidation into `TIME_AFTER_FINAL_INVALIDATION`.

Important execution semantics: candle timestamps label bar opens. A failed/invalidation bar becomes known at its close (`trigger_ts + 5m`), which is the same physical instant as the normal next-bar open. Therefore the nominal timestamp gap is generally 5m, but **actionable lead after terminal confirmation is 0m**.

## Pooled legacy class anatomy

| Class | N | Entry→trigger | Break→trigger | Trigger close | Prev close | Max ext before trigger | Actionable lead |
|---|---:|---:|---:|---:|---:|---:|---:|
| L0_NEVER_BREAK_REFERENCE_INVALIDATION | 76 | 230m | -m | -1.062R | -0.884R | -R | 0m |
| L1_NEVER_BREAK_TIME | 95 | -m | -m | -R | -R | -R | -m |
| L2_BREAK_FAST_FAIL_5M | 234 | 5m | 5m | -0.047R | 0.029R | 0.082R | 0m |
| L3_BREAK_FAST_FAIL_10M | 108 | 10m | 10m | -0.058R | 0.038R | 0.166R | 0m |
| L4_BREAK_FAIL_30M | 133 | 20m | 20m | -0.035R | 0.053R | 0.216R | 0m |
| L5_BREAK_FAIL_LATE | 64 | 60m | 60m | -0.025R | 0.033R | 0.277R | 0m |

## Partition trigger counts

| Partition | L0 | L1 | L2 | L3 | L4 | L5 |
|---|---:|---:|---:|---:|---:|---:|
| development | 37 | 58 | 115 | 54 | 66 | 27 |
| external | 13 | 16 | 51 | 25 | 36 | 25 |
| reference_validation | 26 | 21 | 68 | 29 | 31 | 12 |

## Fixed early-warning diagnostics

The full warning table is persisted in `SOL_LONG_15UTC_LOSS_TRIGGER_A51_WARNING_SUMMARY.csv`. These diagnostics are anatomy only; A51 does not promote a warning or threshold.

### L0_NEVER_BREAK_REFERENCE_INVALIDATION

| Warning | Coverage |
|---|---:|
| NO_BREAK_30M | 96.1% |
| PRE_L25 | 92.1% |
| NO_BREAK_60M | 89.5% |
| NO_BREAK_120M | 78.9% |

### L1_NEVER_BREAK_TIME

| Warning | Coverage |
|---|---:|
| NO_BREAK_30M | 96.8% |
| NO_BREAK_60M | 93.7% |
| NO_BREAK_120M | 86.3% |
| NO_BREAK_180M | 76.8% |

### L2_BREAK_FAST_FAIL_5M

| Warning | Coverage |
|---|---:|
| POST_H10 | 88.9% |
| POST_H05 | 67.9% |
| NO_EXT_010R_BY_10M | 62.8% |
| NO_EXT_005R_BY_5M | 26.1% |

### L3_BREAK_FAST_FAIL_10M

| Warning | Coverage |
|---|---:|
| POST_H10 | 87.0% |
| POST_H05 | 69.4% |
| NO_EXT_010R_BY_10M | 29.6% |
| NO_EXT_005R_BY_5M | 6.5% |

### L4_BREAK_FAIL_30M

| Warning | Coverage |
|---|---:|
| POST_H10 | 96.2% |
| POST_H05 | 78.2% |
| NO_EXT_010R_BY_10M | 13.5% |
| NO_EXT_005R_BY_5M | 3.8% |

### L5_BREAK_FAIL_LATE

| Warning | Coverage |
|---|---:|
| POST_H10 | 100.0% |
| POST_H05 | 93.8% |
| NO_EXT_010R_BY_10M | 7.8% |
| NO_EXT_005R_BY_5M | 1.6% |

## Decision

**Status: SOL_LONG_15UTC_LOSS_TRIGGER_A51_COMPLETE**

A51 establishes the actual failure state machine. Any attempt to exit earlier than the terminal close must be a separately preregistered warning/guard study (A52+), because terminal confirmation itself provides no executable lead before the current next-open exit.

Research only. Live Baba Bot remains unchanged.
