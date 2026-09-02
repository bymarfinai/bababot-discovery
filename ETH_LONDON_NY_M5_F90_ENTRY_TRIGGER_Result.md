# ETH London -> New York M5 F90 Entry Trigger Calibration — Result

ETH raw 5m coverage: **100.0000%**.

Frozen anchor: **F90 after London->NY LONG K1 OPP0 causal leave**. Structural outcome = strict completed 5m breakout `close > H`; H2 is telemetry only.

- Exact M2 F90 filled opportunities: **152**.
- BLIND_TOUCH -> M4 F90 parity: **PASS**.
- Reclaim chronology / geometry audit: **PASS**.

## Major-partition trigger comparison

| Partition | Variant | Opps | Executed | Retention | Same-bar | Later | Strict BO | BO rate | Opposite | No break | Median entry f |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| external | BLIND_TOUCH | 56 | 56 | 100.0% | 0 | 0 | 44 | 78.6% | 1 | 11 | 0.900 |
| external | EARLY_RECLAIM | 56 | 39 | 69.6% | 22 | 17 | 32 | 82.1% | 1 | 6 | 0.922 |
| external | SAME_BAR_REJECTION | 56 | 22 | 39.3% | 22 | 0 | 19 | 86.4% | 1 | 2 | 0.918 |
| development | BLIND_TOUCH | 65 | 65 | 100.0% | 0 | 0 | 49 | 75.4% | 8 | 8 | 0.900 |
| development | EARLY_RECLAIM | 65 | 41 | 63.1% | 18 | 24 | 32 | 78.0% | 5 | 4 | 0.919 |
| development | SAME_BAR_REJECTION | 65 | 17 | 26.2% | 18 | 0 | 13 | 76.5% | 2 | 2 | 0.918 |
| reference_validation | BLIND_TOUCH | 30 | 30 | 100.0% | 0 | 0 | 24 | 80.0% | 4 | 2 | 0.900 |
| reference_validation | EARLY_RECLAIM | 30 | 15 | 50.0% | 9 | 6 | 13 | 86.7% | 2 | 0 | 0.920 |
| reference_validation | SAME_BAR_REJECTION | 30 | 9 | 30.0% | 9 | 0 | 8 | 88.9% | 1 | 0 | 0.916 |

## Pooled-major

| Variant | N | Retention | BO rate | H2 after entry | Median touch->entry | Median entry f | Remaining to H |
|---|---:|---:|---:|---:|---:|---:|---:|
| BLIND_TOUCH | 151 | 100.0% | 77.5% | 83.4% | 0.0m | 0.900 | 0.100R |
| EARLY_RECLAIM | 95 | 62.9% | 81.1% | 87.4% | 5.0m | 0.920 | 0.080R |
| SAME_BAR_REJECTION | 48 | 31.8% | 83.3% | 87.5% | 5.0m | 0.917 | 0.083R |

## Frozen EARLY_RECLAIM trigger screen

- >=15 executed in every major partition: **PASS**
- pooled retention >=60% of blind: **PASS**
- breakout rate >= blind in every major partition: **PASS**
- pooled breakout improvement >=3.0pp: **PASS**

**Status: ETH_LONDON_NY_M5_F90_EARLY_RECLAIM_SCREEN_PASS**

SAME_BAR_REJECTION remains diagnostic only. M5 contains no stop, target, PnL, fee, slippage, runner, or portfolio optimization.