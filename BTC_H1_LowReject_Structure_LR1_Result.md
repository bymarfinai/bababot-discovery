# BTC H1 LOW_REJECT Structure LR1 — Result

Four fixed event hours only: **04/08/18/19 UTC = 11:00/15:00/01:00/02:00 WIB**. Event is LOW_REJECT vs completed prior3H range. Timeframe 1H only.

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-18 23:00:00+00:00**, rows **58,128**. Core LOW_REJECT events: external **412**, reference **810** (dev 567, validation 243), August **11**.

## Selected structural leaf

Development leaf **4**, N **297**, next3H LONG-positive **69.02%**.
Exact path: **reclaim_depth_range <= 0.27562825 AND body_ratio > 0.10717489**

## Directional validation

| Partition | Rule | N | +1H | +3H | Avg 3H | Median 3H |
|---|---|---:|---:|---:|---:|---:|
| development | selected | 297 | 63.97% | 69.02% | 0.21% | 0.17% |
| development | control | 567 | 56.44% | 61.73% | 0.09% | 0.10% |
| reference_validation | selected | 148 | 58.78% | 60.81% | 0.10% | 0.15% |
| reference_validation | control | 243 | 56.38% | 58.85% | 0.06% | 0.11% |
| external | selected | 192 | 57.29% | 59.90% | 0.19% | 0.16% |
| external | control | 412 | 53.64% | 56.31% | 0.09% | 0.09% |
| august | selected | 7 | 71.43% | 42.86% | -0.11% | -0.04% |
| august | control | 11 | 63.64% | 45.45% | -0.07% | -0.04% |

## Executable net RR 1:1 diagnostic

LONG next1H open; SL=LOW_REJECT candle low; TP raw distance=risk+0.30%; fee0.15%; max hold6H; same-hour ambiguity adverse-first.

| Partition | Rule | N | TP | SL | TIME | Decisive WR | Net+ | PnL | Exp/trade | Median risk | Avg target |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | selected | 297 | 97 | 200 | 0 | 32.66% | 32.66% | $-175.45 | $-0.591 | 0.31% | 0.69% |
| development | control | 567 | 164 | 403 | 0 | 28.92% | 28.92% | $-678.75 | $-1.197 | 0.38% | 0.79% |
| reference_validation | selected | 148 | 38 | 110 | 0 | 25.68% | 25.68% | $-148.93 | $-1.006 | 0.24% | 0.63% |
| reference_validation | control | 243 | 67 | 176 | 0 | 27.57% | 27.57% | $-283.76 | $-1.168 | 0.32% | 0.70% |
| external | selected | 192 | 57 | 135 | 0 | 29.69% | 29.69% | $-217.28 | $-1.132 | 0.41% | 0.83% |
| external | control | 412 | 123 | 289 | 0 | 29.85% | 29.85% | $-756.45 | $-1.836 | 0.58% | 1.08% |
| august | selected | 7 | 2 | 5 | 0 | 28.57% | 28.57% | $-4.65 | $-0.664 | 0.15% | 0.45% |
| august | control | 11 | 2 | 9 | 0 | 18.18% | 18.18% | $-14.02 | $-1.274 | 0.17% | 0.51% |

## External selected-leaf chronological blocks

| Block | N | +1H | +3H | Avg3H |
|---|---:|---:|---:|---:|
| B1 | 48 | 56.25% | 54.17% | 0.22% |
| B2 | 48 | 60.42% | 64.58% | 0.31% |
| B3 | 48 | 50.00% | 52.08% | 0.09% |
| B4 | 48 | 62.50% | 68.75% | 0.15% |

## Selected leaf by clock

### Reference validation

| UTC/WIB | N | +3H | Avg3H |
|---|---:|---:|---:|
| 04:00 / 11:00 | 35 | 54.29% | 0.13% |
| 08:00 / 15:00 | 36 | 55.56% | -0.06% |
| 18:00 / 01:00 | 43 | 74.42% | 0.14% |
| 19:00 / 02:00 | 34 | 55.88% | 0.19% |

### External 2020-2021

| UTC/WIB | N | +3H | Avg3H |
|---|---:|---:|---:|
| 04:00 / 11:00 | 64 | 51.56% | 0.04% |
| 08:00 / 15:00 | 44 | 56.82% | 0.11% |
| 18:00 / 01:00 | 49 | 67.35% | 0.41% |
| 19:00 / 02:00 | 35 | 68.57% | 0.27% |

**LR1_STRUCTURE_SUPPORTED: FAIL**
**LR1_80_CANDIDATE: FAIL**

The leaf was selected on reference-development only. Validation, untouched 2020-2021, and August were not used to choose the structural thresholds. No post-result tree/feature/time rescue.
