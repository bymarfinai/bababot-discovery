# ETH Discovery 2 — Z6 Money Geometry Preregistration

**PREREGISTERED before result-bearing execution.**

## Purpose
Translate the supported ETH Discovery 2 Z5 structural parent into a first broad economic geometry test without changing the frozen clock, structure, retest logic, or entry family.

Frozen parent:
- ETH-native Z1→Z4 structure;
- Z5 L06 resting pullback entry = H + 0.06R, active only after B00, maximum 30-minute order window;
- F95 and F90 remain alternative cohorts and are evaluated independently.

Z6 asks only:

> Given the supported L06 entry, which coarse R-normalized TP / SL / max-hold geometry produces the strongest stable Development economics and still replicates historically out of sample?

No leverage optimization, compounding, dynamic sizing, filters, weekday selection, clock retuning, or live promotion.

## Frozen economic assumptions
- Fixed margin = $10.
- Fixed leverage = 50x.
- Fixed notional = $500 per filled trade.
- No compounding.
- Round-trip trading cost = 0.15% of notional = $0.75 per completed trade, matching the conservative BTC money-geometry benchmark.
- If TP and SL are both touched in the same eligible 5m bar, SL is assumed first.
- Trades that do not hit TP or SL are closed at the last available completed 5m close at max-hold or execution_end, whichever comes first.
- No exit may use the L06 fill bar when the fill occurred intrabar; if the entry occurred at the bar open, that bar is eligible for exit evaluation.

## Frozen broad grid
Distances are measured from actual filled entry in units of that session's reference range R.

TP distance:
- 0.20R
- 0.30R
- 0.40R
- 0.50R
- 0.60R

SL distance:
- 0.15R
- 0.20R
- 0.25R
- 0.30R
- 0.40R

Max hold:
- 60 minutes
- 120 minutes
- 240 minutes

Cohort:
- F95
- F90

Total frozen candidate family = 2 × 5 × 5 × 3 = 150 configurations.

No grid extension or interpolation is allowed after holdout inspection. A later local refinement requires a separate preregistration and is allowed only around a Development-selected region.

## Metrics
For each configuration report:
- filled trades;
- TP / SL / timeout counts;
- net-positive / net-negative trades;
- net win rate;
- gross PnL;
- fees;
- net PnL;
- expectancy per trade;
- profit factor computed from net trade PnL;
- max drawdown on chronological cumulative net PnL;
- maximum loss streak;
- maximum win streak;
- four chronological Development block PnLs;
- number of positive Development blocks;
- average and median hold minutes;
- median realized gross return percentage.

## Development-only candidate gate
A configuration is eligible for Development selection only if:
- >=35 filled trades;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.20;
- max drawdown <= $40;
- >=3 of 4 chronological blocks positive.

Among eligible candidates select lexicographically:
1. highest net PnL;
2. highest PF;
3. lower max drawdown;
4. higher net win rate;
5. shorter max hold;
6. smaller SL distance;
7. smaller TP distance;
8. F95 before F90 as final deterministic tie break.

Selection is Development only. External and Reference Validation are invisible to selection.

## Historical replication
Freeze the selected cohort / TP / SL / hold and evaluate it unchanged on External and Reference Validation.

The Development-selected candidate is SUPPORTED only if BOTH holdouts independently satisfy:
- >=15 filled trades;
- net PnL > 0;
- expectancy > 0;
- PF >= 1.05.

Additionally, pooled historical holdouts (External + Reference Validation) must satisfy:
- net PnL > 0;
- PF >= 1.10.

No holdout rescue, no cohort switching, no alternate grid winner after inspection, and no gate relaxation.

## BTC comparison
For context only, not as a selection criterion, compare the final selected ETH configuration with the documented BTC Tuesday A3.9 preferred consistency variant under the same $500 notional and $0.75 round-trip fee assumption:
- BTC trades: 139
- BTC net WR: 56.83%
- BTC net PnL: +$95.734
- BTC expectancy: +$0.6887/trade
- BTC PF: 1.431
- BTC max DD: $31.636
- BTC max loss streak: 4

Raw net PnL is not considered directly comparable when trade counts differ; expectancy, PF, drawdown, WR, and net PnL per 100 trades are also reported.

## Scientific boundary
A SUPPORTED Z6 result is a validated coarse economic region, not a production strategy. If the Development winner sits on a search boundary or has an obvious stable neighborhood, a separate Z7 local refinement / robustness milestone may be preregistered. Otherwise the lineage stops or changes mechanism.

Research/shadow only.
