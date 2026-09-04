# SOL LONG 15:00 UTC RC30_C2 Parent-MAE Transfer — A39 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

Exact A27 RC30_C2 recovery with one frozen A37B/A38 upstream gate: parent_mae_R <= 0.145R.

## Development

| N | Attempt/loss | Rec WR | Rec PF | Rec Net | 5bps PF | 5bps Net | Rescue | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay | +blocks raw/stress | Pass |
|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|
| 56 | 15.7% | 44.6% | 2.19 | $76.78 | 1.87 | $62.78 | 44.6% | 40.6%→44.8% | 1.28→1.32 | 1.14→1.18 | 4/4 | YES |

## Frozen OOS

| Role | Partition | N | Rec WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| CENTRAL | external | 38 | 34.2% | 1.30 | $33.69 | 1.20 | $24.19 | 40.9%→45.6% | 1.55→1.51 | 1.43→1.40 |
| CENTRAL | reference_validation | 31 | 25.8% | 0.88 | $-5.12 | 0.74 | $-12.87 | 44.5%→46.9% | 1.57→1.51 | 1.35→1.30 |
| CLOCK_SUPPORT | external | 45 | 22.2% | 0.88 | $-15.04 | 0.80 | $-26.29 | 38.5%→42.1% | 1.49→1.41 | 1.38→1.30 |
| CLOCK_SUPPORT | reference_validation | 42 | 26.2% | 1.03 | $1.59 | 0.86 | $-8.91 | 37.5%→41.1% | 1.55→1.49 | 1.33→1.27 |
| REF_SUPPORT | external | 36 | 33.3% | 0.85 | $-15.75 | 0.78 | $-24.75 | 45.8%→50.0% | 1.82→1.70 | 1.69→1.57 |
| REF_SUPPORT | reference_validation | 28 | 25.0% | 0.79 | $-6.92 | 0.64 | $-13.92 | 43.9%→45.9% | 1.63→1.57 | 1.39→1.34 |

## Decision

**Status: SOL_LONG_15UTC_RC30C2_PARENT_MAE_TRANSFER_A39_REJECTED_OOS**

No neighboring MAE threshold or reclaim-window scan is authorized after A39.

Research only. Live Baba Bot remains unchanged.
