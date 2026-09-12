# ETH R3 H14 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **RV_MID__RANGE_HIGH / LB240 / H360**; WR 73.33%, Exp $+3.28, PF 3.291, DD $39.49, LS 7.
Preregistered one-step local neighborhood contains **5** timing cells. Economically viable in 2023: **0**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 240 | 360 | 0 | 60 | 56.67% | $-22.89 | $-0.38 | 0.835 | $95.93 | 4 | -16.67pp | -11.6% | 25.4% | N | N | N |
| 180 | 360 | 1 | 58 | 51.72% | $-19.39 | $-0.33 | 0.845 | $75.38 | 8 | -21.61pp | -10.2% | 25.7% | N | N | N |
| 240 | 240 | 1 | 60 | 53.33% | $-64.81 | $-1.08 | 0.565 | $104.22 | 5 | -20.00pp | -33.0% | 17.2% | N | N | N |
| 240 | 480 | 1 | 60 | 48.33% | $-97.65 | $-1.63 | 0.522 | $164.50 | 9 | -25.00pp | -49.7% | 15.9% | N | N | N |
| 360 | 360 | 1 | 59 | 62.71% | $-9.26 | $-0.16 | 0.899 | $43.61 | 5 | -10.62pp | -4.8% | 27.3% | N | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
