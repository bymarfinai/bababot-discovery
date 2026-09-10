# ETH Economic-First E7 — Scientific Verdict

## Status
**ETH_ECONOMIC_FIRST_E7_CANDIDATE_NOT_REPLICATED**

Research/shadow only. No live promotion or profit guarantee.

## Frozen signal
- ETHUSDT Binance Futures raw 5m
- weekday anchor
- entry 17:00 UTC (00:00 WIB)
- pre-entry lookback 360m
- causal strength band B0_20 = [0.00, 0.20)
- MOMENTUM response
- exact 17:00 5m open entry
- NO static SL
- $500 fixed notional
- $0.75 round-trip fee

## Reproduction invariant
E6 seed TP0.60% / hold720m reproduced exactly enough for the preregistered invariant:
- N 153
- WR 78.43%
- net +$64.30
- expectancy +$0.42/trade
- PF 1.321
- max DD $44.43
- max loss streak 4
- 4/4 positive blocks

## Development refinement
49 preregistered TP x hold candidates were tested.
- ridge-gate passers: 6
- ridge + local-stability passers: 6

The deterministic Development winner was:
**TP0.65% / NO SL / hold600m**

Development metrics:
- N 153
- WR 76.47%
- net +$87.26
- expectancy +$0.57/trade
- PF 1.448
- max DD $41.75
- max loss streak 3
- 3/4 positive blocks
- local neighbors 4/4 supportive

## Historical replication
The frozen Development winner was opened unchanged on both holdouts.

### External
- N 95
- WR 72.63%
- net -$70.02
- expectancy -$0.74/trade
- PF 0.711
- max DD $101.80
- max loss streak 4
- FAIL

### Reference Validation
- N 84
- WR 66.67%
- net -$59.11
- expectancy -$0.70/trade
- PF 0.700
- max DD $111.98
- max loss streak 4
- FAIL

### Combined historical — descriptive only
- N 332
- WR 72.89%
- net -$41.87
- expectancy -$0.13/trade
- PF 0.934
- max DD $111.98
- max loss streak 4

## Scientific interpretation
The Development high-WR harvest ridge is real in-sample but does not replicate economically. High hit rate alone is insufficient: the OOS time-exit losers overwhelm the small fixed TP gains. No second-best TP/hold substitution is allowed after seeing holdouts.

The E7 ridge family is closed. The next investigation should return upstream and determine whether the E2 17:00/LB360 momentum anchor itself has cross-partition economic support before any further management optimization. Do not rescue E7 by relaxing holdout gates or trying another TP/hold on the already-opened holdouts.
