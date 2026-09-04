# SOL LONG 15:00 UTC RC30_C2 Early-Failure Guard — A33 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A33 preserves E40 and uses only A30-replicated +5/+10m post-entry follow-through diagnostics to cut bad recoveries earlier.

## Development

| Lane | N | Early-exit rate | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| EF5_C10 | 114 | 60.5% | 39.5% | 0.80 | $-29.00 | 0.64 | $-57.50 | 29.8% | 40.6%→46.3% | 1.28→1.23 | 1.14→1.09 | 3/3 | NO |
| EF10_C12 | 114 | 44.7% | 44.7% | 1.21 | $26.32 | 0.98 | $-2.18 | 34.2% | 40.6%→47.1% | 1.28→1.27 | 1.14→1.13 | 3/3 | NO |
| EF5_C10_THEN10_C12 | 114 | 72.8% | 38.6% | 0.93 | $-8.00 | 0.72 | $-36.50 | 28.1% | 40.6%→45.9% | 1.28→1.25 | 1.14→1.11 | 3/2 | NO |

Frozen Development winner: **NONE**.


## Decision

**Status: SOL_LONG_15UTC_RC30C2_EARLY_FAIL_A33_REJECTED_DEVELOPMENT**

No neighboring post-entry threshold/clock scan is authorized from A33 results.

Research only. Live Baba Bot remains unchanged.
