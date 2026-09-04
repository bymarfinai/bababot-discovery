# SOL LONG Partial Profit + Progressive Runner Floor — A12 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A12 tests partial E20 monetization with an E40 runner on the supported A2 parent + A4 REC_H2 stack. Rejected A6/A8/A10/A11 mechanisms remain absent.

## Central Development

| Lane | Parent E20 hits | H2 retained | H2 E20 hits | Runner-floor triggers P/H2 | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|
| PP20_25 | 361 | 181 | 71 | 0/0 | 100.0% | 53.5%→59.8% | $1380.23→$1202.65 | 1.31→1.31 | $-51.28 | 1.15→1.14 | $-42.53 | 1/1 | NO |
| PP20_50 | 361 | 163 | 63 | 0/0 | 100.0% | 53.5%→65.2% | $1380.23→$1093.37 | 1.31→1.29 | $-103.78 | 1.15→1.12 | $-90.53 | 1/1 | NO |
| HY20_25 | 361 | 174 | 65 | 47/13 | 100.0% | 53.5%→60.9% | $1380.23→$1197.28 | 1.31→1.27 | $-102.24 | 1.15→1.11 | $-91.74 | 1/1 | NO |
| HY20_50 | 361 | 162 | 62 | 47/13 | 100.0% | 53.5%→65.5% | $1380.23→$1092.77 | 1.31→1.27 | $-126.09 | 1.15→1.10 | $-112.59 | 0/0 | NO |

Frozen Development winner: **NONE**.


## Decision

- Validation: **No Development partial/runner lane passed**.

**Status: SOL_LONG_PARTIAL_RUNNER_A12_REJECTED**

A supported result authorizes only the frozen partial/runner lane for subsequent full-stack benchmarking. A rejected result must not be rescued by OOS retuning.

Research only. Live Baba Bot remains unchanged.
