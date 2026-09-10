# ETH Economic-First E10B — Fine Cross-Era Region Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
E10A closed the 06:30 UTC / LB240 region because fine-scale clock/lookback perturbations did not form a stable plateau. E10B now tests the independent second E9 cross-era region around:

**13:00 UTC (20:00 WIB) / MOMENTUM / lookback30m / causal B40_60 / hold360m**.

E9 seed Development: N167 / WR57.4850% / net +$228.2516 / expectancy +$1.3668/trade / PF1.4316 / max DD $64.8184 / loss streak4, with all 2022/2023/2024 net-positive.

No OOS information from this coordinate has been used. External and Reference Validation remain closed until exactly one Development fine-grid winner is frozen.

## Frozen grammar
- ETHUSDT Binance Futures raw 5m.
- weekdays only.
- response: **MOMENTUM**.
- causal strength regime: **B40_60 = [0.40,0.60)** using the E3/E9 rolling same-clock percentile (prior 60 observations; minimum 40 history).
- exact 5m-open entry.
- exact-open time exit only.
- no TP / no SL / no H/L / no breakout / no retest / no EMA / no Fibonacci.
- $500 fixed notional.
- $0.75 round-trip fee.
- no compounding.

## Fine Development grid
### Entry clock UTC
`12:30, 12:45, 13:00, 13:15, 13:30`

Equivalent WIB:
`19:30, 19:45, 20:00, 20:15, 20:30`

### Pre-drive lookback
`15, 20, 30, 45, 60 minutes`

### Hold
`240, 300, 360, 420, 480 minutes`

Total = **125 candidates**.

Outer values are sentinels. E9 seed 13:00 / LB30 / hold360 is interior.

## Development era semantics
Development = calendar years 2022, 2023, 2024. Pre-entry, entry, and exit must all lie within the same calendar year for annual and aggregate Development statistics, exactly matching E9 semantics.

## Seed reproduction invariant
E9 seed must reproduce within floating tolerance:
- N167;
- WR 0.5748502994;
- net +228.251550;
- expectancy +1.366776;
- PF 1.431628;
- max DD 64.818446;
- loss streak4;
- 2022: N51 / WR0.5490196078 / exp+1.148787 / PF1.255699;
- 2023: N63 / WR0.5714285714 / exp+1.416923 / PF1.668686;
- 2024: N53 / WR0.6037735849 / exp+1.516929 / PF1.483765.

Failure invalidates the run.

## Development candidate gate
A candidate must satisfy ALL:
- >=140 trades;
- aggregate WR >=56.0%;
- net PnL >0;
- expectancy >=+$0.75/trade;
- PF >=1.25;
- max DD <=$100;
- max loss streak <=6;
- each 2022/2023/2024: >=40 trades, WR >=52.0%, net >0, expectancy >0, PF >=1.05.

## Fine local stability
Orthogonal adjacent fine-grid neighbors only.

A neighbor is supportive when:
- >=120 trades;
- WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- at least 2 of 3 Development years have positive net PnL.

Require >=4/6 supportive neighbors for an interior cell. For cells with fewer neighbors, require ceil(60%) and at least 2 when >=3 neighbors exist.

## Development selection
Among candidate-gate + local-stability passers, rank by:
1. highest minimum annual expectancy;
2. highest minimum annual WR;
3. highest aggregate expectancy;
4. highest aggregate WR;
5. highest PF;
6. lowest DD;
7. lowest loss streak;
8. shorter hold;
9. shorter lookback;
10. earlier clock.

## Boundary rule
If winner is on clock 12:30/13:30, LB15/60, or hold240/480, status is `ETH_ECONOMIC_FIRST_E10B_BOUNDARY_OPEN`; holdouts remain closed and no second-best substitution is allowed.

## Historical replication
For an interior winner, freeze coordinate unchanged and evaluate External and Reference Validation independently.

Each holdout must satisfy ALL:
- >=50 trades;
- WR >=55.0%;
- net PnL >0;
- expectancy >=+$0.50/trade;
- PF >=1.15;
- max DD <=$150;
- max loss streak <=8.

Both individual holdouts must pass. Pooled results cannot rescue an individual failure.

## Decision
- no Development plateau: `ETH_ECONOMIC_FIRST_E10B_NO_DEV_CANDIDATE`
- sentinel winner: `ETH_ECONOMIC_FIRST_E10B_BOUNDARY_OPEN`
- interior winner but holdout failure: `ETH_ECONOMIC_FIRST_E10B_CANDIDATE_NOT_REPLICATED`
- both holdouts pass: `ETH_ECONOMIC_FIRST_E10B_SUPPORTED`

Research/shadow only. No live promotion or profit guarantee.
