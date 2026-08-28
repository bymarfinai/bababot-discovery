# B27EX — BNB Session-Native LONG M12 Conditional Repair Trigger Discovery

## Purpose
Development-only discovery of a **conditional repair trigger** for the frozen `E5_MICRO_HL_BULL` baseline. The goal is not to skip losing opportunities, but to keep the original entry and only switch into repair mode after the already-open trade shows a causal adverse move **before reaching H**.

## Frozen baseline
- Population: BNB development partition only, 2022-01-01 → 2025-01-01.
- Entry: frozen `E5_MICRO_HL_BULL` from B27EO/B27ES.
- Baseline TP: `H + 0.30R`.
- Baseline SL: `entry - 0.30R`.
- Total completed-trade cost: 0.15% per leg.
- Expected baseline integrity: 50 opportunities, 25 net winners, 25 net losers, including 19 losses that fail before H.

## Conditional-repair mechanics
The original baseline position is opened normally. Repair is considered only while the original trade has **not yet reached H**.

Four preregistered adverse triggers are tested independently:
- `T05_EXIT_REENTER_FRESH_MICROHL`: adverse level `entry - 0.05R`.
- `T10_EXIT_REENTER_FRESH_MICROHL`: adverse level `entry - 0.10R`.
- `T15_EXIT_REENTER_FRESH_MICROHL`: adverse level `entry - 0.15R`.
- `T20_EXIT_REENTER_FRESH_MICROHL`: adverse level `entry - 0.20R`.

### Causal trigger rule
A trigger can fire only on a **completed 5m bar** after entry where:
1. the bar low is at or below the adverse trigger level;
2. the bar high remains strictly below H;
3. the original baseline stop was not touched on that bar.

If H and the adverse level are both touched in the same 5m bar, no repair decision is made from that bar because ordering is ambiguous. If the original stop is touched, baseline SL owns the bar.

When a valid trigger bar completes:
- Exit the original position at the **next 5m open** (one completed trade leg, including 0.15% cost).
- From that point forward, wait for the first **fresh MICRO_HL_BULL**: current bar low > previous bar low, current close > previous close, and current close > current open.
- Enter the repair leg at the next 5m open.
- Repair-leg TP remains `H + 0.30R`.
- Repair-leg SL is `repair_entry - 0.30R`.
- Same-bar TP/SL on the repair leg is conservative: SL wins.
- At most one repair re-entry is allowed.
- If no fresh Micro-HL occurs before NY close, there is no second leg; the opportunity result is the realized first-leg result.

If no valid trigger occurs before H or before the baseline exit, the opportunity remains exactly the baseline trade.

## Primary scoring
For each trigger, report transition counts relative to the same 50 baseline opportunities:
- original loss → actual net win (`L→W`) — primary objective;
- failed-before-H original loss → actual net win (`FBH L→W`);
- original winner retained as net win (`W→W`);
- original winner damaged to net loss (`W→L`);
- total net-positive opportunities out of 50;
- opportunity-level WR, average net return, total PnL at illustrative $500 notional, and profit factor;
- trigger activation counts in baseline winners vs baseline losers;
- number of repair re-entries.

A no-reentry case is **not** counted as a conversion unless the total realized opportunity PnL is actually net positive.

## Discovery ranking
Rank candidates by:
1. highest `L→W`;
2. highest `FBH L→W`;
3. highest `W→W`;
4. highest total net-positive opportunities;
5. highest average net return per opportunity.

This is development discovery only. **No trigger is validated or promoted in B27EX.** No thresholds will be changed after seeing results.

## Stop conditions
B27EX does not:
- combine conditional repair with partial exits or other B27EV management;
- retune TP/SL;
- reveal external, reference-validation, August, or SHORT partitions;
- integrate live trading.
