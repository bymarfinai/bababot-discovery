# B27DE — London Parity Arithmetic Correction

Recorded after the first B27DE run aborted at the mandatory London parity gate and **before any rotated-clock leaderboard or candidate result was persisted or inspected**.

## What happened
The B27DE preregistration correctly froze the known London -> New York SAME_BAR_REJECTION baseline at:
- pooled-major N = 68
- WR = 73.5%
- PF approximately 1.70
- expectancy approximately +$0.91/trade
- total net approximately +$61.80

However, the parenthetical arithmetic was typed incorrectly as `73.5% (47/68)`. The implementation copied that typo into two parity assertions.

The first B27DE run reproduced:
- external N = 27
- development N = 30
- reference_validation N = 11
- august N = 1
- pooled-major N = 68
- actual pooled-major wins = 50
- actual pooled-major WR = 0.735294 = 50/68 = 73.5%
- PF = 1.702098
- expectancy = +$0.908860/trade
- total = +$61.802481
- exact persisted SAME_BAR entry-timestamp identity = 69/69 including August

The run then aborted because it compared the correct 50 wins / 73.5% against the mistyped 47 wins / 69.1% assertion. No rotated-clock ranking was persisted, so no clock result was available to influence this correction.

## Frozen correction
Only the arithmetic identity is corrected:
- pooled-major wins expected: **50**
- pooled-major WR expected: **50/68 = 73.5294%**

Everything else in B27DE remains unchanged:
- 48 half-hour UTC clock placements
- reference duration 5h30m
- execution duration 6h30m
- K1 OPP0 -> causal leave -> pre-H2 F85 Same-Bar Rejection structure
- F85/F35/E20
- fixed-E20 economics
- development-only selection gate
- historical replication thresholds
- no regime filter
- LONG only
- no live BBC change

This is an implementation/parity arithmetic correction, not a result-dependent hypothesis change.
