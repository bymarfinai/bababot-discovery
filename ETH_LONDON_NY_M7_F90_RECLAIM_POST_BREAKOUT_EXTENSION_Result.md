# ETH London -> New York M7 F90 Early-Reclaim Post-Breakout Extension — Result

ETH raw 5m coverage: **100.0000%**.

Frozen cohort: **M5 F90 EARLY_RECLAIM executed trades that reached strict completed 5m breakout close > H**.

- Confirmed-breakout cohort rows: **77**.
- Identity / chronology / extension monotonicity audit: **PASS**.
- Causal extension scoring starts on the next raw 5m bar after breakout-bar completion; same-breakout-bar overshoot is telemetry only.

## Causal extension ladder

| Partition | N BO | E05 | E10 | E15 | E20 | E25 | E30 | Median max ext |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 32 | 93.8% | 93.8% | 93.8% | 81.2% | 71.9% | 68.8% | 0.49R |
| development | 32 | 93.8% | 90.6% | 84.4% | 78.1% | 75.0% | 75.0% | 0.54R |
| reference_validation | 13 | 92.3% | 92.3% | 92.3% | 92.3% | 69.2% | 53.8% | 0.36R |
| august | 0 | - | - | - | - | - | - | -R |
| POOLED_MAJOR | 77 | 93.5% | 92.2% | 89.6% | 81.8% | 72.7% | 68.8% | 0.47R |

## Conditional continuation and timing — POOLED_MAJOR

| Stage | Causal hit | Conditional from prior | Median minutes after BO completion | Same-BO-bar overshoot telemetry |
|---|---:|---:|---:|---:|
| E05 | 93.5% | - | 0.0m | 74.0% |
| E10 | 92.2% | 98.6% | 0.0m | 54.5% |
| E15 | 89.6% | 97.2% | 0.0m | 31.2% |
| E20 | 81.8% | 91.3% | 0.0m | 19.5% |
| E25 | 72.7% | 88.9% | 10.0m | 10.4% |
| E30 | 68.8% | 94.6% | 15.0m | 7.8% |

## Frozen structural target screen

- Major-partition confirmed-breakout adequacy >=10 each: **PASS** ({'external': 32, 'development': 32, 'reference_validation': 13}).
- E05: external=93.8%, development=93.8%, reference_validation=92.3%; pooled=93.5% -> **STRUCTURAL_TARGET_CANDIDATE**
- E10: external=93.8%, development=90.6%, reference_validation=92.3%; pooled=92.2% -> **STRUCTURAL_TARGET_CANDIDATE**
- E15: external=93.8%, development=84.4%, reference_validation=92.3%; pooled=89.6% -> **STRUCTURAL_TARGET_CANDIDATE**
- E20: external=81.2%, development=78.1%, reference_validation=92.3%; pooled=81.8% -> **NO**
- E25: external=71.9%, development=75.0%, reference_validation=69.2%; pooled=72.7% -> **NO**
- E30: external=68.8%, development=75.0%, reference_validation=53.8%; pooled=68.8% -> **NO**

**Supported structural target family: E05, E10, E15.**

**Status: ETH_LONDON_NY_M7_POST_BREAKOUT_TARGET_FAMILY_SUPPORTED**

M7 is reward-side structural calibration only. No TP, stop, PnL, PF, runner, or live configuration is promoted by this result.