# BNB B28M — Frozen OOS Validation Preregistration

## Purpose
Validate the already-selected BNBUSDT LONG B28M character without any post-selection tuning.

## Frozen candidate
- Candidate: **B28M**
- Side: **LONG only**
- WIB habitat: **12:00–13:00**
- UTC quarter-hour anchors: **05:00, 05:15, 05:30, 05:45**
- Character: **RV_MID__RANGE_HIGH**
- Lookback: **30 minutes**
- Hold: **360 minutes**
- Notional: **$500**
- Cost: **$0.75 per trade**
- Selection source: Development only, 2022-01-01 <= entry/outcome < 2025-01-01

The candidate definition above is immutable for this OOS run.

## Data source and unseen intervals
Use the existing frozen loader from `research/eth_london_ny_liquidity_pressure_m1.py`, which reads Binance Vision USD-M futures 5-minute klines.

Primary OOS is the pooled union of the two partitions that were sealed during B28M selection:
1. **external**: 2020-01-01 <= timestamps/outcomes < 2022-01-01
2. **reference_validation**: 2025-01-01 <= timestamps/outcomes < 2026-07-30

`august` (2026-08-01 <= timestamps/outcomes < frozen loader END 2026-08-26) is reported as a **shadow diagnostic only** and must not alter the PASS/REJECT decision.

The gap 2026-07-30 through 2026-08-01 is not part of this validation.

## Anti-leak rules
- No parameter search on OOS.
- No change to hour, direction, character, lookback, hold, notional, or fee after seeing OOS.
- No ranking against other B28 candidates using OOS.
- Feature lookback and trade exit must both remain inside the evaluated partition, using the same boundary rules as Development.
- Any data/tooling repair may only restore the preregistered calculation; it may not create a new strategy variant.
- August shadow results are informational only.

## Frozen evaluation gates
The following gates are declared before OOS is evaluated.

### A. Data integrity
- Raw BNBUSDT 5m coverage from the existing loader must be >= 99.5%.
- No duplicate trade identity `(entry_ts, clock)` in the validation output.

### B. Each primary unseen partition
For both `external` and `reference_validation` independently:
- trades >= 40
- win rate >= 52%
- net PnL > $0
- expectancy > $0/trade
- profit factor >= 1.05

### C. Pooled primary OOS economics/risk
On `external + reference_validation` pooled chronologically:
- trades >= 160
- win rate >= 55%
- net PnL > $0
- expectancy >= $0.50/trade
- profit factor >= 1.20
- max drawdown <= $125
- max loss streak <= 8

### D. Quarter-hour anchor stability on pooled primary OOS
Each anchor is evaluable with >= 40 trades. A supportive anchor requires:
- win rate >= 52%
- net PnL > $0
- expectancy > $0/trade
- profit factor >= 1.05
- max drawdown <= $125
- max loss streak <= 10

Anchor gate requires:
- >= 3 evaluable anchors
- >= 3 supportive anchors

## Decision rule
- **PASS** only if A + B + C + D all pass.
- If data/tooling integrity fails, classify **DATA/TOOLING FAILURE**, not a fundamental strategy rejection.
- If data integrity is sound but one or more frozen performance/stability gates fail, classify **FUNDAMENTAL OOS REJECT**.
- PASS advances B28M to **Trade Construction**.
- Fundamental rejection promotes **B28I (08:00–09:00 WIB)** to the next OOS validation candidate.
- B28Q remains blocked while B28M or B28I is active.

No live orders are part of this validation.