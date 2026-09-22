# SOL Derivatives Liquidity Layer V1 — Preregistration

## Objective

Test whether causal derivatives positioning contains **independent information** about whether an already-detected SOL liquidity setup becomes a profitable trade.

This is **not** a reset of the SOL detector and **not** an options-IV replication claim.

The current filtered SOL universe remains frozen:
- keep Score-3 BUY_SIDE;
- keep Score-3 SELL_SIDE Missing-A/B/D;
- reject Score-3 SELL_SIDE Missing-C;
- keep Score-4 SELL_SIDE/LONG;
- exclude Score-4 BUY_SIDE/SHORT.

Input:
`SOL_SCORE3_SELL_C_HARD_FAILURE_UNIVERSE_V1_Trades.csv`

## Exact-video track vs proxy track

### Exact-video track
The video appears to use option-chain implied volatility / positioning-derived price levels. Binance currently exposes live option mark IV/Greeks, but historical IV-chain snapshots are not available through the documented historical REST endpoints in a form sufficient for a full historical reconstruction.

Therefore V1 does **not** claim to reproduce the video's options model.

### Retrospective proxy track
V1 tests official Binance USD-M historical metrics as a distinct derivatives proxy:
- open interest;
- top-trader long/short positioning;
- global long/short ratio;
- taker buy/sell volume ratio.

These fields are tested only for information content.

## Causality lock

For an entry at timestamp `t_entry`:
- use only the latest completed 5-minute metrics observation strictly before `t_entry`;
- never forward-fill a metric from after entry;
- all deltas use only observations already available before entry;
- no future funding, liquidation, price path, or realized outcome may enter the feature set.

## Frozen features

All features are computed from official 5-minute metrics rows.

Raw:
1. `oi_value` = sum open-interest value.
2. `top_position_ratio` = sum top-trader long/short ratio.
3. `top_account_ratio` = count top-trader long/short ratio.
4. `global_account_ratio` = count global long/short ratio.
5. `taker_ratio` = taker buy/sell volume ratio.

Changes:
6. `oi_change_1h` = OI value / OI value 12 completed 5m rows earlier - 1.
7. `oi_change_4h` = OI value / OI value 48 completed 5m rows earlier - 1.
8. `taker_log` = ln(taker_ratio).
9. `global_log` = ln(global_account_ratio).
10. `top_position_log` = ln(top_position_ratio).

Direction-normalized hypotheses:
- SELL_SIDE liquidity implies LONG after downside sweep. Sweep pressure is negative-flow pressure into the low.
- BUY_SIDE liquidity implies SHORT after upside sweep. Sweep pressure is positive-flow pressure into the high.

11. `sweep_taker_pressure`:
   - LONG/SELL_SIDE = -ln(taker_ratio)
   - SHORT/BUY_SIDE = +ln(taker_ratio)

12. `sweep_crowd_pressure`:
   - LONG/SELL_SIDE = -ln(global_account_ratio)
   - SHORT/BUY_SIDE = +ln(global_account_ratio)

13. `sweep_top_position_pressure`:
   - LONG/SELL_SIDE = -ln(top_position_ratio)
   - SHORT/BUY_SIDE = +ln(top_position_ratio)

14. `oi_trap_interaction_1h` = oi_change_1h * sweep_taker_pressure.

No alternative lookbacks, nonlinear transforms, thresholds, or feature combinations may be introduced after outcomes are inspected in this V1.

## Outcome

Primary binary outcome:
- WIN = `realized_r > 0`
- LOSS = `realized_r <= 0`

Secondary continuous outcome:
- `realized_r`

## Evaluation

For each frozen feature:
- available N;
- winner median;
- loser median;
- median difference;
- Mann-Whitney rank AUC, oriented so AUC > 0.5 means larger feature values occur more often in winners;
- Spearman correlation with realized R.

Subgroups are reported descriptively only:
- BUY_SIDE / SHORT;
- SELL_SIDE / LONG;
- Score-3;
- Score-4 SELL_SIDE/LONG if sample exists.

## Frozen evidence gates

A feature is a **candidate information signal**, not a trading rule, only if:

1. available N >= 100;
2. pooled AUC is >= 0.58 or <= 0.42;
3. absolute Spearman rho with realized R >= 0.10;
4. sign of winner-vs-loser median difference agrees with the AUC direction;
5. the effect is not solely created by one calendar year:
   - at least 4 separate calendar years with >=10 available trades must have the same AUC direction (>0.5 or <0.5);
6. both directional sides with >=30 observations must not show strongly contradictory effects:
   - if pooled AUC > 0.5, neither qualifying side may have AUC < 0.45;
   - if pooled AUC < 0.5, neither qualifying side may have AUC > 0.55.

No WR target, filter cutoff, or economic promotion is allowed in V1.

## Decision

Possible statuses:
- `DERIVATIVES_INFORMATION_SIGNAL_FOUND`
- `DERIVATIVES_INFORMATION_WEAK_OR_UNSTABLE`
- `DERIVATIVES_ARCHIVE_INSUFFICIENT`

If a candidate information signal is found, the next experiment must preregister a fixed threshold or ranking rule **before** testing trade filtering/economics.

If not, derivatives proxy is not used to alter the SOL detector.

## Options capture

Separately, V1 may add a prospective SOL options-chain snapshot logger containing:
- option symbol;
- expiry;
- strike;
- call/put;
- bidIV;
- askIV;
- markIV;
- delta;
- gamma;
- vega;
- mark price;
- open interest where available;
- underlying index price;
- snapshot timestamp.

Prospective options data is not mixed retroactively into this historical V1 result.
