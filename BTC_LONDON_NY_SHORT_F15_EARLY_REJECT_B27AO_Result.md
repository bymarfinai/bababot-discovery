# B27AO — BTC London->NY SHORT F15 Early-Reject Confirmation Audit — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** Independently discovered B27AK F15 fill/touch/H2 identities reproduced exactly before confirmation economics were interpreted.

Fixed economics: E20_DOWN target + D50/F65 completed-close invalidation. No regime gate or exit re-sweep.

## Confirmation economics

| Rule | Partition | Opps | Confirmed | Executed | TP rate | WR | PF | Exp/trade $ | Total $ | Median entry frac | Median nominal RR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F15 | external | 50 | 50 (100.0%) | 50 | 56.0% | 58.0% | 1.544 | 0.818 | 40.886 | 0.150 | 0.700 |
| BLIND_F15 | development | 79 | 79 (100.0%) | 79 | 59.5% | 59.5% | 0.831 | -0.285 | -22.549 | 0.150 | 0.700 |
| BLIND_F15 | reference_validation | 34 | 34 (100.0%) | 34 | 50.0% | 52.9% | 0.553 | -0.882 | -30.002 | 0.150 | 0.700 |
| BLIND_F15 | august | 1 | 1 (100.0%) | 1 | 0.0% | 0.0% | 0.000 | -2.420 | -2.420 | 0.150 | 0.700 |
| EARLY_REJECT | external | 50 | 42 (84.0%) | 42 | 61.9% | 64.3% | 1.406 | 0.587 | 24.649 | 0.108 | 0.569 |
| EARLY_REJECT | development | 79 | 56 (70.9%) | 56 | 58.9% | 58.9% | 0.872 | -0.200 | -11.216 | 0.119 | 0.600 |
| EARLY_REJECT | reference_validation | 34 | 22 (64.7%) | 22 | 50.0% | 50.0% | 0.521 | -0.960 | -21.117 | 0.132 | 0.641 |
| EARLY_REJECT | august | 1 | 1 (100.0%) | 1 | 0.0% | 0.0% | 0.000 | -2.726 | -2.726 | 0.059 | 0.438 |
| SAME_BAR_REJECTION | external | 50 | 25 (50.0%) | 25 | 60.0% | 64.0% | 1.109 | 0.157 | 3.932 | 0.108 | 0.568 |
| SAME_BAR_REJECTION | development | 79 | 25 (31.6%) | 25 | 60.0% | 60.0% | 0.772 | -0.331 | -8.264 | 0.118 | 0.598 |
| SAME_BAR_REJECTION | reference_validation | 34 | 12 (35.3%) | 12 | 41.7% | 41.7% | 0.208 | -1.930 | -23.155 | 0.130 | 0.635 |
| SAME_BAR_REJECTION | august | 1 | 1 (100.0%) | 1 | 0.0% | 0.0% | 0.000 | -2.726 | -2.726 | 0.059 | 0.438 |

## Primary gate

EARLY_REJECT requires in EACH external/development/reference_validation: >=30 executed, WR>=70%, PF>=1.20, expectancy>0.

**Status: B27AO_EARLY_REJECT_NO_PASS.**

SAME_BAR_REJECTION remains diagnostic only. No F14/F16, candle threshold, regime filter, new stop, target, or runner is introduced.

Research only; live BBC unchanged.
