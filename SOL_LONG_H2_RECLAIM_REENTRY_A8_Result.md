# SOL LONG H2 Reclaim Re-entry — A8 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A8 tests confirmed reclaim next-open re-entry after a losing frozen H2 recovery. No resting H3/H4 retry is used.

## Central Development

| Lane | A8 N | WR | PF | Exp | Net | 5bps PF | 5bps Exp | 5bps Net | Rescue | 5bps Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ | +blocks | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---|
| RC10 | 62 | 25.8% | 1.15 | $0.19 | $11.93 | 0.96 | $-0.06 | $-3.57 | 19.4% | 19.4% | 1.31→1.30 | $11.93 | 1.15→1.14 | $-3.57 | 3/6 | NO |
| RC15 | 73 | 31.5% | 1.55 | $0.66 | $48.01 | 1.30 | $0.41 | $29.76 | 26.0% | 26.0% | 1.31→1.32 | $48.01 | 1.15→1.16 | $29.76 | 4/6 | YES |
| RC30 | 91 | 33.0% | 1.58 | $0.68 | $61.97 | 1.32 | $0.43 | $39.22 | 27.5% | 27.5% | 1.31→1.32 | $61.97 | 1.15→1.16 | $39.22 | 4/6 | YES |
| RC60 | 110 | 32.7% | 1.40 | $0.47 | $52.01 | 1.16 | $0.22 | $24.51 | 26.4% | 25.5% | 1.31→1.31 | $52.01 | 1.15→1.15 | $24.51 | 4/6 | YES |

Frozen Development winner: **RC30**.

## Frozen OOS

| Role | Partition | N | PF | Net | 5bps PF | 5bps Net | Rescue | Overlay PF base→new | Overlay Net Δ | 5bps Overlay PF base→new | 5bps Overlay Net Δ |
|---|---|---:|---:|---:|---:|---:|---:|---|---:|---|---:|
| CENTRAL | external | 48 | 0.88 | $-12.35 | 0.78 | $-24.35 | 20.8% | 1.46→1.40 | $-12.35 | 1.34→1.28 | $-24.35 |
| CENTRAL | reference_validation | 60 | 0.48 | $-30.59 | 0.36 | $-45.59 | 11.7% | 1.20→1.14 | $-30.59 | 1.02→0.96 | $-45.59 |
| CLOCK_SUPPORT | external | 47 | 1.03 | $3.05 | 0.93 | $-8.70 | 25.5% | 1.47→1.43 | $3.05 | 1.34→1.30 | $-8.70 |
| CLOCK_SUPPORT | reference_validation | 62 | 0.95 | $-2.83 | 0.74 | $-18.33 | 19.4% | 1.56→1.50 | $-2.83 | 1.30→1.24 | $-18.33 |
| REF_SUPPORT | external | 46 | 0.76 | $-20.44 | 0.65 | $-31.94 | 19.6% | 1.31→1.27 | $-20.44 | 1.20→1.16 | $-31.94 |
| REF_SUPPORT | reference_validation | 55 | 1.17 | $7.51 | 0.89 | $-6.24 | 21.8% | 1.27→1.26 | $7.51 | 1.06→1.05 | $-6.24 |

## Decision

- Frozen lane: **RC30**.
- Validation: **central_ok=False; support positive raw=2/4; support positive 5bps=0/4**.

**Status: SOL_LONG_H2_RECLAIM_REENTRY_A8_REJECTED**

If supported, the next stage should recompute the fully frozen H1 + H2 + reclaim-reentry episode economics, residual-loss anatomy, and benchmark against the prior SOL stack before any exit optimization.

Research only. Live Baba Bot remains unchanged.
