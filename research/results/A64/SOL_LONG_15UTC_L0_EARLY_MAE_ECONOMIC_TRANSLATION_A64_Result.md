# SOL LONG 15:00 UTC L0 Early MAE Economic Translation — A64 Result

**Gate status: SOL_LONG_15UTC_L0_EARLY_MAE_ECONOMIC_TRANSLATION_A64_REJECTED_DEVELOPMENT**

Raw SOLUSDT 5m coverage: **99.7671%**.

A64 is the preregistered economic translation of the A62+A63 `running_mae_R` mechanism-specific signal. Threshold learning is Development-only; OOS is opened only if a Development candidate passes every frozen gate.

## Reconciliation

| Partition | Parent | Losses | L0/M0 | Raw winners |
|---|---:|---:|---:|---:|
| Development | 601 | 357 | 37 | 244 |
| External Validation | 281 | 166 | 13 | 115 |
| Reference Validation | 337 | 187 | 26 | 150 |

## Development threshold family

| Age | Source N | Quantile | Rank | Threshold running_mae_R | Duplicate |
|---:|---:|---:|---:|---:|---:|
| 60m | 33 | Q25 | 9 | 0.336679 | NO |
| 60m | 33 | Q50 | 17 | 0.513333 | NO |
| 60m | 33 | Q75 | 25 | 0.737518 | NO |
| 120m | 29 | Q25 | 8 | 0.588785 | NO |
| 120m | 29 | Q50 | 15 | 0.664723 | NO |
| 120m | 29 | Q75 | 22 | 0.803653 | NO |

## Development candidate economics

| Candidate | Threshold | Triggers | L0 trig | Winners trig | Net Δ | PF | 5bps Net Δ | 5bps PF | DD | L0 Δ | Winner Δ | Blocks raw/stress | Gate |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| A60_Q25 | 0.336679 | 77 | 25 | 29 | $29.02 | 1.35 | $29.02 | 1.19 | $79.17 | $205.48 | $-215.01 | 3/6 / 3/6 | FAIL |
| A60_Q50 | 0.513333 | 30 | 17 | 10 | $49.99 | 1.34 | $49.99 | 1.20 | $113.75 | $117.52 | $-77.42 | 3/6 / 3/6 | FAIL |
| A60_Q75 | 0.737518 | 13 | 9 | 2 | $42.32 | 1.33 | $42.32 | 1.18 | $113.75 | $58.05 | $-23.17 | 3/6 / 3/6 | FAIL |
| A120_Q25 | 0.588785 | 40 | 22 | 9 | $86.29 | 1.39 | $86.29 | 1.23 | $114.01 | $165.54 | $-76.38 | 5/6 / 5/6 | FAIL |
| A120_Q50 | 0.664723 | 25 | 15 | 6 | $46.00 | 1.34 | $46.00 | 1.19 | $120.77 | $96.32 | $-49.92 | 4/6 / 4/6 | FAIL |
| A120_Q75 | 0.803653 | 14 | 8 | 3 | $22.57 | 1.30 | $22.57 | 1.17 | $134.39 | $45.28 | $-15.44 | 5/6 / 5/6 | FAIL |

## Development decision

No preregistered Development candidate passed every gate. Per protocol, External and Reference Validation intervention economics were not computed and cannot be used to rescue A64.

## Interpretation boundary

A64 judges economic feasibility, not WR aesthetics. A rejection does not authorize threshold/age rescue, partial sizing, re-arm, or feature combination. A support result would still require a separate deployment/forward-validation decision before live use.

Research only. Live Baba Bot remains unchanged.
