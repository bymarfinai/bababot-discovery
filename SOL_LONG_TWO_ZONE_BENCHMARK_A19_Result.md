# SOL LONG Two-Zone Operational Benchmark — A19 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

Frozen architecture: **18:00 UTC = A2 parent + A4 REC_H2; 03:00 UTC = A17 parent only**. A18 H2 transfer remains rejected.

## Partition benchmark

| Partition | Mature trades/wk | Mature PF | Mature Net | Mature 5bps PF | Mature 5bps Net | New 03 PF | New 03 Net | New 03 5bps PF | New 03 5bps Net | Combined trades/wk | Combined PF | Combined Net | Combined 5bps PF | Combined 5bps Net | Frequency uplift | New overlap | Peak conc. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 5.32 | 1.31 | $448.82 | 1.15 | $240.57 | 1.21 | $281.47 | 1.09 | $129.22 | 9.21 | 1.26 | $730.29 | 1.12 | $369.79 | 73.1% | 14.9% | 2 |
| external | 3.81 | 1.46 | $460.40 | 1.34 | $360.90 | 2.00 | $527.66 | 1.82 | $464.66 | 6.22 | 1.64 | $988.06 | 1.50 | $825.56 | 63.3% | 9.9% | 2 |
| reference_validation | 5.55 | 1.20 | $127.92 | 1.02 | $13.92 | 1.33 | $171.50 | 1.16 | $91.50 | 9.45 | 1.26 | $299.42 | 1.08 | $105.42 | 70.2% | 14.7% | 2 |

## Drawdown / capital efficiency

| Partition | Mature DD | Combined DD | Mature 5bps DD | Combined 5bps DD | Mature $/exposure-h | Combined $/exposure-h | Mature annual net | Combined annual net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | $99.52 | $142.97 | $110.02 | $158.22 | $0.313 | $0.269 | $149.57 | $243.37 |
| external | $137.47 | $120.50 | $146.47 | $128.07 | $0.853 | $1.059 | $230.04 | $493.68 |
| reference_validation | $69.26 | $87.08 | $100.19 | $141.08 | $0.154 | $0.190 | $81.25 | $190.19 |

## Decision

**Status: SOL_LONG_TWO_ZONE_A19_SUPPORTED_ADDITIVE_EXPANSION**

A19 is an additive portfolio benchmark, not a live single-position scheduler. Reported overlap is diagnostic; no trade was altered using future overlap information.

Research only. Live Baba Bot remains unchanged.
