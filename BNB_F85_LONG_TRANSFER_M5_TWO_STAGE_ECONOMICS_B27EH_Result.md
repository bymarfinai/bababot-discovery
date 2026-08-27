# BNB F85 LONG Transfer — M5 Two-Stage Economics — B27EH Result

Raw BNB 5m coverage: **100.0000%**. Frozen accepted LONG identity: **PASS (106 = 55 ALT_0330 + 51 RAW_0530)**. SHORT control: **64 unchanged B27EF trades**.

B27EH changes economics only and keeps the B27EF accepted set frozen; no re-arbitration is claimed here.

## Frozen B27EF LONG baseline

- N **106**, WR **57.5%**, PF **0.60**, expectancy **$-1.15**, net **$-121.43**, max loss streak **5**.

## Mechanism results

| Mechanism | N | WR | PF | Exp | Net | Max LS | Gate |
|---|---:|---:|---:|---:|---:|---:|---|
| H2_ONLY | 106 | 77.4% | 0.69 | $-0.33 | $-34.62 | 3 | FAIL |
| H2_50_E10_CONFIRM_E20 | 106 | 66.0% | 0.55 | $-0.52 | $-55.03 | 3 | FAIL |

## Source and partition stability

| Mechanism | Scope | N | WR | PF | Net | Max LS |
|---|---|---:|---:|---:|---:|---:|
| H2_ONLY | ALT_0330 | 55 | 81.8% | 0.79 | $-10.34 | 2 |
| H2_ONLY | RAW_0530 | 51 | 72.5% | 0.62 | $-24.27 | 4 |
| H2_ONLY | external | 25 | 72.0% | 0.49 | $-30.69 | 2 |
| H2_ONLY | development | 55 | 80.0% | 1.07 | $+2.47 | 2 |
| H2_ONLY | reference_validation | 26 | 76.9% | 0.65 | $-6.40 | 3 |
| H2_50_E10_CONFIRM_E20 | ALT_0330 | 55 | 65.5% | 0.55 | $-25.78 | 3 |
| H2_50_E10_CONFIRM_E20 | RAW_0530 | 51 | 66.7% | 0.55 | $-29.25 | 3 |
| H2_50_E10_CONFIRM_E20 | external | 25 | 64.0% | 0.38 | $-38.60 | 2 |
| H2_50_E10_CONFIRM_E20 | development | 55 | 67.3% | 0.81 | $-7.56 | 3 |
| H2_50_E10_CONFIRM_E20 | reference_validation | 26 | 65.4% | 0.58 | $-8.87 | 2 |

## Adverse fill sensitivity — LONG only

| Mechanism | bps/fill | N | WR | PF | Net | Max LS |
|---|---:|---:|---:|---:|---:|---:|
| H2_ONLY | 0 | 106 | 77.4% | 0.69 | $-34.62 | 3 |
| H2_ONLY | 2 | 106 | 69.8% | 0.53 | $-55.82 | 3 |
| H2_ONLY | 5 | 106 | 42.5% | 0.34 | $-87.60 | 8 |
| H2_ONLY | 10 | 106 | 25.5% | 0.16 | $-140.53 | 23 |
| H2_50_E10_CONFIRM_E20 | 0 | 106 | 66.0% | 0.55 | $-55.03 | 3 |
| H2_50_E10_CONFIRM_E20 | 2 | 106 | 57.5% | 0.42 | $-76.23 | 7 |
| H2_50_E10_CONFIRM_E20 | 5 | 106 | 41.5% | 0.27 | $-108.00 | 9 |
| H2_50_E10_CONFIRM_E20 | 10 | 106 | 26.4% | 0.12 | $-160.90 | 12 |

## Two-stage state counts

- H2 reached: **92/106 (86.8%)**.
- E10 completed-close continuation confirmed: **22/92 H2 trades (23.9%)**.
- Runner E20 hits after confirmation: **16**.
- Runner continuation-failure exits: **74**.
- Runner time exits: **2**.

## Frozen-acceptance portfolio control (LONG mechanism + unchanged SHORT20)

| Mechanism | N | WR | PF | Net | Max LS |
|---|---:|---:|---:|---:|---:|
| H2_ONLY | 170 | 73.5% | 0.97 | $-5.14 | 5 |
| H2_50_E10_CONFIRM_E20 | 170 | 66.5% | 0.87 | $-25.56 | 5 |

**Preferred mechanism under preregistered gate: NONE**

Neither fixed payout architecture satisfies the preregistered robustness gate. No BNB-native payout rule is selected.

**Status: B27EH_BNB_TWO_STAGE_ECONOMICS_NOT_SUPPORTED**

B27EH stops here. No re-arbitration, parameter optimization, forward shadow, or live integration is run automatically.
