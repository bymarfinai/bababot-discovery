# B27AA — London -> New York Early F85 Rejection / Reclaim Filter — Result

5m rows: **698,112**; coverage: **100.0000%**.

**Audit status: PASS.** B27W F85 touch opportunities are frozen; B27AA only changes blind F85 execution into the earliest causal 5m reclaim entry. Exit economics are frozen to E20 + F35 close-invalidation.

## Results

| Partition | Variant | Opportunities | Confirmed | Executed | Exec rate | Same-bar | Later | TP rate | WR | PF | Net exp | Total net | H2 before exit | Median entry f | Median RR |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | EARLY_RECLAIM | 46 | 43 | 43 | 93.5% | 27 | 16 | 69.8% | 76.7% | 2.89 | $1.62 | $69.65 | 90.7% | 0.886 | 0.58 |
| external | SAME_BAR_REJECTION | 46 | 27 | 27 | 58.7% | 27 | 0 | 66.7% | 74.1% | 2.18 | $1.34 | $36.23 | 88.9% | 0.887 | 0.58 |
| development | EARLY_RECLAIM | 72 | 54 | 54 | 75.0% | 30 | 24 | 66.7% | 66.7% | 1.08 | $0.14 | $7.44 | 81.5% | 0.879 | 0.61 |
| development | SAME_BAR_REJECTION | 72 | 30 | 30 | 41.7% | 30 | 0 | 66.7% | 66.7% | 1.17 | $0.31 | $9.16 | 76.7% | 0.877 | 0.61 |
| reference_validation | EARLY_RECLAIM | 31 | 21 | 21 | 67.7% | 11 | 10 | 71.4% | 71.4% | 0.98 | $-0.03 | $-0.59 | 76.2% | 0.916 | 0.50 |
| reference_validation | SAME_BAR_REJECTION | 31 | 11 | 11 | 35.5% | 11 | 0 | 90.9% | 90.9% | 6.23 | $1.49 | $16.41 | 90.9% | 0.917 | 0.50 |
| august | EARLY_RECLAIM | 3 | 3 | 3 | 100.0% | 1 | 2 | 66.7% | 100.0% | inf | $1.44 | $4.31 | 100.0% | 0.897 | 0.55 |
| august | SAME_BAR_REJECTION | 3 | 1 | 1 | 33.3% | 1 | 0 | 0.0% | 100.0% | inf | $2.65 | $2.65 | 100.0% | 0.897 | 0.55 |

## Frozen EARLY_RECLAIM screen

- external: N=43, WR=76.7%, PF=2.89, exp=$1.62 -> PASS
- development: N=54, WR=66.7%, PF=1.08, exp=$0.14 -> FAIL
- reference_validation: N=21, WR=71.4%, PF=0.98, exp=$-0.03 -> FAIL

**Overall: NO_PASS.**

## Interpretation guardrail

B27AA does not retune F85, E20, or F35 after seeing these results. SAME_BAR_REJECTION is a diagnostic subset only. If EARLY_RECLAIM fails the frozen major-partition gate, this experiment does not authorize F84/F86, candle-shape thresholds, or extra indicator mining.

Research only; live BBC unchanged.
