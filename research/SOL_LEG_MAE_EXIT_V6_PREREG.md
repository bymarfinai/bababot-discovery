# SOL Leg MAE / Exit Geometry V6 — Preregistration

## Motivation
V4/V5 showed that broad derivatives states can overlap 80–90% of real L2/L3/L5 long legs and often hit them early, yet TP2/3/5 with a fixed 1% stop remains loss-making. A plausible mechanical explanation is that valid multi-percent SOL legs commonly experience >1% adverse excursion before reaching their target.

V6 tests that explanation directly before declaring the state useless as an entry context.

## Frozen parent states
Only two V4 states are carried forward:
1. NEW_LONG_BUILD — highest and most stable leg-hit / early-hit coverage.
2. ABSORPTION_RELEASE — second high-coverage structural state.

State definitions are unchanged. No new state threshold is introduced.
Signal-event semantics use the V5 OFF->ON rising edge of each parent state. V5 proved this is execution-equivalent to V4 under SL1, while providing a clean episode-start object for MAE measurement.

## Execution
- completed 15m signal, next 15m open
- one active position
- 0.15% RT cost
- USD500 notional
- same-5m TP+SL ambiguity = loss
- causal derivatives joins unchanged

## Targets and preregistered SL grids
All configurations satisfy TP>=1% and reward:risk >=1:1.

L2 TP +2%:
- SL 1.00%, 1.25%, 1.50%, 2.00%

L3 TP +3%:
- SL 1.00%, 1.25%, 1.50%, 2.00%, 2.50%, 3.00%

L5 TP +5%:
- SL 1.00%, 1.50%, 2.00%, 2.50%, 3.00%, 4.00%, 5.00%

Hold horizons unchanged:
- L2 24h
- L3 48h
- L5 72h

## MAE forensic
For every raw parent-state signal, ignore stop for the forensic label and ask whether target is eventually touched within the target horizon.
For target-eventual-hit signals, measure maximum adverse excursion from next-15m-open entry BEFORE the first target touch.

Report MAE quantiles p25/p50/p75/p90 by state, target, and year.

This is diagnostic only and does not define a trading result.

## SL selection
For each parent state × target:
- select ONE SL width using 2024 only;
- eligible 2024 SL must have positive after-cost expectancy;
- rank eligible SL by highest mean weekly return, then expectancy, then WR;
- if no SL is positive in 2024, report the frontier but mark no eligible configuration.

Freeze selected SL and transfer unchanged to 2025 and 2026.

2023 is reported as historical reference but is not used for SL selection.

## Success gate
Promising only if frozen selected SL has:
- positive expectancy in 2024, 2025, and 2026;
- weighted 2025+2026 expectancy >0;
- >=1 executed trade/week in 2024 and 2025;
- selected RR >=1 by construction.

No 2025/2026 rescue.
