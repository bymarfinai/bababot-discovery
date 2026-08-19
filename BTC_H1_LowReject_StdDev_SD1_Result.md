# BTC H1 LOW_REJECT StdDev SD1 — Result

Four fixed clocks only: **11:00 / 15:00 / 01:00 / 02:00 WIB**. 1H LOW_REJECT vs prior3H range. StdDev uses only the prior 24 completed 1H candle log returns.

Core events: external **411**, reference **810** (dev 567, validation 243), August **11**.

## Development threshold grid

| Min sweep sigma | N | +1H | +3H | Wilson low | Avg3H | Median sweep sigma |
|---:|---:|---:|---:|---:|---:|---:|
| 0.00σ | 567 | 56.44% | 61.73% | 57.66% | 0.09% | 0.304σ |
| 0.25σ | 315 | 57.46% | 60.00% | 54.50% | 0.10% | 0.534σ |
| 0.50σ | 175 | 53.14% | 64.00% | 56.66% | 0.13% | 0.815σ |
| 0.75σ | 96 | 53.12% | 64.58% | 54.62% | 0.21% | 1.150σ |
| 1.00σ | 66 | 59.09% | 63.64% | 51.58% | 0.19% | 1.365σ |
| 1.25σ | 44 | 59.09% | 65.91% | 51.14% | 0.16% | 1.611σ |
| 1.50σ | 27 | 59.26% | 70.37% | 51.52% | 0.24% | 2.158σ |

Frozen selector chose **sweep >= 0.00σ** from development only.

## Directional validation

| Partition | Rule | N | +1H | +3H | Wilson low | Avg3H | Median3H |
|---|---|---:|---:|---:|---:|---:|---:|
| development | selected | 567 | 56.44% | 61.73% | 57.66% | 0.09% | 0.10% |
| development | control | 567 | 56.44% | 61.73% | 57.66% | 0.09% | 0.10% |
| reference_validation | selected | 243 | 56.38% | 58.85% | 52.57% | 0.06% | 0.11% |
| reference_validation | control | 243 | 56.38% | 58.85% | 52.57% | 0.06% | 0.11% |
| external | selected | 411 | 53.77% | 56.45% | 51.62% | 0.09% | 0.09% |
| external | control | 411 | 53.77% | 56.45% | 51.62% | 0.09% | 0.09% |
| august | selected | 11 | 63.64% | 45.45% | 21.27% | -0.07% | -0.04% |
| august | control | 11 | 63.64% | 45.45% | 21.27% | -0.07% | -0.04% |

## External chronological blocks — selected threshold

| Block | N | +1H | +3H | Avg3H |
|---|---:|---:|---:|---:|
| B1 | 102 | 53.92% | 51.96% | -0.10% |
| B2 | 103 | 56.31% | 63.11% | 0.24% |
| B3 | 103 | 51.46% | 52.43% | 0.05% |
| B4 | 103 | 53.40% | 58.25% | 0.15% |

## Selected threshold by clock

### Reference validation

| WIB | N | +3H | Avg3H |
|---:|---:|---:|---:|
| 11:00 | 55 | 56.36% | 0.13% |
| 15:00 | 58 | 55.17% | -0.02% |
| 01:00 | 65 | 64.62% | 0.05% |
| 02:00 | 65 | 58.46% | 0.07% |

### External 2020-2021

| WIB | N | +3H | Avg3H |
|---:|---:|---:|---:|
| 11:00 | 129 | 55.81% | 0.17% |
| 15:00 | 108 | 52.78% | -0.14% |
| 01:00 | 84 | 58.33% | 0.23% |
| 02:00 | 90 | 60.00% | 0.10% |

## Executable net RR 1:1 diagnostic

LONG next1H open; SL=event low; TP raw distance=risk+0.30%; fee0.15%; max6H.

| Partition | Rule | N | TP | SL | WR | PnL | Exp/trade |
|---|---|---:|---:|---:|---:|---:|---:|
| development | selected | 567 | 164 | 403 | 28.92% | $-678.75 | $-1.197 |
| development | control | 567 | 164 | 403 | 28.92% | $-678.75 | $-1.197 |
| reference_validation | selected | 243 | 67 | 176 | 27.57% | $-283.76 | $-1.168 |
| reference_validation | control | 243 | 67 | 176 | 27.57% | $-283.76 | $-1.168 |
| external | selected | 411 | 123 | 288 | 29.93% | $-754.22 | $-1.835 |
| external | control | 411 | 123 | 288 | 29.93% | $-754.22 | $-1.835 |
| august | selected | 11 | 2 | 9 | 18.18% | $-14.02 | $-1.274 |
| august | control | 11 | 2 | 9 | 18.18% | $-14.02 | $-1.274 |

**SD1_DIRECTION_SUPPORTED: FAIL**
**SD1_80_CANDIDATE: FAIL**

Threshold was selected on development only. Validation, external, August and per-clock breakdowns were not used in selection. No post-result rescue.
