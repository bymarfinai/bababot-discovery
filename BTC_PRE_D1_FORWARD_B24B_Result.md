# BTC Pre-D1 Forward B24B — Result

5m source rows: **698,112**; coverage: **100.0000%**

B24B corrects B24A: the outcome clock starts at the causal 4H detector time, not at the earlier 5m seed.

## Primary real-time test — untouched reference validation

- Eligible pre-D1 4H events with full next-72h data: **1,140**
- GOOD_D1_FWD72 events: **145**
- Baseline prevalence: **12.72%**
- ROC AUC: **0.754**
- Average precision: **0.255** (2.01x baseline)

| Highest detector scores | N | Successful | Precision | Recall | Lift vs baseline |
|---|---:|---:|---:|---:|---:|
| Top 5% | 57 | 5 | 8.77% | 3.45% | 0.69x |
| Top 10% | 114 | 22 | 19.30% | 15.17% | 1.52x |
| Top 20% | 228 | 44 | 19.30% | 30.34% | 1.52x |
| Top 30% | 342 | 53 | 15.50% | 36.55% | 1.22x |

## Eventual-Daily cohort — future outcome from the 4H decision time

- Eventual Daily events: **161**
- Price positive over NEXT 72h from 4H anchor: **145**
- Non-positive: **16**
- Future-positive rate: **90.06%**
- Detector AUC inside this eventual-Daily cohort: **1.000**

## Strongest standardized coefficients

| Feature | Coefficient |
|---|---:|
| m15_slow_gap | 3.5714 |
| h4_fast_gap | 2.9251 |
| d1_slow_gap | 1.8889 |
| h4_price_pos | -1.7000 |
| h1_price_pos | -1.6683 |
| h1_fast_gap | -1.6475 |
| d1_fast_gap | 1.2533 |
| d1_price_pos | -1.1371 |

## Frozen gates

- B24B_USEFUL_PRE_D1_FORWARD_DETECTOR: **PASS**
- B24B_HIGH_PRECISION_CLUE: **FAIL**

B24B is the fair forward test. B24A must not be used to claim trading performance.

Research only; live BBC unchanged.
