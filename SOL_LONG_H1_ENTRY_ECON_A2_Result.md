# SOL LONG H1 Entry Economics — A2 Result

Raw SOLUSDT 5m coverage: **99.7671%**.

A2 optimizes actual trade economics, not H1/H2 rate.

## Native target derivation

- Q35 raw H1 extension = **0.089R** -> **E05**.
- Q50 raw H1 extension = **0.224R** -> **E20**.
- Q65 raw H1 extension = **0.428R** -> **E40**.

## Development candidate screen

| Entry | Target | N | WR | PF | Exp/trade | Net | 5bps PF | 5bps Exp | Good blocks | Pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| E0_RESTING_H | E05 | 617 | 85.4% | 0.71 | $-0.29 | $-179.05 | 0.47 | $-0.54 | 0/6 | NO |
| E0_RESTING_H | E20 | 617 | 60.1% | 1.20 | $0.31 | $191.43 | 1.04 | $0.06 | 5/6 | YES |
| E0_RESTING_H | E40 | 617 | 44.7% | 1.26 | $0.51 | $314.06 | 1.12 | $0.26 | 5/6 | YES |
| E1_H1_TOUCH_NEXT_OPEN | E05 | 615 | 52.4% | 0.54 | $-0.76 | $-468.29 | 0.43 | $-1.01 | 0/6 | NO |
| E1_H1_TOUCH_NEXT_OPEN | E20 | 615 | 51.7% | 0.94 | $-0.11 | $-67.22 | 0.82 | $-0.36 | 1/6 | NO |
| E1_H1_TOUCH_NEXT_OPEN | E40 | 615 | 44.4% | 1.09 | $0.21 | $129.06 | 0.98 | $-0.04 | 4/6 | NO |
| E2_H1_BREAK_NEXT_OPEN | E05 | 405 | 18.5% | 0.05 | $-1.67 | $-678.32 | 0.02 | $-1.92 | 0/6 | NO |
| E2_H1_BREAK_NEXT_OPEN | E20 | 405 | 35.1% | 0.41 | $-0.88 | $-354.55 | 0.31 | $-1.13 | 0/6 | NO |
| E2_H1_BREAK_NEXT_OPEN | E40 | 405 | 32.6% | 0.77 | $-0.37 | $-150.95 | 0.65 | $-0.62 | 2/6 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E05 | 333 | 27.9% | 0.11 | $-0.96 | $-320.76 | 0.05 | $-1.21 | 0/6 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E20 | 333 | 38.7% | 0.71 | $-0.30 | $-100.55 | 0.53 | $-0.55 | 0/6 | NO |
| E3_H1_RETEST_RECLAIM_NEXT_OPEN | E40 | 333 | 26.1% | 0.84 | $-0.22 | $-72.33 | 0.69 | $-0.47 | 2/6 | NO |

## Frozen Development winner

- Entry: **E0_RESTING_H**.
- Target: **E40**.
- Development N: **617**; WR **44.7%**; PF **1.26**; expectancy **$0.51**; net **$314.06**.
- Development 5bps PF **1.12**; expectancy **$0.26**; net **$159.81**.

## OOS and topology economics

| Role | Partition | N | WR | PF | Exp/trade | Net | 5bps PF | 5bps Net |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| CENTRAL | development | 617 | 44.7% | 1.26 | $0.51 | $314.06 | 1.12 | $159.81 |
| CENTRAL | external | 273 | 36.3% | 1.46 | $1.27 | $347.53 | 1.35 | $279.28 |
| CENTRAL | reference_validation | 317 | 37.5% | 1.16 | $0.26 | $81.96 | 1.00 | $2.71 |
| CLOCK_SUPPORT | external | 284 | 36.3% | 1.52 | $1.36 | $385.05 | 1.40 | $314.05 |
| CLOCK_SUPPORT | reference_validation | 316 | 41.5% | 1.58 | $0.74 | $232.52 | 1.34 | $153.52 |
| REF_SUPPORT | external | 300 | 40.0% | 1.42 | $1.13 | $338.29 | 1.31 | $263.29 |
| REF_SUPPORT | reference_validation | 349 | 42.4% | 1.23 | $0.31 | $108.84 | 1.04 | $21.59 |

## Decision

**Status: SOL_LONG_H1_ENTRY_ECON_A2_SUPPORTED**

The frozen H1 structure supports **E0_RESTING_H -> E40** under the preregistered central OOS and topology economic gates.

This is the first SOL LONG result in the restarted lineage that is supported by actual WR/PF/expectancy rather than an H-visit proxy. It is still research-only and is not promoted to the live bot.

Research only. Live Baba Bot remains unchanged.
