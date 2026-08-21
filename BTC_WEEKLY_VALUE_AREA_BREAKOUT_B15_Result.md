# BTC Weekly Value-Area Breakout B15 — Result

**Verdict: B15_NO_ROBUST_WEEKLY_100**

15m rows **232,608**, H1 execution rows **58,152**, 2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00.

Frozen setup: **VAH break -> LONG; VAL break -> SHORT; entry next H1 open.**

Frozen development PRIMARY_RULE: **H1|VAH_BREAK_LONG**

Frozen TOP4_ROUTER:
- 1. `H1|VAH_BREAK_LONG`
- 2. `H4|VAH_BREAK_LONG`
- 3. `H4|VAL_BREAK_SHORT`
- 4. `H1|VAL_BREAK_SHORT`

| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|
| PRIMARY_RULE | development | 156/156/100.00% | 71/85/0 | 45.51% | -0.09% | 0.835 | 6 |
| PRIMARY_RULE | external | 103/103/100.00% | 45/58/0 | 43.69% | -0.13% | 0.776 | 6 |
| PRIMARY_RULE | reference_validation | 81/81/100.00% | 39/42/0 | 48.15% | -0.04% | 0.929 | 7 |
| PRIMARY_RULE | august | 2/2/100.00% | 1/1/0 | 50.00% | 0.00% | 1.000 | 1 |
| TOP4_ROUTER | development | 156/156/100.00% | 73/83/0 | 46.79% | -0.06% | 0.880 | 5 |
| TOP4_ROUTER | external | 103/103/100.00% | 51/52/0 | 49.51% | -0.01% | 0.981 | 11 |
| TOP4_ROUTER | reference_validation | 81/81/100.00% | 38/43/0 | 46.91% | -0.06% | 0.884 | 7 |
| TOP4_ROUTER | august | 2/2/100.00% | 1/1/0 | 50.00% | 0.00% | 1.000 | 1 |

## All atomic rules — development ranking

| Rank | Rule | Coverage | WR | PF | N |
|---:|---|---:|---:|---:|---:|
| 1 | `H1|VAH_BREAK_LONG` | 100.00% | 45.51% | 0.835 | 156 |
| 2 | `H4|VAH_BREAK_LONG` | 100.00% | 44.87% | 0.814 | 156 |
| 3 | `H4|VAL_BREAK_SHORT` | 100.00% | 44.23% | 0.793 | 156 |
| 4 | `H1|VAL_BREAK_SHORT` | 100.00% | 43.59% | 0.773 | 156 |
| 5 | `W1|VAH_BREAK_LONG` | 52.56% | 59.76% | 1.485 | 82 |
| 6 | `D1|VAH_BREAK_LONG` | 98.72% | 53.25% | 1.139 | 154 |
| 7 | `D1|VAL_BREAK_SHORT` | 95.51% | 42.28% | 0.733 | 149 |
| 8 | `W1|VAL_BREAK_SHORT` | 53.21% | 36.14% | 0.566 | 83 |

## Gates

- B15_ROBUST_WEEKLY_100: **FAIL**
- B15_HIGH_PRECISION_WEEKLY: **FAIL**

No OOS retuning. Live BBC untouched.
