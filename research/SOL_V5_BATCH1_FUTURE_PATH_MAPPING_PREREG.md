# SOL V5 Batch 1 — Future Path Mapping Preregistration

## Purpose
Characterize the future path that follows the already-frozen SOL V4 precursor state detector. This batch does **not** optimize or authorize an entry, TP, SL, trailing rule, or time stop.

## Frozen state detector
- Reuse `sol_impulse_precursor_discovery_v4.py` exactly for feature construction, matched training, model class, rolling two-year training window, and `pred_impulse` score.
- Test years remain 2021, 2022, 2023, 2024 only.
- 2025+ `reference_validation` remains CLOSED.
- No V4 feature, impulse label, model hyperparameter, or matching rule may be changed in Batch 1.

## Causal HIGH_STATE definition
For each test year:
1. Fit the frozen V4 model using only the frozen prior training window and matched training sample.
2. Score the full prior training opportunity set with that fitted model.
3. Freeze the HIGH_STATE cutoff at the prior-training 90th percentile of `pred_impulse`.
4. Apply that numeric cutoff unchanged to the following test year.

The test-year score distribution is not used to decide HIGH_STATE. Test-year score deciles may be reported for descriptive ranking only.

## Future-path observation anchor
- Observation anchor price = next 5-minute bar open after V4 signal time. This is a normalization anchor, **not** an authorized trade entry.
- Observe only paths fully known before `2025-01-01 UTC`.
- Horizons: +5, +10, +15, +20, +30, +45, +60, +90, +120 minutes.

For every OOS opportunity map:
- close return at each horizon;
- MFE at each horizon using future bar highs;
- MAE at each horizon using future bar lows;
- time-to-MFE and time-to-MAE over +120m;
- first touch of the frozen V4 upside impulse distance;
- first touch of the symmetric downside distance;
- which barrier occurs first (`UP_FIRST`, `DOWN_FIRST`, `BOTH_SAME_BAR`, `NONE`);
- MAE experienced before the first upside impulse touch.

The barrier distance is the already-frozen V4 `impulse_threshold_pct = max(0.75%, 1.5 * prior-24h sigma60)` calculated at the signal. It is a diagnostic barrier, not a TP or SL.

## Batch 1C timing archetypes
Use only the first upside diagnostic-barrier time:
- `EARLY_UP`: <=30m
- `MID_UP`: 35–60m
- `LATE_UP`: 65–120m
- `NO_UP_120`: no upside barrier touch within 120m

No archetype thresholds will be changed after observing results.

## Primary Batch 1 decision
This is a characterization decision, not a trading PASS.

`USEFUL_FOR_BATCH2` requires all of:
- at least 5,000 OOS HIGH_STATE observations;
- HIGH_STATE upside-barrier hit rate by +120m is at least 1.20x INACTIVE;
- HIGH_STATE `UP_FIRST` rate is at least 1.20x INACTIVE;
- HIGH_STATE upside-barrier hit rate exceeds INACTIVE in at least 3 of 4 OOS years;
- HIGH_STATE `UP_FIRST` rate exceeds INACTIVE in at least 3 of 4 OOS years.

Otherwise verdict is `NO_STABLE_PATH_ENRICHMENT`.

MFE/MAE asymmetry, timing, score-to-excursion correlation, and archetype frequencies are descriptive and will inform Batch 2 activation design. They are not used to retune Batch 1.

## Anti-overfit / stop rules
- No threshold sweep.
- No alternate V4 model.
- No hour filter.
- No regime filter beyond what V4 already uses.
- No TP/SL search.
- No opening 2025+.
- If Batch 1 fails, do not rescue it by changing the HIGH_STATE percentile or diagnostic barrier on this same OOS sample.
