# SOL Full-Character Long V1 — Meaningful Sweep Confirmation Preregistration

## Objective
Test one separately frozen causal sub-character suggested by the completed V1 characterization, without threshold sweeping or changing the parent structure.

Parent structure and base trigger remain exactly:
**H1 bullish impulse -> H1 new high -> impulse-origin demand -> first fresh H1 pullback to demand -> 5m demand-low sweep/reclaim -> next 5m open LONG.**

New sub-character requirement at the already-causal 5m reclaim bar:
1. Sweep depth below H1 demand-low must be at least **0.25 x H1 demand-zone width**.
2. The reclaim candle's lower wick must be at least **50% of the full 5m candle range**.

These two constants are frozen as round structural semantics. No alternative values will be tested in this experiment.

## Methodological status
- This rule was motivated by the prior 109-trade characterization, so 2020-2024 is **development confirmation**, not untouched validation.
- No claim of independent validation may be made from this run.
- 2025+ remains CLOSED for a later explicit validation decision.

## Frozen data/economics
- SOLUSDT existing 5m dataset.
- Parent structure: exact `detect_full_character()` from Full-Character Long V1.
- Base trigger: exact `DEMAND_SWEEP_RECLAIM` from Full-Character Long V1.
- Evaluation years: 2020-2024.
- Entry: next 5m open after completed reclaim bar.
- Exit diagnostic: fixed +60m.
- Round-trip cost: 0.15%.
- $500 notional.
- No hour, EMA, RSI, Fibonacci, volume, regime, H4, TP/SL, or post-result rescue.

## Exact causal geometry
For each exact base sweep/reclaim event:
- `zone_width = demand_top - demand_low`.
- `sweep_depth = demand_low - trigger_low`.
- require `sweep_depth / zone_width >= 0.25`.
- `candle_range = trigger_high - trigger_low`.
- `lower_wick = min(trigger_open, trigger_close) - trigger_low`.
- require `lower_wick / candle_range >= 0.50`.
- base reclaim condition remains `trigger_low < demand_low` and `trigger_close > demand_low`.

If either geometry condition fails, there is no trade in this exact sub-character.

## Outputs
- base V1 sweep/reclaim N and economics reproduced,
- selected meaningful-sweep N and retention rate,
- pooled WR, expectancy, PF, PnL, DD, loss streak, MFE/MAE, clean impulse,
- yearly 2020/21/22/23/24 economics,
- comparison against the complementary non-selected base trades for diagnosis only.

## Frozen promotion gates
Keep the original strict V1 gates unchanged:
1. Selected N >= 100.
2. Pooled net +60m expectancy > 0.
3. PF >= 1.15.
4. Positive PnL in >= 4 of 5 years.
5. Median MFE/|MAE| >= 1.20.

`PASS_DEVELOPMENT_CONFIRMATION` requires all five, but still would not be final validation because the rule came from prior 2020-2024 characterization.
`REJECTED_AS_DEFINED` means do not rescue by changing 0.25, 0.50, hours, indicators, parent structure, entry, exit, TP or SL.

2025_PLUS=CLOSED