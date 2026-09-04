# SOL LONG 15:00 UTC RC30_C2 Quality Guard — A29 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A29 applies only A28-derived fixed quality guards to the exact RC30_C2 trigger.

## Development

| Lane | N | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay PF | 5bps PF→Overlay | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| Q_CLOSE08 | 49 | 51.0% | 0.69 | $-34.90 | 0.60 | $-47.15 | 51.0% | 40.6%→44.8% | 1.28→1.23 | 1.14→1.10 | 4/2 | NO |
| Q_BODY04 | 52 | 46.2% | 0.94 | $-6.11 | 0.83 | $-19.11 | 46.2% | 40.6%→44.6% | 1.28→1.25 | 1.14→1.12 | 3/2 | NO |
| Q_CLOSE08_BODY04 | 36 | 55.6% | 0.74 | $-22.10 | 0.65 | $-31.10 | 55.6% | 40.6%→43.9% | 1.28→1.24 | 1.14→1.11 | 2/1 | NO |

Frozen Development winner: **NONE**.


## Decision

**Status: SOL_LONG_15UTC_RC30C2_QUALITY_GUARD_A29_REJECTED_DEVELOPMENT**

No neighboring threshold scan is allowed after A29. If rejected, return to loss anatomy or leave 15UTC parent-only.

Research only. Live Baba Bot remains unchanged.
