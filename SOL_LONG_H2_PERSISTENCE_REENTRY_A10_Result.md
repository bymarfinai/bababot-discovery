# SOL LONG H2 Persistence-Confirmed Re-entry — A10 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A10 tests a small persistence-confirmed re-entry family after the first post-H2 reclaim. A8 RC30 remains rejected and absent.

## Central Development

| Lane | N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | Rescue | 5bps Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ | +blocks | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---|
| AC10_C3 | 67 | 38.8% | 1.09 | $0.13 | $8.56 | 0.92 | $-0.12 | $-8.19 | 31.3% | 28.4% | 1.31→1.29 | $8.56 | 1.15→1.14 | $-8.19 | 3/6 | NO |
| AC15_C4 | 52 | 48.1% | 1.52 | $0.70 | $36.39 | 1.31 | $0.45 | $23.39 | 42.3% | 36.5% | 1.31→1.32 | $36.39 | 1.15→1.16 | $23.39 | 4/6 | YES |
| AC15_C4_E10 | 46 | 52.2% | 1.69 | $0.93 | $42.64 | 1.46 | $0.68 | $31.14 | 47.8% | 41.3% | 1.31→1.32 | $42.64 | 1.15→1.16 | $31.14 | 4/6 | YES |
| AC30_C7 | 29 | 55.2% | 1.36 | $0.57 | $16.44 | 1.19 | $0.32 | $9.19 | 37.9% | 31.0% | 1.31→1.31 | $16.44 | 1.15→1.15 | $9.19 | 2/6 | NO |

Frozen Development winner: **AC15_C4_E10**.

## Frozen OOS

| Role | Partition | N | PF | Net | 5bps PF | 5bps Net | Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| CENTRAL | external | 17 | 2.64 | $57.14 | 2.43 | $52.89 | 47.1% | 1.46→1.50 | $57.14 | 1.34→1.37 | $52.89 |
| CENTRAL | reference_validation | 24 | 0.38 | $-22.34 | 0.30 | $-28.34 | 20.8% | 1.20→1.16 | $-22.34 | 1.02→0.98 | $-28.34 |
| CLOCK_SUPPORT | external | 23 | 1.21 | $14.63 | 1.12 | $8.88 | 34.8% | 1.47→1.45 | $14.63 | 1.34→1.33 | $8.88 |
| CLOCK_SUPPORT | reference_validation | 28 | 0.88 | $-4.00 | 0.72 | $-11.00 | 32.1% | 1.56→1.52 | $-4.00 | 1.30→1.26 | $-11.00 |
| REF_SUPPORT | external | 14 | 1.51 | $10.26 | 1.31 | $6.76 | 42.9% | 1.31→1.31 | $10.26 | 1.20→1.20 | $6.76 |
| REF_SUPPORT | reference_validation | 27 | 0.65 | $-10.67 | 0.51 | $-17.42 | 29.6% | 1.27→1.24 | $-10.67 | 1.06→1.03 | $-17.42 |

## Decision

- Frozen lane: **AC15_C4_E10**.
- Validation: **central_ok=False; support positive raw=2/4; support positive 5bps=2/4**.

**Status: SOL_LONG_H2_PERSISTENCE_REENTRY_A10_REJECTED**

Do not salvage A10 by OOS retuning. Return to forensic residual structure or proceed to later protocol stages only with a new causal hypothesis.

Research only. Live Baba Bot remains unchanged.
