# SOL V5 Batch 2B — Remaining Edge Predictor — PREREG

## Purpose
Batch 2B keeps the frozen V4 HIGH_STATE detector and the Batch 2 post-state checkpoint framework, but changes the question from pure direction classification to **remaining tradable edge**. The objective is to avoid entering after most of the favorable move has already occurred.

## Frozen upstream components
- Pair: SOLUSDT 5m.
- 2025+ reference_validation remains CLOSED.
- V4 state detector, HIGH_STATE definition, episode collapsing, and Batch 2 activation checkpoint construction remain unchanged.
- Research/development universe is 2020-2024; final untouched validation remains 2025+.
- No TP/SL optimization is allowed in Batch 2B.

## Nested walk-forward
Evaluation uses 2022, 2023, 2024 only.
- test 2022: train remaining-edge models on eligible OOS checkpoint rows from 2021.
- test 2023: train on 2021-2022.
- test 2024: rolling train on 2022-2023.
All targets for a training checkpoint must be fully known before the test year begins.

## Checkpoints and execution
- checkpoints: +5, +10, +15, +20, +25, +30 minutes after HIGH_STATE episode start.
- checkpoint must still be eligible under the frozen Batch 2 rule: neither state-anchored upside nor downside diagnostic barrier has been reached.
- prediction uses information through checkpoint close only.
- candidate execution price = next 5m open.
- at most one entry per state episode: earliest checkpoint that passes the frozen entry-utility gate.

## Targets from candidate execution price
For every eligible checkpoint, map the future path from the candidate next-open execution price through the remaining state horizon, capped at +120 minutes from state start.
Targets:
1. `remaining_mfe_pct`: maximum favorable excursion from candidate entry.
2. `remaining_mae_abs_pct`: absolute maximum adverse excursion from candidate entry.
3. `remaining_net60_pct`: fixed +60m return after candidate entry minus 0.15% roundtrip cost when 60m is available before MODEL_END; diagnostic only.
4. frozen state target `UP_FIRST` remains available as the directional target.

## Models
Use the frozen Batch 2 feature set.
- Direction model: same ExtraTreesClassifier architecture as Batch 2.
- MFE model: ExtraTreesRegressor, 320 trees, max_depth=8, min_samples_leaf=20, max_features=sqrt, random_state=52, n_jobs=-1.
- MAE model: same regressor architecture, random_state=53.
Models train only on prior OOS checkpoint rows.

## Entry utility
For each checkpoint:
- `p_up` = predicted P(UP_FIRST).
- `pred_mfe` = predicted remaining MFE %.
- `pred_mae` = predicted absolute remaining MAE %.
- `pred_edge = p_up * pred_mfe - (1-p_up) * pred_mae - 0.15`.

This is a ranking/selection utility, not a claim of an exact expected-return distribution.

## Frozen causal entry gate
For each test year, derive cutoffs from that year's training predictions only:
- direction cutoff = 70th percentile of training `p_up`.
- edge cutoff = 70th percentile of training `pred_edge`.
Candidate checkpoint qualifies only when BOTH `p_up >= direction_cutoff` AND `pred_edge >= edge_cutoff` AND `pred_edge > 0`.
Entry is the earliest qualifying checkpoint. No percentile sweep is allowed after OOS results are observed.

## Diagnostics
Compare Batch 2B entries against:
1. all HIGH_STATE episode starts in the same test years;
2. immediate-state entry on the same selected episodes.
Report:
- N, trigger time, UP_FIRST precision;
- actual remaining MFE/MAE and MFE/|MAE| ratio;
- fixed +60m net WR/expectancy/PF (diagnostic, not an exit optimization);
- Spearman(pred_edge, realized remaining net60) where available;
- year stability.

## Promotion gates to Batch 2C
`READY_FOR_BATCH2C` requires all:
1. selected entries N >= 250;
2. selected UP_FIRST rate >= 55%;
3. selected UP_FIRST beats HIGH_STATE episode baseline in at least 2 of 3 years;
4. pooled actual MFE/|MAE| ratio improves by >= 15% versus all HIGH_STATE episode starts;
5. paired fixed +60m expectancy is not worse than immediate-state entry by more than 0.10 percentage point;
6. Spearman(pred_edge, realized remaining net60) > 0.

Failure means do not rescue the rule by optimizing TP/SL on the same OOS sample.
