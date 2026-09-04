# SOL LONG E20 Conditional Protection — A14 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A14 tests only A13-derived conditional E20 weakness states on the supported A2+A4 stack.

## Central Development

| Lane | Parent interventions | H2 retained | H2 interventions | Winner preserved | Episode WR base→new | Gross loss base→new | Stack PF base→new | Stack Net Δ | 5bps PF base→new | 5bps Net Δ | +blocks raw/stress | Pass |
|---|---:|---:|---:|---:|---|---|---|---:|---|---:|---:|---|
| CP_ANCHOR_FULL | 164 | 178 | 29 | 98.2% | 53.5%→62.2% | $1380.23→$1119.18 | 1.31→1.32 | $-67.32 | 1.15→1.14 | $-57.82 | 3/3 | NO |
| CP_ANCHOR_HALF | 164 | 186 | 30 | 99.3% | 53.5%→58.7% | $1380.23→$1191.68 | 1.31→1.32 | $-39.23 | 1.15→1.15 | $-31.73 | 2/2 | NO |
| CP_E10_5_FULL | 76 | 199 | 5 | 97.5% | 53.5%→57.1% | $1380.23→$1204.58 | 1.31→1.36 | $15.69 | 1.15→1.19 | $19.94 | 3/3 | NO |
| CP_E10_10_FULL | 94 | 193 | 13 | 97.1% | 53.5%→58.3% | $1380.23→$1170.86 | 1.31→1.33 | $-31.55 | 1.15→1.16 | $-25.80 | 4/4 | NO |

Frozen Development winner: **NONE**.


## Decision

- Validation: **No Development conditional-protection lane passed**.

**Status: SOL_LONG_E20_CONDITIONAL_PROTECTION_A14_REJECTED**

A rejected result must not be salvaged by OOS retuning. A supported result authorizes only the frozen A14 rule for subsequent full-stack benchmarking.

Research only. Live Baba Bot remains unchanged.
