# BTC MTF Bull Cascade B21 — Result

5m rows: **698,112**; source coverage: **100.0000%**
Data: **2020-01-01 00:00:00+00:00 → 2026-08-20 23:55:00+00:00**

Frozen bull state: `SMA7 > SMA25 > SMA99 AND close > SMA25`, observable only after each timeframe candle closes.

## Ordered cascade stage by partition

| Partition | 5m seeds | S0 5m | S1 15m | S2 1h | S3 4h | S4 1d | Fresh seeds |
|---|---:|---:|---:|---:|---:|---:|---:|
| external | 5505 | 5505 | 0 | 0 | 0 | 0 | 1267 |
| development | 7974 | 7974 | 0 | 0 | 0 | 0 | 2394 |
| reference_validation | 4017 | 4017 | 0 | 0 | 0 | 0 | 1339 |
| august | 155 | 155 | 0 | 0 | 0 | 0 | 51 |

## 72h outcome by deepest ordered stage — ALL seeds

| Partition | Stage | N72 | Positive 72h | Median 72h ret | Median MFE | Median MAE | MFE≥5% |
|---|---|---:|---:|---:|---:|---:|---:|
| external | S0_5M | 5505 | 56.7% | 0.8% | 3.9% | -3.4% | 40.6% |
| external | S1_15M | 0 | - | - | - | - | - |
| external | S2_1H | 0 | - | - | - | - | - |
| external | S3_4H | 0 | - | - | - | - | - |
| external | S4_1D | 0 | - | - | - | - | - |
| development | S0_5M | 7974 | 52.4% | 0.2% | 2.8% | -2.6% | 27.2% |
| development | S1_15M | 0 | - | - | - | - | - |
| development | S2_1H | 0 | - | - | - | - | - |
| development | S3_4H | 0 | - | - | - | - | - |
| development | S4_1D | 0 | - | - | - | - | - |
| reference_validation | S0_5M | 4017 | 49.8% | -0.0% | 2.3% | -2.2% | 14.9% |
| reference_validation | S1_15M | 0 | - | - | - | - | - |
| reference_validation | S2_1H | 0 | - | - | - | - | - |
| reference_validation | S3_4H | 0 | - | - | - | - | - |
| reference_validation | S4_1D | 0 | - | - | - | - | - |
| august | S0_5M | 124 | 59.7% | 0.9% | 1.6% | -1.1% | 9.7% |
| august | S1_15M | 0 | - | - | - | - | - |
| august | S2_1H | 0 | - | - | - | - | - |
| august | S3_4H | 0 | - | - | - | - | - |
| august | S4_1D | 0 | - | - | - | - | - |

## Propagation lag distribution

| Partition | Leg | N | P25 h | Median h | P75 h |
|---|---|---:|---:|---:|---:|
| external | 5m→15m | 0 | - | - | - |
| external | 15m→1h | 0 | - | - | - |
| external | 1h→4h | 0 | - | - | - |
| external | 4h→1d | 0 | - | - | - |
| development | 5m→15m | 0 | - | - | - |
| development | 15m→1h | 0 | - | - | - |
| development | 1h→4h | 0 | - | - | - |
| development | 4h→1d | 0 | - | - | - |
| reference_validation | 5m→15m | 0 | - | - | - |
| reference_validation | 15m→1h | 0 | - | - | - |
| reference_validation | 1h→4h | 0 | - | - | - |
| reference_validation | 4h→1d | 0 | - | - | - |
| august | 5m→15m | 0 | - | - | - |
| august | 15m→1h | 0 | - | - | - |
| august | 1h→4h | 0 | - | - | - |
| august | 4h→1d | 0 | - | - | - |

## Gates

- B21_PROPAGATION_SUPPORTED: **FAIL**
- B21_EARLY_ENTRY_CLUE: **FAIL**

- external: S3=0, S4=0, deepest N>=30=None, sample=False, deeper-vs-S0=False, monotonic=False.
- development: S3=0, S4=0, deepest N>=30=None, sample=False, deeper-vs-S0=False, monotonic=False.
- reference_validation: S3=0, S4=0, deepest N>=30=None, sample=False, deeper-vs-S0=False, monotonic=False.

## Latest causal state at dataset end

| TF | Bull | Last ON | Last OFF |
|---|---|---|---|
| m5 | ON | 2026-08-20 23:05:00+00:00 | 2026-08-20 23:00:00+00:00 |
| m15 | ON | 2026-08-20 23:15:00+00:00 | 2026-08-20 23:00:00+00:00 |
| h1 | ON | 2026-08-19 14:00:00+00:00 | 2026-08-19 02:00:00+00:00 |
| h4 | ON | 2026-08-19 20:00:00+00:00 | 2026-08-10 16:00:00+00:00 |
| d1 | OFF | 2026-04-27 00:00:00+00:00 | 2026-05-17 00:00:00+00:00 |

B21 is a propagation-forensics experiment, not a live trading rule. No B20 result was changed and live BBC remains untouched.
