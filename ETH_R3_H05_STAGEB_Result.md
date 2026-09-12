# ETH R3 H05 — Stage B 2023 Practical Stability Test

**2023 TEST ONLY AGAINST FROZEN 2022 RULE/LOCAL TIMING. 2024 HARD LOCKED. 2025+ CLOSED.**

Frozen Development: **DRIVE_DOWN__STR_B80_100 / LB180 / H240**; WR 64.47%, Exp $+3.33, PF 2.601, DD $38.09, LS 5.
Preregistered one-step local neighborhood contains **5** timing cells. Economically viable in 2023: **4**; performance-stable: **0**.
Loss streak warning threshold: **12** (diagnostic only).

| LB | H | Dist | N | WR | Net | Exp | PF | DD | LS | WR Δ | Exp retain | PF retain | Viable | Stable | Risk warn |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|:---:|
| 180 | 240 | 0 | 84 | 61.90% | $+105.52 | $+1.26 | 2.048 | $30.42 | 5 | -2.57pp | 37.7% | 78.7% | Y | N | N |
| 120 | 240 | 1 | 76 | 59.21% | $+98.95 | $+1.30 | 2.451 | $23.68 | 6 | -5.26pp | 39.1% | 94.2% | Y | N | N |
| 180 | 120 | 1 | 84 | 50.00% | $+59.55 | $+0.71 | 1.494 | $54.23 | 8 | -14.47pp | 21.3% | 57.5% | N | N | N |
| 180 | 360 | 1 | 84 | 58.33% | $+133.96 | $+1.59 | 2.347 | $26.73 | 7 | -6.14pp | 47.9% | 90.3% | Y | N | N |
| 240 | 240 | 1 | 94 | 69.15% | $+156.64 | $+1.67 | 2.974 | $32.51 | 8 | +4.68pp | 50.0% | 114.3% | Y | N | N |

## Verdict

**TEST_DEGRADATION_FAIL**

No preregistered local 2023 cell retained enough of the frozen 2022 edge. 2024 remains unopened.
