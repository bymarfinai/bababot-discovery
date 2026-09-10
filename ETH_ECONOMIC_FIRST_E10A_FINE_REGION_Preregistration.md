# ETH Economic-First E10A — Fine Cross-Era Region Refinement Preregistration

**PREREGISTERED before result-bearing execution.**

## Lineage and purpose
E9 searched 20,736 economic-first drive-response coordinates and found multiple cross-era-positive Development regions, but no coordinate passed the preregistered coarse-grid local-stability requirement. The strongest high-WR/economic seed was:

**06:30 UTC (13:30 WIB) / MOMENTUM / lookback 240m / causal strength B40_60 / hold720m**

E9 Development seed: N164 / WR60.3659% / net +$513.4872 / expectancy +$3.1310 per trade / PF1.9206 / max DD $80.8794 / max loss streak5; all 2022/2023/2024 economically positive.

E10A tests whether that region is a genuine fine-scale plateau rather than a coarse-grid isolated cell. It does not introduce H/L, range, breakout, retest, EMA, Fibonacci, TP, SL, or post-hoc filters.

External and Reference Validation remain closed until exactly one Development candidate is frozen.

## Frozen grammar
- ETHUSDT Binance Futures raw 5m.
- weekdays only.
- exact 5m-open entry.
- causal pre-entry drive-strength percentile using the same E3/E9 rolling history: prior 60 same-clock observations, minimum 40 historical observations.
- strength regime **B40_60 = [0.40, 0.60)** frozen.
- response **MOMENTUM** frozen.
- exact-open time exit only; no TP and no SL.
- $500 fixed notional.
- $0.75 round-trip fee.
- no compounding.

## Fine Development grid
### Entry clock UTC
`06:00, 06:15, 06:30, 06:45, 07:00`

Equivalent WIB:
`13:00, 13:15, 13:30, 13:45, 14:00`

### Pre-drive lookback
`180, 210, 240, 270, 300 minutes`

### Maximum hold / exact-open exit
`600, 660, 720, 780, 840 minutes`

Total = **125 candidates**.

Outer values in each dimension are sentinels. The original E9 seed 06:30 / LB240 / hold720 is interior.

## Development era construction
Development remains 2022-01-01 through 2024-12-31. For era metrics, pre-entry, entry, and exit must all remain inside the same calendar year, matching E9 semantics.

## Seed reproduction invariant
The exact E9 seed must reproduce within floating tolerance:
- trades 164;
- WR 0.6036585366;
- net PnL +513.487172;
- expectancy +3.131019;
- PF 1.920575;
- max DD 80.879419;
- max loss streak 5;
- 2022 N55 / WR 0.6363636364 / exp +5.428064 / PF 2.291820;
- 2023 N53 / WR 0.6226415094 / exp +3.035058 / PF 2.355878;
- 2024 N56 / WR 0.5535714286 / exp +0.965814 / PF 1.259965.

Failure invalidates the run.

## Development candidate gate
A candidate must satisfy ALL:
- trades >=140;
- aggregate net WR >=58.0%;
- aggregate net PnL >0;
- aggregate expectancy >=+$1.50/trade;
- aggregate PF >=1.40;
- max DD <=$100;
- max loss streak <=6;
- each of 2022, 2023, 2024: >=40 trades, WR >=52.0%, net PnL >0, expectancy >0, PF >=1.05.

## Fine local-stability test
Neighbors are only orthogonal adjacent cells in clock, lookback, and hold.

A neighbor is supportive when:
- trades >=140;
- aggregate WR >=55.0%;
- net PnL >0;
- expectancy >=+$0.75/trade;
- PF >=1.20;
- max DD <=$125;
- all three Development years have positive net PnL.

For an interior cell with six neighbors, at least **4/6** must be supportive. For boundary cells, require at least ceil(60%) supportive and never fewer than 2 when >=3 neighbors exist.

## Development selection
Among candidates passing both candidate and stability gates, rank lexicographically by:
1. highest minimum annual expectancy across 2022/2023/2024;
2. highest minimum annual WR;
3. highest aggregate expectancy;
4. highest aggregate WR;
5. highest PF;
6. lowest max DD;
7. lowest max loss streak;
8. shorter hold;
9. shorter lookback;
10. earlier clock.

## Boundary rule
If selected winner uses clock 06:00 or 07:00 UTC, lookback 180 or 300m, or hold600 or 840m, status is `ETH_ECONOMIC_FIRST_E10A_BOUNDARY_OPEN`; holdouts remain closed and no second-best substitution is allowed.

## Historical replication
For an interior winner, freeze clock/lookback/hold unchanged and open External and Reference Validation independently.

Each holdout must satisfy ALL:
- >=50 trades;
- net WR >=55.0%;
- net PnL >0;
- expectancy >=+$0.50/trade;
- PF >=1.15;
- max DD <=$150;
- max loss streak <=8.

Both must pass independently. Pooled results are descriptive only and cannot rescue an individual failure.

## Decision
- no Development candidate + plateau: `ETH_ECONOMIC_FIRST_E10A_NO_DEV_CANDIDATE`
- selected winner on sentinel: `ETH_ECONOMIC_FIRST_E10A_BOUNDARY_OPEN`
- interior winner but either holdout fails: `ETH_ECONOMIC_FIRST_E10A_CANDIDATE_NOT_REPLICATED`
- both holdouts pass: `ETH_ECONOMIC_FIRST_E10A_SUPPORTED`

If supported, freeze the economic character and compare full historical economics directly with BTC A3.9 before any downstream optimization.

Research/shadow only. No live promotion or profit guarantee.
