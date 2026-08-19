# BTC Global/Pooled Regime Engine — G1 Preregistration

**Status: PREREGISTERED BEFORE G1 EXECUTION — research only; live BBC untouched.**

G0 passed its locked dataset/label gate with 23,304 eligible hourly states. G1 asks the real question: can the locked future-defined regime label be predicted **causally before entry**, using only the locked G0 market-state features?

This document freezes G1 before model results are generated. No model, threshold, feature, or acceptance rule below may be changed after results are seen and still be called G1.

## Frozen inputs from G0
- Instrument: BTCUSDT Binance Futures.
- Decision cadence: every clock hour, minute 00.
- Historical G0 window: 2023-12-02 00:00 UTC to 2026-07-30 00:00 UTC exclusive.
- Label horizon: 6 hours.
- Label barrier: symmetric 0.50% first-passage.
- Classes: `SELL_COMPATIBLE`, `BUY_COMPATIBLE`, `NEUTRAL`.
- Same-5m-bar dual barrier touch: `NEUTRAL`.
- Feature set: exactly the 17 locked G0 market-only features; no calendar features and no feature selection.
- Tuesday A5.11 remains frozen and is not used as a model-training target.

## G1 primary model — locked
A deliberately simple pooled regime classifier:

- median imputation fit on training data only,
- standardization fit on training data only,
- L2 multinomial logistic regression,
- `C = 1.0`,
- `solver = lbfgs`,
- no class weighting,
- no feature selection,
- no hyperparameter sweep,
- hard regime prediction = class with maximum predicted probability (`argmax`).

The model predicts the 3-class **G0 regime label**, not trade PnL.

## Causal expanding walk-forward — locked
### Warmup
- First scored prediction month: **March 2024**.
- December 2023 through February 2024 acts as initial training history.

### Monthly frozen models
For each calendar prediction month `M`:
1. Define `month_start`.
2. Train only on G0 rows whose complete 6h label horizon is known by that time:
   `decision_t + 6h <= month_start`.
3. Fit one model once.
4. Freeze it for the entire prediction month.
5. Predict all eligible G0 states inside that month.

This creates an explicit 6h outcome embargo and prevents future labels from leaking into the current month.

The final historical scored period ends at the existing G0 cutoff on 2026-07-30.

## Locked no-skill baseline
For every monthly prediction batch, calculate the class frequencies in that batch's training set only.

The baseline probability forecast for every row in the month is that training-only class-prior vector. The baseline hard class is the largest training prior.

Therefore G1 must beat an expanding causal no-skill baseline, not a full-sample constant guessed after seeing results.

## Primary pooled metrics
Report at minimum:
- number of scored pseudo-OOS states,
- overall accuracy,
- balanced accuracy,
- macro F1,
- multiclass log loss,
- multiclass Brier score,
- SELL-vs-rest ROC AUC using `p(SELL_COMPATIBLE)`,
- confusion matrix,
- predicted-class coverage,
- actual class rate inside each predicted class.

Also report the same metrics for the expanding class-prior baseline where applicable.

## Four chronological robustness blocks
Split the complete G1 pseudo-OOS prediction stream into four consecutive blocks of approximately equal row count. For each block report model vs prior-baseline log loss and Brier score.

No block is allowed to alter the model specification.

## G1 pooled-model acceptance gate — locked
The pooled model is considered to have useful pre-entry regime information only if **all** conditions pass:

1. **Coverage:** at least **18,000** pseudo-OOS hourly predictions.
2. **Causal embargo:** every prediction batch trains only on rows with `decision_t + 6h <= month_start`.
3. **Log-loss skill:** pooled model log loss is strictly lower than the causal class-prior baseline.
4. **Brier skill:** pooled model multiclass Brier is strictly lower than the causal class-prior baseline.
5. **SELL discrimination:** SELL-vs-rest ROC AUC is at least **0.55**.
6. **SELL enrichment:** among rows hard-predicted `SELL_COMPATIBLE`, the realized SELL_COMPATIBLE rate is at least **3 percentage points higher** than the unconditional realized SELL_COMPATIBLE rate in the scored G1 stream.
7. **Nontrivial SELL coverage:** hard-predicted `SELL_COMPATIBLE` covers at least **20%** of scored states.
8. **Chronological robustness:** model log loss beats the causal prior baseline in at least **3 of 4** chronological blocks.

If this gate fails, G1 does not switch to XGBoost, tune C, add features, change class weights, or optimize probability thresholds. A failure is information.

## Frozen Tuesday overlay — secondary but predeclared
Only after the pooled walk-forward predictions are complete, map predictions onto eligible frozen Tuesday 06:00 WIB A5.11 opportunities.

For every Tuesday whose timestamp has a causal G1 prediction:
- `TRADE` iff hard predicted regime = `SELL_COMPATIBLE`.
- `WAIT` iff predicted `BUY_COMPATIBLE` or `NEUTRAL`.
- no probability threshold tuning.
- execution/outcome remains frozen A5.11.

Compare on the exact same eligible Tuesday subset:
- Always-trade A5.11.
- G1 regime-gated A5.11.

Report:
- opportunities,
- trades / waits / coverage,
- trade WR,
- total PnL,
- expectancy per opportunity,
- expectancy per trade,
- PF,
- max drawdown,
- four chronological Tuesday blocks.

### Tuesday overlay promotion gate — locked
The pooled regime layer is eligible to become a **Tuesday shadow candidate** only if all conditions pass:

1. Tuesday gate coverage is at least **35%** of eligible Tuesday opportunities.
2. Gated expectancy **per opportunity** is strictly higher than always-trade A5.11 on the same subset.
3. Gated total PnL is at least equal to always-trade A5.11 on the same subset.
4. Gated trade WR is strictly higher than always-trade A5.11 on the same subset.
5. Gated PnL delta vs always-trade is positive in at least **3 of 4** chronological Tuesday blocks.

This gate is intentionally economic: improving WR by deleting profitable trades is not sufficient.

Passing this gate still means **SHADOW CANDIDATE**, not live promotion.

## August batch holdout — locked report-only diagnostic
After the historical walk-forward and Tuesday overlay are fully scored:

- fit one final G1 model using only historical G0 rows through the Jul-30 cutoff,
- score the three already-known post-cutoff Tuesday opportunities: Aug 4, Aug 11, Aug 18, 2026,
- freeze that same model across all three; no August outcome refit,
- report predicted probabilities, hard regime, TRADE/WAIT, realized G0 regime label, and frozen A5.11 PnL.

August does **not** select the model or modify any G1 gate. It is a diagnostic because these dates have already received extensive research attention.

## Explicitly prohibited in G1
- XGBoost, Random Forest, neural nets.
- hyperparameter sweeps.
- threshold sweeps.
- feature selection.
- calendar/day/hour features.
- Tuesday win/loss as the training target.
- fitting on August outcomes.
- changing G0 labels after seeing G1 performance.
- changing A5.11.
- touching live BBC.

## Interpretation hierarchy
1. First ask whether the **global pooled market state is predictably classifiable** pseudo-OOS.
2. Then ask whether that independent state information improves **Tuesday A5.11 economics**.
3. Then inspect August only as a report-only stress case.

A good August skip with weak historical pooled skill is not enough. A good pooled classifier that damages Tuesday expectancy is not enough for Tuesday gating. Both layers must earn their role separately.
