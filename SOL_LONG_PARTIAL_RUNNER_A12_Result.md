# SOL LONG Partial Profit + Progressive Runner Floor — A12 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A12 tests partial E20 monetization with an E40 runner on the supported A2 parent + A4 REC_H2 stack. Rejected A6/A8/A10/A11 mechanisms remain absent.

## Central Development

| Lane | Parent E20 hits | H2 retained | H2 E20 hits | Runner-floor triggers P/H2 | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|
| PP20_25 | 320 | 181 | 71 | 0/0 | 82.2% | 53.5%→53.6% | $1380.23→$937.94 | 1.31→1.40 | $-44.40 | 1.15→1.18 | $-35.65 | 3/3 | NO |
| PP20_50 | 320 | 163 | 63 | 0/0 | 85.9% | 53.5%→60.5% | $1380.23→$893.78 | 1.31→1.35 | $-107.36 | 1.15→1.14 | $-94.11 | 3/3 | NO |
| HY20_25 | 320 | 174 | 65 | 64/13 | 84.4% | 53.5%→55.8% | $1380.23→$930.40 | 1.31→1.35 | $-93.38 | 1.15→1.14 | $-82.88 | 2/2 | NO |
| HY20_50 | 320 | 162 | 62 | 64/13 | 86.2% | 53.5%→60.9% | $1380.23→$893.03 | 1.31→1.33 | $-128.35 | 1.15→1.12 | $-114.85 | 1/2 | NO |

Frozen Development winner: **NONE**.


## Decision

- Validation: **No Development partial/runner lane passed**.

**Status: SOL_LONG_PARTIAL_RUNNER_A12_REJECTED**

A supported result authorizes only the frozen partial/runner lane for subsequent full-stack benchmarking. A rejected result must not be rescued by OOS retuning.

Research only. Live Baba Bot remains unchanged.
