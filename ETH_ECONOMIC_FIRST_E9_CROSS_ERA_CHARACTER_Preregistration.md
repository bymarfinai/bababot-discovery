# ETH Economic-First E9 — Cross-Era Economic Character Search Preregistration

**PREREGISTERED before result-bearing execution.**

## Scientific purpose
E8 proved that the attractive E2 aggregate winner `17:00 UTC / LB360 / MOMENTUM / hold720m` was Development-specific and did not replicate on either historical holdout. E9 changes the discovery protocol rather than rescuing that coordinate.

The question is:

> **Can ETH reveal a clock / pre-drive / response / hold character whose WR and economics repeat inside each Development era before any candidate is exposed to External or Reference Validation?**

No H/L/reference range/breakout/retest/EMA/Fibonacci is used.

## Data and economics
- ETHUSDT Binance Futures raw 5m.
- Weekdays only.
- Fixed $500 notional.
- $0.75 round-trip fee on every trade.
- No compounding.
- Exact 5m open entry and exact 5m open time exit.
- Development remains 2022-01-01 through 2024-12-31.
- Development era audit is fixed as calendar years **2022, 2023, 2024**.
- External = 2020-01-01 through 2021-12-31.
- Reference Validation = 2025-01-01 through 2026-07-29.

## Candidate grammar
### Entry clock
Every 30 minutes UTC: 48 clocks.

### Pre-entry lookback
`15, 30, 60, 120, 240, 360 minutes`.

### Response
- `MOMENTUM`: trade in the sign of the pre-entry return.
- `REVERSAL`: trade opposite the sign of the pre-entry return.

### Causal drive-strength regime
Strength is the percentile rank of the absolute pre-drive return against the prior 60 same-clock/lookback observations, using only observations available before the current entry. Minimum prior history = 40.

Six mutually interpretable regimes are tested:
- `ALL`: no strength filter, causal-history availability still required;
- `B0_20`: [0.00, 0.20);
- `B20_40`: [0.20, 0.40);
- `B40_60`: [0.40, 0.60);
- `B60_80`: [0.60, 0.80);
- `B80_100`: [0.80, 1.00].

These are exclusive bands, not post-hoc thresholds.

### Hold
`60, 120, 240, 360, 720, 960 minutes`.

Total Development universe: **48 × 6 × 2 × 6 × 6 = 20,736 candidates**.

## Development era semantics
A trade belongs to a Development era only if its pre-entry timestamp, entry timestamp, and exit timestamp are all contained inside the same calendar year. This prevents a year-end trade from borrowing outcome from the following era.

The causal strength computation may use earlier observations because that is information available in a live chronological replay; candidate outcome selection is still based only on Development trades.

## Cross-era gate
A candidate must satisfy ALL aggregate Development requirements:
- >= 140 trades;
- net WR >= 55.0%;
- net PnL > 0;
- expectancy >= +$0.25/trade;
- PF >= 1.20;
- max DD <= $100;
- max loss streak <= 8.

And for **each** of 2022, 2023, 2024 independently:
- >= 40 trades;
- WR >= 52.0%;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.05.

No aggregate result may rescue a losing Development year.

## Local stability
Neighbors preserve response mode and strength regime and vary only one coordinate at a time:
- clock ±30m (cyclic);
- adjacent lookback;
- adjacent hold.

A neighbor is supportive when:
- >=120 Development trades;
- aggregate WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- at least 2/3 Development calendar years have positive net PnL.

Require >=60% supportive neighbors, with a minimum of 3 when >=5 neighbors exist and minimum 2 when 3–4 exist.

## Selection
Among candidates passing both cross-era and local-stability gates, rank lexicographically by:
1. highest **minimum calendar-year expectancy** (maximin persistence);
2. highest **minimum calendar-year WR**;
3. highest aggregate expectancy / net-per-100;
4. highest aggregate WR;
5. highest aggregate PF;
6. lowest max DD;
7. lowest max loss streak;
8. larger trade count;
9. shorter hold;
10. shorter lookback;
11. earlier UTC clock;
12. MOMENTUM before REVERSAL only as final deterministic tie-break.

Exactly one Development winner may be frozen.

## Boundary rule
If the winner uses lookback 15m or 360m, or hold 60m or 960m, status is `ETH_ECONOMIC_FIRST_E9_BOUNDARY_OPEN`; holdouts remain closed. No second-best substitution.

Clock is cyclic and strength bands are complete partitions, so they have no artificial boundary rule.

## Historical replication
Only for an interior frozen winner, evaluate External and Reference Validation independently with unchanged clock/lookback/mode/strength-band/hold.

Each holdout must satisfy ALL:
- >=50 trades;
- WR >=52.0%;
- net PnL >0;
- expectancy >0;
- PF >=1.05;
- max loss streak <=10.

Both must pass independently. Pooled history is descriptive only and cannot rescue either holdout.

## Decision
- no Development candidate → `ETH_ECONOMIC_FIRST_E9_NO_DEV_CANDIDATE`;
- winner at lookback/hold sentinel → `ETH_ECONOMIC_FIRST_E9_BOUNDARY_OPEN`;
- interior winner but either holdout fails → `ETH_ECONOMIC_FIRST_E9_CANDIDATE_NOT_REPLICATED`;
- both pass → `ETH_ECONOMIC_FIRST_E9_SUPPORTED`.

The objective is high WR plus healthy economics that persist through time. Research/shadow only; no live promotion or profit guarantee.
