# ETH R3 H08 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **EFF_LOW__RANGE_MID / LB360 / H240**; WR 61.76%, Exp $+2.10, PF 2.859, DD $30.85, LS 5.
Preregistered one-step local neighborhood contains **4** timing cells. Economically viable in 2023: **1**; performance-stable: **1**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 360 | 240 | 0 | 80 | 41.25% | $+31.00 | $+0.39 | 1.445 | $32.30 | 17 | -20.51pp | 18.5% | 50.5% | N | N | Y |
| 240 | 240 | 1 | 108 | 41.67% | $+14.71 | $+0.14 | 1.116 | $66.61 | 10 | -20.10pp | 6.5% | 39.0% | N | N | N |
| 360 | 120 | 1 | 80 | 28.75% | $-22.77 | $-0.28 | 0.763 | $66.78 | 10 | -33.01pp | -13.6% | 26.7% | N | N | N |
| 360 | 360 | 1 | 80 | 57.50% | $+116.53 | $+1.46 | 2.391 | $25.85 | 7 | -4.26pp | 69.4% | 83.6% | Y | Y | N |

## Verdict

**LOCAL_NEIGHBORHOOD_FAIL**

A stable point exists, but fewer than two local timing cells are economically viable. 2024 remains unopened.
