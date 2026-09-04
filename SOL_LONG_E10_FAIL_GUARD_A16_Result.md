# SOL LONG E10-Fail False-Positive Guard — A16 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A16 guards the rejected A14 CP_E10_5_FULL signal using only A15-supported trigger-time dimensions.

## Central Development

| Lane | Parent interventions | H2 retained | H2 interventions | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|
| G_FAST10 | 36 | 205 | 3 | 98.9% | 53.5%→55.6% | $1380.23→$1358.63 | 1.31→1.28 | $-50.79 | 1.15→1.12 | $-48.04 | 2/2 | NO |
| G_SHALLOW25 | 40 | 203 | 4 | 100.0% | 53.5%→56.9% | $1380.23→$1264.31 | 1.31→1.38 | $57.14 | 1.15→1.21 | $60.39 | 5/5 | YES |
| G_FAST10_SHALLOW25 | 27 | 208 | 3 | 100.0% | 53.5%→56.1% | $1380.23→$1333.49 | 1.31→1.32 | $7.81 | 1.15→1.16 | $9.81 | 4/4 | YES |
| G_FAST10_OR_SHALLOW25 | 49 | 200 | 4 | 98.9% | 53.5%→56.4% | $1380.23→$1289.45 | 1.31→1.33 | $-1.46 | 1.15→1.16 | $2.54 | 3/3 | NO |

Frozen Development winner: **G_SHALLOW25**.


## Frozen OOS

| Role | Partition | Winner preserved | Episode WR base→new | Gross loss base→new | PF base→new | Net Δ | 5bps PF base→new | 5bps Net Δ |
|---|---|---:|---|---|---|---:|---|---:|
| CENTRAL | external | 100.0% | 47.3%→52.4% | $920.85→$883.81 | 1.46→1.41 | $-63.71 | 1.34→1.29 | $-59.96 |
| CENTRAL | reference_validation | 99.2% | 48.6%→53.3% | $588.64→$557.55 | 1.20→1.21 | $-3.17 | 1.02→1.02 | $0.33 |
| CLOCK_SUPPORT | external | 100.0% | 48.6%→52.1% | $945.36→$890.27 | 1.47→1.47 | $-18.99 | 1.34→1.34 | $-17.49 |
| CLOCK_SUPPORT | reference_validation | 99.2% | 50.0%→55.4% | $460.47→$438.80 | 1.56→1.57 | $-11.82 | 1.30→1.30 | $-8.07 |
| REF_SUPPORT | external | 100.0% | 50.3%→55.3% | $1014.66→$936.45 | 1.31→1.34 | $2.46 | 1.20→1.22 | $6.46 |
| REF_SUPPORT | reference_validation | 98.6% | 55.3%→59.3% | $569.15→$540.15 | 1.27→1.31 | $18.58 | 1.06→1.10 | $21.83 |

## Decision

- Validation: **central_ok=False; support positive raw=2/4; support positive 5bps=2/4**.

**Status: SOL_LONG_E10_FAIL_GUARD_A16_REJECTED**

A rejected result must not be salvaged by OOS retuning. A supported result may be benchmarked as an additive exit-efficiency improvement to A2+A4.

Research only. Live Baba Bot remains unchanged.
