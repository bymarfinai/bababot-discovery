# BTC Global/Pooled Regime Engine — G5 Preregistration

**Status: PREREGISTERED BEFORE G5 EXECUTION — research only; live BBC untouched.**

## Why G5 exists
G1 demonstrated genuine but modest pooled pseudo-OOS regime skill. G1/G2/G3 showed that converting that signal into a binary TRADE/WAIT rule destroys too much positive Tuesday expectancy. G4 showed that frozen A5.11 itself is not a profitable all-hours strategy and its pooled hourly WIN label is not predictably learnable with the locked simple model.

G5 therefore tests the remaining role that is statistically and economically consistent with the evidence:

> use the causal pooled regime signal as a **risk/conviction governor**, not as an entry gate.

Every Tuesday temporal opportunity remains a trade. The global regime layer may only reduce exposure when current SELL compatibility is below its own causal historical base rate. It may never increase exposure above the frozen baseline size.

## Frozen inputs
- G1 embargoed monthly pooled predictions unchanged.
- G1 `p_sell` unchanged.
- G1 causal monthly `baseline_p_sell` unchanged.
- Frozen Tuesday A5.11 PnL stream unchanged.
- No new model.
- No threshold sweep.
- No A5.11 tuning.

## G5 sizing rule — locked before execution
For each causal Tuesday opportunity:

`SELL_LIFT = p_sell / baseline_p_sell`

Position weight:

`WEIGHT = min(1.0, SELL_LIFT)`

Therefore:
- if current pooled SELL compatibility is at or above its causal training base rate, use **1.0x baseline size**;
- if it is below base rate, reduce size proportionally;
- weight is never negative and never above 1.0;
- there is no minimum floor and no fitted scaling coefficient.

Reference exposure:
- baseline A5.11 uses the existing $500 reference notional ($10 margin at 50x in the established research convention);
- G5 effective notional is `$500 × WEIGHT`;
- because A5.11 PnL and fee convention scale linearly with notional, G5 realized PnL is `frozen_A5.11_PnL × WEIGHT`.

This test does not claim exchange position sizing granularity or live implementation yet.

## Historical comparison — locked
Use exactly the same 126 causal Tuesday opportunities scored by G1.

Compare:
1. Always-trade A5.11 at 1.0x size.
2. G5 risk-governed A5.11 using the locked weight above.

Report:
- number of opportunities (both remain 126),
- mean / median / min / max weight,
- total gross exposure units (`sum(weight)` versus baseline `N`),
- exposure ratio,
- total PnL,
- PnL per gross exposure unit,
- max drawdown,
- PnL / max drawdown,
- chronological four-block metrics.

WR is reported but is not an acceptance criterion because positive weights do not change trade signs.

## G5 shadow-candidate acceptance gate — locked
G5 becomes eligible as a **risk-governor shadow candidate** only if all pass:

1. **De-risking is nontrivial:** mean weight < 1.0.
2. **Capital efficiency improves:** G5 PnL per gross exposure unit > baseline PnL per exposure unit.
3. **Drawdown improves:** G5 max drawdown < baseline max drawdown.
4. **Risk-adjusted profitability improves:** G5 PnL / max drawdown > baseline PnL / max drawdown.
5. **Absolute profitability remains positive:** G5 total PnL > 0.
6. **Chronological robustness:** exposure-normalized PnL efficiency improves versus baseline in at least 3 of 4 chronological blocks.

There is deliberately **no requirement that lower-risk G5 total PnL exceed the 1.0x baseline total PnL**, because that would force a risk reducer to manufacture leverage. The comparison instead requires better capital efficiency and better drawdown at lower or equal exposure.

Passing means SHADOW CANDIDATE only. It does not authorize live sizing.

## August 2026 — report only
Use the already-frozen final G1 probabilities and frozen historical SELL prior from the Jul-30 cutoff.

For Aug 4/11/18:
- compute the same `WEIGHT = min(1, p_sell / baseline_p_sell)`,
- multiply frozen A5.11 PnL by the weight,
- report loss reduction / retention.

August does not enter the G5 acceptance gate and cannot change the sizing rule.

## Explicitly prohibited
- testing alternative floors or caps,
- odds-ratio sizing,
- square-root / nonlinear sizing,
- leverage above 1.0x baseline,
- threshold sweeps,
- new model fitting,
- changing G1 predictions,
- changing A5.11,
- using August to select the rule,
- touching live BBC.

If G5 fails, keep the result. Any slow-regime-health, rolling-window, or alternative risk-budget concept must be a separately preregistered experiment.
