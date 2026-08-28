# B27EV — BNB Session-Native MICRO_HL_BULL Loss Conversion Discovery

## Objective
Convert as many of the **25 development net losses** from frozen B27ET into **actual net wins** while preserving as many of the original **25 development net winners** as possible.

This is a **development-only discovery milestone**. It does not reveal external, reference-validation, or August data and cannot validate any intervention.

## Frozen baseline
- Pair: BNBUSDT
- Structure: B27EM London→New York K1→causal leave
- Entry: B27EO `E5_MICRO_HL_BULL`
- Original execution: next 5m open after completed MICRO_HL_BULL signal
- TP: `H + 0.30R`
- SL: `entry - 0.30R`
- Round-trip fee: 0.10%
- Slippage: 0.05%
- Total cost: 0.15% per completed trade
- Same-bar TP/SL: SL wins
- Session-close unresolved exit retained
- Development integrity target: exactly 50 opportunities = 25 baseline net wins + 25 baseline net losses.

## Fixed intervention menu
No thresholds may be added after seeing results.

### Entry-confirmation interventions
These replace the original next-open entry. If no confirmed fill occurs before NY close, the opportunity is recorded as `NO_TRADE`, not as a converted win.

1. `C1_CLOSE_ABOVE_SIGNAL_HIGH`
   - After the original MICRO_HL signal completes, wait for the first later completed 5m candle with `close > original_signal_high`.
   - Enter at the next 5m open.
   - Use the same TP `H+0.30R` and same SL distance `0.30R` from the new entry.

2. `C2_SECOND_BULL_PROGRESS`
   - After the original MICRO_HL signal completes, wait for the first later completed bullish 5m candle satisfying `close > original_signal_close` and `close > previous_close`.
   - Enter at the next 5m open.
   - Same TP and SL rules.

3. `C3_CLOSE_ABOVE_PREV_HIGH`
   - After the original signal completes, wait for the first later completed 5m candle with `close > original_previous_bar_high`.
   - Enter at the next 5m open.
   - Same TP and SL rules.

### Trade-management interventions
These keep the original entry unchanged.

4. `M1_H_TOUCH_LOCK_005R`
   - Once a completed post-entry 5m candle has touched `H`, from the **next bar onward** raise stop to `entry + 0.05R`, but only if that stop is below the completed trigger candle close.
   - Original TP remains `H+0.30R`.

5. `M2_H10_TOUCH_LOCK_H`
   - Once a completed post-entry bar has touched `H+0.10R`, from the next bar onward raise stop to `H`, only if `H` is below the completed trigger candle close.
   - Original TP remains.

6. `M3_PARTIAL50_AT_H`
   - On first touch of H, close 50% at H.
   - Remaining 50% keeps original TP and SL.
   - Apply 0.15% total round-trip cost proportionally to each closed fraction.

7. `M4_PARTIAL50_AT_H10`
   - On first touch of `H+0.10R`, close 50% there.
   - Remaining 50% keeps original TP and SL.
   - Same proportional cost accounting.

### One-retry intervention
8. `R1_ONE_FRESH_MICROHL_AFTER_SL_BEFORE_H`
   - Keep original trade.
   - Only if the original trade exits by SL **before H was reached**, allow exactly one fresh `MICRO_HL_BULL` signal after the SL exit and before NY close.
   - Fresh signal uses the same causal MICRO_HL definition and enters at its next 5m open.
   - Retry uses TP `H+0.30R`, SL `0.30R`, same costs.
   - Opportunity PnL = first trade + retry trade. It counts as loss→win only if combined net PnL > 0.

## Causal execution rules
- Completed bars only may trigger confirmation or management changes.
- A confirmation detected on bar N can only enter at bar N+1 open.
- A stop change triggered by completed bar N is active only from bar N+1 onward.
- Partial exits at H/H+0.10R are allowed on the first touch because the fill price is the predefined level; if the same bar also touches original SL before that level, conservative ordering gives SL precedence unless prior state already guarantees the partial level was reached on an earlier completed bar.
- No lower-timeframe ordering assumptions.

## Scorecard
For each intervention report:
- original losses converted to net wins (`L→W`) — **primary objective**
- original losses converted to no-trade (`L→NT`) separately
- original winners retained as net wins (`W→W`)
- original winners damaged to net loss (`W→L`)
- resulting net-win opportunities / 50
- executed trades / opportunities
- net WR on executed opportunities
- average net return per opportunity
- total PnL @ $500 notional per trade leg
- profit factor where defined.

## Discovery ranking
Rank interventions lexicographically by:
1. highest `L→W`,
2. highest `W→W`,
3. highest resulting net-win opportunities,
4. highest average net return per opportunity.

A no-trade is **never** counted as a converted win.

## Interpretation
B27EV may nominate a descriptive loss-conversion leader only. Any selected intervention must be frozen in a later milestone before any untouched holdout economics is opened.

STOP after reporting the intervention comparison. No external/reference/August reveal, no threshold tuning, no combining multiple interventions after seeing results, no SHORT/live integration.