# BNB R4c — H22 Plateau Execution Policy Freeze

**2022-2025 execution-synthesis diagnostic only. 2025 is not re-labeled as fresh OOS. 2026 REMAINS CLOSED.**

Raw BNBUSDT 5m coverage: **100.0000%**.
Frozen R4b target: **H22 WIB / RV_HIGH__RANGE_MID / rank 3**.
Policy: **2-of-3 unique-lookback consensus (LB180/LB240/LB360), earliest qualifying H22 anchor, H720, one position/day, no pyramiding**.
True de-duplicated trades, 2022-2025: **113**.

## Execution metrics

| Period | Slip/side | N | WR | Net | Exp/trade | PF | DD | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 0 bps | 33 | 60.61% | $+72.19 | $+2.19 | 1.802 | $+31.89 | 3 |
| 2023 | 0 bps | 31 | 51.61% | $+62.09 | $+2.00 | 1.727 | $+33.64 | 5 |
| 2024 | 0 bps | 24 | 66.67% | $+131.75 | $+5.49 | 5.218 | $+13.41 | 2 |
| 2025 | 0 bps | 25 | 60.00% | $+31.75 | $+1.27 | 1.401 | $+28.16 | 6 |
| 2022-2025 | 0 bps | 113 | 59.29% | $+297.77 | $+2.64 | 2.041 | $+33.64 | 6 |
| 2022 | 2 bps | 33 | 57.58% | $+65.59 | $+1.99 | 1.707 | $+32.29 | 3 |
| 2023 | 2 bps | 31 | 51.61% | $+55.89 | $+1.80 | 1.632 | $+35.04 | 5 |
| 2024 | 2 bps | 24 | 66.67% | $+126.95 | $+5.29 | 4.866 | $+13.61 | 2 |
| 2025 | 2 bps | 25 | 56.00% | $+26.75 | $+1.07 | 1.329 | $+28.81 | 6 |
| 2022-2025 | 2 bps | 113 | 57.52% | $+275.17 | $+2.44 | 1.932 | $+35.04 | 6 |
| 2022 | 5 bps | 33 | 51.52% | $+55.69 | $+1.69 | 1.572 | $+33.19 | 5 |
| 2023 | 5 bps | 31 | 48.39% | $+46.59 | $+1.50 | 1.500 | $+37.14 | 5 |
| 2024 | 5 bps | 24 | 66.67% | $+119.75 | $+4.99 | 4.398 | $+13.91 | 2 |
| 2025 | 5 bps | 25 | 52.00% | $+19.25 | $+0.77 | 1.227 | $+30.01 | 6 |
| 2022-2025 | 5 bps | 113 | 53.98% | $+241.27 | $+2.14 | 1.777 | $+37.14 | 6 |
| 2022 | 10 bps | 33 | 48.48% | $+39.19 | $+1.19 | 1.371 | $+36.02 | 5 |
| 2023 | 10 bps | 31 | 45.16% | $+31.09 | $+1.00 | 1.307 | $+40.64 | 5 |
| 2024 | 10 bps | 24 | 66.67% | $+107.75 | $+4.49 | 3.746 | $+14.41 | 2 |
| 2025 | 10 bps | 25 | 52.00% | $+6.75 | $+0.27 | 1.074 | $+32.20 | 6 |
| 2022-2025 | 10 bps | 113 | 52.21% | $+184.77 | $+1.64 | 1.549 | $+44.43 | 6 |

## Anchor usage

| UTC | WIB | Eligible observations | Selected trades | Mean votes |
|---:|---:|---:|---:|---:|
| 15:00 | 22:00 | 66 | 66 | 0.20 |
| 15:15 | 22:15 | 70 | 24 | 0.21 |
| 15:30 | 22:30 | 64 | 10 | 0.22 |
| 15:45 | 22:45 | 62 | 13 | 0.20 |

## Frozen gate audit

- 0 bps annual gates: **3/4 pass**.
- 0 bps pooled gate: **PASS**.
- 2 bps/side stress gate: **PASS**; positive years **4/4**.
- Loss streak remains diagnostic only.

**Status: BNB_R4C_H22_EXECUTION_POLICY_NOT_SUPPORTED**

The execution policy was frozen from plateau topology, not from the best 2025 coordinate.
No alternative consensus threshold, hold, coordinate, TP/SL, or weekday rule was searched after observing this output.
The inherited R4b signal universe is weekday-only; weekend generalization is not tested here.
2026 remains unopened and is reserved for later forward/shadow validation.

Research/shadow only.
