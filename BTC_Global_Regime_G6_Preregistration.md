# BTC Global/Pooled Regime Engine — G6 Preregistration

**Status: PREREGISTERED BEFORE G6 EXECUTION — research only; live BBC untouched.**

## Why G6 exists
G1 proved that pooled hourly market-state classification contains modest causal pseudo-OOS information. G1/G2/G3 showed that a single Tuesday snapshot is not sufficiently aligned with frozen A5.11 economics. G4 showed that A5.11 is not a general all-hours strategy. G5 showed that point-in-time pSELL can slightly improve capital efficiency but does not improve full-sample drawdown/risk-adjusted return.

The remaining original regime-shift hypothesis is slower:

> August may reflect a persistent market environment change that is not captured by one timestamp. A weekly temporal edge should be conditioned on the **market regime accumulated over the preceding week**, learned from all hourly states.

G6 tests exactly one slow-state definition and does not sweep lookbacks.

## Frozen inputs
- G1 causal pooled hourly predictions unchanged.
- For each historical hour, use its already-produced `p_sell` and causal training-only `baseline_p_sell`.
- Frozen Tuesday A5.11 PnL stream unchanged.
- No new historical model fitting for the primary walk-forward test.
- No G1 threshold/model/feature changes.

## Slow regime-health feature — locked
For each eligible Tuesday 06:00 WIB opportunity at timestamp `t`, use the **168 completed hourly G1 predictions strictly before t** (the preceding 7×24 hours).

For each hourly state `h` define:

`SELL_DELTA_h = p_sell_h - baseline_p_sell_h`

Define weekly health:

`WEEKLY_SELL_HEALTH = mean(SELL_DELTA_h over the prior 168 hours)`

Eligibility requires all 168 consecutive hourly predictions. Early Tuesdays without a full causal 168h prediction history are excluded from both baseline and G6 comparison.

### Locked decision
- `WEEKLY_SELL_HEALTH >= 0` => **TRADE**
- `WEEKLY_SELL_HEALTH < 0` => **WAIT**

Zero is the natural no-lift boundary: over the preceding week, the pooled model must on average assign SELL compatibility at least its own causal base rate.

No other lookback (24h/72h/14d/30d), statistic (median/min), threshold, or smoothing parameter is tested inside G6.

## Historical evaluation — locked
Compare on the exact same eligible Tuesday subset:
1. Always-trade frozen A5.11.
2. G6 weekly-health gate.

Report:
- eligible opportunities,
- trades/waits/coverage,
- WR,
- PnL,
- expectancy per opportunity,
- expectancy per trade,
- PF,
- max drawdown,
- distribution of weekly health,
- outcome attribution for health >=0 vs <0.

## Four chronological Tuesday blocks
Split the eligible Tuesday stream into four consecutive approximately equal blocks and report G6 PnL delta versus always-trade.

## G6 shadow-promotion gate — locked
All conditions must pass:

1. At least **120** eligible historical Tuesday opportunities.
2. G6 trade coverage >= **35%**.
3. G6 expectancy per opportunity > always-trade A5.11 on the same subset.
4. G6 total PnL >= always-trade A5.11 on the same subset.
5. G6 trade WR > always-trade A5.11.
6. G6 max drawdown < always-trade A5.11.
7. PnL delta versus always-trade is positive in at least **3 of 4** chronological blocks.

Passing means a SHADOW CANDIDATE only.

## August 2026 — report only
For the August diagnostic, use one final pooled G1 model fitted only through the Jul-30 cutoff and frozen thereafter.

At each Aug 4/11/18 Tuesday timestamp:
- score every hourly state required for the preceding 168h window with that already-frozen final model as information available by the August decision time;
- use the frozen historical SELL prior through Jul-30 as `baseline_p_sell`;
- compute the same mean weekly SELL delta;
- apply the locked zero threshold;
- report TRADE/WAIT and frozen A5.11 PnL.

No August outcome is used to fit/refit the model or select the 168h window.

## Explicitly prohibited
- alternative rolling windows,
- threshold sweeps,
- percentile/quantile gates,
- adding current Tuesday outcome history,
- fitting a model to weekly-health values,
- changing A5.11,
- changing G1,
- August-driven changes,
- touching live BBC.

If G6 fails, preserve it. The slow-regime hypothesis under this natural weekly specification is then not promoted; any later multi-timescale or online health design must be separately preregistered.
