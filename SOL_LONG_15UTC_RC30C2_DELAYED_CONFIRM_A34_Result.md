# SOL LONG 15:00 UTC RC30_C2 Delayed Confirmation — A34 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A34 reuses the exact A33 +5/+10m follow-through states as pre-entry confirmation instead of paying for an immediate recovery and exiting weak follow-through later.

## Development

| Lane | N | Attempt/loss | Confirm delay | Reentry R | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | 5bps PF→Overlay | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| DC5_C10 | 39 | 10.9% | 5m | 0.166R | 59.0% | 0.66 | $-29.06 | 0.56 | $-38.81 | 53.8% | 40.6%→44.1% | 1.28→1.24 | 1.14→1.11 | 2/2 | NO |
| DC10_C12 | 27 | 7.6% | 10m | 0.174R | 59.3% | 0.91 | $-3.61 | 0.77 | $-10.36 | 55.6% | 40.6%→43.1% | 1.28→1.27 | 1.14→1.13 | 2/2 | NO |
| DC5_OR10 | 46 | 12.9% | 5m | 0.165R | 52.2% | 0.61 | $-39.61 | 0.53 | $-51.11 | 47.8% | 40.6%→44.3% | 1.28→1.23 | 1.14→1.10 | 2/2 | NO |

Frozen Development winner: **NONE**.


## Decision

**Status: SOL_LONG_15UTC_RC30C2_DELAYED_CONFIRM_A34_REJECTED_DEVELOPMENT**

No neighboring follow-through threshold or delay scan is authorized after A34.

Research only. Live Baba Bot remains unchanged.
