# BTC Pre-D1 Good Cascade B24A — Preregistration

## Purpose
Test whether the B21 cascades that later become the successful Daily-bull cohort can be identified causally before Daily bull is known.

## Core question
At the first causal 4H-bull activation in an ordered B21 cascade, while Daily bull is still OFF, can already-observable multi-timeframe state geometry distinguish events that will later become a Daily-bull cascade with positive 72h return from events that will not?

This experiment is specifically designed to avoid treating the old 77.9% B21 hindsight cohort as a live-entry accuracy claim.

## Data and partitions
Reuse frozen B21 BTCUSDT data and partitions:
- External: 2020-01-01 to 2022-01-01
- Development: 2022-01-01 to 2025-01-01
- Reference validation: 2025-01-01 to 2026-07-30
- August: 2026-08-01 to 2026-08-21

Source resolution is 5m, resampled causally exactly as B21. No future candle values may be used in features.

## Event universe
Use every ordered B21 cascade that has causally reached the 4H stage (`stage_index >= 3`).

Anchor time = the first ordered 4H bull activation (`on_4h`).

Exclude an event from the causal detector if Daily bull is already ON at that exact anchor time. The detector must operate before Daily confirmation.

## Frozen B21 bull state
For each timeframe:
`SMA7 > SMA25 > SMA99 AND close > SMA25`.

## Primary target
`GOOD_D1_72H = 1` only if BOTH are eventually true:
1. the ordered cascade subsequently reaches Daily bull within the frozen B21 propagation window; and
2. the frozen B21 72h return from the original 5m seed is positive.

Otherwise `GOOD_D1_72H = 0`.

This target is evaluated across ALL eligible 4H-stage events. Therefore the live detector is not allowed to assume beforehand that Daily will eventually turn bull.

## Secondary forensic cohort
For transparency only, separately report the old B21 Daily-stage cohort (`stage_index == 4`) and compare its positive vs non-positive members. This secondary view is NOT a tradable performance claim because membership in that cohort is known only later.

## Features — state only, no candle-count persistence rule
Features are measured strictly at the 4H anchor from the latest completed candles available then.

For 15m, 1H, 4H, and 1D:
- normalized fast MA gap: `(SMA7 - SMA25) / close`
- normalized slow MA gap: `(SMA25 - SMA99) / close`
- normalized price position: `(close - SMA25) / close`
- current frozen B21 bull flag

No feature may use:
- future Daily confirmation,
- future return/MFE/MAE,
- number of candles the regime later survives,
- future propagation time,
- post-anchor data.

## Detector
Use one fixed interpretable logistic-regression detector.

Training set: External + Development eligible events only.
Test set: Reference Validation only.
August is descriptive only.

Pipeline:
- median-impute training-feature missing values;
- standardize using training mean/std only;
- logistic regression with L2 penalty, `C=1.0`, `class_weight='balanced'`, `max_iter=5000`, fixed random_state=23.

No hyperparameter search and no feature selection after seeing validation.

## Frozen reporting
On reference validation report:
- eligible 4H events;
- number and prevalence of `GOOD_D1_72H`;
- ROC AUC and average precision;
- precision and recall in the top 5%, 10%, 20%, and 30% of detector scores;
- how many successful events are captured in each bucket;
- baseline success prevalence for comparison.

Secondary Daily-cohort report:
- total Daily-stage events;
- positive vs non-positive counts;
- score distribution/AUC within that hindsight cohort, clearly labeled forensic only.

## Gates
`B24A_USEFUL_PRE_D1_DETECTOR = PASS` only if on untouched reference validation ALL are true:
1. ROC AUC >= 0.65;
2. average precision >= 1.50x baseline prevalence;
3. top-20% precision >= 1.50x baseline prevalence;
4. top-20% captures at least 30% of all `GOOD_D1_72H` events.

`B24A_HIGH_PRECISION_CLUE = PASS` only if top-10% precision >= 2.0x baseline prevalence AND top-10% captures at least 20% of all `GOOD_D1_72H` events.

Otherwise FAIL. No positive framing if gates fail.

Research only. No live BBC changes.
