# B27DF — F85 LONG Zone-Specific Causal Filter Screen — Preregistration

## Purpose
Test whether the two frozen LONG F85 Same-Bar Rejection zones can improve trading win rate toward ~75% by removing low-quality setups with a small, causal, interpretable filter menu, while explicitly limiting overfit.

B27DF does **not** change the underlying detector, clock geometry, F85/F35/E20 levels, execution rule, or fixed-E20 economics. It only asks whether a small subset of already-known causal context variables can remove losers.

## Frozen source cohorts
Use persisted B27DE cases only.

Zones:
1. `LONDON`: reference start 08:00 UTC (08:00-13:30 reference -> 13:30-20:00 execution).
2. `ALT_0330`: reference start 03:30 UTC (03:30-09:00 reference -> 09:00-15:30 execution).

Only rows with `entry_executed == True` and non-null `net_pnl_usd` are eligible trades.

Expected BASE development counts from B27DE:
- LONDON: N=30, WR=66.7%, PF~1.17.
- ALT_0330: N=37, WR=67.6%, PF~1.49.

B27DF must reproduce the exact BASE trade identities and economics before filters are interpreted.

## Causal context features
All features must be known no later than entry.

### 1. 4H regime at K1 signal
Use the existing B27AG `SwingRegime` semantics exactly:
- completed 4H UTC bars only
- EMA7 / EMA20
- swing lookback 5
- swing ATR separation 0.5
- ATR14
- BULL only with >=2 HH, >=2 HL, EMA7>EMA20, close>EMA20
- BEAR only with >=2 LH, >=2 LL, EMA7<EMA20, close<EMA20
- otherwise SIDEWAYS

Attach the latest regime whose availability timestamp is <= B27DE `k1_signal_ts`.

Define `NO_BEAR` = regime is BULL or SIDEWAYS.

### 2. Touch timing
`touch_elapsed = touch_bar_start - execution_start`.

Define `TOUCH_FIRST_HALF` = touch occurs in the first half of the frozen 6h30 execution window, i.e. elapsed <= 3h15m.

This is a fixed structural midpoint, not a fitted threshold.

### 3. Entry reward:risk geometry
Use the already-persisted causal `nominal_rr` from entry to frozen E20 versus F35 invalidation.

Define `RR_GE_050` = nominal_rr >= 0.50.

0.50 is frozen before results and is not swept.

## Frozen filter menu
Exactly eight variants are allowed in each zone:
1. `BASE`
2. `NO_BEAR`
3. `TOUCH_FIRST_HALF`
4. `RR_GE_050`
5. `NO_BEAR__TOUCH_FIRST_HALF`
6. `NO_BEAR__RR_GE_050`
7. `TOUCH_FIRST_HALF__RR_GE_050`
8. `TRIPLE_NO_BEAR__TOUCH_FIRST_HALF__RR_GE_050`

No other thresholds, indicators, candle-shape rules, weekdays, months, or neighboring clock changes may be introduced after seeing B27DF results.

## Zone-specific treatment rule
London and ALT_0330 are selected independently from the same frozen menu. They are allowed to choose different filters because the purpose is explicitly zone-specific treatment.

Selection uses **development only**.

A filtered variant is `DEV_75_ELIGIBLE` only if:
- retained N >= 20
- retention >= 60% of that zone's BASE development trades
- WR >= 75%
- PF >= 1.30
- mean net expectancy > 0

If multiple variants qualify in one zone, choose by:
1. highest WR
2. higher PF
3. higher expectancy
4. higher retention
5. simpler rule (fewer component filters)
6. lexical name as final deterministic tie-break

If no variant reaches 75%, report the best non-BASE development improvement but do not call it a 75% candidate.

## Historical replication guardrail
After development selection only, inspect the chosen rule unchanged in external and reference_validation.

`REPLICATION_SUPPORTED` requires in **both** external and reference_validation:
- N >= 10
- retention >= 45% of partition BASE trades
- WR >= 70%
- PF >= 1.20
- expectancy > 0

Because these partitions have been inspected before, this is historical replication evidence, not pristine OOS or live authorization.

A candidate that reaches 75% only in development but fails replication is explicitly rejected as likely unstable/overfit.

## Outputs
Persist:
1. exact BASE parity audit for both zones
2. one row per trade with regime/timing/RR features and pass flags
3. summary by zone x filter x partition
4. development selection table
5. selected-rule replication readout
6. status file

Report N, retention, wins, WR, PF, expectancy, total net, TP rate and time-exit rate.

## Guardrails
- LONG only.
- Same-Bar Rejection only.
- Fixed E20 / F35 economics only.
- No new clock scan.
- No continuous threshold sweep.
- No result-dependent filter invention.
- No live BBC change.
- Any follow-up mechanism requires a new experiment ID.

Research only; live BBC unchanged.
