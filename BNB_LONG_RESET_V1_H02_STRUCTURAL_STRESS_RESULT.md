# BNB LONG Reset V1 — H02 Structural Stress / Secondary Confirmation

**Verdict: STRUCTURAL_PASS_WITH_SECONDARY**

- Habitat: **02:00–03:00 WIB**
- Frozen primary: **`rv_ratio_60_240__HIGH`**
- Selected secondary: **`efficiency_60m__HIGH`**
- Development: **2022–2024 WIB**
- OOS: **SEALED — not downloaded / not evaluated**
- H03+ scanning: **STOPPED**

## Mandatory stress gates

| Stress | Result |
|---|---|
| FIRST_PER_DAY overlap reduction | PASS |
| DAILY_MEAN overlap reduction | PASS |
| Day-cluster bootstrap 95% CI lower > 0 | PASS |
| HIGH-boundary sensitivity | PASS (5/5 supportive) |
| Causal percentile-window sensitivity | PASS (4/4 supportive) |
| Quarter consistency | PASS (9/12 positive mean; 9/12 PF>1) |

## Overlap / pseudo-sample stress

| Reduction | N days | WR | Mean | PF | Raw $/day @ $500 | Raw DD @ $500 |
|---|---:|---:|---:|---:|---:|---:|
| FIRST_PER_DAY | 590 | 55.42% | 0.0523% | 1.208 | $+0.26 | $-36.04 |
| DAILY_MEAN | 590 | 58.81% | 0.0771% | 1.352 | $+0.39 | $-29.04 |

Day-cluster bootstrap (10,000 resamples, seed 20260913) 95% CI mean: **0.0123% to 0.1419%**.

## Boundary sensitivity

| HIGH cutoff | N | WR | Mean | PF | Gate |
|---:|---:|---:|---:|---:|---|
| 0.600 | 1,712 | 57.30% | 0.0709% | 1.305 | PASS |
| 0.625 | 1,591 | 57.76% | 0.0751% | 1.325 | PASS |
| 0.667 | 1,448 | 57.32% | 0.0691% | 1.291 | PASS |
| 0.700 | 1,317 | 57.48% | 0.0693% | 1.289 | PASS |
| 0.750 | 1,109 | 57.80% | 0.0666% | 1.271 | PASS |

## Percentile-window sensitivity

| Window | N | WR | Mean | PF | Supportive years | Gate |
|---:|---:|---:|---:|---:|---:|---|
| 40 | 1,461 | 57.36% | 0.0728% | 1.302 | 3/3 | PASS |
| 60 | 1,448 | 57.32% | 0.0691% | 1.291 | 3/3 | PASS |
| 90 | 1,442 | 57.63% | 0.0781% | 1.331 | 3/3 | PASS |
| 120 | 1,432 | 57.68% | 0.0775% | 1.328 | 3/3 | PASS |

## Quarter consistency

| Quarter | N | WR | Mean | PF |
|---|---:|---:|---:|---:|
| 2022Q1 | 60 | 48.33% | 0.0919% | 1.230 |
| 2022Q2 | 136 | 64.71% | 0.2036% | 1.873 |
| 2022Q3 | 130 | 61.54% | 0.1375% | 1.546 |
| 2022Q4 | 128 | 53.91% | -0.1489% | 0.572 |
| 2023Q1 | 117 | 52.99% | 0.1058% | 1.421 |
| 2023Q2 | 119 | 56.30% | -0.0379% | 0.844 |
| 2023Q3 | 126 | 59.52% | 0.0403% | 1.322 |
| 2023Q4 | 132 | 64.39% | 0.1565% | 2.486 |
| 2024Q1 | 129 | 58.91% | 0.1409% | 1.748 |
| 2024Q2 | 121 | 52.89% | -0.0120% | 0.960 |
| 2024Q3 | 136 | 58.82% | 0.1223% | 1.677 |
| 2024Q4 | 114 | 48.25% | 0.0089% | 1.028 |

## Selected secondary confirmation

Three secondaries passed the preregistered gate: **`efficiency_60m__HIGH`**, `lower_wick_pressure_15m__HIGH`, and `drive_15m__HIGH`. Deterministic ranking selects **`efficiency_60m__HIGH`** because it has the highest minimum yearly mean return.

| Metric | Primary only | Primary + secondary |
|---|---:|---:|
| N | 1,448 | 483 |
| Approx signals/week | 9.25 | 3.09 |
| WR | 57.32% | **60.25%** |
| Mean return/signal | 0.0691% | **0.1470%** |
| PF | 1.291 | **1.642** |
| Raw $/signal @ $500 | $+0.35 | **$+0.74** |
| Raw total equivalent | $+499.93 | **$+355.02** |
| Avg winning signal @ $500 | $+2.67 | **$+3.12** |
| Avg losing signal @ $500 | $-2.78 | **$-2.88** |
| Raw max DD @ $500 | $-144.25 | **$-75.88** |
| Max loss streak | 12 | **8** |

### Cross-year primary + secondary

| Year | N | WR | Mean | PF | Raw $/signal @ $500 | Raw total | DD @ $500 | LS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 172 | 56.98% | 0.0866% | 1.296 | $+0.43 | $+74.47 | $-57.63 | 8 |
| 2023 | 172 | 58.72% | 0.0692% | 1.347 | $+0.35 | $+59.47 | $-75.88 | 6 |
| 2024 | 139 | 66.19% | 0.3181% | 2.705 | $+1.59 | $+221.08 | $-21.23 | 3 |

### Quarter-hour anchors primary + secondary

| Entry WIB | N | WR | Mean | PF | Raw $/signal | Gate |
|---|---:|---:|---:|---:|---:|---|
| 02:00 | 110 | 60.91% | 0.1371% | 1.641 | $+0.69 | PASS |
| 02:15 | 120 | 51.67% | 0.0894% | 1.334 | $+0.45 | FAIL |
| 02:30 | 130 | 66.15% | 0.1782% | 1.978 | $+0.89 | PASS |
| 02:45 | 123 | 61.79% | 0.1792% | 1.706 | $+0.90 | PASS |

## Locked next state

- Freeze **primary + secondary** exactly as above.
- Do not reopen H03 while this promoted structure is alive.
- Next stage: **untouched OOS 2025-01-01 through 2026-07-30** with zero retuning.
- Trade construction / TP / SL / fees / slippage / leverage remain out of scope until OOS passes.

Research/shadow only.
