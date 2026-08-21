# BTC MTF Bull Cascade B21 — Result

**Implementation revision:** `B21_V1_R2_RESOLUTION_SAFE`  
**Supersedes:** first run `32478430958`, invalidated only for timestamp-unit lookup implementation.

5m rows: **698,112**; source coverage: **100.0000%**
Data: **2020-01-01 00:00:00+00:00 → 2026-08-20 23:55:00+00:00**

Frozen bull state: `SMA7 > SMA25 > SMA99 AND close > SMA25`, observable only after each timeframe candle closes.

## Ordered cascade stage by partition

| Partition | 5m seeds | S0 5m | S1 15m | S2 1h | S3 4h | S4 1d | Fresh seeds |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 5505 | 0 | 821 | 2153 | 2144 | 387 | 1267 |
| development | 7974 | 0 | 1339 | 3472 | 2841 | 322 | 2394 |
| reference_validation | 4017 | 0 | 606 | 1801 | 1411 | 199 | 1339 |
| august | 155 | 0 | 28 | 34 | 93 | 0 | 51 |

## 72h outcome by deepest ordered stage — ALL seeds

| Partition | Stage | N72 | Positive 72h | Median 72h ret | Median MFE | Median MAE | MFE≥5% |
|---|---|---:|---:|---:|---:|---:|---:|
| external | S0_5M | 0 | - | - | - | - | - |
| external | S1_15M | 821 | 42.5% | -1.0% | 2.9% | -4.9% | 30.9% |
| external | S2_1H | 2153 | 46.1% | -0.5% | 3.3% | -4.2% | 35.0% |
| external | S3_4H | 2144 | 70.8% | 2.2% | 4.9% | -2.7% | 48.6% |
| external | S4_1D | 387 | 67.7% | 2.2% | 4.8% | -2.0% | 48.6% |
| development | S0_5M | 0 | - | - | - | - | - |
| development | S1_15M | 1339 | 33.2% | -1.2% | 1.7% | -3.3% | 17.3% |
| development | S2_1H | 3472 | 45.4% | -0.3% | 2.5% | -3.0% | 23.3% |
| development | S3_4H | 2841 | 67.1% | 1.3% | 3.5% | -1.9% | 34.6% |
| development | S4_1D | 322 | 77.6% | 2.5% | 4.0% | -1.2% | 45.7% |
| reference_validation | S0_5M | 0 | - | - | - | - | - |
| reference_validation | S1_15M | 606 | 28.5% | -2.2% | 1.4% | -3.6% | 7.8% |
| reference_validation | S2_1H | 1801 | 39.9% | -0.7% | 1.9% | -2.7% | 10.8% |
| reference_validation | S3_4H | 1411 | 67.5% | 1.0% | 2.8% | -1.5% | 19.3% |
| reference_validation | S4_1D | 199 | 77.9% | 2.9% | 4.7% | -1.1% | 41.2% |
| august | S0_5M | 0 | - | - | - | - | - |
| august | S1_15M | 8 | 75.0% | 1.3% | 2.0% | -0.5% | 37.5% |
| august | S2_1H | 34 | 0.0% | -1.4% | 0.8% | -1.9% | 0.0% |
| august | S3_4H | 82 | 82.9% | 1.3% | 1.9% | -0.8% | 11.0% |
| august | S4_1D | 0 | - | - | - | - | - |

## Propagation lag distribution

| Partition | Leg | N | P25 h | Median h | P75 h |
|---|---|---:|---:|---:|---:|
| external | 5m→15m | 5505 | 1.83 | 5.00 | 11.00 |
| external | 15m→1h | 4684 | 6.25 | 21.25 | 49.50 |
| external | 1h→4h | 2531 | 3.00 | 42.00 | 77.00 |
| external | 4h→1d | 387 | 28.00 | 52.00 | 96.00 |
| development | 5m→15m | 7974 | 1.92 | 5.08 | 11.83 |
| development | 15m→1h | 6635 | 7.25 | 22.50 | 50.38 |
| development | 1h→4h | 3163 | 4.00 | 45.00 | 69.00 |
| development | 4h→1d | 322 | 20.00 | 40.00 | 60.00 |
| reference_validation | 5m→15m | 4017 | 1.92 | 5.08 | 11.33 |
| reference_validation | 15m→1h | 3411 | 8.12 | 24.00 | 50.00 |
| reference_validation | 1h→4h | 1610 | 2.00 | 27.00 | 80.00 |
| reference_validation | 4h→1d | 199 | 8.00 | 40.00 | 64.00 |
| august | 5m→15m | 155 | 2.29 | 5.08 | 9.17 |
| august | 15m→1h | 127 | 3.50 | 29.25 | 54.25 |
| august | 1h→4h | 93 | 29.00 | 58.00 | 73.00 |
| august | 4h→1d | 0 | - | - | - |

## Gates

- B21_PROPAGATION_SUPPORTED: **FAIL**
- B21_EARLY_ENTRY_CLUE: **FAIL**

- external: S3=2144, S4=387, deepest N>=30=4, sample=True, deeper-vs-S0=False, monotonic=False.
- development: S3=2841, S4=322, deepest N>=30=4, sample=True, deeper-vs-S0=False, monotonic=False.
- reference_validation: S3=1411, S4=199, deepest N>=30=4, sample=True, deeper-vs-S0=False, monotonic=False.

## Latest causal state at dataset end

| TF | Bull | Last ON | Last OFF |
|---|---|---|---|
| m5 | ON | 2026-08-20 23:05:00+00:00 | 2026-08-20 23:00:00+00:00 |
| m15 | ON | 2026-08-20 23:15:00+00:00 | 2026-08-20 23:00:00+00:00 |
| h1 | ON | 2026-08-19 14:00:00+00:00 | 2026-08-19 02:00:00+00:00 |
| h4 | ON | 2026-08-19 20:00:00+00:00 | 2026-08-10 16:00:00+00:00 |
| d1 | OFF | 2026-04-27 00:00:00+00:00 | 2026-05-17 00:00:00+00:00 |

B21 is a propagation-forensics experiment, not a live trading rule. No B20 result was changed and live BBC remains untouched.
