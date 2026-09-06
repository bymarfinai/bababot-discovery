# SOL LONG 15:00 UTC A40 B2 Regime Guard — A42 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

Exact A40 geometry; only A41 Development-midpoint regime guards are applied.

## Development

| Lane | N | WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | Stress WR→Episode WR | PF→Overlay | Stress PF→Overlay | Adequate/+ raw/+ stress | B2 N/net/stress | Pass |
|---|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|
| G_MAE145 | 12 | 83.3% | 7.66 | $27.56 | 6.30 | $24.56 | 40.6%→42.3% | 40.3%→41.9% | 1.28→1.30 | 1.14→1.16 | 3/3/3 | 1/$-2.01/$-2.26 | YES |
| G_RET30_220 | 13 | 76.9% | 3.89 | $17.16 | 3.08 | $13.91 | 40.6%→42.3% | 40.3%→41.9% | 1.28→1.29 | 1.14→1.15 | 4/3/3 | 2/$-0.15/$-0.65 | NO |
| G_BOTH | 7 | 85.7% | 7.84 | $13.72 | 6.30 | $11.97 | 40.6%→41.6% | 40.3%→41.3% | 1.28→1.29 | 1.14→1.15 | 3/3/3 | 1/$-2.01/$-2.26 | NO |

Frozen Development winner: **G_MAE145**.

## Frozen OOS

| Role | Partition | N | WR | PF | Net | 5bps PF | 5bps Net | Parent WR→Episode WR | PF→Overlay | Stress PF→Overlay |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| CENTRAL | external | 9 | 77.8% | 2.77 | $42.74 | 2.64 | $40.49 | 40.9%→43.4% | 1.55→1.58 | 1.43→1.47 |
| CENTRAL | reference_validation | 7 | 57.1% | 3.97 | $12.37 | 3.16 | $10.62 | 44.5%→45.7% | 1.57→1.59 | 1.35→1.37 |
| CLOCK_SUPPORT | external | 3 | 100.0% | inf | $23.81 | inf | $23.06 | 38.5%→39.6% | 1.49→1.52 | 1.38→1.41 |
| CLOCK_SUPPORT | reference_validation | 12 | 33.3% | 0.66 | $-6.62 | 0.56 | $-9.62 | 37.5%→38.8% | 1.55→1.51 | 1.33→1.29 |
| REF_SUPPORT | external | 7 | 71.4% | 1.41 | $10.15 | 1.33 | $8.40 | 45.8%→47.6% | 1.82→1.81 | 1.69→1.67 |
| REF_SUPPORT | reference_validation | 7 | 57.1% | 4.03 | $12.44 | 3.20 | $10.69 | 43.9%→45.1% | 1.63→1.65 | 1.39→1.41 |

## Decision

**Status: SOL_LONG_15UTC_A40_B2_GUARD_A42_SUPPORTED**

No neighboring MAE/momentum threshold, E20/E10 change, or OOS retuning is authorized after A42.

Research only. Live Baba Bot remains unchanged.
