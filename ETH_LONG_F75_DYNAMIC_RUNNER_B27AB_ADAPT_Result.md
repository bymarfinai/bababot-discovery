# ETH LONG B27AB-Adapt — Post-Breakout Dynamic Runner — Result

ETHUSDT 5m rows: **698,112**; coverage: **100.0000%**.

Frozen cohorts are reused from B27W/B27Z/B27AA. Runner uses F15 pre-breakout close invalidation, first completed close > H activation, and one strict causal 3-bar pivot-low trail definition.

| Cohort | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Runner WR | Runner PF | Runner exp | Runner net | Δexp | Activation | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F75 | external | 42 | 71.4% | 1.49 | $1.08 | $45.44 | 66.7% | 2.21 | $2.79 | $117.11 | $1.71 | 71.4% | 2 |
| BLIND_F75 | development | 65 | 69.2% | 1.08 | $0.17 | $11.31 | 55.4% | 1.12 | $0.27 | $17.37 | $0.09 | 63.1% | 5 |
| BLIND_F75 | reference_validation | 31 | 67.7% | 1.02 | $0.06 | $1.73 | 51.6% | 1.05 | $0.15 | $4.67 | $0.09 | 67.7% | 3 |
| BLIND_F75 | august | 2 | 50.0% | 0.81 | $-0.59 | $-1.19 | 50.0% | 1.11 | $0.35 | $0.70 | $0.94 | 50.0% | 1 |
| EARLY_RECLAIM | external | 40 | 72.5% | 1.21 | $0.50 | $20.02 | 60.0% | 1.92 | $2.36 | $94.35 | $1.86 | 72.5% | 2 |
| EARLY_RECLAIM | development | 54 | 74.1% | 1.07 | $0.15 | $8.00 | 51.9% | 0.98 | $-0.04 | $-1.93 | $-0.18 | 68.5% | 5 |
| EARLY_RECLAIM | reference_validation | 28 | 71.4% | 1.02 | $0.06 | $1.75 | 46.4% | 1.06 | $0.21 | $5.75 | $0.14 | 71.4% | 3 |
| EARLY_RECLAIM | august | 2 | 50.0% | 0.76 | $-0.74 | $-1.47 | 50.0% | 1.07 | $0.21 | $0.42 | $0.94 | 50.0% | 1 |
| SAME_BAR_REJECTION | external | 23 | 73.9% | 1.34 | $0.64 | $14.77 | 60.9% | 1.70 | $1.42 | $32.73 | $0.78 | 73.9% | 2 |
| SAME_BAR_REJECTION | development | 31 | 67.7% | 0.81 | $-0.46 | $-14.14 | 48.4% | 0.73 | $-0.80 | $-24.82 | $-0.34 | 58.1% | 3 |
| SAME_BAR_REJECTION | reference_validation | 15 | 66.7% | 0.67 | $-1.06 | $-15.89 | 40.0% | 0.92 | $-0.31 | $-4.71 | $0.75 | 66.7% | 3 |
| SAME_BAR_REJECTION | august | 2 | 50.0% | 0.76 | $-0.74 | $-1.47 | 50.0% | 1.07 | $0.21 | $0.42 | $0.94 | 50.0% | 1 |

## Primary EARLY_RECLAIM pooled-major comparison

- Fixed baseline: N=122, WR=73.0%, PF=1.11, exp=$0.24, net=$29.77.
- Dynamic runner: N=122, WR=53.3%, PF=1.31, exp=$0.80, net=$98.17.

**Status: ETH_LONG_B27AB_ADAPT_PRIMARY_RUNNER_NOT_SUPPORTED**

Research only; no live changes.
