# ETH R3 H06 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **DRIVE_DOWN__STR_B40_60 / LB240 / H480**; WR 62.79%, Exp $+4.11, PF 2.510, DD $82.29, LS 6.
Preregistered one-step local neighborhood contains **4** timing cells. Economically viable in 2023: **1**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 240 | 480 | 0 | 81 | 55.56% | $+21.59 | $+0.27 | 1.161 | $58.05 | 12 | -7.24pp | 6.5% | 46.2% | Y | N | N |
| 180 | 480 | 1 | 92 | 44.57% | $-37.10 | $-0.40 | 0.808 | $93.09 | 11 | -18.23pp | -9.8% | 32.2% | N | N | N |
| 240 | 360 | 1 | 81 | 46.91% | $-33.55 | $-0.41 | 0.741 | $65.72 | 14 | -15.88pp | -10.1% | 29.5% | N | N | Y |
| 360 | 480 | 1 | 74 | 36.49% | $-58.00 | $-0.78 | 0.563 | $60.91 | 8 | -26.30pp | -19.0% | 22.4% | N | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
