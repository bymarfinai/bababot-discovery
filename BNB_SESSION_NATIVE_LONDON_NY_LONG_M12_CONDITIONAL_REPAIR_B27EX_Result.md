# BNB Session-Native LONG M12 Conditional Repair Trigger Discovery — B27EX Result

Raw BNB 5m coverage: **100.0000%**.

Development only. Frozen baseline: **E5_MICRO_HL_BULL**, TP **H+0.30R**, SL **0.30R**, total cost **0.15% per completed leg**.

Baseline integrity: **50 opportunities = 25 net wins + 25 net losses**; **19/25 losses failed before H**.

Repair preserves the original entry and activates only after a completed adverse bar before H; it exits at next 5m open and allows one fresh-Micro-HL re-entry.

| Rank | Conditional repair | L→W | FBH L→W | W→W | W→L | Net wins/50 | WR | Triggered W/L | Reentries | Legs | Avg net/opp | PnL @ $500 | PF |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0 | BASELINE | 0 | 0 | 25 | 0 | 25/50 | 50.0% | 0/0 | 0 | 50 | 0.111% | $27.84 | 1.34 |
| 1 | T05_EXIT_REENTER_FRESH_MICROHL | 2 | 2 | 23 | 2 | 25/50 | 50.0% | 9/22 | 31 | 81 | -0.054% | $-13.59 | 0.87 |
| 2 | T20_EXIT_REENTER_FRESH_MICROHL | 1 | 1 | 24 | 1 | 25/50 | 50.0% | 4/15 | 19 | 69 | 0.031% | $7.71 | 1.08 |
| 3 | T15_EXIT_REENTER_FRESH_MICROHL | 1 | 1 | 24 | 1 | 25/50 | 50.0% | 5/18 | 23 | 73 | 0.015% | $3.78 | 1.04 |
| 4 | T10_EXIT_REENTER_FRESH_MICROHL | 1 | 1 | 24 | 1 | 25/50 | 50.0% | 6/21 | 27 | 77 | 0.008% | $2.10 | 1.02 |

## Development discovery leader

By preregistered conversion ranking: **T05_EXIT_REENTER_FRESH_MICROHL** converts **2/25** original losses, including **2/19** failed-before-H losses, while retaining **23/25** original winners.
Resulting net-positive opportunities: **25/50 (50.0%)**.

This is development discovery only. No trigger is validated or promoted here.

**Status: B27EX_BNB_CONDITIONAL_REPAIR_TRIGGER_DEV_COMPLETE**

STOP: no partial-management combination, no threshold retuning, no external/reference-validation/August reveal, no SHORT/live integration.
