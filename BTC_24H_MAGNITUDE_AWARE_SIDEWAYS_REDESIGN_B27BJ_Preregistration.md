# B27BJ — BTC 24H Magnitude-Aware SIDEWAYS Redesign Audit — Preregistration

## Purpose

Test one minimal redesign of the existing causal 4H regime detector before any directional trading, entry, stop, target, fee, WR, PF, or PnL research.

B27BH showed that the current SIDEWAYS label mixes same-direction pauses and genuine opposite-direction transitions. B27BI showed that simple binary clause counts are insufficient, while continuous first-SIDEWAYS-bar magnitude features contain descriptive information. B27BJ tests whether that information survives a development-only fit and out-of-sample evaluation.

This experiment does **not** change BULL/BEAR raw detector semantics and does **not** modify live BBC.

## Frozen data / chronology

- Reuse the exact 698,112-row BTC 5m research dataset and the exact B27BG/B27BH/B27BI partitions.
- Regime source remains completed 4H bars only; a state/feature is usable only after its source 4H bar completes.
- Reproduce the B27BI episode identity before any result is accepted:
  - 1,023 complete directionally bracketed SIDEWAYS episodes;
  - 527 RESUME and 496 TRANSITION;
  - BULL-origin 532, BEAR-origin 491.
- `development` is the **only** fitting partition.
- `external` and `reference_validation` are out-of-sample evaluation partitions and may not influence coefficients, scaling, threshold, feature selection, or model choice.
- `august` is diagnostic only because sample size is expected to be small.

## Frozen labels

At the first completed 4H bar labeled SIDEWAYS after a raw directional state:

- `RESUME = 1`: the complete SIDEWAYS episode later exits to the same directional state as its origin.
- `TRANSITION = 0`: the complete SIDEWAYS episode later exits to the opposite directional state.

Future outcome is used **only as the supervised historical label**. All predictor inputs must be known at the first SIDEWAYS bar's causal availability timestamp.

## Frozen predictor set

Use only these six B27BI preregistered continuous causal features; no additions/removals after seeing B27BJ results:

1. `dir_ema_spread_atr`
2. `dir_close_ema20_atr`
3. `dir_ema7_slope_atr`
4. `dir_ema20_slope_atr`
5. `dir_body_atr`
6. `bar_range_atr`

Do **not** use episode duration, exit state, future returns, clock/session labels, trade outcomes, liquidity outcomes, or any future bar.

## Frozen model

Fit **two separate deterministic logistic regressions**, one for BULL-origin and one for BEAR-origin, using only `development` episodes of that origin.

- Standardize each feature using development-partition mean and population standard deviation (`ddof=0`) for the same origin.
- Logistic regression: L2 penalty, `C=1.0`, `solver='lbfgs'`, max_iter=1000, no class weights, intercept enabled.
- No cross-validation.
- No hyperparameter sweep.
- No feature selection.
- No calibration pass.
- Frozen classification threshold: `P(RESUME) >= 0.50` => predicted `RESUME`; otherwise predicted `TRANSITION`.

The intent is to avoid hand-picking ATR thresholds from B27BI descriptive medians.

## Frozen redesigned state-machine rule

Raw BULL/BEAR/SIDEWAYS generation remains unchanged.

Only on the **first raw SIDEWAYS bar immediately following raw BULL or raw BEAR**:

- if the frozen origin-specific model predicts `RESUME`, expose the origin directional state for **that one completed 4H interval only** and tag it `INHERITED_PAUSE`;
- if the model predicts `TRANSITION`, expose raw `SIDEWAYS` immediately;
- if raw SIDEWAYS persists into a second consecutive 4H interval, that second interval is exposed as `SIDEWAYS` regardless of the first prediction;
- raw BULL or BEAR bars are never relabeled by B27BJ;
- no recursive inheritance and no multi-bar hysteresis.

This one-bar rule is intentionally minimal: B27BJ tests whether a causal magnitude-aware filter can remove temporary one-bar SIDEWAYS flicker without silently converting long SIDEWAYS episodes into directional regimes.

## Mandatory outputs

### A. Identity / causality audit

- B27BI episode counts reproduced exactly.
- no feature timestamp later than the first SIDEWAYS availability timestamp.
- no OOS sample used in scaler/model fitting.

### B. Classifier metrics

For BULL-origin and BEAR-origin separately, report for development, external, reference_validation, pooled OOS (`external + reference_validation`), and august diagnostic:

- N;
- actual RESUME rate;
- predicted RESUME rate;
- ROC AUC where defined;
- balanced accuracy;
- sensitivity / RESUME recall;
- specificity / TRANSITION recall;
- Brier score.

Also persist frozen development means/stds, coefficients, and intercepts.

### C. Redesigned detector metrics

Rebuild the complete causal 4H state sequence and report raw versus redesigned:

- interval occupancy by state/partition;
- state-change count;
- one-interval `A->B->A` flip-back numerator, denominator, and rate using the exact B27BG accounting;
- BULL and BEAR next-state persistence;
- direct BULL<->BEAR change share;
- maximum occupancy drift across major partitions;
- number of `INHERITED_PAUSE` intervals.

### D. Delay/error accounting

For complete bracketed episodes, report by origin and partition:

- true RESUME predicted RESUME;
- true RESUME predicted TRANSITION;
- true TRANSITION predicted RESUME (a one-bar / 4h delayed exposure of SIDEWAYS);
- true TRANSITION predicted TRANSITION.

No economic interpretation is permitted.

## Frozen promotion gate

Call the redesign `B27BJ_MAGNITUDE_AWARE_RED​​ESIGN_SUPPORTED` only if **all** of the following hold:

1. identity and causality assertions PASS;
2. for **each origin separately**, ROC AUC is >= 0.60 in both `external` and `reference_validation`;
3. for each origin, pooled-OOS balanced accuracy >= 0.57;
4. for each origin, pooled-OOS TRANSITION recall (specificity) >= 0.55, so the rule does not hide most genuine transitions;
5. redesigned pooled-major one-interval flip-back rate is < the raw B27BG 20.8% rate and <= 18.0%;
6. redesigned BULL and BEAR next-state persistence remain >= 60% in every major partition;
7. redesigned maximum state-occupancy drift across major partitions is <= the raw B27BG 20.5pp drift (must not worsen it).

If any gate fails, verdict is `B27BJ_MAGNITUDE_AWARE_REDESIGN_NOT_SUPPORTED`. No threshold, feature, model, or state rule may be changed inside B27BJ after seeing results.

## Prohibitions

- No LONG/SHORT mapping.
- No entry/stop/TP/runner/fee/WR/PF/PnL.
- No session or clock optimization.
- No feature engineering after the run.
- No hand-tuned ATR threshold.
- No live BBC modification.
- A failed B27BJ must lead to a new experiment ID for any redesign.
