# SOL LONG Progressive Risk Floor — A11 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A11 tests progressive profit floors on the supported A2 parent + A4 REC_H2 stack. Rejected A6/A8/A10 mechanisms remain absent.

## Central Development

| Lane | Parent triggers | H2 retained | H2 triggers | Winner preserved | Episode WR base→new | Episode gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|
| RF_LOOSE | 74 | 178 | 29 | 100.0% | 53.5%→60.6% | $1380.23→$1288.03 | 1.31→1.27 | $-87.43 | 1.15→1.11 | $-77.93 | 3/3 | NO |
| RF_BALANCED | 115 | 163 | 47 | 100.0% | 53.5%→64.8% | $1380.23→$1245.54 | 1.31→1.28 | $-77.46 | 1.15→1.12 | $-64.21 | 1/2 | NO |
| RF_TIGHT | 142 | 136 | 54 | 100.0% | 53.5%→67.9% | $1380.23→$1205.88 | 1.31→1.29 | $-88.35 | 1.15→1.13 | $-68.35 | 1/1 | NO |
| RF_GIVEBACK15 | 97 | 173 | 38 | 100.0% | 53.5%→62.1% | $1380.23→$1271.29 | 1.31→1.27 | $-80.02 | 1.15→1.12 | $-69.27 | 2/2 | NO |

Frozen Development winner: **NONE**.


## Decision

- Validation: **No Development ratchet passed**.

**Status: SOL_LONG_PROGRESSIVE_RISK_FLOOR_A11_REJECTED**

A supported result authorizes only the frozen ratchet for further full-stack residual/benchmark analysis. A rejected result must not be rescued by OOS retuning.

Research only. Live Baba Bot remains unchanged.
