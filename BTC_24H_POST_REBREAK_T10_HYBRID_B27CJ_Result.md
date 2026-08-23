# B27CJ — BTC 24H Post-Rebreak T10 Profit-Lock Hybrid — Result

5m rows: **698,112**; coverage **100.0000%**.

**Audit status: PASS.** B27CI eligible identity reproduced: external 147 / development 233 / validation 133 / pooled OOS 280 / pooled major 513; exact T10 reaches external 96 / development 172 / validation 98 / pooled major 366.

TP-management anatomy only. Trading WR/PF/PnL/expectancy/SL are **N/A**. T10 is frozen; no alternate milestone or pivot width was searched.

## Fixed T10 vs hybrid — major partitions

| Scope | Eligible | T10 reach | Hybrid valid | Preserve >=T10 | Mean exit ext | Median exit ext | Mean delta vs fixed | Median peak | Median capture | Median giveback | Median ratchets | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | 147 | 96 (65.3%) | 96 | 62.5% | 17.0% | 10.0% | 7.0% | 52.4% | 19.0% | 42.3% | 0.00 | 5.00m |
| development | 233 | 172 (73.8%) | 172 | 54.1% | 10.8% | 10.0% | 0.8% | 51.7% | 13.7% | 42.9% | 0.00 | 5.00m |
| reference_validation | 133 | 98 (73.7%) | 98 | 62.2% | 16.7% | 10.0% | 6.7% | 42.3% | 20.7% | 33.9% | 0.00 | 5.00m |
| POOLED_OOS | 280 | 194 (69.3%) | 194 | 62.4% | 16.8% | 10.0% | 6.8% | 47.4% | 19.3% | 38.5% | 0.00 | 5.00m |
| POOLED_MAJOR | 513 | 366 (71.3%) | 366 | 58.5% | 14.0% | 10.0% | 4.0% | 50.3% | 16.9% | 39.8% | 0.00 | 5.00m |

## Hybrid exit anatomy — major partitions

| Scope | T10 ceiling | Structural ceiling | Open/gap | Time | Touch-bar close > T10 |
|---|---:|---:|---:|---:|---:|
| external | 44 | 13 | 36 | 3 | 36.5% |
| development | 66 | 19 | 76 | 11 | 45.9% |
| reference_validation | 46 | 11 | 37 | 4 | 37.8% |
| POOLED_OOS | 90 | 24 | 73 | 7 | 37.1% |
| POOLED_MAJOR | 156 | 43 | 149 | 18 | 41.3% |

## Six-clock diagnostics — pooled major

| UTC block | Eligible | T10 reach | Preserve | Mean exit ext | Median exit ext | Mean delta | Median peak | Median hold |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 00-04 | 80 | 62 (77.5%) | 62.9% | 9.6% | 10.0% | -0.4% | 49.6% | 5.00m |
| 04-08 | 86 | 57 (66.3%) | 42.1% | 17.0% | 8.4% | 7.0% | 30.4% | 5.00m |
| 08-12 | 84 | 64 (76.2%) | 64.1% | 25.8% | 10.0% | 15.8% | 57.6% | 5.00m |
| 12-16 | 114 | 91 (79.8%) | 63.7% | 10.4% | 10.0% | 0.4% | 73.2% | 5.00m |
| 16-20 | 84 | 52 (61.9%) | 53.8% | 9.1% | 10.0% | -0.9% | 47.4% | 5.00m |
| 20-00 | 65 | 40 (61.5%) | 60.0% | 12.3% | 10.0% | 2.3% | 47.5% | 5.00m |

## Frozen gate

- sample gate: **PASS**
- median hybrid exit >= T10 in every major partition: **PASS**
- mean hybrid exit > fixed T10 in every major partition: **PASS**
- T10 preservation >=80% in every major partition: **FAIL**
- pooled-major mean extension > fixed T10: **PASS**

**Frozen verdict: `B27CJ_T10_HYBRID_NOT_SUPPORTED`.**

This verdict concerns TP management only. No SL/economic inference is authorized by B27CJ. Research only; live BBC unchanged.
