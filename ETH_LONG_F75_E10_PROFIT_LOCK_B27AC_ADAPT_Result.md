# ETH LONG B27AC-Adapt — E10 Profit-Lock Runner — Result

ETHUSDT 5m rows: **698,112**; coverage: **100.0000%**.

Frozen F75 cohorts and E10+D60/F15 baseline are reused. E10 becomes a hard floor only from the bar after first reach; strict causal 3-bar pivot lows may ratchet it upward.

| Cohort | Partition | N | Fixed WR | Fixed PF | Fixed exp | Fixed net | Hybrid WR | Hybrid PF | Hybrid exp | Hybrid net | Δexp | E10 reach | Floor exit | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BLIND_F75 | external | 42 | 71.4% | 1.49 | $1.08 | $45.44 | 71.4% | 1.62 | $1.36 | $57.05 | $0.28 | 69.0% | 69.0% | 2 |
| BLIND_F75 | development | 65 | 69.2% | 1.08 | $0.17 | $11.31 | 69.2% | 1.25 | $0.53 | $34.25 | $0.35 | 64.6% | 64.6% | 3 |
| BLIND_F75 | reference_validation | 31 | 67.7% | 1.02 | $0.06 | $1.73 | 67.7% | 0.92 | $-0.22 | $-6.79 | $-0.27 | 67.7% | 67.7% | 3 |
| BLIND_F75 | august | 2 | 50.0% | 0.81 | $-0.59 | $-1.19 | 50.0% | 0.81 | $-0.59 | $-1.19 | $0.00 | 50.0% | 50.0% | 1 |
| EARLY_RECLAIM | external | 40 | 72.5% | 1.21 | $0.50 | $20.02 | 72.5% | 1.33 | $0.79 | $31.63 | $0.29 | 70.0% | 70.0% | 2 |
| EARLY_RECLAIM | development | 54 | 74.1% | 1.07 | $0.15 | $8.00 | 68.5% | 1.09 | $0.18 | $9.95 | $0.04 | 70.4% | 70.4% | 3 |
| EARLY_RECLAIM | reference_validation | 28 | 71.4% | 1.02 | $0.06 | $1.75 | 67.9% | 0.92 | $-0.22 | $-6.11 | $-0.28 | 71.4% | 71.4% | 3 |
| EARLY_RECLAIM | august | 2 | 50.0% | 0.76 | $-0.74 | $-1.47 | 50.0% | 0.76 | $-0.74 | $-1.47 | $0.00 | 50.0% | 50.0% | 1 |
| SAME_BAR_REJECTION | external | 23 | 73.9% | 1.34 | $0.64 | $14.77 | 73.9% | 1.17 | $0.32 | $7.40 | $-0.32 | 69.6% | 69.6% | 2 |
| SAME_BAR_REJECTION | development | 31 | 67.7% | 0.81 | $-0.46 | $-14.14 | 64.5% | 0.93 | $-0.16 | $-5.01 | $0.29 | 61.3% | 61.3% | 3 |
| SAME_BAR_REJECTION | reference_validation | 15 | 66.7% | 0.67 | $-1.06 | $-15.89 | 60.0% | 0.62 | $-1.25 | $-18.81 | $-0.19 | 66.7% | 66.7% | 2 |
| SAME_BAR_REJECTION | august | 2 | 50.0% | 0.76 | $-0.74 | $-1.47 | 50.0% | 0.76 | $-0.74 | $-1.47 | $0.00 | 50.0% | 50.0% | 1 |

## Primary EARLY_RECLAIM pooled major

- Fixed: N=122, WR=73.0%, PF=1.11, exp=$0.24, net=$29.77.
- Hybrid: N=122, WR=69.7%, PF=1.13, exp=$0.29, net=$35.47.

**Status: ETH_LONG_B27AC_ADAPT_PRIMARY_HYBRID_NOT_SUPPORTED**

Research only; no live changes.
