# BTC Global/Pooled Regime Engine — G3 Preregistration

**Status: PREREGISTERED BEFORE G3 EXECUTION — research only; live BBC untouched.**

## Motivation
G1 proved the pooled regime model contains causal pseudo-OOS information, but hard `argmax SELL` gating was too selective. G2 showed that vetoing every hard `BUY_COMPATIBLE` state is also too aggressive because the Tuesday temporal prior remains profitable even inside many globally BUY-labeled states.

G3 therefore stops treating the global classifier as a competing directional strategy. It uses the classifier only to answer a narrower question:

> Does the current market state raise or lower SELL compatibility relative to the model's own unconditional causal training base rate?

## Frozen inputs
- G0 dataset/labels/features unchanged.
- G1 monthly embargoed models and probabilities unchanged.
- Tuesday A5.11 unchanged.
- No new model.
- No probability-threshold sweep.
- No feature change.

## G3 Relative SELL Lift policy — locked
For every historical Tuesday opportunity, use two values already produced causally by G1 for that timestamp:

- `p_sell`: G1 model probability of `SELL_COMPATIBLE`.
- `baseline_p_sell`: SELL_COMPATIBLE frequency in that month's **training set only**, i.e. the causal expanding class-prior baseline used by G1.

Define:

`SELL_LIFT = p_sell / baseline_p_sell`

Decision:
- if `p_sell >= baseline_p_sell` (SELL_LIFT >= 1.0) => **TRADE**
- if `p_sell < baseline_p_sell` (SELL_LIFT < 1.0) => **WAIT**

The threshold `1.0` is not fitted to Tuesday outcomes. It is the neutral likelihood-ratio boundary: the pooled market state must make SELL at least as likely as the model's unconditional training base rate.

No BUY/NEUTRAL hard class is used in the decision.

## Historical evaluation — locked
Use the same 126 causal Tuesday opportunities as G1/G2.

Compare:
1. Always-trade frozen A5.11.
2. G1 hard argmax SELL gate.
3. G2 conflict-only veto.
4. G3 relative SELL lift gate.

Report:
- trades/waits/coverage,
- WR,
- PnL,
- expectancy per opportunity,
- expectancy per trade,
- PF,
- max drawdown.

Also report separate outcome attribution for:
- SELL_LIFT >= 1.0,
- SELL_LIFT < 1.0.

## Four chronological blocks
Use the same chronological 4-block partition as G1/G2 and report G3 PnL delta versus always-trade.

## G3 shadow-promotion gate — locked
G3 becomes a Tuesday shadow candidate only if **all** pass:

1. Coverage >= **35%**.
2. Expectancy per opportunity strictly higher than always-trade A5.11.
3. Total PnL at least equal to always-trade A5.11.
4. Trade WR strictly higher than always-trade A5.11.
5. PnL delta versus always-trade positive in at least **3 of 4** chronological blocks.

No gate may be changed after the result.

## August 2026 — report only
Use the one final G1 model already frozen through the Jul-30 cutoff.

For August, the reference `baseline_p_sell` is the SELL_COMPATIBLE frequency in the frozen G0 historical training set through Jul-30. Apply the same `p_sell >= baseline_p_sell` rule to Aug 4/11/18.

- no August refit,
- no August outcomes in the threshold,
- August is diagnostic only.

## Explicitly prohibited
- optimizing SELL_LIFT threshold,
- testing 0.9 / 1.1 / 1.2 variants inside G3,
- class-specific sizing,
- changing G1 probabilities,
- changing A5.11,
- using August to alter the rule,
- touching live BBC.

If G3 fails, it fails. Any quantile, confidence-margin, sizing, or risk-budget experiment must be separately preregistered.
