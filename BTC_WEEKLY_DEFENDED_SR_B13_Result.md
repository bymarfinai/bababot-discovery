# BTC Weekly Defended S/R B13 — Result

Implementation revision **B13_V1_FIX1**.

Renumber note: preregistered logic was originally labeled defended-S/R B12, but a separate level-survival experiment had already occupied B12. Renumbering occurred before any valid defended-S/R result; trading logic is unchanged.

**Verdict: B13_DEFENDED_ORACLE_NOT_100**

Coverage **2020-01-01 00:00:00+00:00 -> 2026-08-19 23:00:00+00:00**, official Binance BTCUSDT H1 rows **58,152**.

Definition: H1/H4/D1/W1 displacement-origin or accepted polarity-flip zone; fresh first H1 revisit; no close through distal; directional H1 reclaim above/below proximal; body >=0.25 ATR; micro-BOS; next-H1-open execution; net +1.00% vs -1.00%; 0.15% fee; adverse-first; same-week exit.

## Stage A — defended-zone feasibility (hindsight outcome only; NOT a strategy)

| Partition | Weeks | Signal weeks | TP weeks | Signal coverage | Oracle TP coverage | Signals | TP signals | Median signals/week |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| development | 156 | 137 | 90 | 87.82% | 57.69% | 383 | 156 | 2.0 |
| external | 103 | 86 | 60 | 83.50% | 58.25% | 247 | 87 | 2.0 |
| reference_validation | 81 | 71 | 49 | 87.65% | 60.49% | 225 | 87 | 3.0 |
| august | 2 | 2 | 2 | 100.00% | 100.00% | 5 | 2 | 2.5 |

## Stage B — causal one-trade selectors

Development-frozen model threshold: quantile **0.000**, probability **0.198153**.

| Selector | Partition | Weeks/N/Coverage | TP/SL/TIME | WR | Exp | PF | Max LS |
|---|---|---:|---:|---:|---:|---:|---:|
| FIRST_DEFENSE | development | 156/137/87.82% | 51/86/0 | 37.23% | -0.26% | 0.593 | 7 |
| FIRST_DEFENSE | external | 103/86/83.50% | 33/53/0 | 38.37% | -0.23% | 0.623 | 7 |
| FIRST_DEFENSE | reference_validation | 81/71/87.65% | 26/45/0 | 36.62% | -0.27% | 0.578 | 10 |
| FIRST_DEFENSE | august | 2/2/100.00% | 2/0/0 | 100.00% | 1.00% | 999.000 | 0 |
| MODEL_TRIGGER | development | 156/137/87.82% | 51/86/0 | 37.23% | -0.26% | 0.593 | 7 |
| MODEL_TRIGGER | external | 103/86/83.50% | 33/53/0 | 38.37% | -0.23% | 0.623 | 7 |
| MODEL_TRIGGER | reference_validation | 81/71/87.65% | 26/45/0 | 36.62% | -0.27% | 0.578 | 10 |
| MODEL_TRIGGER | august | 2/2/100.00% | 2/0/0 | 100.00% | 1.00% | 999.000 | 0 |

## Source-zone counts

| TF | Origins | Flips | Defended signals |
|---|---:|---:|---:|
| H1 | 2653 | 1727 | 833 |
| H4 | 710 | 380 | 188 |
| D1 | 109 | 36 | 21 |
| W1 | 21 | 1 | 0 |

## Gates

- B13_DEFENDED_ORACLE_100: **FAIL**
- B13_ROBUST_WEEKLY_100: **FAIL**
- B13_HIGH_PRECISION_WEEKLY: **FAIL**

If the oracle gate fails, this frozen defended-S/R vocabulary itself does not contain a +1R winner in every week; selector tuning cannot mathematically rescue those zero-TP weeks.

No post-result retuning is promoted. Live BBC untouched.
