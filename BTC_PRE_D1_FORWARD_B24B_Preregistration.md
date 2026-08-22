# BTC Pre-D1 Forward B24B — Preregistration

## Why B24B exists
B24A used the frozen B21 72h return measured from the original 5m seed. Because the detector decision is made later at the first ordered 4H-bull activation, part of that 72h outcome may already have happened by detector time. B24A is therefore retained as forensic classification only and must not be presented as a fair trading-forward result.

B24B corrects the outcome clock.

## Question
At the first causal ordered 4H-bull activation, while Daily bull is still OFF, can already-visible multi-timeframe SMA state geometry identify events that subsequently reach Daily bull and produce positive return over the NEXT 72 hours from the 4H decision time?

## Event universe
Same as B24A: every ordered B21 cascade that has reached 4H (`stage_index >= 3`). Anchor = first ordered `on_4h`. Exclude if Daily bull is already ON at the anchor.

## Features
Exactly the frozen B24A feature set, measured only from completed information available at the 4H anchor:
For 15m, 1H, 4H, 1D:
- `(SMA7-SMA25)/close`
- `(SMA25-SMA99)/close`
- `(close-SMA25)/close`
- current B21 bull flag

No candle-persistence counts and no post-anchor features.

## Corrected forward outcome
Entry/reference price = BTCUSDT open at the 4H anchor timestamp, immediately after the completed 4H candle made the state observable.

Forward return = close of the last completed 5m bar before `anchor + 72h` divided by anchor entry price minus 1.

Primary label:
`GOOD_D1_FWD72 = 1` only if BOTH:
1. the ordered cascade subsequently reaches Daily bull within the frozen B21 7-day propagation window; and
2. the NEXT-72h return from the 4H anchor is positive.

Otherwise 0.

Also report future-72h positive rate inside the eventual Daily cohort, but label it as cohort analysis rather than live selection accuracy.

## Training/test
Same frozen model and split as B24A:
- Train: External + Development
- Untouched test: Reference Validation
- August descriptive only
- median imputation, standardization, L2 logistic regression C=1.0, balanced classes, max_iter=5000, random_state=23
- no hyperparameter search and no validation feature selection.

## Reporting
Reference validation:
- eligible events
- GOOD_D1_FWD72 count and baseline prevalence
- AUC and average precision
- top 5/10/20/30% score bucket precision, recall, and lift
- eventual-Daily cohort: future-positive vs future-non-positive counts

## Gates
Same standards as B24A:
`B24B_USEFUL_PRE_D1_FORWARD_DETECTOR = PASS` only if:
1. AUC >= 0.65
2. average precision >= 1.50x baseline
3. top-20% precision >= 1.50x baseline
4. top-20% recall >= 30%

`B24B_HIGH_PRECISION_CLUE = PASS` only if top-10% precision >= 2.0x baseline and top-10% recall >= 20%.

If gates fail, result is FAIL. B24A must not be used to override B24B.

Research only; live BBC unchanged.
