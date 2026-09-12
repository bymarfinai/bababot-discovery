# BNB R4c — H22 Scientific Verdict

## Scope
Execution-policy synthesis for the previously validated BNB R4b H22 `RV_HIGH__RANGE_MID` plateau.

This stage did **not** search for a best 2025 coordinate. The policy was frozen from plateau topology before the R4c result was read:
- unique lookback voters: LB180, LB240, LB360;
- entry consensus: at least 2 of 3 voters;
- H22 quarter-hour anchors only;
- earliest qualifying anchor per WIB day;
- fixed Hold 720 minutes because H720 is the only frozen layer spanning all three unique lookbacks and is the modal hold layer;
- one position/day, no pyramiding;
- LONG only;
- fixed $500 notional and $0.75 round-trip fee;
- inherited weekday-only signal universe.

## Scientific-status caveat
2025 is **not** fresh OOS for R4c because the execution policy was synthesized after the R4b 2025 plateau outcome had already been observed. R4c 2022-2025 is therefore an execution-synthesis diagnostic.

**2026 remained closed throughout R4c.**

## True execution ledger
The de-duplicated deterministic policy produced **113 actual trades** across 2022-2025, approximately 28 trades/year on average.

### 0 bps/side
| Period | N | WR | Net | Exp/trade | PF | DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 33 | 60.61% | +$72.19 | +$2.19 | 1.802 | $31.89 | 3 |
| 2023 | 31 | 51.61% | +$62.09 | +$2.00 | 1.727 | $33.64 | 5 |
| 2024 | 24 | 66.67% | +$131.75 | +$5.49 | 5.218 | $13.41 | 2 |
| 2025 | 25 | 60.00% | +$31.75 | +$1.27 | 1.401 | $28.16 | 6 |
| **2022-2025** | **113** | **59.29%** | **+$297.77** | **+$2.64** | **2.041** | **$33.64** | **6** |

### Implementation-cost stress
| Slippage/side | N | WR | Net | Exp/trade | PF | DD | LS |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 bps | 113 | 59.29% | +$297.77 | +$2.64 | 2.041 | $33.64 | 6 |
| 2 bps | 113 | 57.52% | +$275.17 | +$2.44 | 1.932 | $35.04 | 6 |
| 5 bps | 113 | 53.98% | +$241.27 | +$2.14 | 1.777 | $37.14 | 6 |
| 10 bps | 113 | 52.21% | +$184.77 | +$1.64 | 1.549 | $44.43 | 6 |

All four years remained net-positive at 2 bps/side.

## Frozen gate audit
Preregistered R4c support gate required every 0-bps calendar year to satisfy N>=24, WR>=52%, Net>0, Exp>0, PF>=1.15 and DD<=$160.

- 2022: PASS
- **2023: FAIL solely on WR, 51.61% versus frozen minimum 52.00%**
- 2024: PASS
- 2025: PASS
- Annual 0-bps gates: **3/4 PASS**
- Pooled 0-bps gate: **PASS**
- 2-bps/side stress gate: **PASS**, with 4/4 positive years

## Formal verdict
**`BNB_R4C_H22_EXECUTION_POLICY_NOT_SUPPORTED`**

The policy is an economically strong near-pass, but the preregistered gate cannot be relaxed by 0.39 percentage points after seeing the result. No change to the WR threshold, consensus vote, hold, coordinate, anchor rule, TP/SL or weekday universe is allowed as a rescue.

This verdict does **not** invalidate the R4b H22 plateau itself. It only says that this particular topology-derived 2-of-3 / H720 deployment policy failed its stricter R4c execution gate.

## Next scientific step
Do not open 2026 for this failed execution policy. The clean next experiment is an independent R4c execution-policy freeze for the second R4b robust plateau, H05 `DRIVE_DOWN__STR_B60_80`, using a topology-derived policy preregistered before its execution results are inspected.

Research/shadow only.