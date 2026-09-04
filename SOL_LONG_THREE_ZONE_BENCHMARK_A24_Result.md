# SOL LONG Three-Zone Portfolio Benchmark — A24 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

Frozen architecture: **03:00/R420 parent-only + 15:00/R360 parent-only + 18:00/R240 parent + REC_H2**. A18 and A23 recovery transfers remain rejected.

## Partition benchmark

| Partition | 18 PF | 18 Net | 03 PF | 03 Net | 15 PF | 15 Net | Two-zone PF | Two-zone Net | Three-zone trades/wk | Three-zone PF | Three-zone Net | Three-zone 5bps PF | Three-zone 5bps Net | +15 net raw/stress | Freq uplift vs two | Freq uplift vs 18 | 15 overlap | Peak conc. |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|
| development | 1.31 | $448.82 | 1.21 | $281.47 | 1.28 | $338.91 | 1.26 | $730.29 | 13.05 | 1.27 | $1069.20 | 1.13 | $558.45 | $338.91/$188.66 | 41.7% | 145.3% | 38.9% | 2 |
| external | 1.46 | $460.40 | 2.00 | $527.66 | 1.55 | $419.82 | 1.64 | $988.06 | 8.92 | 1.61 | $1407.88 | 1.48 | $1175.13 | $419.82/$349.57 | 43.2% | 133.9% | 29.5% | 2 |
| reference_validation | 1.20 | $127.92 | 1.33 | $171.50 | 1.57 | $263.33 | 1.26 | $299.42 | 13.55 | 1.35 | $562.75 | 1.16 | $284.50 | $263.33/$179.08 | 43.4% | 144.1% | 35.3% | 2 |

## Drawdown / capital efficiency

| Partition | Two-zone DD | Three-zone DD | Two-zone 5bps DD | Three-zone 5bps DD | Two-zone $/exposure-h | Three-zone $/exposure-h | Two-zone annual net | Three-zone annual net |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | $142.97 | $162.79 | $158.22 | $201.11 | $0.269 | $0.281 | $243.37 | $356.31 |
| external | $120.50 | $167.06 | $128.07 | $183.81 | $1.059 | $1.046 | $493.68 | $703.44 |
| reference_validation | $87.08 | $77.28 | $141.08 | $105.63 | $0.190 | $0.258 | $190.19 | $357.46 |

## Decision

**Status: SOL_LONG_THREE_ZONE_A24_SUPPORTED_ADDITIVE_EXPANSION**

A24 is an additive portfolio audit, not a live concurrency scheduler. Overlap is diagnostic and no trade is altered using future information.

Research only. Live Baba Bot remains unchanged.
