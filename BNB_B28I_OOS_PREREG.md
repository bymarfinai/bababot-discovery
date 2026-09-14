# BNB B28I — Frozen OOS Validation Preregistration

## Purpose
Validate the already-selected BNBUSDT LONG B28I character without any post-selection tuning.

## Frozen candidate
- Candidate: **B28I**
- Side: **LONG only**
- WIB habitat: **08:00–09:00**
- UTC quarter-hour anchors: **01:00, 01:15, 01:30, 01:45**
- Character: **RV_HIGH__RANGE_MID**
- Lookback: **360 minutes**
- Hold: **720 minutes**
- Notional: **$500**
- Cost: **$0.75 per trade**
- Selection source: Development only, 2022-01-01 <= entry/outcome < 2025-01-01

The candidate definition above is immutable for this OOS run.

## Data source and unseen intervals
Use the existing frozen loader from `research/eth_london_ny_liquidity_pressure_m1.py`, reading Binance Vision USD-M futures 5-minute klines.

Primary OOS is the pooled union of the two partitions sealed during selection:
1. **external**: 2020-01-01 <= timestamps/outcomes < 2022-01-01
2. **reference_validation**: 2025-01-01 <= timestamps/outcomes < 2026-07-30

`august` (2026-08-01 <= timestamps/outcomes < frozen loader END 2026-08-26) is a **shadow diagnostic only** and cannot alter PASS/REJECT.

## Anti-leak rules
- No parameter search on OOS.
- No change to hour, direction, character, lookback, hold, notional, or fee after seeing OOS.
- No ranking against B28M or other B28 candidates using OOS.
- Feature lookback and trade exit must both stay inside the evaluated partition.
- Tooling repairs may restore only this preregistered calculation, not create a new strategy variant.

## Frozen gates
### A. Data integrity
- Raw BNBUSDT 5m coverage >= 99.5%.
- No duplicate trade identity `(entry_ts, clock)`.

### B. Each primary unseen partition
For both `external` and `reference_validation` independently:
- trades >= 40
- win rate >= 52%
- net PnL > $0
- expectancy > $0/trade
- profit factor >= 1.05

### C. Pooled primary OOS
- trades >= 160
- win rate >= 55%
- net PnL > $0
- expectancy >= $0.50/trade
- profit factor >= 1.20
- max drawdown <= $125
- max loss streak <= 8

### D. Quarter-hour stability on pooled primary OOS
Each anchor is evaluable with >=40 trades. A supportive anchor requires WR>=52%, net>0, exp>0, PF>=1.05, DD<=125, loss streak<=10. Gate requires >=3 evaluable and >=3 supportive anchors.

## Decision
- **PASS** only if A+B+C+D pass.
- Sound data + any frozen gate failure = **FUNDAMENTAL OOS REJECT**.
- Data/tooling failure is classified separately.
- PASS -> Trade Construction.
- Fundamental rejection -> do not tune B28I; return to the frozen candidate inventory for the next independent candidate decision.
- No live orders are part of validation.
