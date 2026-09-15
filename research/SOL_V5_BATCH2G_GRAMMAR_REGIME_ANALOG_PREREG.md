# SOL V5 Batch 2G — Grammar-Conditioned Causal Regime Analog PREREG

## Objective
Batch 2F showed that exact 4-token structural grammar is informative but not stable by itself. The clearest case was `U-U-U-U`: positive OOS economics in 2022, near-flat in 2023, and negative in 2024.

Batch 2G tests one architecture change only:

> When the exact grammar is held fixed, can the current causal market regime identify whether that grammar is occurring in a continuation-like versus exhaustion-like context?

This is not a grammar search and not a new dense sequence classifier. The exact Batch 2F grammar is frozen, and each test episode is compared only with historical episodes carrying the same grammar.

## Research boundary
- SOLUSDT Futures 5m.
- Same frozen V4 `HIGH_STATE` detector and Batch 1 episode-start definition.
- Research/development years: 2020–2024.
- Nested OOS test years: 2022, 2023, 2024.
- `2025+ reference_validation` remains CLOSED.
- LONG only.

## Frozen structural grammar
Use the exact Batch 2F terminal grammar:
- 24 completed 5m bars immediately before HIGH_STATE onset;
- transition alphabet `U/D/O/I/F` exactly as Batch 2F;
- motif = final **4 tokens**;
- no grammar-length, token-definition, support, hour, or direction sweep.

## Frozen grammar eligibility
Before regime conditioning, a grammar must pass the unchanged Batch 2F training-only rule:
1. training support `N >= 30`;
2. Batch 2F shrunk fixed +60m mean net return `> 0`;
3. Batch 2F shrunk `UP_FIRST` rate `> global training UP_FIRST rate`.

Prior strength remains **40 observations**, unchanged from Batch 2F.

## Causal regime vector
For each HIGH_STATE episode, construct exactly six pre-entry context dimensions, all already observable at the final completed 5m bar before entry:

1. `ret_60_sigma = ret_60 / sigma60_pct` — recent directional stretch relative to trailing volatility;
2. `eff_60` — directional efficiency over the preceding 60m;
3. `compression_range_30_120 = range_30 / range_120` — how much of the 120m structural range is concentrated in the latest 30m;
4. `compression_rv_30_120 = rv_30 / rv_120` — recent realized-volatility activation versus the broader 120m state;
5. `close_pos_120` — current close location within the preceding 120m high-low range;
6. `state_margin = pred_impulse - state_cutoff` — strength of the frozen V4 precursor-state activation.

No hour/day/session, EMA, VWAP, Fib, RSI, future path, TP, SL, or post-entry information is used.

## Training-only scaling
Within each walk-forward fold, each regime dimension is robust-scaled using the training episodes only:
- center = training median;
- scale = training IQR (`Q75-Q25`);
- if IQR is effectively zero, scale = 1.

The same frozen training center/scale is applied to that fold's test year.

## Same-grammar causal analog
For each test HIGH_STATE episode:
1. require its exact grammar to be Batch-2F eligible using training data only;
2. restrict the historical candidate pool to training episodes with the **same exact grammar**;
3. compute Euclidean distance in the six-dimensional robust-scaled causal regime vector;
4. take the **30 nearest historical same-grammar episodes**;
5. estimate:
   - local analog mean fixed +60m net return;
   - local analog `UP_FIRST` rate;
   - local analog profit factor;
   - mean and median neighbor distance.

`K = 30` is frozen and equals the existing Batch 2F minimum grammar support. No K sweep is allowed.

## Frozen LONG selection rule
A test episode is selected LONG only if all are true:
1. its grammar is Batch-2F eligible in that fold;
2. at least 30 same-grammar historical episodes exist;
3. local 30-neighbor mean fixed +60m net return is **> 0**;
4. local 30-neighbor `UP_FIRST` rate is **greater than the full training rate of that same grammar**.

This makes the regime layer a genuine within-grammar filter: it must identify a historically stronger context than the grammar's own average, not merely inherit the grammar prior.

No score percentile, model probability threshold, top-k trade selection, or post-hoc rescue is allowed.

## Nested walk-forward
Use the unchanged causal fold structure:
- test 2022 from training episodes in 2021;
- test 2023 from 2021–2022;
- test 2024 from 2022–2023.

All neighbor outcomes are fully known before the corresponding test year begins.

## Execution diagnostic
For selected episodes:
- LONG at frozen HIGH_STATE `anchor_price` / onset;
- fixed exit at +60m close;
- round-trip cost = 0.15%;
- reference notional = $500;
- no TP, SL, trailing, scaling, or exit optimization.

## Required comparisons
For each year and pooled 2022–2024 report:
1. **ALL HIGH_STATE** baseline;
2. **GRAMMAR_ONLY** = Batch-2F eligible grammar without regime filter;
3. **GRAMMAR_REGIME** = same eligible grammar plus Batch-2G same-grammar analog filter.

Also report exact-grammar transfer for `U-U-U-U` and every grammar that actually trades after regime filtering.

## Outputs
- all OOS assignments with grammar and analog diagnostics;
- Batch-2F training grammar dictionary per fold;
- selected regime-filtered trades;
- pooled comparison table;
- yearly comparison table;
- grammar × year transfer audit;
- neighbor-distance / analog audit;
- gate audit;
- frozen verdict.

## Frozen PASS gates
All must pass:
1. regime-filtered OOS selected `N >= 100`;
2. pooled regime-filtered `UP_FIRST` lift >= **1.20x** versus ALL HIGH_STATE;
3. pooled fixed +60m net expectancy **> 0**;
4. pooled fixed +60m PF >= **1.10**;
5. positive regime-filtered PnL in at least **2 of 3** test years;
6. regime-filtered pooled expectancy must exceed GRAMMAR_ONLY pooled expectancy;
7. **2024 regime-filtered expectancy > 0** with at least **30 selected trades**.

Gate 7 is deliberately explicit because Batch 2G exists to test whether causal regime context can prevent the 2024 collapse seen in Batch 2F rather than merely re-harvest 2022–2023.

## Stop rule
If Batch 2G fails, do not rescue it on 2022–2024 by sweeping K, context dimensions, distance metric, scaling method, grammar length, support, prior strength, hours, holding horizon, TP, or SL. A failure means the frozen six-dimensional same-grammar regime analog is not sufficient for a ready-to-trade LONG selector. A new revision must introduce a new structural hypothesis, not parameter tuning.
