# B27DM — E20 Close-Confirmed Step-10 Runner — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Fixed-E20 B27DK parity was reproduced before B27DM was interpreted.

Frozen causal rule: on the first E20-touch bar, completed close >= E20 confirms the runner; completed close < E20 exits at that bar close. No retroactive E20 fill is allowed. Confirmed trades then use the same B27DL step-10 structural floor.

## Exact portfolio comparison after global one-position re-lock

| Partition | Variant | Candidates | Accepted | Blocked | WR | PF | Exp | Net | Max loss streak |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | FIXED_E20 | 81 | 74 | 7 | 77.0% | 2.91 | $+1.89 | $+139.72 | 3 |
| external | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 81 | 74 | 7 | 71.6% | 2.78 | $+1.83 | $+135.76 | 3 |
| development | FIXED_E20 | 113 | 107 | 6 | 72.0% | 1.52 | $+0.60 | $+63.83 | 3 |
| development | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 113 | 106 | 7 | 66.0% | 1.51 | $+0.61 | $+64.58 | 4 |
| reference_validation | FIXED_E20 | 48 | 47 | 1 | 80.9% | 2.26 | $+0.84 | $+39.30 | 2 |
| reference_validation | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 48 | 47 | 1 | 80.9% | 3.02 | $+1.34 | $+63.11 | 2 |
| august | FIXED_E20 | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| august | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 2 | 1 | 1 | 100.0% | inf | $+2.65 | $+2.65 | 0 |
| POOLED_MAJOR | FIXED_E20 | 242 | 228 | 14 | 75.4% | 2.07 | $+1.07 | $+242.84 | 3 |
| POOLED_MAJOR | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 242 | 227 | 15 | 70.9% | 2.13 | $+1.16 | $+263.44 | 4 |

## Pooled-major contribution by zone

| Zone | Variant | N | WR | PF | Exp | Net | Confirmed | Wick reject | Floor exits |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ALT_0330 | FIXED_E20 | 61 | 77.0% | 2.44 | $+1.35 | $+82.44 | - | - | - |
| ALT_0330 | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 61 | 70.5% | 2.15 | $+1.16 | $+70.85 | 15 | 32 | 14 |
| RAW_0530 | FIXED_E20 | 55 | 76.4% | 1.90 | $+0.86 | $+47.28 | - | - | - |
| RAW_0530 | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 54 | 72.2% | 1.77 | $+0.76 | $+40.88 | 18 | 22 | 18 |
| LONDON | FIXED_E20 | 67 | 74.6% | 1.73 | $+0.94 | $+63.05 | - | - | - |
| LONDON | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 67 | 70.1% | 1.83 | $+1.08 | $+72.66 | 22 | 26 | 22 |
| RAW_2330 | FIXED_E20 | 45 | 73.3% | 2.66 | $+1.11 | $+50.07 | - | - | - |
| RAW_2330 | E20_CLOSE_CONFIRMED_STEP10_RUNNER | 45 | 71.1% | 3.52 | $+1.76 | $+79.04 | 14 | 12 | 13 |

## Confirmation anatomy

Accepted pooled-major confirmed runners: **69**.
Accepted pooled-major wick-reject close exits: **92**.
Average candidate-level delta on confirmed runners vs fixed E20: **$+1.53**; median **$+0.00**.
Average candidate-level delta on wick-reject exits vs fixed E20: **$-0.87**; median **$-0.56**.

- High reached E30 or farther among confirmed runners: **78.3%**.
- High reached E40 or farther among confirmed runners: **50.7%**.
- High reached E50 or farther among confirmed runners: **37.7%**.
- High reached E60 or farther among confirmed runners: **27.5%**.
- High reached E80 or farther among confirmed runners: **20.3%**.
- High reached E100 or farther among confirmed runners: **13.0%**.

## Decision

Pooled-major fixed E20: **N 228 / WR 75.4% / PF 2.07 / Exp $+1.07 / Net $+242.84**.
Pooled-major B27DM: **N 227 / WR 70.9% / PF 2.13 / Exp $+1.16 / Net $+263.44**.
Net delta vs fixed E20: **$+20.60**; accepted delta: **-1**; WR delta: **-4.5 pp**.
For context, prior B27DL universal touch-armed runner: **N 227 / WR 70.9% / PF 2.13 / Exp $+1.16 / Net $+263.59**.
B27DM net delta vs B27DL: **$-0.15**; WR delta: **+0.0 pp**.
**Status: B27DM_CLOSE_CONFIRMED_RUNNER_SUPPORTED**

Research/operating exit experiment only; live BBC unchanged.
