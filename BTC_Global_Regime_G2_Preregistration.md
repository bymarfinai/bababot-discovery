# BTC Global/Pooled Regime Engine — G2 Preregistration

**Status: PREREGISTERED BEFORE G2 EXECUTION — research only; live BBC untouched.**

## Motivation
G1 established that the pooled regime model has causal pseudo-OOS predictive skill, but the first Tuesday overlay used an unnecessarily strict policy:

- `SELL_COMPATIBLE` => TRADE
- `BUY_COMPATIBLE` => WAIT
- `NEUTRAL` => WAIT

That policy passed the pooled model gate but failed the Tuesday economic promotion gate because it removed too many opportunities.

G2 does **not** change the model. It tests the semantic architecture originally intended for the system: the temporal prior owns neutral states; the pooled regime layer only vetoes an explicitly conflicting state.

## Frozen inputs
- G0 labels/features unchanged.
- G1 pooled model unchanged.
- G1 monthly embargoed walk-forward predictions unchanged.
- Tuesday A5.11 execution/management unchanged.
- No probability threshold is introduced.
- No model refit or feature change is allowed.

## G2 policy — locked before execution
For the frozen Tuesday 06:00 WIB SELL temporal prior:

- predicted `SELL_COMPATIBLE` => **TRADE**
- predicted `NEUTRAL` => **TRADE**
- predicted `BUY_COMPATIBLE` => **WAIT**

In words: **only explicit directional conflict can veto the temporal prior.**

This is a deterministic class policy. It does not use confidence thresholds, probability margins, position sizing, or A5.11 outcomes to choose the action.

## Historical evaluation — locked
Use exactly the same 126 causal Tuesday opportunities already scored by G1.

Compare three policies on the exact same opportunity stream:
1. Frozen A5.11 always trade.
2. G1 hard compatibility gate: trade only `SELL_COMPATIBLE`.
3. G2 conflict-only veto: wait only `BUY_COMPATIBLE`.

Report for each:
- opportunities,
- trades / waits / coverage,
- trade WR,
- PnL,
- expectancy per opportunity,
- expectancy per trade,
- PF,
- max drawdown.

Also report outcome attribution by G1 predicted class (`SELL_COMPATIBLE`, `NEUTRAL`, `BUY_COMPATIBLE`) so the result is explainable.

## Four chronological Tuesday blocks
Split the same 126 opportunities into four consecutive blocks exactly as in G1 and report G2 PnL delta versus always-trade in each block.

## G2 shadow-promotion gate — locked
G2 becomes a Tuesday **shadow candidate** only if all conditions pass:

1. Coverage >= **35%**.
2. Expectancy per opportunity is strictly higher than always-trade A5.11.
3. Total PnL is at least equal to always-trade A5.11.
4. Trade WR is strictly higher than always-trade A5.11.
5. PnL delta vs always-trade is positive in at least **3 of 4** chronological blocks.

No condition may be changed after the result.

## August 2026 — report only
Apply the exact same deterministic G2 mapping to the already-frozen G1 predictions for Aug 4, Aug 11, Aug 18.

- no August refit,
- no August threshold tuning,
- report G2 TRADE/WAIT and realized frozen A5.11 PnL,
- August is diagnostic only and does not select G2.

## Explicitly prohibited
- changing G1 probabilities or class predictions,
- probability threshold sweeps,
- confidence-margin sweeps,
- half-risk or variable sizing inside G2,
- retuning A5.11,
- using August to change the mapping,
- touching live BBC.

If G2 fails, the result is kept. Any sizing or confidence-governor idea must be preregistered as a separate later experiment.
