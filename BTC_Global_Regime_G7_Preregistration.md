# BTC Global/Pooled Regime Engine — G7 Preregistration

**Status: PREREGISTERED BEFORE G7 EXECUTION — research only; live BBC untouched.**

## Why G7 exists
G6 showed that the 168h slow regime-health state ranks Tuesday quality meaningfully, but a hard WAIT rule discards a historically profitable hostile-regime subset. Specifically, the G6 healthy subset had materially stronger expectancy/PF than the hostile subset, while the hostile subset remained positive expectancy.

G7 therefore keeps the validated slow state but changes its role from binary veto to bounded risk sizing.

## Frozen inputs
- G6 exactly-168h weekly health construction unchanged.
- G6 historical Tuesday rows unchanged.
- G6 August weekly-health rows unchanged.
- Frozen A5.11 PnL unchanged.
- No new model.
- No new feature/window/threshold.

## G7 sizing rule — locked before execution
For each eligible Tuesday, G6 already provides:
- `mean_p_sell_168h`
- the corresponding mean causal SELL baseline over those same 168 historical hourly states.

Define:

`WEEKLY_SELL_LIFT = mean_p_sell_168h / mean_baseline_p_sell_168h`

Position weight:

`WEIGHT = min(1.0, WEEKLY_SELL_LIFT)`

Therefore:
- weekly SELL environment at/above causal base rate => 1.0x baseline size;
- weekly SELL environment below base rate => proportional de-risking;
- never increase above baseline exposure;
- no minimum floor;
- no fitted coefficient;
- every eligible Tuesday remains a trade.

Reference baseline remains the existing $500 notional research convention; weighted PnL scales linearly as frozen A5.11 PnL × WEIGHT.

## Historical comparison — locked
Use exactly the same eligible Tuesday subset as G6 (expected 125 opportunities).

Compare:
1. Always A5.11 at 1.0x.
2. G5 point-in-time risk governor (context only; not used for selection).
3. G7 weekly-health governor.

Primary G7 report:
- mean/median/min/max weight,
- total exposure units,
- exposure ratio,
- total PnL,
- PnL per exposure unit,
- max drawdown,
- PnL/maxDD,
- four chronological blocks.

WR is reported but not an acceptance criterion because positive weights preserve trade signs.

## G7 shadow-candidate acceptance gate — locked
All must pass:

1. At least **120** eligible opportunities.
2. Mean weight < 1.0 (nontrivial de-risking).
3. PnL per gross exposure unit > baseline.
4. Max drawdown < baseline.
5. PnL/maxDD > baseline.
6. Total weighted PnL remains positive.
7. Exposure-normalized PnL efficiency improves in at least **3 of 4** chronological blocks.

There is no requirement for lower-risk total PnL to exceed the full-size baseline.

Passing means **risk-governor shadow candidate only**, never automatic live sizing.

## August 2026 — report only
Use the frozen G6 August weekly states and apply the exact same weight rule. Report weighted PnL for Aug 4/11/18 and total loss reduction. August is excluded from the acceptance gate.

## Explicitly prohibited
- alternative lookback windows,
- minimum weight floors,
- nonlinear/odds sizing,
- leverage above baseline,
- threshold sweeps,
- model changes,
- A5.11 changes,
- August-driven changes,
- touching live BBC.

If G7 fails, preserve it. Any next step must change the hypothesis rather than tune this sizing formula.
