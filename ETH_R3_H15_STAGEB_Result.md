# ETH R3 H15 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **DRIVE_UP__STR_B40_60 / LB180 / H480**; WR 59.68%, Exp $+2.77, PF 2.014, DD $71.74, LS 6.
Preregistered one-step local neighborhood contains **4** timing cells. Economically viable in 2023: **1**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 180 | 480 | 0 | 72 | 48.61% | $+144.40 | $+2.01 | 1.878 | $48.14 | 6 | -11.07pp | 72.5% | 93.3% | N | N | N |
| 120 | 480 | 1 | 84 | 34.52% | $-89.25 | $-1.06 | 0.712 | $182.42 | 12 | -25.15pp | -38.4% | 35.3% | N | N | N |
| 180 | 360 | 1 | 72 | 47.22% | $+59.23 | $+0.82 | 1.481 | $67.48 | 5 | -12.46pp | 29.7% | 73.5% | N | N | N |
| 240 | 480 | 1 | 85 | 55.29% | $+113.88 | $+1.34 | 1.566 | $120.22 | 8 | -4.38pp | 48.4% | 77.8% | Y | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
