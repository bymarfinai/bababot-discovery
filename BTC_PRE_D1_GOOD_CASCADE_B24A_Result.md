# BTC Pre-D1 Good Cascade B24A — Result

5m source rows: **698,112**; coverage: **100.0000%**

Question: at the first causal 4H-bull activation, while Daily bull is still OFF, can already-visible state geometry identify events that later become a Daily-bull cascade AND have positive 72h return?

No candle-survival counting rule is used. Features are current causal SMA-state geometry only.

## Primary real-time test — untouched reference validation

- Eligible pre-D1 4H events: **1,140**
- GOOD_D1_72H events: **143**
- Baseline success prevalence: **12.54%**
- ROC AUC: **0.871**
- Average precision: **0.412** (3.28x baseline)

| Highest detector scores | N | Successful | Precision | Recall of all successes | Lift vs baseline |
|---|---:|---:|---:|---:|---:|
| Top 5% | 57 | 6 | 10.53% | 4.20% | 0.84x |
| Top 10% | 114 | 35 | 30.70% | 24.48% | 2.45x |
| Top 20% | 228 | 123 | 53.95% | 86.01% | 4.30x |
| Top 30% | 342 | 123 | 35.96% | 86.01% | 2.87x |

## Secondary forensic view — old Daily-stage cohort

This section is hindsight-only and is NOT a trading accuracy claim.

- Daily-stage events still eligible at the pre-D1 4H anchor: **161**
- Positive 72h: **143**
- Non-positive 72h: **18**
- Positive rate: **88.82%**
- Detector AUC inside this hindsight cohort: **0.872**

## Strongest standardized model coefficients

| Feature | Coefficient |
|---|---:|
| h4_price_pos | -2.1029 |
| m15_slow_gap | 1.9308 |
| d1_slow_gap | 1.8650 |
| h4_fast_gap | 1.7959 |
| h1_bull | 1.1036 |
| h1_fast_gap | -0.9711 |
| h1_slow_gap | 0.8207 |
| d1_fast_gap | 0.7822 |

## Frozen gates

- B24A_USEFUL_PRE_D1_DETECTOR: **PASS**
- B24A_HIGH_PRECISION_CLUE: **PASS**

If the gates fail, this experiment is not useful as a real-time pre-D1 trading detector.

Research only; live BBC unchanged.
