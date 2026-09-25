# SOL Donor Transplant — Stage 3 Result

Raw SOLUSDT 5m coverage: **100.0000%**.

Frozen execution: donor signal on completed 5m bars -> hourly latch -> **next 1H open** entry; one active LONG; TP +1%; SL -1%; same-5m double-touch = SL first; fee assumption 0.15%.

## Results

| Detector | Partition | Trades | WR | Trades/day | Avg net/trade | Median hold h | P90 hold h |
|---|---|---:|---:|---:|---:|---:|---:|
| E0V1E | DEV_2023_24 | 66 | 47.0% | 0.090 | -0.2% | 0.00 | 0.29 |
| E0V1E | HOLDOUT_2025 | 26 | 42.3% | 0.071 | -0.3% | 0.00 | 0.33 |
| E0V1E | FINAL_2026 | 2 | 50.0% | 0.008 | -0.1% | 0.25 | 0.45 |
| CCI_BB | DEV_2023_24 | 4145 | 48.3% | 5.670 | -0.2% | 0.92 | 4.17 |
| CCI_BB | HOLDOUT_2025 | 1974 | 50.2% | 5.408 | -0.1% | 1.08 | 4.58 |
| CCI_BB | FINAL_2026 | 997 | 48.3% | 4.103 | -0.2% | 1.75 | 7.78 |
| OVERLAP | DEV_2023_24 | 55 | 49.1% | 0.075 | -0.2% | 0.00 | 0.17 |
| OVERLAP | HOLDOUT_2025 | 19 | 42.1% | 0.052 | -0.3% | 0.00 | 0.33 |
| OVERLAP | FINAL_2026 | 2 | 50.0% | 0.008 | -0.1% | 0.25 | 0.45 |
| DNA_V1 | DEV_2023_24 | 539 | 50.3% | 0.737 | -0.1% | 1.00 | 4.00 |
| DNA_V1 | HOLDOUT_2025 | 205 | 49.8% | 0.562 | -0.2% | 1.25 | 5.15 |
| DNA_V1 | FINAL_2026 | 130 | 47.7% | 0.535 | -0.2% | 2.42 | 11.29 |

## Raw hourly signal density

| Detector | Signal-hours | Signals/day (2023-2026 window) |
|---|---:|---:|
| E0V1E | 94 | 0.070 |
| CCI_BB | 10530 | 7.864 |
| OVERLAP | 76 | 0.057 |
| DNA_V1 | 955 | 0.713 |

## Stage 3 interpretation

- **E0V1E:** DEV WR 47.0%, 2025 WR 42.3%, 2026 WR 50.0%; DEV frequency 0.090/day.
- **CCI_BB:** DEV WR 48.3%, 2025 WR 50.2%, 2026 WR 48.3%; DEV frequency 5.670/day.
- **OVERLAP:** DEV WR 49.1%, 2025 WR 42.1%, 2026 WR 50.0%; DEV frequency 0.075/day.
- **DNA_V1:** DEV WR 50.3%, 2025 WR 49.8%, 2026 WR 47.7%; DEV frequency 0.737/day.

Stage 3 does **not** tune thresholds and does not promote a final strategy. Its purpose is to test whether public-repo entry DNA survives BabaBot's fixed +1%/-1% first-hit execution.
