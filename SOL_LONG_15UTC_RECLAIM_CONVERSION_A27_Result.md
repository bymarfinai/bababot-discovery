# SOL LONG 15:00 UTC Reclaim Conversion — A27 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A27 tests only the three A26-derived reclaim/persistence states. A23 resting recovery remains absent.

## Development

| Lane | N | Attempt/loss | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | Parent PF→Overlay PF | 5bps Parent PF→Overlay PF | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| RC30_FIRST | 151 | 42.3% | 31.1% | 1.12 | $25.27 | 0.95 | $-12.48 | 29.8% | 40.6%→48.1% | 1.28→1.25 | 1.14→1.11 | 4/3 | NO |
| RC30_C2 | 114 | 31.9% | 38.6% | 1.18 | $33.52 | 1.02 | $5.02 | 37.7% | 40.6%→47.8% | 1.28→1.27 | 1.14→1.13 | 4/4 | NO |
| RC60_C5 | 81 | 22.7% | 39.5% | 0.92 | $-11.06 | 0.80 | $-31.31 | 38.3% | 40.6%→45.8% | 1.28→1.24 | 1.14→1.11 | 2/1 | NO |

Frozen Development winner: **NONE**.


## Decision

**Status: SOL_LONG_15UTC_RECLAIM_CONVERSION_A27_REJECTED_DEVELOPMENT**

A27 is a bounded loss-conversion overlay. If rejected, no neighboring threshold/window scan is authorized; return to anatomy.

Research only. Live Baba Bot remains unchanged.
