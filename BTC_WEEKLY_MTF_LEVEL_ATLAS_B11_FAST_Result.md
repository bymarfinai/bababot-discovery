# BTC Weekly MTF Level Atlas B11 — Result

Implementation revision **B11_FAST1** (performance-only; preregistered logic unchanged).

**Verdict: B11_NO_ROBUST_WEEKLY_100**

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00**, official Binance BTCUSDT H1 rows **58,152** (includes 2019 prehistory for causal level state).

Execution: level signal on completed H1; next-H1-open; net target +1.00%; net loss -1.00%; fee 0.15%; adverse-first; same-week exit.

Frozen development PRIMARY_RULE: **H1|SWING2_HIGH|SUPPORT|BODY**

Frozen development TOP4_ROUTER:
- 1. `H1|SWING2_HIGH|SUPPORT|BODY`
- 2. `H1|PREV_HIGH|RESISTANCE|HOLD`
- 3. `H1|PREV_OPEN|RESISTANCE|BODY`
- 4. `H1|R6_HIGH|SUPPORT|BODY`

## Selected-rule performance

| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|
| PRIMARY_RULE | development | 156/156/100.00% | 76/80/0 | 48.72% | -0.03% | 0.950 | 7 |
| PRIMARY_RULE | external | 103/103/100.00% | 38/65/0 | 36.89% | -0.26% | 0.585 | 6 |
| PRIMARY_RULE | reference_validation | 81/81/100.00% | 35/46/0 | 43.21% | -0.14% | 0.761 | 9 |
| PRIMARY_RULE | august | 2/2/100.00% | 1/1/0 | 50.00% | 0.00% | 1.000 | 1 |
| TOP4_ROUTER | development | 156/156/100.00% | 73/83/0 | 46.79% | -0.06% | 0.880 | 6 |
| TOP4_ROUTER | external | 103/103/100.00% | 48/55/0 | 46.60% | -0.07% | 0.873 | 6 |
| TOP4_ROUTER | reference_validation | 81/81/100.00% | 32/49/0 | 39.51% | -0.21% | 0.653 | 6 |
| TOP4_ROUTER | august | 2/2/100.00% | 2/0/0 | 100.00% | 1.00% | 999.000 | 0 |

## Development top 10 frozen rule ranking

| Rank | Rule | Coverage | WR | Wilson LB | PF | N |
|---:|---|---:|---:|---:|---:|---:|
| 1 | `H1|SWING2_HIGH|SUPPORT|BODY` | 100.00% | 48.72% | 41.00% | 0.950 | 156 |
| 2 | `H1|SWING2_HIGH|SUPPORT|HOLD` | 100.00% | 48.08% | 40.38% | 0.926 | 156 |
| 3 | `H1|SWING2_HIGH|SUPPORT|RECLAIM` | 100.00% | 48.08% | 40.38% | 0.926 | 156 |
| 4 | `H1|PREV_HIGH|RESISTANCE|HOLD` | 100.00% | 48.08% | 40.38% | 0.926 | 156 |
| 5 | `H1|PREV_HIGH|RESISTANCE|RECLAIM` | 100.00% | 48.08% | 40.38% | 0.926 | 156 |
| 6 | `H1|PREV_HIGH|RESISTANCE|WICK` | 100.00% | 46.79% | 39.14% | 0.880 | 156 |
| 7 | `H1|PREV_HIGH|SUPPORT|BODY` | 100.00% | 46.15% | 38.52% | 0.857 | 156 |
| 8 | `H1|PREV_HIGH|SUPPORT|HOLD` | 100.00% | 46.15% | 38.52% | 0.857 | 156 |
| 9 | `H1|PREV_HIGH|SUPPORT|RECLAIM` | 100.00% | 46.15% | 38.52% | 0.857 | 156 |
| 10 | `H1|PREV_OPEN|RESISTANCE|BODY` | 100.00% | 46.15% | 38.52% | 0.857 | 156 |

## Gates

- B11_ROBUST_WEEKLY_100: **FAIL**
- B11_HIGH_PRECISION_WEEKLY: **FAIL**

No post-result atlas row is promoted. Atlas diagnostics are persisted separately for follow-up preregistration only.

Live BBC untouched.
