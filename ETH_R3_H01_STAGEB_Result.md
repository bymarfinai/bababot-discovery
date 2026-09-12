# ETH R3 H01 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **RV_LOW__RANGE_MID / LB240 / H480**; WR 62.07%, Exp $+4.29, PF 4.145, DD $46.05, LS 8.
Preregistered one-step local neighborhood contains **4** timing cells. Economically viable in 2023: **1**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 240 | 480 | 0 | 52 | 59.62% | $+4.30 | $+0.08 | 1.044 | $59.46 | 4 | -2.45pp | 1.9% | 25.2% | N | N | N |
| 180 | 480 | 1 | 61 | 57.38% | $+127.20 | $+2.09 | 2.784 | $33.28 | 4 | -4.69pp | 48.6% | 67.2% | Y | N | N |
| 240 | 360 | 1 | 52 | 46.15% | $-42.34 | $-0.81 | 0.671 | $91.76 | 13 | -15.92pp | -19.0% | 16.2% | N | N | Y |
| 360 | 480 | 1 | 61 | 62.30% | $+7.11 | $+0.12 | 1.041 | $118.26 | 4 | +0.23pp | 2.7% | 25.1% | N | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
