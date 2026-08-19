# BTC AOH2 — Asia Open HIGH Context Optimization Preregistration

**FROZEN BEFORE RESULT. Research-only. Live BBC untouched. No 1m data.**

## Objective
Find the most defensible fixed values for the two pre-anchor context variables already exposed by Session Archetype Map V1 for `ASIA_OPEN + HIGH_IMMEDIATE_RECLAIM`, without adding new indicators or altering the core event.

## Frozen core setup
BTCUSDT USD-M perpetual, official Binance Futures 5m data aggregated to completed 15m candles.

For every UTC day:
1. Previous completed UTC-day HIGH/LOW are frozen at 00:00 UTC.
2. During the first 90 minutes after Asia Open (00:00-01:30 UTC), find the first completed 15m candle that:
   - trades strictly above previous-day HIGH;
   - closes strictly back below previous-day HIGH.
3. SHORT at the next causal 15m open.
4. Structural SL = reclaim/sweep candle HIGH.
5. Modeled round-trip fee = 0.15%.
6. TP is sized so modeled **net reward equals net loss magnitude (net RR 1:1)**:
   - structural risk fraction `r = (SL-entry)/entry`;
   - raw TP distance = `r + 0.0030`;
   - SHORT TP = `entry * (1 - (r + 0.0030))`.
7. Max hold 6h; same-5m TP/SL ambiguity is adverse/SL first.

No second confirmation candle is used; AOH1 already rejected that path.

## Two frozen context dimensions
Measured strictly at the Asia Open anchor, before the sweep window begins.

### PRE_UP_60 return
`pre60 = anchor_price / price_60m_before_anchor - 1`.
Candidate minimum thresholds:
- 0.00%
- 0.05%
- 0.10%
- 0.15%
- 0.20%
- 0.30%
- 0.50%

### Previous-day range location
`location = (anchor_price - previous_day_LOW) / (previous_day_HIGH - previous_day_LOW)`.
Candidate minimum thresholds:
- 0.70
- 0.75
- 0.80
- 0.85
- 0.90
- 0.95

Exactly 42 combinations are evaluated. No other threshold is searched.

## Evidence partitions
### Reference period
`2023-12-02 <= date < 2026-07-30`.
This is the period that identified `ASIA_OPEN HIGH` as the strongest session-sweep cell, so it cannot alone validate the optimized threshold.

Reference events are split chronologically by event order:
- first 70% = **development**;
- last 30% = **reference validation**.

### External historical validation
`2022-01-01 <= date < 2023-12-02`.
This period was not used to select the Asia Open HIGH cell and is the primary independent historical check.

### August post-cutoff
`2026-08-01 <= date < 2026-08-20`, restricted to completed official archives available at runtime.

## Frozen selection rule
For every grid combination on the **development** events only:
- require confirmed trade N >=12;
- compute decisive WR and 95% Wilson lower bound for the binomial win rate;
- compute net expectancy/trade and PnL.

Select exactly one combination by:
1. highest Wilson lower bound;
2. then higher development decisive WR;
3. then higher development N;
4. then higher development expectancy/trade;
5. then **less restrictive** thresholds (lower pre60 minimum, then lower location minimum) as final tie-breakers.

Validation/external/August outcomes are never used to select thresholds.

## Required reporting
- all 42 development combinations, sorted by frozen selector;
- exact selected thresholds;
- development / reference validation / external / August results for the selected thresholds;
- unfiltered core setup in the same partitions as control;
- TP/SL/TIME, decisive WR, Wilson interval, net-positive rate, expectancy, PnL, median structural risk, mean raw TP distance;
- four chronological blocks for external selected-rule trades;
- every August qualifying setup.

## Interpretation gates
`AOH2_CONTEXT_SUPPORTED` requires selected rule:
- reference-validation decisive N >=8 and WR >=60%;
- external decisive N >=12 and WR >=60%;
- positive external expectancy and PnL;
- at least 3/4 external blocks non-negative expectancy when block N>0.

`AOH2_80_CANDIDATE` requires:
- reference-validation decisive N >=8 and WR >=80%;
- external decisive N >=12 and WR >=80%;
- positive PnL in both;
- no causality/integrity violations.

If external sample is below N12, the rule cannot be labeled 80% even if observed WR is high.

## Guardrails
- no 1m data;
- no Asia-open time shift;
- no 90m event-window change;
- no alternate level definition;
- no additional confirmation;
- no wick/body/EMA/taker/OI/funding/premium feature;
- no RR/fee/hold sweep;
- no threshold outside the frozen grid;
- no post-result weekday/weekend carve-out;
- no direction flip;
- no live BBC changes.

CI trigger note only; research rules above are unchanged.
