# B27CW — BTC 24H F05 SHORT Clock-Specific Full-Loser Threshold — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** B27CV PLUS15 model reproduced exactly: AUC 0.8860088365; global SAFE threshold 0.6079191233; global development SAFE flags 28 BAD / 9 GOOD; 652 trades / 78 BAD / 348 GOOD / 226 OTHER.

**Anatomy calibration only:** trading WR/PF/expectancy/PnL are N/A. Model/features are unchanged; only development-selected cutoff differs by clock.

## Six clocks — SAFE threshold map

| WIB | Threshold | Dev BAD caught | Dev GOOD cut | External BAD / GOOD | Validation BAD / GOOD |
|---|---:|---:|---:|---:|---:|
| 07-11 | **0.533** | 7/7 (100.0%) | 3/30 (10.0%) | 0/2 (0.0%) / 2/23 (8.7%) | 3/4 (75.0%) / 6/23 (26.1%) |
| 11-15 | **0.844** | 1/1 (100.0%) | 0/10 (0.0%) | 0/2 (0.0%) / 0/18 (0.0%) | 0/2 (0.0%) / 0/8 (0.0%) |
| 15-19 | **0.737** | 3/8 (37.5%) | 2/26 (7.7%) | 4/7 (57.1%) / 4/19 (21.1%) | 1/2 (50.0%) / 3/10 (30.0%) |
| 19-23 | **0.608** | 16/18 (88.9%) | 2/49 (4.1%) | 0/2 (0.0%) / 4/18 (22.2%) | 2/5 (40.0%) / 5/28 (17.9%) |
| 23-03 | **+inf** | 0/2 (0.0%) | 0/29 (0.0%) | 0/6 (0.0%) / 0/10 (0.0%) | 0/0 (-) / 0/11 (0.0%) |
| 03-07 | **+inf** | 0/2 (0.0%) | 0/15 (0.0%) | 0/4 (0.0%) / 0/10 (0.0%) | 0/4 (0.0%) / 0/11 (0.0%) |

## SAFE map vs frozen global B27CV SAFE

| Scope | BAD capture global→clock | GOOD sacrifice global→clock | Flag precision clock |
|---|---:|---:|---:|
| development | 73.7% → **71.1%** | 5.7% → **4.4%** | 79.4% |
| external | 39.1% → **17.4%** | 14.3% → **10.2%** | 28.6% |
| reference_validation | 47.1% → **35.3%** | 16.5% → **15.4%** | 30.0% |
| POOLED_REUSED_EXTVAL | 42.5% → **25.0%** | 15.3% → **12.7%** | 29.4% |
| POOLED_MAJOR | 57.7% → **47.4%** | 10.9% → **8.9%** | 54.4% |

## AGGRESSIVE development thresholds (secondary)

| WIB | Threshold | BAD capture | GOOD sacrifice |
|---|---:|---:|---:|
| 07-11 | 0.533 | 100.0% | 10.0% |
| 11-15 | 0.844 | 100.0% | 0.0% |
| 15-19 | 0.653 | 62.5% | 11.5% |
| 19-23 | 0.608 | 88.9% | 4.1% |
| 23-03 | +inf | 0.0% | 0.0% |
| 03-07 | 0.410 | 100.0% | 13.3% |

**Frozen verdict: `B27CW_CLOCK_THRESHOLD_NOT_SUPPORTED`.**

External/reference_validation are reused-data confirmation, not untouched OOS. No economic abort simulation or live BBC change is authorized by this experiment.
