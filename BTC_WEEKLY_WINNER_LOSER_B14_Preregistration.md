# BTC Weekly Winner-vs-Loser Fingerprint B14 — Preregistration

## Question
Across causal BTCUSDT H1 next-open entries, what observable pre-entry state differentiates a net +1% winner from a net -1% loser, and which differences remain stable out of sample?

This is a diagnostic/fingerprint study first. It does not assume support/resistance is the correct primitive and does not use future information in features.

## Data / partitions
- Binance USD-M BTCUSDT 1H official klines via existing repository loader.
- External: complete ISO weeks in 2020-01-01 <= week < 2022-01-01.
- Development: complete ISO weeks in 2022-01-01 <= week < 2025-01-01.
- Reference validation: complete ISO weeks in 2025-01-01 <= week < 2026-07-30.
- August 2026 remains diagnostic only.

## Candidate / execution contract
For every completed H1 bar from Monday 00:00 UTC through Saturday 12:00 UTC of each complete ISO week:
- signal is based only on data available at that completed H1 bar;
- entry is next H1 open;
- evaluate LONG and SHORT as separate candidate-side observations;
- fee = 0.15% round-trip;
- exact net +1.00% TP => favorable price barrier 1.15%;
- exact net -1.00% SL => adverse price barrier 0.85%;
- exit no later than end of same ISO week;
- same-bar TP/SL ambiguity = adverse-first.

Primary winner/loser comparison uses decisive TP vs SL observations. TIME rows are reported separately and excluded from decisive binary effect-size calculations.

## Causal features
All features are computed at signal close, before next-open entry.

### Side-aligned momentum / path
- aligned_ret_1/3/6/12/24/48h
- directional efficiency_3/6/12/24 = side-aligned net move / sum absolute hourly moves
- directional up-fraction equivalents over 3/6/12h
- signed EMA8/21/55 distance aligned to candidate side
- EMA8/21 slope aligned to side

### Compression / expansion
- ATR14 percent
- signal true-range / ATR14
- mean TR 3h / mean TR 24h
- mean TR 6h / mean TR 24h
- rolling 3h/6h/12h range divided by ATR14
- current range vs prior 12h median range

### Candle / immediate reaction
- side-aligned body fraction
- supportive wick fraction (lower for LONG, upper for SHORT)
- opposing wick fraction
- close location in candle aligned to side
- sweep-reclaim of prior 3h and prior 6h extreme in candidate direction
- breakout close beyond prior 3h and prior 6h extreme in candidate direction

### Location / available space
- side-aligned position inside rolling 12h/24h/48h range
- forward space to rolling 12h/24h/48h extreme in ATR
- adverse space to opposite rolling extreme in ATR
- previous-day high/low distances transformed into forward/adverse side space
- previous-week high/low distances transformed into forward/adverse side space

### Week/day state
- week position, side-aligned week return, week range percent
- day position, side-aligned day return, day range percent
- hours into week and hours remaining
- hour/day cyclic controls

## Analysis frozen before results
1. Build all candidate-side observations independently for LONG and SHORT.
2. For each partition report candidate counts, TP/SL/TIME and decisive base WR.
3. On development only, for every feature compute:
   - winner mean/median;
   - loser mean/median;
   - pooled standardized mean difference (SMD);
   - univariate ROC AUC, orientation-free as max(AUC, 1-AUC).
4. Freeze the development top 20 features by |SMD|, tie-break by orientation-free AUC then feature name.
5. Evaluate those same frozen features in external and validation and report SMD sign/magnitude stability.
6. A feature is called `STABLE_DIFFERENTIATOR` only if:
   - development |SMD| >= 0.20;
   - same SMD sign in development, external and validation;
   - external |SMD| >= 0.10;
   - validation |SMD| >= 0.10.
7. Fit one standardized L2 logistic regression on development using only the frozen top-20 features. No hyperparameter tuning: C=1.0, max_iter=2000, class_weight=balanced, random_state=20260821 where applicable.
8. Report untouched external and validation ROC AUC and accuracy. Classifier output is separability diagnostic, not a weekly trading strategy.
9. Create simple development-frozen quantile fingerprints for the strongest stable differentiators: winner-favored direction is inferred on development, and thresholds are development quartiles only. Report OOS TP rates and support; do not retune thresholds after seeing OOS.

## Success interpretation
- Strong evidence of a useful winner fingerprint: >=3 STABLE_DIFFERENTIATOR features and logistic ROC AUC >=0.65 in both external and validation.
- Very strong: ROC AUC >=0.75 in both external and validation.
- This study does NOT pass the user's weekly 100% trading gate by itself. It identifies causal characteristics to feed the next selector experiment.

## Anti-leakage / anti-overfit
- No future-derived feature.
- No feature/threshold selection on external or validation.
- No post-hoc rescue within B14.
- Live BBC untouched.
