# ETH R3 H19 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **RV_LOW__RANGE_MID / LB60 / H240**; WR 59.21%, Exp $+3.68, PF 2.413, DD $34.60, LS 7.
Preregistered one-step local neighborhood contains **4** timing cells. Economically viable in 2023: **1**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 60 | 240 | 0 | 59 | 50.85% | $+57.16 | $+0.97 | 1.523 | $32.70 | 5 | -8.36pp | 26.3% | 63.1% | N | N | N |
| 60 | 120 | 1 | 59 | 42.37% | $-3.36 | $-0.06 | 0.956 | $29.16 | 6 | -16.84pp | -1.5% | 39.6% | N | N | N |
| 60 | 360 | 1 | 59 | 54.24% | $+97.11 | $+1.65 | 1.764 | $43.49 | 4 | -4.97pp | 44.7% | 73.1% | Y | N | N |
| 120 | 240 | 1 | 66 | 33.33% | $-15.64 | $-0.24 | 0.915 | $131.09 | 12 | -25.88pp | -6.4% | 37.9% | N | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
