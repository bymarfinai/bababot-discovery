# B27ET — BNB MICRO_HL_BULL Loss Anatomy Preregistration

## Purpose
Diagnose why the current development economics leader loses. This milestone is descriptive only: it must not add, tune, or promote a new entry filter.

## Frozen trading setup
- Partition: `development` only, 2022-01-01 through 2025-01-01.
- Entry: frozen B27EO `E5_MICRO_HL_BULL`.
- TP: `H + 0.30R`.
- SL: `entry - 0.30R`.
- Cost: 0.10% round-trip fee + 0.05% slippage = 0.15% total.
- TP/SL active from the 5m entry bar.
- If TP and SL touch on the same 5m bar, SL wins.
- If neither is hit by NY close, exit at session close.

## Integrity expected from B27ES
- 50 trades.
- 19 TP exits, 20 SL exits, 11 session-close exits.
- 25 net winners and 25 net losers.
- No same-bar collisions for this frozen cell.

## Causal pre-entry diagnostics
Measured using information available no later than the entry open:
- entry depth in R;
- leave-to-entry minutes and pre-entry bar count;
- minutes from NY open to entry and minutes remaining to NY close;
- session reference-range percentage (`R/H`);
- signal-bar range/body/body-ratio/close-position normalized by R where applicable;
- signal low depth from H;
- previous-bar low depth from H;
- micro higher-low lift (`signal low - previous low`) / R;
- micro close lift (`signal close - previous close`) / R;
- deepest excursion from H between leave and signal bar;
- maximum close-depth from H between leave and signal bar.

Winner/loss separation is descriptive. For each feature report winner and loser medians/IQR plus common-language effect size (probability a random loss value is greater than a random winner value). No cutoff is selected.

## Post-entry failure anatomy
For every net loser report:
- exit type and time-to-exit;
- MFE/MAE before exit;
- whether H, H+0.10R, or H+0.20R was reached before exit;
- maximum progress toward the frozen H+0.30R target;
- whether a gross-positive session-close result was flipped negative only by costs.

Loss paths are classified only by fixed structural landmarks, not optimized thresholds:
1. `SL_BEFORE_H` — hard stop before ever reaching H.
2. `SL_AFTER_H_BEFORE_H10` — reached H, not H+0.10R, then stopped.
3. `SL_AFTER_H10_BEFORE_H20` — reached H+0.10R, not H+0.20R, then stopped.
4. `SL_AFTER_H20_BEFORE_TP` — reached H+0.20R, missed H+0.30R, then stopped.
5. `CLOSE_LOSS_BEFORE_H` — session close net loss without reaching H.
6. `CLOSE_LOSS_AFTER_H` — session close net loss after reaching H but missing TP.
7. `COST_FLIP_CLOSE` — session-close gross return > 0 but net return <= 0 after the frozen 0.15% cost.

## Hard stop
No filter selection, no TP/SL retuning, no alternative E5 definition, no external/reference/August reveal, no SHORT/live integration.