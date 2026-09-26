# SOL Indicator Relationship Discovery — Stage 3 Result

**Research only. Live BabaBot untouched.**

## Data integrity

- Frozen end-exclusive: **2026-09-26 00:00:00+00:00**.
- SOLUSDT raw 5m: **396,000 rows**, coverage **100.0000%**, detected gaps **0**.
- Raw range: **2022-12-20 00:00:00+00:00 -> 2026-09-24 23:55:00+00:00**.
- OI metrics rows: **395,849**; range **2022-12-20 00:00:00+00:00 -> 2026-09-24 23:55:00+00:00**.
- Funding rows: **4,053**; range **2022-12-20 00:00:00.005000+00:00 -> 2026-08-31 16:00:00.001000+00:00**.
- Stage 3A decision rows: **130,848**.

## Stage 3A — frozen single-indicator classification

| Feature | Class | Dev delta-D | 2025 delta-D | 2026 delta-D | Same sign |
|---|---|---:|---:|---:|---:|
| quotevol_15m | NON_INFORMATIVE | 0.1% | 1.4% | -1.5% | NO |
| quotevol_ratio_1h | NON_INFORMATIVE | 0.2% | -0.4% | 1.4% | NO |
| quotevol_z_24h | UNSTABLE_OR_WEAK | -3.2% | -1.1% | 5.3% | NO |
| trades_ratio_1h | NON_INFORMATIVE | -0.0% | 0.2% | -0.4% | NO |
| taker_buy_ratio_15m | NON_INFORMATIVE | -0.4% | -0.5% | 0.0% | NO |
| taker_imb_15m | NON_INFORMATIVE | -0.4% | -0.5% | 0.0% | NO |
| taker_imb_1h | UNSTABLE_OR_WEAK | 4.2% | -0.7% | 0.2% | NO |
| taker_imb_change_1h | UNSTABLE_OR_WEAK | -2.6% | -2.4% | 0.0% | NO |
| loc_24h | REPLICATED_DIRECTIONAL | 9.7% | 5.1% | 13.2% | YES |
| dist_high_24h | REPLICATED_DIRECTIONAL | 7.0% | 3.7% | 7.0% | YES |
| dist_low_24h | REPLICATED_DIRECTIONAL | 6.1% | 5.0% | 9.2% | YES |
| breakout_up_24h | UNSTABLE_OR_WEAK | -4.8% | 4.5% | 4.9% | NO |
| breakout_down_24h | UNSTABLE_OR_WEAK | 7.0% | -16.8% | -12.1% | NO |
| oi_value | UNSTABLE_OR_WEAK | -1.8% | -35.0% | -9.9% | YES |
| oi_chg_15m | REPLICATED_DIRECTIONAL | 14.9% | 40.1% | 38.3% | YES |
| oi_chg_1h | REPLICATED_DIRECTIONAL | 6.8% | 22.8% | 20.6% | YES |
| oi_chg_4h | REPLICATED_DIRECTIONAL | 5.9% | 16.9% | 3.3% | YES |
| funding_rate | UNSTABLE_OR_WEAK | -6.4% | 2.9% | 11.9% | NO |
| funding_z_30 | UNSTABLE_OR_WEAK | -1.3% | 5.3% | 9.4% | NO |
| funding_change | UNSTABLE_OR_WEAK | -3.7% | -4.7% | 3.9% | NO |

Replicated directional: **6 / 20**. Unstable/weak: **9**. Non-informative: **5**.

Full frozen-bucket detail is persisted in SOL_INDICATOR_RELATIONSHIP_S3A_BUCKETS.csv.

## Stage 3B — 5m impulse -> expansion

Cumulative impulse thresholds: 0.50%, 0.75%, 1.00%, 1.50%, 2.00%, 3.00%.

| Partition | Dir | 5m impulse >= | N | +1% further in 4h | Opposite 1% reversal | Median 4h MFE |
|---|---|---:|---:|---:|---:|---:|
| development | UP | 0.50% | 7470 | 67.7% | 66.8% | 1.66% |
| validation_2025 | UP | 0.50% | 2849 | 64.2% | 65.5% | 1.48% |
| validation_2026 | UP | 0.50% | 1168 | 55.3% | 59.9% | 1.19% |
| development | UP | 0.75% | 2766 | 71.7% | 71.7% | 1.90% |
| validation_2025 | UP | 0.75% | 1000 | 70.3% | 70.1% | 1.74% |
| validation_2026 | UP | 0.75% | 402 | 58.7% | 65.7% | 1.32% |
| development | UP | 1.00% | 1236 | 75.9% | 74.1% | 2.16% |
| validation_2025 | UP | 1.00% | 447 | 72.7% | 72.5% | 1.87% |
| validation_2026 | UP | 1.00% | 171 | 62.0% | 70.2% | 1.32% |
| development | UP | 1.50% | 361 | 79.5% | 75.6% | 2.99% |
| validation_2025 | UP | 1.50% | 129 | 78.3% | 78.3% | 2.39% |
| validation_2026 | UP | 1.50% | 44 | 63.6% | 77.3% | 1.51% |
| development | UP | 2.00% | 142 | 85.2% | 83.1% | 3.39% |
| validation_2025 | UP | 2.00% | 48 | 83.3% | 77.1% | 3.61% |
| validation_2026 | UP | 2.00% | 14 | 78.6% | 71.4% | 2.04% |
| development | UP | 3.00% | 47 | 87.2% | 89.4% | 3.11% |
| validation_2025 | UP | 3.00% | 14 | 78.6% | 78.6% | 5.73% |
| validation_2026 | UP | 3.00% | 4 | 75.0% | 75.0% | 2.21% |
| development | DOWN | 0.50% | 7227 | 66.1% | 70.2% | 1.56% |
| validation_2025 | DOWN | 0.50% | 2748 | 66.0% | 65.9% | 1.58% |
| validation_2026 | DOWN | 0.50% | 1080 | 59.5% | 59.7% | 1.28% |
| development | DOWN | 0.75% | 2525 | 69.9% | 74.7% | 1.79% |
| validation_2025 | DOWN | 0.75% | 886 | 70.0% | 74.3% | 1.89% |
| validation_2026 | DOWN | 0.75% | 330 | 64.8% | 67.9% | 1.47% |
| development | DOWN | 1.00% | 1011 | 71.7% | 80.4% | 2.01% |
| validation_2025 | DOWN | 1.00% | 374 | 73.3% | 79.7% | 2.32% |
| validation_2026 | DOWN | 1.00% | 131 | 68.7% | 69.5% | 1.59% |
| development | DOWN | 1.50% | 257 | 70.0% | 87.5% | 1.83% |
| validation_2025 | DOWN | 1.50% | 108 | 81.5% | 84.3% | 3.22% |
| validation_2026 | DOWN | 1.50% | 29 | 55.2% | 75.9% | 1.26% |
| development | DOWN | 2.00% | 106 | 68.9% | 90.6% | 2.06% |
| validation_2025 | DOWN | 2.00% | 54 | 79.6% | 90.7% | 3.67% |
| validation_2026 | DOWN | 2.00% | 14 | 57.1% | 71.4% | 1.43% |
| development | DOWN | 3.00% | 37 | 70.3% | 97.3% | 1.96% |
| validation_2025 | DOWN | 3.00% | 14 | 64.3% | 100.0% | 3.07% |
| validation_2026 | DOWN | 3.00% | 3 | 66.7% | 66.7% | 6.96% |

A 4h de-overlapped sensitivity table is included in SOL_INDICATOR_RELATIONSHIP_S3B_IMPULSE_EXPANSION.csv.

## Stage 3 verdict

At least one preregistered single indicator meets the frozen cross-partition directional-replication gate. Stage 4 may test interactions, but Stage 3 anatomy is not a deployable signal.

**Status: SOL_INDICATOR_RELATIONSHIP_S3_COMPLETED_WITH_REPLICATED_SINGLE_INDICATORS**

Stage 3B is descriptive expansion anatomy. It does not change the frozen Stage 2 primary target or authorize a 5m impulse trading rule.
