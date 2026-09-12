# ETH R3 H02 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **RV_LOW__RANGE_MID / LB180 / H240**; WR 67.16%, Exp $+3.10, PF 2.968, DD $40.40, LS 7.
Preregistered one-step local neighborhood contains **5** timing cells. Economically viable in 2023: **0**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 180 | 240 | 0 | 65 | 38.46% | $-20.02 | $-0.31 | 0.785 | $52.29 | 9 | -28.70pp | -9.9% | 26.5% | N | N | N |
| 120 | 240 | 1 | 61 | 27.87% | $-81.97 | $-1.34 | 0.310 | $100.22 | 12 | -39.30pp | -43.4% | 10.4% | N | N | N |
| 180 | 120 | 1 | 65 | 30.77% | $-39.55 | $-0.61 | 0.545 | $64.09 | 13 | -36.39pp | -19.6% | 18.4% | N | N | Y |
| 180 | 360 | 1 | 65 | 50.77% | $+119.68 | $+1.84 | 2.409 | $43.54 | 10 | -16.39pp | 59.4% | 81.2% | N | N | N |
| 240 | 240 | 1 | 54 | 25.93% | $-51.72 | $-0.96 | 0.354 | $71.11 | 11 | -41.24pp | -30.9% | 11.9% | N | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
